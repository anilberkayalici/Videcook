"""Small Groq Whisper transcription client with i18n-aware error messages."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from videcook.core.subtitles import SubtitleSegment

NON_SPEECH_PATTERNS = [
    r"\[(?:laughter|giggle|chuckle|sigh|gasp|groan|screams?|music|applause|cough|snicker|crying|cheering|yelling|silence|throat-clearing)[^\]]*\]",
    r"\((?:laughter|giggle|chuckle|sigh|gasp|groan|screams?|music|applause|cough|snicker|crying|cheering|yelling|gülüşme|kahkaha|müzik|bağırış|sessizlik|gülme|çığlık)[^\)]*\)",
    r"\*(?:laughs?|giggles?|screams?|sighs?|gasps?|chuckles?|kahkaha|gülüşme|güler)\*",
    r"\b(?:hahaha+|hehehe+|ahahah+|hihihi+|hohoho+|ha\s+ha(?:\s+ha)*|he\s+he(?:\s+he)*|a\s+ha\s+ha)\b",
    r"\b(?:kahkaha+|gülüşme+|bağırış+|çığlık+)\b",
]


def clean_non_speech_text(text: str) -> str:
    """Strip out bracketed, parenthesized, asterisked, and explicit laugh/scream sound effect words."""
    for pattern in NON_SPEECH_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    # Collapse leftover punctuation and whitespace
    text = re.sub(r"^[,\.\!\?\-\s]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_verbose_transcription(payload: dict[str, Any]) -> list[SubtitleSegment]:
    """Convert Groq's verbose JSON response into clean subtitle segments aligned strictly to spoken words."""
    result: list[SubtitleSegment] = []
    raw_segments = payload.get("segments", [])
    raw_words = payload.get("words", [])

    for item in raw_segments:
        raw_text = str(item.get("text", "")).strip()
        cleaned_text = clean_non_speech_text(raw_text)
        if not cleaned_text or len(cleaned_text) < 2:
            continue

        start = float(item.get("start", 0))
        end = float(item.get("end", 0))

        # If word timestamps are provided, filter non-speech words and align start time strictly to speech
        if raw_words:
            seg_words = [
                w for w in raw_words
                if float(w.get("start", 0)) >= (start - 0.3) and float(w.get("end", 0)) <= (end + 0.3)
            ]
            valid_words = [
                w for w in seg_words
                if clean_non_speech_text(str(w.get("word", ""))).strip()
            ]
            if valid_words:
                first_word = valid_words[0]
                first_w_text = clean_non_speech_text(str(first_word.get("word", ""))).strip()
                first_w_start = float(first_word.get("start", start))
                first_w_end = float(first_word.get("end", end))

                # If the first word duration is artificially stretched (>1.5s for a short word), trim pre-speech delay
                if (first_w_end - first_w_start) > 1.5 and len(first_w_text) <= 5:
                    first_w_start = max(start, first_w_end - 0.8)

                if first_w_start > start:
                    start = first_w_start

                last_w_end = float(valid_words[-1].get("end", end))
                if last_w_end < end and (end - last_w_end) > 0.4:
                    end = last_w_end

        if end > start and cleaned_text:
            result.append(SubtitleSegment(start=start, end=end, text=cleaned_text))

    return result


class GroqTranscriptionClient:
    """Adapter around Groq's official Python SDK transcription endpoint."""

    model = "whisper-large-v3"

    def __init__(
        self,
        api_key: str,
        get_text: Callable[[str], str] | None = None,
        client: Any | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        if not self.api_key:
            raise ValueError("API key must not be empty.")
        self._t = get_text or (lambda key: key)
        self._client = client

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        from groq import Groq

        self._client = Groq(api_key=self.api_key)
        return self._client

    def transcribe(self, audio_path: Path, language: str | None = None) -> list[SubtitleSegment]:
        """Transcribe an audio chunk through Groq and return timestamped text."""
        from groq import APIConnectionError, APIStatusError, RateLimitError

        try:
            with audio_path.open("rb") as audio_file:
                kwargs = {
                    "file": (audio_path.name, audio_file.read()),
                    "model": self.model,
                    "response_format": "verbose_json",
                    "timestamp_granularities": ["segment", "word"],
                    "temperature": 0.0,
                    "prompt": "Clean spoken dialogue subtitles without background noise, laughter or sound effect descriptions.",
                }
                if language:
                    kwargs["language"] = language

                response = self._ensure_client().audio.transcriptions.create(**kwargs)
        except RateLimitError as exc:
            raise RuntimeError(self._t("subtitle.error.rate_limited")) from exc
        except APIConnectionError as exc:
            raise RuntimeError(self._t("subtitle.error.connection_failed")) from exc
        except APIStatusError as exc:
            raise RuntimeError(
                self._t("subtitle.error.api_error").format(
                    status=exc.status_code, detail=exc.message
                )
            ) from exc

        payload = response if isinstance(response, dict) else response.model_dump()
        return parse_verbose_transcription(payload)

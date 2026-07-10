"""Small Groq Whisper transcription client with i18n-aware error messages."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from videcook.core.subtitles import SubtitleSegment


def parse_verbose_transcription(payload: dict[str, Any]) -> list[SubtitleSegment]:
    """Convert Groq's verbose JSON response into safe subtitle segments."""
    result: list[SubtitleSegment] = []
    for item in payload.get("segments", []):
        text = str(item.get("text", "")).strip()
        start = float(item.get("start", 0))
        end = float(item.get("end", 0))
        if text and end > start:
            result.append(SubtitleSegment(start=start, end=end, text=text))
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

    def transcribe(self, audio_path: Path, language: str = "en") -> list[SubtitleSegment]:
        """Transcribe an audio chunk through Groq and return timestamped text."""
        from groq import APIConnectionError, APIStatusError, RateLimitError

        try:
            with audio_path.open("rb") as audio_file:
                response = self._ensure_client().audio.transcriptions.create(
                    file=(audio_path.name, audio_file.read()),
                    model=self.model,
                    language=language,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    temperature=0.0,
                )
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

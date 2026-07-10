"""Small, dependency-free Groq Whisper transcription client."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from groq import APIConnectionError, APIStatusError, Groq, RateLimitError

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

    def __init__(self, api_key: str, client: Any | None = None) -> None:
        self.api_key = api_key.strip()
        if not self.api_key:
            raise ValueError("Groq API key is required.")
        self._client = client or Groq(api_key=self.api_key)

    def transcribe(self, audio_path: Path, language: str = "en") -> list[SubtitleSegment]:
        """Transcribe an audio chunk through Groq and return timestamped text."""
        try:
            with audio_path.open("rb") as audio_file:
                response = self._client.audio.transcriptions.create(
                    file=(audio_path.name, audio_file.read()),
                    model=self.model,
                    language=language,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    temperature=0.0,
                )
        except RateLimitError as exc:
            raise RuntimeError("Groq kullanım kotası doldu. Bir süre sonra tekrar deneyin.") from exc
        except APIConnectionError as exc:
            raise RuntimeError("Groq sunucusuna ulaşılamadı. İnternet bağlantınızı kontrol edin.") from exc
        except APIStatusError as exc:
            raise RuntimeError(f"Groq altyazı isteği başarısız oldu ({exc.status_code}): {exc.message}") from exc

        payload = response if isinstance(response, dict) else response.model_dump()
        return parse_verbose_transcription(payload)

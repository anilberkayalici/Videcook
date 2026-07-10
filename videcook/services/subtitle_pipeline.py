"""FFmpeg-assisted audio chunking and SRT generation."""

from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from videcook.core.subtitles import SubtitleSegment, merge_chunk_segments, render_srt


@dataclass(frozen=True)
class ChunkWindow:
    start: float
    end: float


def build_chunk_windows(
    duration: float, chunk_seconds: float = 600.0, overlap_seconds: float = 1.0
) -> list[ChunkWindow]:
    """Create overlapping windows; a 20 minute file becomes two safe chunks."""
    if duration <= 0:
        raise ValueError("Audio duration must be positive.")
    windows: list[ChunkWindow] = []
    start = 0.0
    while start < duration:
        remaining = duration - start
        end = duration if remaining <= chunk_seconds + overlap_seconds else start + chunk_seconds
        windows.append(ChunkWindow(start=start, end=end))
        if end >= duration:
            break
        start = end - overlap_seconds
    return windows


class SubtitlePipeline:
    """Prepare audio, transcribe each chunk, and write a single SRT file."""

    def __init__(
        self,
        ffmpeg_path: Path,
        ffprobe_path: Path,
        transcriber,
    ) -> None:
        self._ffmpeg_path = ffmpeg_path
        self._ffprobe_path = ffprobe_path
        self._transcriber = transcriber

    def create_srt(
        self,
        source: Path,
        destination: Path,
        on_progress: Callable[[int, str], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> None:
        if not source.is_file():
            raise FileNotFoundError(f"Ses dosyası bulunamadı: {source}")
        with tempfile.TemporaryDirectory(prefix="videcook_subtitles_") as temp_dir:
            temp = Path(temp_dir)
            normalized = temp / "normalized.ogg"
            self._run(
                [
                    str(self._ffmpeg_path), "-y", "-i", str(source), "-vn", "-ar", "16000",
                    "-ac", "1", "-c:a", "libopus", "-b:a", "32k", str(normalized),
                ]
            )
            duration = self._duration(normalized)
            windows = build_chunk_windows(duration)
            merged: list[SubtitleSegment] = []
            for index, window in enumerate(windows, start=1):
                if is_cancelled and is_cancelled():
                    raise RuntimeError("İşlem kullanıcı tarafından iptal edildi.")
                chunk = temp / f"chunk_{index}.ogg"
                self._run(
                    [
                        str(self._ffmpeg_path), "-y", "-ss", str(window.start), "-t",
                        str(window.end - window.start), "-i", str(normalized), "-c", "copy", str(chunk),
                    ]
                )
                if on_progress:
                    on_progress(round((index - 1) / len(windows) * 100), f"Parça {index}/{len(windows)} işleniyor")
                shifted = [
                    SubtitleSegment(segment.start + window.start, segment.end + window.start, segment.text)
                    for segment in self._transcriber.transcribe(chunk, language="en")
                ]
                merged = merge_chunk_segments(merged, shifted)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(render_srt(merged), encoding="utf-8")
            if on_progress:
                on_progress(100, "Altyazı hazır")

    def _duration(self, audio_path: Path) -> float:
        result = subprocess.run(
            [str(self._ffprobe_path), "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("Ses dosyasının süresi okunamadı.")
        return float(result.stdout.strip())

    @staticmethod
    def _run(args: list[str]) -> None:
        result = subprocess.run(args, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "FFmpeg ses dosyasını işleyemedi.")

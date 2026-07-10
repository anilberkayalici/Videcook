"""Subtitle segment utilities and SRT rendering."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubtitleSegment:
    """One timed line returned by a transcription provider."""

    start: float
    end: float
    text: str


def format_srt_timestamp(seconds: float) -> str:
    """Format seconds as the timestamp syntax required by SRT."""
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def merge_chunk_segments(
    existing: list[SubtitleSegment], incoming: list[SubtitleSegment]
) -> list[SubtitleSegment]:
    """Append a chunk while removing its repeated overlap line."""
    merged = list(existing)
    for segment in incoming:
        normalized = " ".join(segment.text.lower().split())
        if merged:
            previous = merged[-1]
            previous_normalized = " ".join(previous.text.lower().split())
            if normalized == previous_normalized and segment.start <= previous.end + 2:
                continue
        merged.append(segment)
    return merged


def render_srt(segments: list[SubtitleSegment]) -> str:
    """Render ordered segments as a standard UTF-8 SRT document."""
    lines: list[str] = []
    for index, segment in enumerate(sorted(segments, key=lambda item: item.start), start=1):
        if not segment.text.strip() or segment.end <= segment.start:
            continue
        lines.extend(
            [
                str(index),
                f"{format_srt_timestamp(segment.start)} --> {format_srt_timestamp(segment.end)}",
                segment.text.strip(),
                "",
            ]
        )
    return "\n".join(lines)

"""SRT subtitle formatter — converts .srt files to a custom plain-text
dubbing format.

Ported from the TypeScript Çeviri-Uygulaması. The pipeline is:

    parse_srt → normalize_cues → detect_sequence_markers →
    format_subtitles → stringify_formatted_lines

No external dependencies (stdlib only). Qt-free and fully testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Configuration (matches shared/config/subtitleFormat.ts)
# ---------------------------------------------------------------------------

OUTPUT_SEPARATOR = " - "
UNKNOWN_SPEAKER_PLACEHOLDER = "(Karakter İsmi)"
DIALOGUE_BLOCK_SEPARATOR = "\n\n"
SEQUENCE_BLOCK_SEPARATOR = "\n\n\n"

OPENING_TERMS = {"opening", "op", "açılış", "acilis", "intro"}
ENDING_TERMS = {"ending", "ed", "kapanış", "kapanis", "outro"}
GENERIC_MARKER_TERMS = {"jenerik", "credits"}

SEQUENCE_MARKER_CONFIG = {
    "min_gap_ms": 75_000,
    "max_gap_ms": 150_000,
    "opening": {
        "min_previous_cue_count": 2,
        "max_marker_start_ms": 4 * 60 * 1_000,
    },
    "ending": {
        "min_progress_ratio": 0.82,
    },
}

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

NoticeSeverity = Literal["info", "warning", "error"]
MarkerHint = Literal["opening", "ending", "generic"] | None
LineKind = Literal["dialogue", "sequence"]


@dataclass
class ParseIssue:
    block_number: int
    severity: Literal["warning", "error"]
    message: str
    raw_block: str = ""


@dataclass
class SubtitleCue:
    block_number: int
    sequence: int | None
    start_ms: int
    end_ms: int
    text_lines: list[str]
    raw_block: str = ""


@dataclass
class ParsedSubtitle:
    cues: list[SubtitleCue] = field(default_factory=list)
    issues: list[ParseIssue] = field(default_factory=list)


@dataclass
class NormalizedCue:
    block_number: int
    sequence: int | None
    start_ms: int
    end_ms: int
    text: str
    text_lines: list[str]
    speakers: list[str]
    is_parenthetical: bool
    marker_hint: MarkerHint = None


@dataclass
class FormattedLine:
    block_number: int
    kind: LineKind
    text: str


@dataclass
class SequenceMarker:
    block_number: int
    label: Literal["Opening", "Ending"]
    start_ms: int
    end_ms: int


@dataclass
class ConversionResult:
    file_name: str
    encoding: str
    lines: list[FormattedLine]
    output: str
    notices: list  # list[ConversionNotice]


# ---------------------------------------------------------------------------
# Parser — matches parser/parseSrt.ts
# ---------------------------------------------------------------------------

_TIMECODE_RE = re.compile(
    r"^\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})(?:\s+.*)?$"
)


def _parse_timestamp(parts: tuple[str, ...], offset: int) -> int:
    h = int(parts[offset])
    m = int(parts[offset + 1])
    s = int(parts[offset + 2])
    ms = int(parts[offset + 3])
    return ((h * 60 + m) * 60 + s) * 1000 + ms


def parse_srt(content: str) -> ParsedSubtitle:
    """Parse raw .srt text into structured cues and issues."""
    normalized = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ParsedSubtitle(
            cues=[],
            issues=[
                ParseIssue(
                    block_number=1,
                    severity="error",
                    message="Dosya boş görünüyor.",
                    raw_block="",
                )
            ],
        )

    blocks = re.split(r"\n{2,}", normalized)
    cues: list[SubtitleCue] = []
    issues: list[ParseIssue] = []

    for index, raw_block in enumerate(blocks):
        block_number = index + 1
        lines = [ln.rstrip() for ln in raw_block.split("\n") if ln.strip()]
        if not lines:
            continue

        has_sequence = bool(re.match(r"^\d+$", lines[0] or ""))
        sequence = int(lines[0]) if has_sequence else None
        time_line = lines[1] if has_sequence else lines[0]

        if time_line is None:
            issues.append(
                ParseIssue(
                    block_number=block_number,
                    severity="warning",
                    message=f"{block_number}. blok atlandı: zaman satırı eksik.",
                    raw_block=raw_block,
                )
            )
            continue

        match = _TIMECODE_RE.match(time_line)
        if not match:
            issues.append(
                ParseIssue(
                    block_number=block_number,
                    severity="warning",
                    message=f"{block_number}. blok atlandı: zaman satırı okunamadı.",
                    raw_block=raw_block,
                )
            )
            continue

        parts = match.groups()
        start_ms = _parse_timestamp(parts, 0)
        end_ms = _parse_timestamp(parts, 4)

        if end_ms < start_ms:
            issues.append(
                ParseIssue(
                    block_number=block_number,
                    severity="warning",
                    message=f"{block_number}. blok atlandı: bitiş zamanı başlangıçtan küçük.",
                    raw_block=raw_block,
                )
            )
            continue

        text_lines = [ln.strip() for ln in lines[2 if has_sequence else 1:]]
        if not text_lines:
            issues.append(
                ParseIssue(
                    block_number=block_number,
                    severity="warning",
                    message=f"{block_number}. blok atlandı: metin içeriği boş.",
                    raw_block=raw_block,
                )
            )
            continue

        cues.append(
            SubtitleCue(
                block_number=block_number,
                sequence=sequence,
                start_ms=start_ms,
                end_ms=end_ms,
                text_lines=text_lines,
                raw_block=raw_block,
            )
        )

    return ParsedSubtitle(cues=cues, issues=issues)


# ---------------------------------------------------------------------------
# Normalizer — matches normalizer/normalizeCues.ts
# ---------------------------------------------------------------------------

_SPEAKER_RE = re.compile(
    r"^-?\s*([A-Za-zğüşıöçĞÜŞİÖÇ][A-Za-zğüşıöçĞÜŞİÖÇ\s'.\+\-]{0,40}):\s*(.+)$",
)
_MULTI_SPACE_RE = re.compile(r"[ \u00A0]{2,}")
_TAB_RE = re.compile(r"\t+")


def _clean_line(line: str) -> str:
    s = line.strip()
    s = _TAB_RE.sub(" ", s)
    s = _MULTI_SPACE_RE.sub(" ", s)
    return s


def _uniq(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for v in values:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result


def _split_speakers(label: str) -> list[str]:
    return [p.strip() for p in re.split(r"\s*\+\s*", label) if p.strip()]


def _match_speaker(line: str) -> dict | None:
    m = _SPEAKER_RE.match(line)
    if not m:
        return None
    speaker_label = m.group(1).strip()
    text = m.group(2).strip()
    if not text or _has_sentence_punctuation(speaker_label):
        return None
    return {"speaker_label": speaker_label, "text": text}


def _has_sentence_punctuation(s: str) -> bool:
    return any(ch in s for ch in ".?!")


def _extract_speakers(text_lines: list[str]) -> tuple[list[str], str]:
    matches = [_match_speaker(ln) for ln in text_lines]
    if any(m is None for m in matches):
        return [], " ".join(text_lines)

    safe_matches = [m for m in matches if m is not None]
    unique_labels = _uniq([m["speaker_label"] for m in safe_matches])
    unique_texts = _uniq([m["text"] for m in safe_matches])

    if len(unique_labels) == 1:
        return _split_speakers(unique_labels[0]), " ".join(
            m["text"] for m in safe_matches
        )
    if len(unique_texts) == 1:
        return _uniq(
            sum((_split_speakers(m["speaker_label"]) for m in safe_matches), [])
        ), unique_texts[0]

    return [], " ".join(text_lines)


def _detect_marker_hint(text: str) -> MarkerHint:
    normalized = text.strip().lower()
    normalized = "".join(
        ch for ch in normalized if ch.isalpha()
    )  # simplified Turkish lower
    if normalized in OPENING_TERMS:
        return "opening"
    if normalized in ENDING_TERMS:
        return "ending"
    if normalized in GENERIC_MARKER_TERMS:
        return "generic"
    return None


# matches normalizer/normalizeSentenceStarts.ts
def _normalize_sentence_starts(text: str) -> str:
    """Normalize Turkish sentence starts — capitalise first letter after `. ! ?`"""
    trimmed = text.strip()
    if not trimmed or re.match(r"^\(.+\)$", trimmed):
        return text
    chars = list(text)
    should_upper = True
    for i, ch in enumerate(chars):
        if should_upper and ch.isalpha():
            chars[i] = ch.upper()  # Python upper() works for Turkish if locale is tr
            should_upper = False
            continue
        if ch in ".!?":
            should_upper = True
            continue
        if not ch.isspace() and ch != "." and should_upper:
            should_upper = False
    return "".join(chars)


def normalize_cues(cues: list[SubtitleCue]) -> list[NormalizedCue]:
    """Clean text lines, extract speakers, detect markers, normalise case."""
    result: list[NormalizedCue] = []
    for cue in cues:
        text_lines = [ln for ln in (_clean_line(ln) for ln in cue.text_lines) if ln]
        speakers, raw_text = _extract_speakers(text_lines)
        raw_text = raw_text.strip()
        marker_hint = _detect_marker_hint(raw_text)
        text = (
            raw_text
            if marker_hint in ("opening", "ending")
            else _normalize_sentence_starts(raw_text)
        )
        result.append(
            NormalizedCue(
                block_number=cue.block_number,
                sequence=cue.sequence,
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                text=text,
                text_lines=text_lines,
                speakers=speakers,
                is_parenthetical=bool(re.match(r"^\(.+\)$", text)),
                marker_hint=marker_hint,
            )
        )
    return result


# ---------------------------------------------------------------------------
# Sequence marker detection — matches detectSequenceMarkers.ts
# ---------------------------------------------------------------------------


def detect_sequence_markers(cues: list[NormalizedCue]) -> list[SequenceMarker]:
    """Detect Opening and Ending markers based on silence gaps and position."""
    if not cues:
        return []
    markers: list[SequenceMarker] = []
    total_duration_ms = cues[-1].end_ms
    opening_added = False
    ending_added = False

    for index, cue in enumerate(cues):
        if cue.marker_hint == "opening":
            markers.append(
                SequenceMarker(
                    block_number=cue.block_number,
                    label="Opening",
                    start_ms=cue.start_ms,
                    end_ms=cue.end_ms,
                )
            )
            opening_added = True
            continue
        if cue.marker_hint == "ending":
            markers.append(
                SequenceMarker(
                    block_number=cue.block_number,
                    label="Ending",
                    start_ms=cue.start_ms,
                    end_ms=cue.end_ms,
                )
            )
            ending_added = True
            continue
        if index == 0:
            continue

        previous_cue = cues[index - 1]
        silence_gap_ms = cue.start_ms - previous_cue.end_ms

        if not (
            SEQUENCE_MARKER_CONFIG["min_gap_ms"]
            <= silence_gap_ms
            <= SEQUENCE_MARKER_CONFIG["max_gap_ms"]
        ):
            continue

        marker_start_ms = previous_cue.start_ms
        marker_end_ms = cue.start_ms
        progress_ratio = (
            0 if total_duration_ms == 0 else cue.start_ms / total_duration_ms
        )

        if (
            not opening_added
            and index >= SEQUENCE_MARKER_CONFIG["opening"]["min_previous_cue_count"]
            and marker_start_ms <= SEQUENCE_MARKER_CONFIG["opening"]["max_marker_start_ms"]
        ):
            markers.append(
                SequenceMarker(
                    block_number=cue.block_number,
                    label="Opening",
                    start_ms=marker_start_ms,
                    end_ms=marker_end_ms,
                )
            )
            opening_added = True
            continue

        if (
            not ending_added
            and progress_ratio >= SEQUENCE_MARKER_CONFIG["ending"]["min_progress_ratio"]
        ):
            markers.append(
                SequenceMarker(
                    block_number=cue.block_number,
                    label="Ending",
                    start_ms=marker_start_ms,
                    end_ms=marker_end_ms,
                )
            )
            ending_added = True

    return markers


# ---------------------------------------------------------------------------
# Formatter — matches formatter/formatSubtitles.ts
# ---------------------------------------------------------------------------


def _format_timestamp(milliseconds: int) -> str:
    total_seconds = milliseconds // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}.{seconds:02d}"


def _format_speaker_label(speakers: list[str]) -> str:
    return f"({' + '.join(speakers)})"


def _format_range_line(start_ms: int, end_ms: int, label: str) -> str:
    return f"{_format_timestamp(start_ms)}{OUTPUT_SEPARATOR}{_format_timestamp(end_ms)}{OUTPUT_SEPARATOR}{label}"


def _format_cue(cue: NormalizedCue) -> FormattedLine:
    if cue.marker_hint == "opening":
        return FormattedLine(
            block_number=cue.block_number,
            kind="sequence",
            text=_format_range_line(cue.start_ms, cue.end_ms, "Opening"),
        )
    if cue.marker_hint == "ending":
        return FormattedLine(
            block_number=cue.block_number,
            kind="sequence",
            text=_format_range_line(cue.start_ms, cue.end_ms, "Ending"),
        )

    start = _format_timestamp(cue.start_ms)
    speaker_label = (
        _format_speaker_label(cue.speakers)
        if cue.speakers
        else UNKNOWN_SPEAKER_PLACEHOLDER
    )
    parts = [start, speaker_label, cue.text]
    return FormattedLine(
        block_number=cue.block_number,
        kind="dialogue",
        text=OUTPUT_SEPARATOR.join(parts),
    )


def format_subtitles(cues: list[NormalizedCue]) -> list[FormattedLine]:
    """Build the final formatted line list, inserting sequence markers."""
    markers_by_block: dict[int, SequenceMarker] = {}
    for marker in detect_sequence_markers(cues):
        if marker.start_ms < marker.end_ms:
            markers_by_block[marker.block_number] = marker

    lines: list[FormattedLine] = []
    for cue in cues:
        marker = markers_by_block.get(cue.block_number)
        if marker and cue.marker_hint is None:
            lines.append(
                FormattedLine(
                    block_number=cue.block_number,
                    kind="sequence",
                    text=_format_range_line(
                        marker.start_ms, marker.end_ms, marker.label
                    ),
                )
            )
        lines.append(_format_cue(cue))

    return lines


def stringify_formatted_lines(lines: list[FormattedLine]) -> str:
    """Join formatted lines with appropriate separators."""
    if not lines:
        return ""

    parts = [lines[0].text]
    for i in range(1, len(lines)):
        prev_kind = lines[i - 1].kind
        curr_kind = lines[i].kind
        sep = (
            SEQUENCE_BLOCK_SEPARATOR
            if prev_kind == "sequence" or curr_kind == "sequence"
            else DIALOGUE_BLOCK_SEPARATOR
        )
        parts.append(sep + lines[i].text)

    # Separators are already embedded in the parts; join without an
    # extra delimiter.
    return "".join(parts)


# ---------------------------------------------------------------------------
# Top-level API
# ---------------------------------------------------------------------------


def convert_srt(content: str, file_name: str = "unknown.srt", encoding: str = "utf-8") -> ConversionResult:
    """Run the full SRT → formatted text pipeline.

    Returns a ``ConversionResult`` with the formatted output and any
    parse/recovery notices. Raises ``ValueError`` when no cues can be
    parsed or the output is empty.
    """
    parsed = parse_srt(content)
    notices: list = []
    for issue in parsed.issues:
        notices.append(
            {"severity": issue.severity, "code": "parse_recovery", "message": issue.message}
        )

    if not parsed.cues:
        raise ValueError(
            "Dönüştürme tamamlanamadı: "
            "Geçerli altyazı bloğu bulunamadı. Dosyayı kontrol edip tekrar deneyin."
        )

    normalized = normalize_cues(parsed.cues)
    lines = format_subtitles(normalized)
    output = stringify_formatted_lines(lines)

    if not output.strip():
        raise ValueError(
            "Dönüştürme sonucu boş kaldı. "
            "Kaynak dosyada işlenebilir satır bulunamadı."
        )

    return ConversionResult(
        file_name=file_name,
        encoding=encoding,
        lines=lines,
        output=output,
        notices=notices,
    )


def build_export_filename(source_name: str) -> str:
    """Return ``<original>_formatted.txt``."""
    normalized = source_name.strip()
    idx = normalized.rfind(".")
    base = normalized[:idx] if idx > 0 else normalized
    return f"{base}_formatted.txt"

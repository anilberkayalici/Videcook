"""Translation File Parser — Parses .md, .txt, and .srt dubbing/translation scripts into SubtitleSegments."""

from __future__ import annotations

import re
from pathlib import Path

from videcook.core.subtitles import SubtitleSegment


def parse_timestamp_to_seconds(ts_str: str) -> float:
    """Convert timestamps like '01:23.45', '01.23', '01:23:45', '00:01:23,456' to float seconds."""
    ts_str = ts_str.strip().replace(",", ".")
    # Handle MM.SS format (like 01.35 meaning 1 min 35 sec)
    if re.match(r"^\d{1,2}\.\d{2}$", ts_str):
        parts = ts_str.split(".")
        return int(parts[0]) * 60 + int(parts[1])

    parts = ts_str.split(":")
    if len(parts) == 3:
        # HH:MM:SS.mmm
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        # MM:SS.mmm
        return int(parts[0]) * 60 + float(parts[1])
        try:
            return float(ts_str)
        except ValueError:
            return 0.0


FORBIDDEN_STAGE_WORDS = [
    r"\b(?:nara|naralar|bağırış|çığlık|gülüşme|gülme|kahkaha|sessizlik|müzik|alkış|fısıltı|iç\s+çekiş|içini\s+çeker)\b",
]


def clean_dialogue_line(text: str) -> str:
    """Clean markdown artifacts, backslashes, dashes, character tags, stage directions, and sound effects."""
    if not text:
        return ""
    text = text.strip()

    # 0. Strip leading timestamp prefix if present
    text = re.sub(r"^\d{1,2}[:\.]\d{2}(?:[:\.]\d{2,3})?\s*[\-\:]*\s*", "", text).strip()

    # 1. Remove markdown escaped characters like `\-`, `\*`, `\_`, `\#`, `\\`
    text = re.sub(r"\\[\-\*\_\#\\]", " ", text)
    text = text.replace("\\", "")

    # 2. Remove all parenthesized, bracketed, and braced tags completely (e.g. `(nara)`, `(bağırış)`, `[laughter]`, `(Glam)`)
    text = re.sub(r"\([^\)]*\)", "", text)
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"\{[^\}]*\}", "", text)

    # 3. Strip table cell character prefixes like '| Dee |'
    text = re.sub(r"^\|?\s*[A-Za-zÇĞİÖŞÜçğıöşü\s]{2,15}\s*\|\s*", "", text)

    # 4. Strip markdown bold/italic/table markers
    text = re.sub(r"[\*\_\|\~]+", " ", text)

    # 5. Strip leading character name prefixes like 'Glam:' or 'Dee - ' or 'Dee |'
    text = re.sub(r"^[A-Za-zÇĞİÖŞÜçğıöşü\s]{2,15}\s*[:\|\-]\s*", "", text).strip()

    # 5. Remove forbidden stage direction words
    for pat in FORBIDDEN_STAGE_WORDS:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)

    # 6. Strip leading and trailing dashes, slashes, colons, pipes, asterisks
    text = re.sub(r"^[\s\-\—\–\/\\\|\*\:\.\,]+", "", text)
    text = re.sub(r"[\s\-\—\–\/\\\|\*\:]+$", "", text)

    # 7. Collapse leftover whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_translation_content(content: str, file_ext: str = ".md") -> list[SubtitleSegment]:
    """Parse text content from .md, .txt, or .srt into SubtitleSegment objects."""
    if not content or not content.strip():
        return []

    ext = file_ext.lower()

    # 1. Try standard SRT parsing if file is .srt or contains SRT timestamp arrows
    if ext == ".srt" or ("-->" in content and re.search(r"\d+\s*\n\d{2}:\d{2}:\d{2}", content)):
        from videcook.core.subtitles import parse_srt
        return parse_srt(content)

    # 2. Parse Markdown tables, bullet lists, or Gecekondu formatted scripts
    lines = content.splitlines()
    raw_entries: list[tuple[float, str]] = []

    # Timestamp regex matching '00:31', '00.31', '01:23:45', etc.
    pattern_time = re.compile(
        r"(?:^|[\s\|\[\(\*])(?P<time>\d{1,2}[:\.]\d{2}(?:[:\.]\d{2,3})?)(?:[\s\]\)\|\-\*]+)"
        r"(?:\((?P<char>[^\)]+)\)[\s\-\:]*|(?P<char2>[^:\-]+)\s*[:\-]\s*)?"
        r"(?P<text>.+)$"
    )

    for line in lines:
        line_s = line.strip()
        if not line_s or line_s.startswith("#") or line_s.startswith("---") or line_s.startswith("| :"):
            continue

        # Check for markdown table rows: | 00:31 | Character | Dialogue |
        if "|" in line_s:
            cells = [c.strip() for c in line_s.split("|") if c.strip()]
            if len(cells) >= 2:
                # Find cell with timestamp
                time_idx = -1
                for idx, cell in enumerate(cells):
                    if re.search(r"\b\d{1,2}[:\.]\d{2}\b", cell):
                        time_idx = idx
                        break
                if time_idx != -1 and time_idx < len(cells) - 1:
                    t_match = re.search(r"\b\d{1,2}[:\.]\d{2}(?:[:\.]\d{2,3})?\b", cells[time_idx])
                    if t_match:
                        t_sec = parse_timestamp_to_seconds(t_match.group(0))
                        # If 3 or more cells (e.g. Time | Character | Text), text is the last cell
                        if len(cells) >= 3 and time_idx == 0:
                            dialogue_raw = cells[-1]
                        else:
                            dialogue_raw = " ".join(cells[time_idx + 1:])
                        dialogue_clean = clean_dialogue_line(dialogue_raw)
                        if dialogue_clean and dialogue_clean not in ["🎵", "...", "---"]:
                            raw_entries.append((t_sec, dialogue_clean))
                            continue

        # Standard line parsing (e.g. '00.31 - (Glam) - Replik' or '[01:23] Replik')
        match = pattern_time.search(line_s)
        if match:
            t_str = match.group("time")
            raw_text = match.group("text")
            dialogue_clean = clean_dialogue_line(raw_text)
            if dialogue_clean and dialogue_clean not in ["🎵", "...", "---"]:
                sec = parse_timestamp_to_seconds(t_str)
                raw_entries.append((sec, dialogue_clean))

    if not raw_entries:
        return []

    # Sort entries chronologically
    raw_entries.sort(key=lambda x: x[0])

    segments: list[SubtitleSegment] = []
    for i, (start_t, txt) in enumerate(raw_entries):
        if i + 1 < len(raw_entries):
            next_t = raw_entries[i + 1][0]
            end_t = min(next_t, start_t + 5.0)
            if end_t <= start_t:
                end_t = start_t + 2.5
        else:
            end_t = start_t + 3.0

        segments.append(SubtitleSegment(start=start_t, end=end_t, text=txt))

    return segments


def parse_translation_file(file_path: Path) -> list[SubtitleSegment]:
    """Parse .md, .txt, or .srt dubbing translation file into clean SubtitleSegments."""
    if not file_path.is_file():
        return []

    content = file_path.read_text(encoding="utf-8", errors="replace")
    return parse_translation_content(content, file_ext=file_path.suffix)

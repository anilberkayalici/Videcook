"""Download history service — persistence and management of downloaded items."""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from videcook.paths import get_user_data_dir

_HISTORY_FILENAME = "videcook_history.json"


@dataclass
class HistoryItem:
    """A record of a completed download."""

    id: str
    title: str
    file_path: str
    file_size_bytes: int
    duration_seconds: int
    download_type: str  # "video" | "audio" | "thumbnail"
    format_label: str  # e.g. "VIDEO: 1080p - MP4", "SES: MP3", "THUMBNAIL: 1280x720"
    url: str
    timestamp: str  # ISO 8601 string
    thumbnail_b64: str = ""  # Base64 encoded thumbnail JPEG

    def formatted_size(self) -> str:
        """Return human-readable file size."""
        size = self.file_size_bytes
        if not size and self.file_path:
            p = Path(self.file_path)
            if p.is_file():
                try:
                    size = p.stat().st_size
                except OSError:
                    pass

        if not size:
            return "—"
        if size >= 1_073_741_824:
            return f"{size / 1_073_741_824:.2f} GB"
        if size >= 1_048_576:
            return f"{size / 1_048_576:.2f} MB"
        if size >= 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size} B"

    def formatted_duration(self) -> str:
        """Return formatted duration string (e.g. 22m:41s or 01h:15m:30s)."""
        if self.duration_seconds <= 0:
            return "—"
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        if hours > 0:
            return f"{hours:02d}h:{minutes:02d}m:{seconds:02d}s"
        return f"{minutes:02d}m:{seconds:02d}s"

    def formatted_date(self) -> str:
        """Return a user-friendly date/time string."""
        if not self.timestamp:
            return "—"
        try:
            dt = datetime.fromisoformat(self.timestamp)
            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return self.timestamp


def _history_file_path() -> Path:
    return get_user_data_dir() / _HISTORY_FILENAME


def load_history() -> list[HistoryItem]:
    """Load all history items from disk, sorted newest first."""
    path = _history_file_path()
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        items = []
        for d in raw:
            if isinstance(d, dict):
                items.append(
                    HistoryItem(
                        id=d.get("id") or str(uuid.uuid4()),
                        title=d.get("title", ""),
                        file_path=d.get("file_path", ""),
                        file_size_bytes=int(d.get("file_size_bytes") or 0),
                        duration_seconds=int(d.get("duration_seconds") or 0),
                        download_type=d.get("download_type", "video"),
                        format_label=d.get("format_label", ""),
                        url=d.get("url", ""),
                        timestamp=d.get("timestamp", ""),
                        thumbnail_b64=d.get("thumbnail_b64", ""),
                    )
                )
        items.sort(key=lambda x: x.timestamp, reverse=True)
        return items
    except Exception as exc:
        logging.warning("Could not load history: %s", exc)
        return []


def save_history(items: list[HistoryItem]) -> None:
    """Save history items list to disk."""
    path = _history_file_path()
    try:
        data = [asdict(item) for item in items]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logging.warning("Could not save history: %s", exc)


def add_history_entry(
    title: str,
    file_path: str,
    file_size_bytes: int = 0,
    duration_seconds: int = 0,
    download_type: str = "video",
    format_label: str = "",
    url: str = "",
    thumbnail_b64: str = "",
) -> HistoryItem:
    """Create and persist a new download history record."""
    item = HistoryItem(
        id=str(uuid.uuid4()),
        title=title or Path(file_path).name,
        file_path=file_path,
        file_size_bytes=file_size_bytes,
        duration_seconds=duration_seconds,
        download_type=download_type,
        format_label=format_label,
        url=url,
        timestamp=datetime.now().isoformat(),
        thumbnail_b64=thumbnail_b64,
    )
    items = load_history()
    items.insert(0, item)
    save_history(items)
    return item


def _normalize_search_text(text: str) -> str:
    """Normalize text for fuzzy filename matching (handles Turkish accents and sanitization)."""
    import unicodedata
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    t = text.translate(tr_map)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9\s]", " ", t).lower()


def resolve_history_item_file(item: HistoryItem) -> Path | None:
    """Resolve the real, valid on-disk file path for a history item.

    Handles corrupted/escaped paths, encoding issues, and auto-repairs history.
    """
    if not item.file_path:
        return None

    img_exts = (".jpg", ".jpeg", ".webp", ".png")
    sub_exts = (".srt", ".vtt", ".txt", ".ass")
    media_exts = (
        ".mp4",
        ".mkv",
        ".webm",
        ".avi",
        ".mov",
        ".mp3",
        ".wav",
        ".m4a",
        ".opus",
        ".flac",
    )
    is_thumb = item.download_type == "thumbnail"
    is_sub = item.download_type == "subtitle"
    if is_thumb:
        allowed_exts = img_exts
    elif is_sub:
        allowed_exts = sub_exts
    else:
        allowed_exts = media_exts

    # 1. Direct check with matching extension type
    p = Path(item.file_path)
    if p.is_file() and p.suffix.lower() in allowed_exts:
        return p

    # 2. Extract video ID (e.g. from [cnQFareYaHA] in path or ?v=cnQFareYaHA in url)
    video_id = ""
    m_path = re.search(r"\[([a-zA-Z0-9_-]{11})\]", item.file_path)
    if m_path:
        video_id = m_path.group(1)
    elif item.url:
        m_url = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", item.url) or re.search(
            r"youtu\.be/([a-zA-Z0-9_-]{11})", item.url
        )
        if m_url:
            video_id = m_url.group(1)

    # Search candidate directories
    candidate_dirs: list[Path] = []
    try:
        candidate_dirs.append(p.parent)
    except Exception:
        pass

    user_home = Path.home()
    candidate_dirs.extend([
        user_home / "Desktop",
        user_home / "Downloads",
        user_home / "Videos",
        user_home / "Music",
        user_home / "Pictures",
    ])

    for c_dir in candidate_dirs:
        if not c_dir.is_dir():
            continue
        try:
            # Check by video ID
            if video_id:
                for f in c_dir.iterdir():
                    if (
                        f.is_file()
                        and f.suffix.lower() in allowed_exts
                        and video_id in f.name
                    ):
                        _repair_item_path(item, str(f))
                        return f

            # Check by normalized title match
            if item.title:
                norm_title = _normalize_search_text(item.title)
                words = norm_title.split()[:2]
                if words:
                    for f in c_dir.iterdir():
                        if f.is_file() and f.suffix.lower() in allowed_exts:
                            norm_fname = _normalize_search_text(f.name)
                            if all(w in norm_fname for w in words):
                                _repair_item_path(item, str(f))
                                return f
        except Exception:
            continue

    return None


def _repair_item_path(item: HistoryItem, correct_path: str) -> None:
    """Auto-update corrupted file_path and file_size_bytes in history persistence."""
    item.file_path = correct_path
    try:
        p = Path(correct_path)
        if p.is_file():
            item.file_size_bytes = p.stat().st_size
    except Exception:
        pass

    try:
        items = load_history()
        for idx, it in enumerate(items):
            if it.id == item.id:
                items[idx].file_path = correct_path
                items[idx].file_size_bytes = item.file_size_bytes
                break
        save_history(items)
    except Exception:
        pass


def delete_history_entry(item_id: str, delete_file: bool = False) -> bool:
    """Delete a history record by ID, and optionally delete the file from disk."""
    items = load_history()
    target_item = None
    remaining = []
    for item in items:
        if item.id == item_id:
            target_item = item
        else:
            remaining.append(item)

    if not target_item:
        return False

    if delete_file and target_item.file_path:
        real_file = resolve_history_item_file(target_item) or Path(target_item.file_path)
        if real_file.is_file():
            try:
                real_file.unlink()
            except OSError as exc:
                logging.warning("Could not delete file %s: %s", real_file, exc)

    save_history(remaining)
    return True


def clear_history_entries(delete_files: bool = False) -> None:
    """Clear all history items, optionally deleting files."""
    if delete_files:
        items = load_history()
        for item in items:
            real_file = resolve_history_item_file(item)
            if real_file and real_file.is_file():
                try:
                    real_file.unlink()
                except OSError:
                    pass
    save_history([])

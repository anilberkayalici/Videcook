"""User preference persistence in the current user's data directory.

The on-disk schema is intentionally additive: every load falls back to
defaults for any missing key, so older preference files keep working
after upgrades.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from videcook.paths import get_user_data_dir

_PREFS_FILENAME = "videcook_prefs.json"


@dataclass
class UserPreferences:
    language: str = "tr"
    last_output_folder: str = ""
    last_quality: str = "quality.best"
    last_audio_format: str = "audio_format.wav"
    last_download_type: str = "video"
    embed_thumbnail: bool = True
    advanced_args: str = ""
    # --- H.264 compatibility -----------------------------------------------
    # When True, video downloads always end up as H.264 (avc1) in MP4.
    # Non-H.264 source streams are re-encoded via FFmpeg. Slower but
    # universally compatible with Adobe Audition, Reaper, etc.
    h264_compat_mode: bool = True
    # --- Theme ------------------------------------------------------------
    # One of THEME_KEYS in videcook.ui.theme. Defaults to "wine".
    theme: str = "wine"
    # --- Dynamic format cache (per URL) -------------------------------------
    # Last format decision summary shown to the user, per URL. Capped in
    # size to keep the prefs file from growing unbounded.
    format_cache: dict[str, str] = field(default_factory=dict)


_CACHE_MAX_ENTRIES = 32


def _prefs_path() -> Path:
    return get_user_data_dir() / _PREFS_FILENAME


def load_preferences() -> UserPreferences:
    path = _prefs_path()
    if not path.is_file():
        return UserPreferences()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logging.warning("Could not load preferences, using defaults.")
        return UserPreferences()

    raw_cache = data.get("format_cache", {}) or {}
    if not isinstance(raw_cache, dict):
        raw_cache = {}

    # Cap the cache size to the most recent N entries; we don't track
    # recency explicitly so this is a rough cutoff by insertion order
    # which is good enough for a tiny cache.
    items = list(raw_cache.items())[:_CACHE_MAX_ENTRIES]

    return UserPreferences(
        language=data.get("language", "tr"),
        last_output_folder=data.get("last_output_folder", ""),
        last_quality=data.get("last_quality", "quality.best"),
            last_audio_format=data.get("last_audio_format", "audio_format.wav"),
            last_download_type=data.get("last_download_type", "video"),
            embed_thumbnail=data.get("embed_thumbnail", True),
        advanced_args=data.get("advanced_args", ""),
        h264_compat_mode=data.get("h264_compat_mode", True),
        theme=data.get("theme", "wine"),
        format_cache=dict(items),
    )


def save_preferences(prefs: UserPreferences) -> None:
    path = _prefs_path()
    # Trim cache to the cap before serialising.
    cache_items = list(prefs.format_cache.items())[:_CACHE_MAX_ENTRIES]
    data = {
        "language": prefs.language,
        "last_output_folder": prefs.last_output_folder,
        "last_quality": prefs.last_quality,
        "last_audio_format": prefs.last_audio_format,
        "last_download_type": prefs.last_download_type,
        "embed_thumbnail": prefs.embed_thumbnail,
        "advanced_args": prefs.advanced_args,
        "h264_compat_mode": prefs.h264_compat_mode,
        "theme": prefs.theme,
        "format_cache": dict(cache_items),
    }
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        logging.warning("Could not save preferences.")

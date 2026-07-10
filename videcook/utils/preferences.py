"""User preference persistence in the current user's data directory."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from videcook.paths import get_user_data_dir

_PREFS_FILENAME = "videcook_prefs.json"


@dataclass
class UserPreferences:
    language: str = "tr"
    last_output_folder: str = ""
    last_quality: str = "quality.best"
    last_audio_format: str = "audio_format.mp3"
    embed_thumbnail: bool = True
    advanced_args: str = ""


def _prefs_path() -> Path:
    return get_user_data_dir() / _PREFS_FILENAME


def load_preferences() -> UserPreferences:
    path = _prefs_path()
    if not path.is_file():
        return UserPreferences()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return UserPreferences(
            language=data.get("language", "tr"),
            last_output_folder=data.get("last_output_folder", ""),
            last_quality=data.get("last_quality", "quality.best"),
            last_audio_format=data.get("last_audio_format", "audio_format.mp3"),
            embed_thumbnail=data.get("embed_thumbnail", True),
            advanced_args=data.get("advanced_args", ""),
        )
    except Exception:
        logging.warning("Could not load preferences, using defaults.")
        return UserPreferences()


def save_preferences(prefs: UserPreferences) -> None:
    path = _prefs_path()
    data = {
        "language": prefs.language,
        "last_output_folder": prefs.last_output_folder,
        "last_quality": prefs.last_quality,
        "last_audio_format": prefs.last_audio_format,
        "embed_thumbnail": prefs.embed_thumbnail,
        "advanced_args": prefs.advanced_args,
    }
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        logging.warning("Could not save preferences.")

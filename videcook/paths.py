"""Path helpers for bundled resources and writable user data."""

import os
import shutil
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Return the project root directory.

    During development: the parent of the ``videcook`` package.
    When frozen (PyInstaller): ``sys._MEIPASS``.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def get_user_data_dir() -> Path:
    """Return Videcook's writable per-user Windows data directory.

    PyInstaller's ``_MEIPASS`` directory belongs to the application bundle and
    may be read-only. Preferences, logs, and downloaded tools therefore live
    under ``%LOCALAPPDATA%\\Videcook`` instead.
    """
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    directory = Path(base) / "Videcook" if base else Path.home() / ".videcook"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_bin_dir() -> Path:
    """Return the writable ``bin/`` directory for managed helper tools."""
    if getattr(sys, "frozen", False):
        return get_user_data_dir() / "bin"
    return get_project_root() / "bin"


def get_bundled_bin_dir() -> Path:
    """Return the read-only ``bin/`` directory shipped with the app bundle."""
    return get_project_root() / "bin"


def _exe(name: str) -> str:
    """Append ``.exe`` on Windows, nothing elsewhere."""
    return f"{name}.exe" if os.name == "nt" else name


def get_ytdlp_path() -> Path:
    """Return the expected path to the yt-dlp executable."""
    return get_bin_dir() / _exe("yt-dlp")


def get_ffmpeg_path() -> Path:
    """Return the expected path to the ffmpeg executable."""
    return get_bin_dir() / _exe("ffmpeg")


def get_ffprobe_path() -> Path:
    """Return the expected path to the ffprobe executable."""
    return get_bin_dir() / _exe("ffprobe")


def find_on_path(name: str) -> Path | None:
    """Search for *name* on the system PATH; return ``None`` if not found."""
    resolved = shutil.which(name)
    return Path(resolved) if resolved else None


def get_assets_dir() -> Path:
    """Return the ``assets/`` directory."""
    return get_project_root() / "assets"


def get_asset_path(filename: str) -> Path:
    """Return the path to *filename* inside ``assets/``."""
    return get_assets_dir() / filename

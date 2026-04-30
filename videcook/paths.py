"""Path helpers for Videcook — resolve project and binary locations."""

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


def get_bin_dir() -> Path:
    """Return the ``bin/`` directory containing helper executables."""
    return get_project_root() / "bin"


def get_ytdlp_path() -> Path:
    """Return the expected path to ``yt-dlp.exe``."""
    return get_bin_dir() / "yt-dlp.exe"


def get_ffmpeg_path() -> Path:
    """Return the expected path to ``ffmpeg.exe``."""
    return get_bin_dir() / "ffmpeg.exe"


def get_ffprobe_path() -> Path:
    """Return the expected path to ``ffprobe.exe``."""
    return get_bin_dir() / "ffprobe.exe"


def get_assets_dir() -> Path:
    """Return the ``assets/`` directory."""
    return get_project_root() / "assets"


def get_asset_path(filename: str) -> Path:
    """Return the path to *filename* inside ``assets/``."""
    return get_assets_dir() / filename

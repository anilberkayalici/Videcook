"""Update checker — verifies yt-dlp freshness.

Strategy: use ``yt-dlp --version`` for the current version, and query
the GitHub API directly for the latest release tag.  This avoids the
rate-limit-prone ``yt-dlp -U`` flow and is faster.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from videcook.paths import get_ytdlp_path
from videcook import __version__

_YTDLP_RELEASES_API = (
    "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
)
_REQUEST_TIMEOUT = 15


@dataclass
class UpdateStatus:
    """Outcome of an update check."""

    update_available: bool
    current_version: str
    latest_version: str
    message: str
    detail: str = ""


def check_for_updates(ytdlp_path: Path) -> UpdateStatus:
    """Compare installed yt-dlp version against the latest GitHub release."""
    if not ytdlp_path.is_file():
        return UpdateStatus(
            update_available=False,
            current_version="unknown",
            latest_version="unknown",
            message="settings.update_ytdlp_missing",
        )

    current = get_current_version(ytdlp_path)
    if current == "unknown":
        return UpdateStatus(
            update_available=False,
            current_version="unknown",
            latest_version="unknown",
            message="settings.update_current_unknown",
        )

    try:
        latest = _fetch_latest_version()
    except Exception as exc:
        msg = str(exc).lower()
        if "403" in msg:
            return UpdateStatus(
                update_available=False,
                current_version=current,
                latest_version="unknown",
                message="settings.update_rate_limited",
            )
        if "timed out" in msg or "timeout" in msg:
            return UpdateStatus(
                update_available=False,
                current_version=current,
                latest_version="unknown",
                message="settings.update_timeout",
            )
        return UpdateStatus(
            update_available=False,
            current_version=current,
            latest_version="unknown",
            message="settings.update_check_failed",
            detail=str(exc),
        )

    if latest == "unknown":
        return UpdateStatus(
            update_available=False,
            current_version=current,
            latest_version="unknown",
            message="settings.update_latest_unknown",
        )

    if current == latest:
        return UpdateStatus(
            update_available=False,
            current_version=current,
            latest_version=latest,
            message="settings.update_not_needed",
        )

    return UpdateStatus(
        update_available=True,
        current_version=current,
        latest_version=latest,
        message="settings.update_available_status",
    )


def get_current_version(ytdlp_path: Path) -> str:
    """Return the installed yt-dlp version string."""
    if not ytdlp_path.is_file():
        return "unknown"
    try:
        result = subprocess.run(
            [str(ytdlp_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip().splitlines()[-1].strip()
    except Exception:
        return "unknown"


def _fetch_latest_version() -> str:
    """Fetch the latest yt-dlp release tag from GitHub API."""
    req = urllib.request.Request(_YTDLP_RELEASES_API)
    req.add_header("User-Agent", f"Videcook/{__version__}")
    req.add_header("Accept", "application/vnd.github+json")

    with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        tag = data.get("tag_name", "")
        return tag.lstrip("v") if tag else "unknown"


def perform_update(ytdlp_path: Path) -> tuple[bool, str]:
    """Run ``yt-dlp -U`` to apply an update.  Returns (success, message)."""
    if not ytdlp_path.is_file():
        return False, "yt-dlp not found."

    try:
        result = subprocess.run(
            [str(ytdlp_path), "-U"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode == 0 or "updated" in output.lower():
            return True, output
        return False, output or "Update failed with no output."
    except Exception as exc:
        return False, str(exc)


def prepare_ytdlp_update(ytdlp_path: Path) -> Path:
    """Copy a bundled or PATH yt-dlp into Videcook's writable folder first."""
    managed_path = get_ytdlp_path()
    if ytdlp_path.resolve() == managed_path.resolve():
        return managed_path
    managed_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ytdlp_path, managed_path)
    return managed_path

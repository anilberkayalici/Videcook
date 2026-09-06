"""App self-update checker — queries GitHub Releases for newer versions.

Fires once at startup. No UI dependency — the caller handles the dialog.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from videcook import __version__

_RELEASES_API = (
    "https://api.github.com/repos/anilberkayalici/Videcook/releases/latest"
)
_REQUEST_TIMEOUT = 8  # seconds — keep it snappy so startup isn't delayed


@dataclass
class AppUpdateStatus:
    """Result of checking for a newer Videcook release."""

    update_available: bool
    current_version: str
    latest_version: str


def _parse_version(tag: str) -> str:
    """Return ``"0.5.0"`` from a tag like ``"v0.5.0"``."""
    return tag.lstrip("v")


def check_for_app_update() -> AppUpdateStatus | None:
    """Return an :class:`AppUpdateStatus` if a newer version exists,
    or ``None`` when the check fails (network error, rate-limit, …).

    ``None`` is deliberately returned on failure so the caller can
    just ignore it — startup must never be blocked.
    """
    try:
        req = urllib.request.Request(_RELEASES_API)
        req.add_header("User-Agent", f"Videcook/{__version__}")
        req.add_header("Accept", "application/vnd.github+json")

        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        latest_tag = data.get("tag_name", "")
        latest = _parse_version(latest_tag)
        if not latest:
            return None

        if latest == __version__:
            return AppUpdateStatus(
                update_available=False,
                current_version=__version__,
                latest_version=latest,
            )

        return AppUpdateStatus(
            update_available=True,
            current_version=__version__,
            latest_version=latest,
        )
    except Exception:
        # Network down, rate-limited, GitHub unreachable — never block
        # the user from using the app.
        return None

"""Playlist detection — conservative URL inspection.

No network calls, no subprocesses.  The functions only inspect the URL string.
"""

import re
from urllib.parse import parse_qs, urlparse


def detect_playlist_intent(url: str) -> bool:
    """Return ``True`` if *url* appears to reference a playlist.

    Currently detects the ``list=`` query parameter commonly used by YouTube.
    May be expanded for other platforms in the future.
    """
    if not url or not url.strip():
        return False

    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False

    if _is_youtube_url(parsed.netloc):
        query = parse_qs(parsed.query)
        if "list" in query:
            return True

    if _looks_like_playlist_path(parsed.path):
        return True

    return False


_YT_HOST_PATTERN = re.compile(
    r"(^|\.)(youtube\.com|youtu\.be)$", re.IGNORECASE
)


def _is_youtube_url(netloc: str) -> bool:
    """Check whether the netloc belongs to YouTube."""
    # Strip optional port
    host = netloc.split(":")[0] if netloc else ""
    return bool(_YT_HOST_PATTERN.search(host))


_PLAYLIST_PATH_PATTERN = re.compile(r"/playlist", re.IGNORECASE)


def _looks_like_playlist_path(path: str) -> bool:
    """Heuristic: does the URL path contain '/playlist'?"""
    return bool(_PLAYLIST_PATH_PATTERN.search(path))

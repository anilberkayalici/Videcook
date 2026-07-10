"""Translate raw yt-dlp errors into user-friendly messages."""

from __future__ import annotations


def translate_error(raw: str) -> str:
    """Map a raw yt-dlp error line to a user-friendly explanation.

    Falls back to the original message if no pattern matches.
    """
    lower = raw.lower()

    if "403" in lower or "forbidden" in lower:
        if "cookie" in lower:
            return "error.cookie_expired"
        return "error.http_403"

    if "404" in lower or "not found" in lower:
        return "error.http_404"

    if "429" in lower:
        return "error.http_429"

    if "video unavailable" in lower or "video is unavailable" in lower:
        return "error.video_unavailable"

    if "this video is private" in lower:
        return "error.video_private"

    if "members-only" in lower or "join this channel" in lower:
        return "error.members_only"

    if "unable to download video" in lower or "unable to extract" in lower:
        return "error.network"

    if "unable to extract" in lower:
        return "error.extract_failed"

    if "requested format not available" in lower or "no video formats" in lower:
        return "error.format_unavailable"

    if "ffmpeg not found" in lower or "ffprobe not found" in lower:
        return "error.ffmpeg_missing"

    if "login" in lower or "sign in" in lower or "registered users" in lower:
        return "error.login_required"

    if "ssl" in lower or "certificate" in lower:
        return "error.ssl"

    if "cookie" in lower and ("invalid" in lower or "expired" in lower or "error" in lower):
        return "error.invalid_cookie"

    if "geoblocked" in lower or "not available in your country" in lower:
        return "error.geo_restricted"

    if "rate limit" in lower or "too many" in lower:
        return "error.rate_limit"

    if "connection" in lower or "resolve" in lower or "name or service not known" in lower:
        return "error.no_internet"

    return ""

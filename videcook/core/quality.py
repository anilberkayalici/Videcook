"""Quality selector — maps :class:`QualityOption` or dynamic string to yt-dlp ``-f`` values.

Always prefers H.264 (avc1) when available, falls back to any codec.
The format selectors below are what yt-dlp itself would construct for a
given resolution cap.
"""

from __future__ import annotations
from videcook.core.models import QualityOption


def get_format_selector(quality: QualityOption | str) -> str:
    """Return the yt-dlp ``-f`` format string for a preset or dynamic resolution.

    Prefers H.264 (avc1) video and AAC (m4a) audio so that the downloaded MP4
    is directly and natively compatible with Adobe Audition, Reaper, Premiere,
    and all DAW / video editing software without extra re-encoding.
    Falls back to any video + m4a audio, then any best video + best audio, then best generic stream.
    """
    if isinstance(quality, QualityOption):
        if quality is QualityOption.BEST:
            return "bv*[vcodec^=avc1]+ba[ext=m4a]/bv*+ba[ext=m4a]/bv*+ba/b/best"
        elif quality is QualityOption.P1080:
            return "bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=1080]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/b/best"
        elif quality is QualityOption.P720:
            return "bv*[height<=720][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=720]+ba[ext=m4a]/bv*[height<=720]+ba/b[height<=720]/b/best"
        elif quality is QualityOption.P480:
            return "bv*[height<=480][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=480]+ba[ext=m4a]/bv*[height<=480]+ba/b[height<=480]/b/best"

    if quality == "best":
        return "bv*[vcodec^=avc1]+ba[ext=m4a]/bv*+ba[ext=m4a]/bv*+ba/b/best"

    try:
        height = int(quality)
    except (ValueError, TypeError):
        return "bv*[vcodec^=avc1]+ba[ext=m4a]/bv*+ba[ext=m4a]/bv*+ba/b/best"

    return f"bv*[height<={height}][vcodec^=avc1]+ba[ext=m4a]/bv*[height<={height}]+ba[ext=m4a]/bv*[height<={height}]+ba/b[height<={height}]/b/best"

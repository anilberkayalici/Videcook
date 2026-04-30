"""Quality selector — maps :class:`QualityOption` to yt-dlp ``-f`` values."""

from videcook.core.models import QualityOption

_FORMAT_MAP: dict[QualityOption, str] = {
    QualityOption.BEST: "bv*+ba/b",
    QualityOption.P1080: "bv*[height<=1080]+ba/b[height<=1080]/b",
    QualityOption.P720: "bv*[height<=720]+ba/b[height<=720]/b",
    QualityOption.P480: "bv*[height<=480]+ba/b[height<=480]/b",
}


def get_format_selector(quality: QualityOption) -> str:
    """Return the yt-dlp ``-f`` format string for *quality*."""
    if quality not in _FORMAT_MAP:
        raise ValueError(f"Unknown quality option: {quality}")
    return _FORMAT_MAP[quality]

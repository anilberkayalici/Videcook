"""Binary locator — checks PATH, then ``bin/`` for helper executables.

No network access for existence checks; subprocess only for version queries.
"""

from dataclasses import dataclass
from pathlib import Path

from videcook.paths import (
    find_on_path,
    get_bundled_bin_dir,
    get_ffmpeg_path,
    get_ffprobe_path,
    get_ytdlp_path,
)


@dataclass
class BinaryStatus:
    """Snapshot of which helper binaries are present and where they live."""

    ytdlp_path: Path | None
    ffmpeg_path: Path | None
    ffprobe_path: Path | None
    ytdlp_source: str = "missing"
    ffmpeg_source: str = "missing"
    ffprobe_source: str = "missing"

    @property
    def ytdlp_exists(self) -> bool:
        return self.ytdlp_path is not None and self.ytdlp_path.is_file()

    @property
    def ffmpeg_exists(self) -> bool:
        return self.ffmpeg_path is not None and self.ffmpeg_path.is_file()

    @property
    def ffprobe_exists(self) -> bool:
        return self.ffprobe_path is not None and self.ffprobe_path.is_file()

    @property
    def is_ready(self) -> bool:
        """``True`` when yt-dlp **and** ffmpeg are available."""
        return self.ytdlp_exists and self.ffmpeg_exists

    def to_display(self) -> str:
        """Human-readable summary for logs."""
        yt = f"OK ({self.ytdlp_source})" if self.ytdlp_exists else "MISSING"
        ff = f"OK ({self.ffmpeg_source})" if self.ffmpeg_exists else "MISSING"
        fp = f"OK ({self.ffprobe_source})" if self.ffprobe_exists else "MISSING"
        return f"yt-dlp: {yt} | ffmpeg: {ff} | ffprobe: {fp}"


def check_binaries(bin_dir: str | Path | None = None) -> BinaryStatus:
    """Inspect PATH and ``bin/``; return a :class:`BinaryStatus`.

    Priority: PATH first, then ``bin/``.  Only checks ``.is_file()`` —
    does **not** execute any binary.
    """
    _ = bin_dir  # kept for API compatibility

    bundled = get_bundled_bin_dir()
    ytdlp = _resolve_binary(
        "yt-dlp", [get_ytdlp_path(), bundled / get_ytdlp_path().name], "ytdlp"
    )
    ffmpeg = _resolve_binary(
        "ffmpeg", [get_ffmpeg_path(), bundled / get_ffmpeg_path().name], "ffmpeg"
    )
    ffprobe = _resolve_binary(
        "ffprobe", [get_ffprobe_path(), bundled / get_ffprobe_path().name], "ffprobe"
    )

    return BinaryStatus(**ytdlp, **ffmpeg, **ffprobe)


def _resolve_binary(executable_name: str, local_paths: list[Path], field_prefix: str) -> dict:
    """Check PATH then local ``bin/`` for *executable_name*.
    Returns a dict with ``{field_prefix}_path`` and ``{field_prefix}_source`` keys.
    """
    for index, local_path in enumerate(local_paths):
        if local_path.is_file():
            source = "managed" if index == 0 else "bundled"
            return {f"{field_prefix}_path": local_path, f"{field_prefix}_source": source}

    on_path = find_on_path(executable_name)
    if on_path is not None and on_path.is_file():
        return {f"{field_prefix}_path": on_path, f"{field_prefix}_source": "PATH"}

    return {f"{field_prefix}_path": local_paths[0], f"{field_prefix}_source": "missing"}

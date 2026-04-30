"""Binary locator — checks whether helper executables exist in ``bin/``.

No network access, no subprocess execution.
"""

from dataclasses import dataclass
from pathlib import Path

from videcook.paths import get_bin_dir, get_ffmpeg_path, get_ffprobe_path, get_ytdlp_path


@dataclass
class BinaryStatus:
    """Snapshot of which helper binaries are present."""

    ytdlp_path: Path
    ffmpeg_path: Path
    ffprobe_path: Path

    @property
    def ytdlp_exists(self) -> bool:
        return self.ytdlp_path.is_file()

    @property
    def ffmpeg_exists(self) -> bool:
        return self.ffmpeg_path.is_file()

    @property
    def ffprobe_exists(self) -> bool:
        return self.ffprobe_path.is_file()

    @property
    def is_ready(self) -> bool:
        """``True`` when yt-dlp **and** ffmpeg are available."""
        return self.ytdlp_exists and self.ffmpeg_exists

    def to_display(self) -> str:
        """Human-readable summary for logs."""
        return (
            f"yt-dlp: {'OK' if self.ytdlp_exists else 'MISSING'}"
            f" | ffmpeg: {'OK' if self.ffmpeg_exists else 'MISSING'}"
            f" | ffprobe: {'OK' if self.ffprobe_exists else 'MISSING'}"
        )


def check_binaries(bin_dir: str | Path | None = None) -> BinaryStatus:
    """Inspect the ``bin/`` directory and return a :class:`BinaryStatus`.

    Only checks ``.is_file()`` — does **not** execute any binary.
    """
    if bin_dir is None:
        bin_dir = get_bin_dir()
    return BinaryStatus(
        ytdlp_path=get_ytdlp_path(),
        ffmpeg_path=get_ffmpeg_path(),
        ffprobe_path=get_ffprobe_path(),
    )

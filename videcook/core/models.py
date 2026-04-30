"""Core data models for Videcook — enums and dataclasses with no external dependencies."""

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path


class DownloadMode(Enum):
    """Whether to download a single video or an entire playlist."""

    SINGLE_VIDEO = auto()
    PLAYLIST = auto()


class QualityOption(Enum):
    """Video quality presets for the user to choose from."""

    BEST = auto()
    P1080 = auto()
    P720 = auto()
    P480 = auto()


@dataclass
class DownloadRequest:
    """All parameters needed to start a download.

    The *cookie_file* path is only forwarded to yt-dlp via its ``--cookies``
    flag.  Videcook never reads the file contents.
    """

    url: str
    cookie_file: Path
    output_folder: Path
    quality: QualityOption
    mode: DownloadMode


@dataclass
class CommandBuildResult:
    """The args list ready for :func:`subprocess.Popen` and a safe display string."""

    args: list[str]
    redacted_display: str

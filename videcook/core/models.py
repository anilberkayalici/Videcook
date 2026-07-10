"""Core data models for Videcook — enums and dataclasses with no external dependencies."""

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path


class DownloadMode(Enum):
    """Whether to download a single video or an entire playlist."""

    SINGLE_VIDEO = auto()
    PLAYLIST = auto()


class DownloadType(Enum):
    """Download type — video with merged audio, or audio-only extraction."""

    VIDEO = auto()
    AUDIO = auto()


class QualityOption(Enum):
    """Video quality presets."""

    BEST = auto()
    P1080 = auto()
    P720 = auto()
    P480 = auto()


class AudioFormat(Enum):
    """Audio container formats for extraction."""

    MP3 = "mp3"
    M4A = "m4a"
    OPUS = "opus"
    AAC = "aac"
    FLAC = "flac"
    WAV = "wav"

    def extension(self) -> str:
        return self.value


@dataclass
class DownloadRequest:
    """All parameters needed to start a download.

    The *cookie_file* path is only forwarded to yt-dlp via its ``--cookies``
    flag.  Videcook never reads the file contents.
    """

    url: str
    cookie_file: Path | None
    output_folder: Path
    quality: QualityOption
    mode: DownloadMode
    download_type: DownloadType = DownloadType.VIDEO
    audio_format: AudioFormat = AudioFormat.MP3
    embed_thumbnail: bool = False


@dataclass
class CommandBuildResult:
    """The args list ready for :func:`subprocess.Popen` and a safe display string."""

    args: list[str]
    redacted_display: str

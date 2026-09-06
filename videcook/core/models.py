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
    """Audio container formats for extraction.

    Note: M4A is intentionally absent. The yt-dlp ``--audio-format aac``
    option produces an M4A container with AAC inside, so a separate
    M4A entry would be redundant. AAC is exposed for users who need a
    raw ADTS ``.aac`` stream (e.g. legacy media players).
    """

    MP3 = "mp3"
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
    quality: str
    mode: DownloadMode
    download_type: DownloadType = DownloadType.VIDEO
    audio_format: AudioFormat = AudioFormat.WAV
    audio_quality: str = "320"
    embed_thumbnail: bool = False
    # When True, force the final file to use H.264 (avc1) video even if
    # the source stream is VP9/AV1. The video stream is re-encoded with
    # libx264; the audio stream is copied (no quality loss). The format
    # selector above already prefers avc1 streams, so this only triggers
    # for 1440p/4K where YouTube only serves VP9/AV1.
    force_h264_transcode: bool = False
    # > 1 when the same video is being re-downloaded; appended as a
    # suffix to the output filename so repeated clicks produce
    # ``video.mp4``, ``video (#2).mp4``, ``video (#3).mp4``, …
    download_counter: int = 0


@dataclass
class CommandBuildResult:
    """The args list ready for :func:`subprocess.Popen` and a safe display string."""

    args: list[str]
    redacted_display: str

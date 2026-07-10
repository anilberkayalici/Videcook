"""Build yt-dlp argument lists — never shell strings, never shell=True."""

import shlex
from pathlib import Path

from videcook.core.models import (
    CommandBuildResult,
    DownloadMode,
    DownloadRequest,
    DownloadType,
)
from videcook.core.quality import get_format_selector
from videcook.core.validators import validate_download_request
from videcook.utils.preferences import load_preferences


def build_ytdlp_command(
    request: DownloadRequest,
    ytdlp_path: Path,
    ffmpeg_location: Path,
) -> CommandBuildResult:
    """Construct a :class:`CommandBuildResult` ready for :func:`subprocess.Popen`.

    Args:
        request: The validated download parameters.
        ytdlp_path: Absolute or relative path to ``yt-dlp.exe``.
        ffmpeg_location: Directory containing ``ffmpeg.exe`` and ``ffprobe.exe``,
            or the ``ffmpeg.exe`` path itself.

    Returns:
        A result with a safe argument list and a redacted display string.

    Raises:
        FileNotFoundError: If *ytdlp_path* or *ffmpeg_location* does not exist.
        ValidationError: If the request fails pre-flight validation.
    """
    validate_download_request(request)

    if not ytdlp_path.exists():
        raise FileNotFoundError(f"yt-dlp not found: {ytdlp_path}")
    if not ffmpeg_location.exists():
        raise FileNotFoundError(f"ffmpeg location not found: {ffmpeg_location}")

    ytdlp = str(ytdlp_path)
    ffmpeg_dir = str(ffmpeg_location)
    out_dir = str(request.output_folder)

    if request.download_type is DownloadType.AUDIO:
        return _build_audio_command(request, ytdlp, ffmpeg_dir, out_dir)

    return _build_video_command(request, ytdlp, ffmpeg_dir, out_dir)


def _build_video_command(
    request: DownloadRequest, ytdlp: str, ffmpeg_dir: str, out_dir: str
) -> CommandBuildResult:
    args: list[str] = [
        ytdlp,
        "--ffmpeg-location", ffmpeg_dir,
        "-f", get_format_selector(request.quality),
        "--merge-output-format", "mp4",
        "--remux-video", "mp4",
        "-P", out_dir,
        "--newline",
    ]

    if request.cookie_file is not None:
        args[1:1] = ["--cookies", str(request.cookie_file)]

    if request.mode is DownloadMode.SINGLE_VIDEO:
        args.append("--no-playlist")

    args.append(request.url)
    _append_extra_args(args)

    redacted = _build_redacted_display(request, ytdlp, ffmpeg_dir, out_dir)
    return CommandBuildResult(args=args, redacted_display=redacted)


def _build_audio_command(
    request: DownloadRequest, ytdlp: str, ffmpeg_dir: str, out_dir: str
) -> CommandBuildResult:
    fmt = request.audio_format.value
    args: list[str] = [
        ytdlp,
        "--ffmpeg-location", ffmpeg_dir,
        "-x",
        "--audio-format", fmt,
        "--audio-quality", "0",
        "-P", out_dir,
        "--newline",
    ]

    if request.cookie_file is not None:
        args[1:1] = ["--cookies", str(request.cookie_file)]

    if request.mode is DownloadMode.SINGLE_VIDEO:
        args.append("--no-playlist")

    if request.embed_thumbnail:
        args.append("--embed-thumbnail")
        args.append("--embed-metadata")

    args.append(request.url)
    _append_extra_args(args)

    thumb = " --embed-thumbnail --embed-metadata" if request.embed_thumbnail else ""
    cookie_part = (
        f" --cookies {_COOKIE_REDACTED}"
        if request.cookie_file is not None
        else ""
    )
    mode_flag = "" if request.mode is DownloadMode.PLAYLIST else " --no-playlist"
    display = (
        f"{ytdlp}{cookie_part}"
        f" --ffmpeg-location {ffmpeg_dir}"
        f" -x --audio-format {fmt} --audio-quality 0"
        f" -P {out_dir}{thumb}{mode_flag}"
        f" {request.url}"
    )
    return CommandBuildResult(args=args, redacted_display=display)


_COOKIE_REDACTED = "[COOKIE_PATH_REDACTED]"


def _build_redacted_display(
    request: DownloadRequest,
    ytdlp_path: str,
    ffmpeg_dir: str,
    out_dir: str,
) -> str:
    """Produce a human-readable command summary with the cookie path redacted."""
    mode_flag = "" if request.mode is DownloadMode.PLAYLIST else " --no-playlist"
    cookie_part = (
        f" --cookies {_COOKIE_REDACTED}"
        if request.cookie_file is not None
        else ""
    )
    return (
        f"{ytdlp_path}"
        f"{cookie_part}"
        f" --ffmpeg-location {ffmpeg_dir}"
        f" -f {get_format_selector(request.quality)}"
        f" --merge-output-format mp4 --remux-video mp4"
        f" -P {out_dir}"
        f"{mode_flag}"
        f" {request.url}"
    )


def _append_extra_args(args: list[str]) -> None:
    """Append user-defined extra yt-dlp flags from saved preferences."""
    prefs = load_preferences()
    extra = prefs.advanced_args.strip()
    if extra:
        for token in shlex.split(extra):
            if token:
                args.append(token)

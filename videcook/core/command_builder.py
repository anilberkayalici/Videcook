"""Build yt-dlp argument lists — never shell strings, never shell=True.

Supports one new request field, :attr:`DownloadRequest.force_h264_transcode`:
when ``True``, the video stream is re-encoded to H.264 via FFmpeg even if
the source was VP9/AV1. The audio stream is copied (no quality loss).
This is what makes downloads work in Adobe Audition, Reaper, and any
media app that doesn't decode modern video codecs in MP4.
"""

from __future__ import annotations

import shlex
from pathlib import Path

from videcook.core.models import (
    AudioFormat,
    CommandBuildResult,
    DownloadMode,
    DownloadRequest,
    DownloadType,
)
from videcook.core.quality import get_format_selector
from videcook.core.validators import validate_download_request


# Standard modern desktop browser User-Agent to ensure CDN and generic HLS compatibility
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# FFmpeg arguments for H.264 re-encoding. Audio is copied (no quality
# loss). CRF 20 = visually transparent, preset medium = good
# speed/quality balance.
_H264_TRANSCODE_ARGS = "ffmpeg:-c:v libx264 -preset medium -crf 20 -c:a copy"


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


# ---------------------------------------------------------------------------
# Video
# ---------------------------------------------------------------------------


def _build_video_command(
    request: DownloadRequest, ytdlp: str, ffmpeg_dir: str, out_dir: str
) -> CommandBuildResult:
    format_selector = get_format_selector(request.quality)

    args: list[str] = [
        ytdlp,
        "--extractor-args", "youtube:player_client=visionos,android,mweb",
        "--user-agent", _DEFAULT_USER_AGENT,
        "--ffmpeg-location", ffmpeg_dir,
        "-f", format_selector,
        "--merge-output-format", "mp4",
        "--remux-video", "mp4",
        "--newline",
    ]

    # On re-downloads of the same URL, suffix the filename so the
    # files don't collide: ``video.mp4``, ``video (#2).mp4``, …
    if request.download_counter > 1:
        args.extend([
            "-o",
            f"{out_dir}/%(title)s [%(id)s] (#{request.download_counter}).%(ext)s",
        ])
    else:
        args.extend(["-P", out_dir])

    if request.cookie_file is not None:
        args[1:1] = ["--cookies", str(request.cookie_file)]

    if request.mode is DownloadMode.SINGLE_VIDEO:
        args.append("--no-playlist")

    # H.264 compatibility: re-encode the video stream to H.264 if the
    # source isn't already H.264. The format selector above already
    # prefers avc1 streams, so this only triggers for 1440p/4K where
    # YouTube only serves VP9/AV1.
    if request.force_h264_transcode:
        args.extend(["--postprocessor-args", _H264_TRANSCODE_ARGS])

    args.append(request.url)
    _append_extra_args(args)

    redacted = _build_video_redacted_display(
        request, ytdlp, ffmpeg_dir, out_dir, format_selector
    )
    return CommandBuildResult(args=args, redacted_display=redacted)


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------


def _build_audio_command(
    request: DownloadRequest, ytdlp: str, ffmpeg_dir: str, out_dir: str
) -> CommandBuildResult:
    fmt = request.audio_format.value
    if request.audio_format in (AudioFormat.WAV, AudioFormat.FLAC):
        audio_quality_flag = "0"
    else:
        aq = getattr(request, "audio_quality", "320") or "320"
        if aq.isdigit() and int(aq) > 9:
            audio_quality_flag = f"{aq}K"
        elif aq == "lossless":
            audio_quality_flag = "0"
        else:
            audio_quality_flag = aq

    args: list[str] = [
        ytdlp,
        "--extractor-args", "youtube:player_client=visionos,android,mweb",
        "--user-agent", _DEFAULT_USER_AGENT,
        "--ffmpeg-location", ffmpeg_dir,
        "-x",
        "--audio-format", fmt,
        "--audio-quality", audio_quality_flag,
        "--force-overwrites",
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
        f" -x --audio-format {fmt} --audio-quality {audio_quality_flag}"
        f" -P {out_dir}{thumb}{mode_flag}"
        f" {request.url}"
    )
    return CommandBuildResult(args=args, redacted_display=display)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

_COOKIE_REDACTED = "[COOKIE_PATH_REDACTED]"


def _build_video_redacted_display(
    request: DownloadRequest,
    ytdlp_path: str,
    ffmpeg_dir: str,
    out_dir: str,
    format_selector: str,
) -> str:
    """Produce a human-readable command summary with the cookie path redacted."""
    mode_flag = "" if request.mode is DownloadMode.PLAYLIST else " --no-playlist"
    cookie_part = (
        f" --cookies {_COOKIE_REDACTED}"
        if request.cookie_file is not None
        else ""
    )
    transcode_part = (
        f" --postprocessor-args '{_H264_TRANSCODE_ARGS}'"
        if request.force_h264_transcode
        else ""
    )
    return (
        f"{ytdlp_path}{cookie_part}"
        f" --ffmpeg-location {ffmpeg_dir}"
        f" -f {format_selector}"
        f" --merge-output-format mp4 --remux-video mp4"
        f" -P {out_dir}"
        f"{mode_flag}{transcode_part}"
        f" {request.url}"
    )


# ---------------------------------------------------------------------------
# User-defined extra args
# ---------------------------------------------------------------------------


def _append_extra_args(args: list[str]) -> None:
    """Append user-defined extra yt-dlp flags from saved preferences."""
    from videcook.utils.preferences import load_preferences

    prefs = load_preferences()
    extra = prefs.advanced_args.strip()
    if extra:
        for token in shlex.split(extra):
            if token:
                args.append(token)

"""Build yt-dlp argument lists — never shell strings, never shell=True."""

from pathlib import Path

from videcook.core.models import (
    CommandBuildResult,
    DownloadMode,
    DownloadRequest,
)
from videcook.core.quality import get_format_selector
from videcook.core.validators import validate_download_request


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
    cookies = str(request.cookie_file)
    ffmpeg_dir = str(ffmpeg_location)
    out_dir = str(request.output_folder)

    args: list[str] = [
        ytdlp,
        "--cookies", cookies,
        "--ffmpeg-location", ffmpeg_dir,
        "-f", get_format_selector(request.quality),
        "--merge-output-format", "mp4",
        "--remux-video", "mp4",
        "-P", out_dir,
        "--newline",
    ]

    if request.mode is DownloadMode.SINGLE_VIDEO:
        args.append("--no-playlist")

    args.append(request.url)

    redacted = _build_redacted_display(request, ytdlp, ffmpeg_dir, out_dir)

    return CommandBuildResult(args=args, redacted_display=redacted)


_COOKIE_REDACTED = "[COOKIE_PATH_REDACTED]"


def _build_redacted_display(
    request: DownloadRequest,
    ytdlp_path: str,
    ffmpeg_dir: str,
    out_dir: str,
) -> str:
    """Produce a human-readable command summary with the cookie path redacted."""
    mode_flag = "" if request.mode is DownloadMode.PLAYLIST else " --no-playlist"
    return (
        f"{ytdlp_path}"
        f" --cookies {_COOKIE_REDACTED}"
        f" --ffmpeg-location {ffmpeg_dir}"
        f" -f {get_format_selector(request.quality)}"
        f" --merge-output-format mp4 --remux-video mp4"
        f" -P {out_dir}"
        f"{mode_flag}"
        f" {request.url}"
    )

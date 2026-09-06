"""YouTube thumbnail download — pure Python, no Qt.

YouTube exposes public thumbnail images at predictable URLs based on
the video ID. No API key, no authentication, no rate limits (for
ordinary use). This module extracts the video ID from common YouTube
URL shapes, builds the image URL for the requested size, and
downloads the bytes to disk.
"""

from __future__ import annotations

import os
import re
import subprocess
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Thumbnail sizes
# ---------------------------------------------------------------------------


class ThumbnailSize:
    """YouTube thumbnail variants, ordered from largest to smallest."""

    MAXRES = "maxresdefault"
    SD = "sddefault"
    HQ = "hqdefault"
    MQ = "mqdefault"
    DEFAULT = "default"

    ALL: tuple[str, ...] = (MAXRES, SD, HQ, MQ, DEFAULT)
    LABELS: dict[str, str] = {
        MAXRES: "1280x720 (MaxRes)",
        SD: "640x480 (SD)",
        HQ: "480x360 (HQ)",
        MQ: "320x180 (MQ)",
        DEFAULT: "120x90 (Default)",
    }


# ---------------------------------------------------------------------------
# Video ID extraction
# ---------------------------------------------------------------------------


_VIDEO_ID_PATTERNS: tuple[re.Pattern[str], ...] = (
    # youtube.com/watch?v=ID
    re.compile(r"(?:youtube\.com/watch\?.*v=)([A-Za-z0-9_\-]{11})"),
    # youtu.be/ID
    re.compile(r"(?:youtu\.be/)([A-Za-z0-9_\-]{11})"),
    # youtube.com/shorts/ID
    re.compile(r"(?:youtube\.com/shorts/)([A-Za-z0-9_\-]{11})"),
    # youtube.com/embed/ID
    re.compile(r"(?:youtube\.com/embed/)([A-Za-z0-9_\-]{11})"),
    # youtube.com/v/ID (legacy)
    re.compile(r"(?:youtube\.com/v/)([A-Za-z0-9_\-]{11})"),
    # youtube.com/live/ID
    re.compile(r"(?:youtube\.com/live/)([A-Za-z0-9_\-]{11})"),
    # music.youtube.com/watch?v=ID
    re.compile(r"(?:music\.youtube\.com/watch\?.*v=)([A-Za-z0-9_\-]{11})"),
)


def extract_video_id(url: str) -> str | None:
    """Return the 11-character YouTube video ID, or ``None`` if not found."""
    if not url:
        return None
    url = url.strip()
    for pattern in _VIDEO_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def thumbnail_url(video_id: str, size: str) -> str:
    """Build the public thumbnail URL for *video_id* at the given *size*."""
    if size not in ThumbnailSize.ALL:
        raise ValueError(f"Unknown thumbnail size: {size}")
    return f"https://img.youtube.com/vi/{video_id}/{size}.jpg"


# ---------------------------------------------------------------------------
# File naming
# ---------------------------------------------------------------------------


_FILENAME_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_FILENAME_WHITESPACE = re.compile(r"\s+")


def sanitize_filename(text: str, max_length: int = 100) -> str:
    """Return a filename-safe version of *text*.

    Removes characters that are illegal on Windows/macOS/Linux,
    collapses whitespace, and strips leading/trailing dots and spaces.
    """
    if not text:
        return ""
    # Normalize unicode (NFD strips combining marks).
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    # Whitespace first: collapse runs of whitespace to a single space so
    # tab/newline/etc become a single space rather than vanishing.
    text = _FILENAME_WHITESPACE.sub(" ", text)
    # Then strip characters that are illegal in filenames. The
    # control-char range \x00-\x1f is included so NULs and similar
    # bytes are dropped.
    text = _FILENAME_INVALID.sub("", text)
    text = text.strip().strip(".")
    if len(text) > max_length:
        text = text[:max_length].strip()
    return text


def build_filename(title: str, size: str, fallback_id: str) -> str:
    """Compose the output filename: ``"{title} - {size}.jpg"``.

    Falls back to the video ID if the title is empty or sanitizes to
    nothing.
    """
    safe_title = sanitize_filename(title)
    if not safe_title:
        safe_title = fallback_id
    return f"{safe_title} - {size}.jpg"


# ---------------------------------------------------------------------------
# Metadata fetch (for nice filenames)
# ---------------------------------------------------------------------------


@dataclass
class VideoMetadata:
    """Minimal video metadata for naming the downloaded thumbnail."""

    title: str = ""
    video_id: str = ""


def fetch_metadata(ytdlp_path: Path, video_id: str, timeout: float = 10.0) -> VideoMetadata:
    """Return the video title via ``yt-dlp --dump-json``.

    Returns an empty ``VideoMetadata`` on any failure — the caller can
    fall back to using the video ID as the filename.
    """
    if not ytdlp_path.is_file():
        return VideoMetadata(video_id=video_id)

    url = f"https://www.youtube.com/watch?v={video_id}"
    args: list[str] = [
        str(ytdlp_path),
        "--extractor-args", "youtube:player_client=visionos,android,mweb",
        "--dump-json",
        "--no-warnings",
        "--no-progress",
        "--skip-download",
        url,
    ]
    kwargs: dict = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    proc = subprocess.Popen(args, **kwargs)  # noqa: S603
    try:
        stdout, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        return VideoMetadata(video_id=video_id)
    except Exception:
        return VideoMetadata(video_id=video_id)

    if proc.returncode != 0 or not stdout:
        return VideoMetadata(video_id=video_id)

    # The first line of `--dump-json` output is the JSON object;
    # the rest (if any) is yt-dlp's own log.
    first_line = stdout.splitlines()[0].strip() if stdout else ""
    if not first_line.startswith("{"):
        return VideoMetadata(video_id=video_id)

    import json

    try:
        data = json.loads(first_line)
    except json.JSONDecodeError:
        return VideoMetadata(video_id=video_id)

    title = (data.get("title") or "").strip()
    return VideoMetadata(title=title, video_id=video_id)


# ---------------------------------------------------------------------------
# Image download
# ---------------------------------------------------------------------------


@dataclass
class DownloadResult:
    """Outcome of a thumbnail download attempt."""

    success: bool
    saved_path: Path | None
    used_size: str
    bytes_written: int
    error_message: str = ""


# A minimal "fake" JPEG header so callers can verify the bytes look
# like a JPEG even without PIL.
_JPEG_MAGIC = b"\xff\xd8\xff"


def download_thumbnail(
    video_id: str,
    output_dir: Path,
    filename: str,
    requested_size: str,
    timeout: float = 15.0,
) -> DownloadResult:
    """Download a YouTube thumbnail to disk.

    Tries the requested size first; on 404 (size unavailable for this
    video), falls back through smaller sizes until one succeeds.

    Returns a :class:`DownloadResult` describing what happened.
    """
    if not video_id:
        return DownloadResult(
            success=False,
            saved_path=None,
            used_size="",
            bytes_written=0,
            error_message="Video ID boş",
        )
    if requested_size not in ThumbnailSize.ALL:
        return DownloadResult(
            success=False,
            saved_path=None,
            used_size="",
            bytes_written=0,
            error_message=f"Bilinmeyen thumbnail boyutu: {requested_size}",
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    # Try the requested size first, then progressively smaller sizes.
    sizes_to_try = [requested_size] + [
        s for s in ThumbnailSize.ALL if s != requested_size
    ]

    for size in sizes_to_try:
        url = thumbnail_url(video_id, size)
        try:
            data = _fetch_bytes(url, timeout)
        except TimeoutError:
            return DownloadResult(
                success=False,
                saved_path=None,
                used_size="",
                bytes_written=0,
                error_message="Zaman aşımı: YouTube yanıt vermedi",
            )
        except Exception as exc:  # noqa: BLE001
            return DownloadResult(
                success=False,
                saved_path=None,
                used_size="",
                bytes_written=0,
                error_message=f"İndirme hatası: {exc}",
            )

        if data is None:
            # 404 — try the next size.
            continue

        if not data.startswith(_JPEG_MAGIC):
            # Not a valid JPEG. Treat as failure.
            return DownloadResult(
                success=False,
                saved_path=None,
                used_size="size",
                bytes_written=0,
                error_message="Gelen veri JPEG formatında değil",
            )

        safe_filename = sanitize_filename(filename) or f"{video_id}.jpg"
        if not safe_filename.lower().endswith(".jpg"):
            safe_filename = f"{safe_filename}.jpg"
        # Ensure the size label is part of the filename.
        if f"- {size}" not in safe_filename:
            base, dot, ext = safe_filename.rpartition(".")
            if dot:
                safe_filename = f"{base} - {size}.{ext}"
            else:
                safe_filename = f"{safe_filename} - {size}"

        target = output_dir / safe_filename
        target.write_bytes(data)

        return DownloadResult(
            success=True,
            saved_path=target,
            used_size=size,
            bytes_written=len(data),
        )

    return DownloadResult(
        success=False,
        saved_path=None,
        used_size="",
        bytes_written=0,
        error_message="Bu video için hiçbir thumbnail boyutu mevcut değil",
    )


def _fetch_bytes(url: str, timeout: float) -> bytes | None:
    """GET *url* and return the body, or ``None`` for 404.

    Raises:
        TimeoutError: if the request exceeds *timeout*.
        OSError: for other transport-level failures.
    """
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", f"Videcook/0.2 (https://github.com/anilberkayalici/Videcook)")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise

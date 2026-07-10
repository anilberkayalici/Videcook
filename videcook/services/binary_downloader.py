"""Binary downloader — downloads helper executables with progress reporting.

Public API is split into two layers:

* :mod:`videcook.services.binary_downloader` — pure-logic download functions
  (no Qt dependency, usable from CLI and UI).

* The UI wraps these inside a :class:`BinaryDownloadWorker` (QObject + QThread)
  so downloads run off the main thread and emit progress signals.
"""

from __future__ import annotations

import tempfile
import time
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from videcook import __version__

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_YTDLP_URL = (
    "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
)
_FFMPEG_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)

_YTDLP_SOURCE = "github.com/yt-dlp/yt-dlp/releases"
_FFMPEG_SOURCE = "github.com/BtbN/FFmpeg-Builds/releases"

CHUNK = 65536

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class DownloadTask:
    """A single file to download."""

    url: str
    dest: Path
    label: str
    source_display: str  # human-readable source for approval UI


@dataclass
class DownloadProgress:
    """Snapshot of download progress at a given moment."""

    label: str
    percent: float  # 0.0 – 100.0
    downloaded_bytes: int
    total_bytes: int
    speed_bytes: float  # bytes per second
    eta_seconds: float  # -1 if unknown


# ---------------------------------------------------------------------------
# Pure-logic download helpers (no Qt)
# ---------------------------------------------------------------------------


def _download_file(
    task: DownloadTask,
    on_progress: Callable[[DownloadProgress], None] | None = None,
) -> Path:
    """Download *task.url* → *task.dest* with optional progress callback."""
    if task.dest.exists():
        if on_progress:
            dp = DownloadProgress(
                label=task.label,
                percent=100.0,
                downloaded_bytes=task.dest.stat().st_size,
                total_bytes=task.dest.stat().st_size,
                speed_bytes=0.0,
                eta_seconds=0.0,
            )
            on_progress(dp)
        return task.dest

    req = urllib.request.Request(task.url, method="GET")
    req.add_header("User-Agent", f"Videcook/{__version__}")
    total = -1

    with urllib.request.urlopen(req) as resp:
        total = int(resp.headers.get("Content-Length", -1))
        start_time = time.monotonic()
        downloaded = 0
        task.dest.parent.mkdir(parents=True, exist_ok=True)
        buf = memoryview(bytearray(CHUNK))
        with open(task.dest, "wb") as outf:
            while True:
                n = resp.readinto(buf)
                if n == 0:
                    break
                outf.write(buf[:n])
                downloaded += n
                elapsed = time.monotonic() - start_time
                speed = downloaded / elapsed if elapsed > 0 else 0.0
                pct = (downloaded / total * 100.0) if total > 0 else 0.0
                eta = (total - downloaded) / speed if speed > 0 and total > 0 else -1.0
                if on_progress:
                    dp = DownloadProgress(
                        label=task.label,
                        percent=pct,
                        downloaded_bytes=downloaded,
                        total_bytes=total,
                        speed_bytes=speed,
                        eta_seconds=eta,
                    )
                    on_progress(dp)
    return task.dest


def _download_ffmpeg_zip(
    url: str,
    ffmpeg_dest: Path,
    ffprobe_dest: Path,
    on_progress: Callable[[DownloadProgress], None] | None = None,
) -> tuple[Path, Path]:
    """Download FFmpeg ZIP, extract ffmpeg.exe & ffprobe.exe."""
    if ffmpeg_dest.exists() and ffprobe_dest.exists():
        return ffmpeg_dest, ffprobe_dest

    zip_task = DownloadTask(
        url=url,
        dest=Path(tempfile.gettempdir()) / "videcook_ffmpeg.zip",
        label="ffmpeg.zip",
        source_display=_FFMPEG_SOURCE,
    )
    zip_path = _download_file(zip_task, on_progress=on_progress)

    ffmpeg_dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            ffmpeg_member = next(
                (n for n in zf.namelist() if n.endswith("/ffmpeg.exe")), None
            )
            ffprobe_member = next(
                (n for n in zf.namelist() if n.endswith("/ffprobe.exe")), None
            )
            if not ffmpeg_member or not ffprobe_member:
                raise RuntimeError(
                    "Could not find ffmpeg.exe / ffprobe.exe in the archive"
                )
            with tempfile.TemporaryDirectory() as tmp:
                zf.extract(ffmpeg_member, tmp)
                zf.extract(ffprobe_member, tmp)
                import shutil
                shutil.move(str(Path(tmp) / ffmpeg_member), str(ffmpeg_dest))
                shutil.move(str(Path(tmp) / ffprobe_member), str(ffprobe_dest))
    finally:
        try:
            zip_path.unlink(missing_ok=True)
        except OSError:
            pass

    return ffmpeg_dest, ffprobe_dest


# ---------------------------------------------------------------------------
# High-level task builders
# ---------------------------------------------------------------------------


def build_ytdlp_tasks(bin_dir: Path) -> list[DownloadTask]:
    """Return the task(s) needed to obtain yt-dlp."""
    return [
        DownloadTask(
            url=_YTDLP_URL,
            dest=bin_dir / "yt-dlp.exe",
            label="yt-dlp.exe",
            source_display=_YTDLP_SOURCE,
        )
    ]


def build_ffmpeg_tasks(bin_dir: Path) -> tuple[Path, Path]:
    """Return the (ffmpeg_dest, ffprobe_dest) pair for FFmpeg download."""
    return (bin_dir / "ffmpeg.exe", bin_dir / "ffprobe.exe")


def get_ffmpeg_url() -> str:
    return _FFMPEG_URL


def get_expected_size() -> dict[str, int]:
    """Estimated download sizes in bytes. Actual values vary per release."""
    return {
        "yt-dlp.exe": 15 * 1024 * 1024,    # ~15 MB
        "ffmpeg.zip": 90 * 1024 * 1024,    # ~90 MB (compressed)
    }


def get_total_size_mb() -> float:
    sizes = get_expected_size()
    return sum(sizes.values()) / (1024 * 1024)


# ---------------------------------------------------------------------------
# Qt worker (UI-thread-safe)
# ---------------------------------------------------------------------------

from PySide6.QtCore import QObject, Signal, Slot


class BinaryDownloadWorker(QObject):
    """QObject that downloads binaries on a QThread with progress signals."""

    progress_changed = Signal(float)       # 0.0 – 100.0 global
    status_changed = Signal(str)           # human-readable status
    log_message = Signal(str)              # per-file log lines
    finished = Signal(bool, str)           # success, message
    file_progress = Signal(object)         # DownloadProgress

    def __init__(
        self,
        bin_dir: Path,
        download_ytdlp: bool = True,
        download_ffmpeg: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._bin_dir = bin_dir
        self._download_ytdlp = download_ytdlp
        self._download_ffmpeg = download_ffmpeg
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        self._bin_dir.mkdir(parents=True, exist_ok=True)
        tasks: list[tuple[DownloadTask, str]] = []  # (task, kind)
        ffmpeg_url = _FFMPEG_URL
        ffmpeg_dest = self._bin_dir / "ffmpeg.exe"
        ffprobe_dest = self._bin_dir / "ffprobe.exe"

        if self._download_ytdlp:
            for t in build_ytdlp_tasks(self._bin_dir):
                tasks.append((t, "ytdlp"))

        if self._download_ffmpeg and not (ffmpeg_dest.exists() and ffprobe_dest.exists()):
            tasks.append(
                (
                    DownloadTask(
                        url=ffmpeg_url,
                        dest=Path(tempfile.gettempdir()) / "videcook_ffmpeg.zip",
                        label="ffmpeg.zip",
                        source_display=_FFMPEG_SOURCE,
                    ),
                    "ffmpeg_zip",
                )
            )

        total_tasks = len(tasks)
        if total_tasks == 0:
            self.finished.emit(True, "All binaries already present.")
            return

        for idx, (task, kind) in enumerate(tasks):
            if self._cancelled:
                self.finished.emit(False, "Download cancelled.")
                return

            self.log_message.emit(f"Downloading {task.label} from {task.source_display}...")
            try:
                if kind == "ffmpeg_zip":
                    _download_ffmpeg_zip(
                        ffmpeg_url, ffmpeg_dest, ffprobe_dest,
                        on_progress=lambda dp: self._on_file_progress(dp, idx, total_tasks),
                    )
                else:
                    _download_file(
                        task,
                        on_progress=lambda dp: self._on_file_progress(dp, idx, total_tasks),
                    )
            except Exception as exc:
                self.log_message.emit(f"Failed: {exc}")
                self.finished.emit(False, str(exc))
                return

        self.progress_changed.emit(100.0)
        self.status_changed.emit("All binaries ready.")
        self.log_message.emit("All binaries downloaded successfully.")
        self.finished.emit(True, "All binaries ready.")

    def cancel(self) -> None:
        self._cancelled = True

    def _on_file_progress(
        self, dp: DownloadProgress, file_index: int, total_files: int
    ) -> None:
        if total_files <= 1:
            overall = dp.percent
        else:
            overall = (file_index * 100.0 + dp.percent) / total_files
        self.progress_changed.emit(overall)
        self.file_progress.emit(dp)

        pct = dp.percent
        speed = _format_speed(dp.speed_bytes)
        eta = _format_eta(dp.eta_seconds)
        parts = [f"{dp.label}: {pct:.0f}%"]
        if speed:
            parts.append(speed)
        if eta:
            parts.append(f"ETA {eta}")
        self.status_changed.emit(" | ".join(parts))


def _format_speed(bytes_per_sec: float) -> str:
    if bytes_per_sec <= 0:
        return ""
    if bytes_per_sec >= 1_000_000:
        return f"{bytes_per_sec / 1_000_000:.1f} MB/s"
    if bytes_per_sec >= 1_000:
        return f"{bytes_per_sec / 1_000:.0f} KB/s"
    return f"{bytes_per_sec:.0f} B/s"


def _format_eta(seconds: float) -> str:
    if seconds <= 0:
        return ""
    m, s = divmod(int(seconds), 60)
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"

"""Videcook services package."""

from videcook.services.binary_downloader import (
    BinaryDownloadWorker,
    DownloadProgress,
    DownloadTask,
    build_ffmpeg_tasks,
    build_ytdlp_tasks,
    get_total_size_mb,
)
from videcook.services.binary_locator import BinaryStatus, check_binaries
from videcook.services.download_process import (
    DownloadProcessResult,
    create_process,
    stream_lines,
    wait_process,
)
from videcook.services.update_checker import (
    UpdateStatus,
    check_for_updates,
    get_current_version,
    perform_update,
)

__all__ = [
    "BinaryDownloadWorker",
    "BinaryStatus",
    "DownloadProcessResult",
    "DownloadProgress",
    "DownloadTask",
    "UpdateStatus",
    "build_ffmpeg_tasks",
    "build_ytdlp_tasks",
    "check_binaries",
    "check_for_updates",
    "create_process",
    "get_current_version",
    "get_total_size_mb",
    "perform_update",
    "stream_lines",
    "wait_process",
]

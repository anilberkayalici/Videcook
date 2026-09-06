"""Qt workers for thumbnail preview and download.

Two workers, both off the UI thread:

* :class:`ThumbnailPreviewWorker` — fetches the MaxRes thumbnail bytes
  for a video ID so the page can show a small preview. Cancels itself
  if a new preview is requested before this one finishes.

* :class:`ThumbnailDownloadWorker` — resolves the video title via
  yt-dlp, then downloads the requested thumbnail size (with fallback
  to smaller sizes on 404). Emits progress and result signals.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from videcook.core.thumbnail import (
    ThumbnailSize,
    build_filename,
    download_thumbnail,
    extract_video_id,
    fetch_metadata,
    thumbnail_url,
)
from videcook.services.binary_locator import check_binaries


class ThumbnailPreviewWorker(QObject):
    """Fetch preview bytes for the MaxRes thumbnail of a video."""

    # Emitted with the raw JPEG bytes and the video ID.
    preview_ready = Signal(str, bytes)
    # Emitted when the preview cannot be loaded.
    preview_failed = Signal(str, str)
    # Emitted when work starts (so the UI can show a spinner).
    preview_started = Signal(str)

    def __init__(
        self,
        video_id: str,
        timeout: float = 10.0,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._video_id = video_id
        self._timeout = timeout
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        if self._cancelled or not self._video_id:
            return
        self.preview_started.emit(self._video_id)
        url = thumbnail_url(self._video_id, ThumbnailSize.MAXRES)
        try:
            import urllib.error
            import urllib.request

            req = urllib.request.Request(url, method="GET")
            req.add_header(
                "User-Agent",
                "Videcook/0.2 (https://github.com/anilberkayalici/Videcook)",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = resp.read()
        except Exception as exc:  # noqa: BLE001
            if self._cancelled:
                return
            self.preview_failed.emit(self._video_id, str(exc))
            return
        if self._cancelled:
            return
        self.preview_ready.emit(self._video_id, data)

    def cancel(self) -> None:
        self._cancelled = True


class ThumbnailDownloadWorker(QObject):
    """Download a thumbnail to disk, with progress and result signals."""

    # Step indicators.
    download_started = Signal(str)  # video_id
    metadata_fetched = Signal(str, str)  # video_id, title
    download_progress = Signal(int)  # 0..100
    log_message = Signal(str)
    finished = Signal(bool, str)  # success, message

    def __init__(
        self,
        video_id: str,
        output_dir: Path,
        size: str,
        timeout: float = 15.0,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._video_id = video_id
        self._output_dir = output_dir
        self._size = size
        self._timeout = timeout
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        if self._cancelled:
            return
        if not self._video_id:
            self.finished.emit(False, "Video ID bulunamadı")
            return

        self.download_started.emit(self._video_id)
        self.log_message.emit(
            f"Thumbnail indiriliyor: {self._video_id} (boyut: {self._size})"
        )

        # Resolve a friendly filename via yt-dlp metadata, falling back
        # to the raw video ID.
        title = ""
        status = check_binaries()
        if status.is_ready and status.ytdlp_path is not None:
            self.log_message.emit("Video başlığı alınıyor...")
            try:
                meta = fetch_metadata(status.ytdlp_path, self._video_id, timeout=10.0)
                title = meta.title
            except Exception as exc:  # noqa: BLE001
                self.log_message.emit(f"Başlık alınamadı: {exc}")
        if self._cancelled:
            return

        if title:
            self.metadata_fetched.emit(self._video_id, title)

        filename = build_filename(title, self._size, self._video_id)
        self.log_message.emit(f"Hedef: {self._output_dir / filename}")

        self.download_progress.emit(10)

        try:
            result = download_thumbnail(
                video_id=self._video_id,
                output_dir=self._output_dir,
                filename=filename,
                requested_size=self._size,
                timeout=self._timeout,
            )
        except Exception as exc:  # noqa: BLE001
            self.finished.emit(False, f"İndirme başarısız: {exc}")
            return

        if self._cancelled:
            return

        self.download_progress.emit(100)

        if result.success and result.saved_path is not None:
            self.saved_path = result.saved_path
            self.bytes_written = result.bytes_written
            size_label = ThumbnailSize.LABELS.get(result.used_size, result.used_size)
            self.finished.emit(
                True,
                f"Thumbnail kaydedildi: {result.saved_path} "
                f"({result.bytes_written // 1024} KB, {size_label})",
            )
        else:
            self.saved_path = None
            self.bytes_written = 0
            self.finished.emit(False, result.error_message or "İndirme başarısız")

    def cancel(self) -> None:
        self._cancelled = True

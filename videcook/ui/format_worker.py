"""Qt worker for fetching available video formats asynchronously."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot
from pathlib import Path
from videcook.services.binary_locator import check_binaries
from videcook.services.format_parser import fetch_available_formats


class FormatFetchWorker(QObject):
    """Fetch available resolutions from yt-dlp off the UI thread."""

    # Emitted with the list of formats (e.g. ["8K (4320p)", ...])
    formats_ready = Signal(list)
    # Emitted when fetching fails or returns empty, giving a chance to fallback
    formats_failed = Signal()

    def __init__(
        self,
        url: str,
        timeout: float = 15.0,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._url = url
        self._timeout = timeout
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        if self._cancelled or not self._url:
            self.formats_failed.emit()
            return

        status = check_binaries()
        if not status.is_ready or status.ytdlp_path is None:
            self.formats_failed.emit()
            return

        formats = fetch_available_formats(status.ytdlp_path, self._url, self._timeout)
        
        if self._cancelled:
            return

        if formats:
            self.formats_ready.emit(formats)
        else:
            self.formats_failed.emit()

    def cancel(self) -> None:
        self._cancelled = True

"""Background worker for a subtitle creation job."""

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot


class SubtitleWorker(QObject):
    progress_changed = Signal(int)
    status_changed = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, pipeline, source: Path, destination: Path) -> None:
        super().__init__()
        self._pipeline = pipeline
        self._source = source
        self._destination = destination
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        try:
            self._pipeline.create_srt(
                self._source,
                self._destination,
                on_progress=self._on_progress,
                is_cancelled=lambda: self._cancelled,
            )
            self.finished.emit(True, str(self._destination))
        except Exception as exc:
            self.finished.emit(False, str(exc))

    def cancel(self) -> None:
        self._cancelled = True

    def _on_progress(self, value: int, message: str) -> None:
        self.progress_changed.emit(value)
        self.status_changed.emit(message)

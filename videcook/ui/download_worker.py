"""Qt download worker — runs yt-dlp off the main thread.

Signals are emitted in response to parsed progress lines so the UI stays responsive.
"""

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from videcook.core.command_builder import build_ytdlp_command
from videcook.core.models import DownloadRequest
from videcook.core.progress_parser import parse_progress_line
from videcook.paths import get_ffmpeg_path, get_ytdlp_path
from videcook.services.binary_locator import check_binaries
from videcook.services.download_process import (
    create_process,
    stream_lines,
    wait_process,
)
from videcook.utils.i18n import LanguageManager


class DownloadWorker(QObject):
    """Off-thread worker that owns a yt-dlp subprocess and streams progress."""

    # -- signals --
    progress_changed = Signal(int)
    status_changed = Signal(str)
    log_message = Signal(str)
    finished = Signal(bool, str)
    error_message = Signal(str)

    def __init__(
        self,
        request: DownloadRequest,
        i18n: LanguageManager,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._request = request
        self._i18n = i18n
        self._process = None
        self._cancelled = False

    # ---- public ------------------------------------------------------------

    @Slot()
    def run(self) -> None:
        """Entry point — called when the worker thread starts."""
        t = self._i18n.get_text

        # 1. Check binaries
        self.log_message.emit(t("log.checking_binaries"))
        status = check_binaries()
        self.log_message.emit(status.to_display())
        if not status.is_ready:
            msg = t("error.binaries_missing").format(bin_dir=str(status.ytdlp_path.parent))
            self.error_message.emit(msg)
            self.finished.emit(False, msg)
            return

        # 2. Build command
        self.log_message.emit(t("log.building_command"))
        try:
            cmd_result = build_ytdlp_command(
                self._request,
                ytdlp_path=get_ytdlp_path(),
                ffmpeg_location=get_ffmpeg_path().parent,
            )
        except Exception as exc:
            self.error_message.emit(str(exc))
            self.finished.emit(False, str(exc))
            return

        self.log_message.emit(cmd_result.redacted_display)
        self.status_changed.emit(t("status.downloading"))

        # 3. Launch subprocess
        try:
            self._process = create_process(cmd_result.args)
        except Exception as exc:
            msg = t("error.download_failed").format(message=str(exc))
            self.error_message.emit(msg)
            self.finished.emit(False, msg)
            return

        # 4. Stream lines
        stream_lines(
            self._process.stdout,
            on_line=self._handle_line,
            check_cancelled=self._is_cancelled,
        )

        # 5. Wait and report
        result = wait_process(self._process, cancelled=self._cancelled)

        if result.cancelled:
            self.status_changed.emit(t("status.cancelled"))
            self.log_message.emit(t("log.download_cancelled"))
            self.finished.emit(False, t("log.download_cancelled"))
        elif result.success:
            self.progress_changed.emit(100)
            self.status_changed.emit(t("status.completed"))
            self.log_message.emit(t("log.download_completed"))
            self.finished.emit(True, t("log.download_completed"))
        else:
            self.status_changed.emit(t("status.error"))
            self.log_message.emit(result.message)
            self.finished.emit(False, result.message)

        # Clear sensitive state
        self._clear_sensitive_state()

    def cancel(self) -> None:
        """Request cancellation. The running subprocess is terminated."""
        self._cancelled = True
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
        self._clear_sensitive_state()

    # ---- internal -----------------------------------------------------------

    def _is_cancelled(self) -> bool:
        return self._cancelled

    def _handle_line(self, line: str) -> None:
        parsed = parse_progress_line(line)

        if parsed["type"] == "download_progress":
            pct = int(float(str(parsed.get("percent", 0))))
            self.progress_changed.emit(pct)
            detail_parts = [f"{pct}%"]
            speed = parsed.get("speed")
            eta = parsed.get("eta")
            if speed is not None:
                detail_parts.append(f"{speed}")
            if eta is not None:
                detail_parts.append(f"ETA {eta}")
            self.status_changed.emit(" | ".join(detail_parts))

        elif parsed["type"] == "download_completed":
            self.progress_changed.emit(100)
            self.status_changed.emit(self._i18n.get_text("status.completed"))

        elif parsed["type"] == "postprocess":
            self.log_message.emit(line)

        else:
            # destination, log, etc. — show in log area
            if line.strip():
                self.log_message.emit(line)

    def _clear_sensitive_state(self) -> None:
        """Remove any lingering cookie path references from memory."""
        self._request.cookie_file = Path(".")

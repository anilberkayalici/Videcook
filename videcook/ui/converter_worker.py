"""Qt worker for FFmpeg conversions."""
import re
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot
from videcook.core.converter_builder import ConverterRequest, build_ffmpeg_command
from videcook.services.binary_locator import check_binaries
from videcook.services.download_process import create_process, stream_lines, wait_process
from videcook.utils.i18n import LanguageManager
from videcook.core.document_converter import convert_document

class ConverterWorker(QObject):
    progress_changed = Signal(int)
    status_changed = Signal(str)
    log_message = Signal(str)
    finished = Signal(bool, str, str) # success, message, output_path
    error_message = Signal(str)

    def __init__(self, request: ConverterRequest, i18n: LanguageManager, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._request = request
        self._i18n = i18n
        self._process = None
        self._cancelled = False
        self._error_lines = []

    @Slot()
    def run(self) -> None:
        t = self._i18n.get_text
        self._error_lines.clear()

        try:
            self._do_run(t)
        finally:
            pass

    def _do_run(self, t) -> None:
        in_ext = self._request.input_file.suffix.lower()
        if in_ext in ['.pdf', '.docx', '.pptx', '.xlsx']:
            self._do_run_document(t)
            return

        self.log_message.emit(t("log.checking_binaries"))
        status = check_binaries()
        if not status.is_ready or status.ffmpeg_path is None:
            msg = t("converter.ffmpeg_missing")
            self.error_message.emit(msg)
            self.finished.emit(False, msg, "")
            return

        ffmpeg_exe = status.ffmpeg_path.parent / "ffmpeg.exe" if status.ffmpeg_path.is_file() else status.ffmpeg_path
        if not ffmpeg_exe.exists():
            ffmpeg_exe = status.ffmpeg_path # fallback

        try:
            cmd_result = build_ffmpeg_command(self._request, ffmpeg_exe)
        except Exception as exc:
            self.error_message.emit(str(exc))
            self.finished.emit(False, str(exc), "")
            return

        self.log_message.emit(cmd_result.redacted_display)
        self.status_changed.emit(t("converter.status_converting"))

        try:
            self._process = create_process(cmd_result.args)
        except Exception as exc:
            self.error_message.emit(str(exc))
            self.finished.emit(False, str(exc), "")
            return

        stream_lines(
            self._process.stdout,
            on_line=self._handle_line,
            check_cancelled=self._is_cancelled,
        )

        result = wait_process(self._process, cancelled=self._cancelled)

        if result.cancelled:
            self.status_changed.emit(t("status.cancelled"))
            self.log_message.emit(t("status.cancelled"))
            self.finished.emit(False, t("status.cancelled"), "")
        elif result.success:
            self.progress_changed.emit(100)
            self.status_changed.emit(t("converter.status_completed"))
            self.log_message.emit(t("converter.status_completed"))
            out_path = str(self._request.output_file.parent) if self._request.split_channels else str(self._request.output_file)
            self.finished.emit(True, t("converter.status_completed"), out_path)
        else:
            self.status_changed.emit(t("converter.status_error"))
            last = self._error_lines[-1] if self._error_lines else f"Exit code {result.return_code}"
            self.log_message.emit(last)
            self.finished.emit(False, last, "")

    def cancel(self) -> None:
        self._cancelled = True
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()

    def _is_cancelled(self) -> bool:
        return self._cancelled

    def _handle_line(self, line: str) -> None:
        if line.strip():
            # FFmpeg uses progress output, we could parse time=... for progress, but for simplicity we just log
            if "out_time=" in line or "frame=" in line or "fps=" in line:
                pass # avoid spamming log
            else:
                self.log_message.emit(line)
            if "error" in line.lower() or "invalid" in line.lower() or "unsupported" in line.lower():
                self._error_lines.append(line.strip())

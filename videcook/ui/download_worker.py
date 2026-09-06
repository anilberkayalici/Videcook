"""Qt download worker — runs yt-dlp off the main thread.

Signals are emitted in response to parsed progress lines so the UI stays responsive.
"""

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from videcook.core.command_builder import build_ytdlp_command
from videcook.core.models import DownloadRequest
from videcook.core.progress_parser import parse_progress_line
from videcook.services.binary_locator import check_binaries
from videcook.services.download_process import (
    create_process,
    stream_lines,
    wait_process,
)
from videcook.utils.error_parser import translate_error
from videcook.utils.i18n import LanguageManager


class DownloadWorker(QObject):
    """Off-thread worker that owns a yt-dlp subprocess and streams progress."""

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
        self._error_lines: list[str] = []
        self._playlist_current = 1
        self._playlist_total = 1
        self._playlist_is_active = False

    @Slot()
    def run(self) -> None:
        t = self._i18n.get_text
        self._error_lines.clear()

        try:
            self._do_run(t)
        finally:
            self._clear_sensitive_state()

    def _do_run(self, t) -> None:
        self.log_message.emit(t("log.checking_binaries"))
        status = check_binaries()
        self.log_message.emit(status.to_display())
        if not status.is_ready:
            msg = t("error.binaries_missing").format(bin_dir=str(status.ytdlp_path.parent))
            self.error_message.emit(msg)
            self.finished.emit(False, msg)
            return

        self.log_message.emit(t("log.building_command"))
        try:
            cmd_result = build_ytdlp_command(
                self._request,
                ytdlp_path=status.ytdlp_path,
                ffmpeg_location=status.ffmpeg_path.parent,
            )
        except Exception as exc:
            self.error_message.emit(str(exc))
            self.finished.emit(False, str(exc))
            return

        self.log_message.emit(cmd_result.redacted_display)
        self.status_changed.emit(t("status.downloading"))

        try:
            self._process = create_process(cmd_result.args)
        except Exception as exc:
            msg = t("error.download_failed").format(message=str(exc))
            self.error_message.emit(msg)
            self.finished.emit(False, msg)
            return

        stream_lines(
            self._process.stdout,
            on_line=self._handle_line,
            check_cancelled=self._is_cancelled,
        )

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
            friendly = self._build_friendly_error(t)
            self.finished.emit(False, friendly)

    def cancel(self) -> None:
        """Request cancellation. The running subprocess is terminated."""
        self._cancelled = True
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
        self._clear_sensitive_state()

    def _build_friendly_error(self, t) -> str:
        combined = " ".join(self._error_lines) if self._error_lines else ""
        key = translate_error(combined)
        if key:
            return t(key)
        last = self._error_lines[-1] if self._error_lines else t("error.unknown")
        return f"{t('error.download_failed').format(message=last)}"

    # ---- internal -----------------------------------------------------------

    def _is_cancelled(self) -> bool:
        return self._cancelled

    def _handle_line(self, line: str) -> None:
        parsed = parse_progress_line(line)

        if parsed["type"] == "playlist_item":
            self._playlist_current = parsed["current"]
            self._playlist_total = parsed["total"]
            self._playlist_is_active = True
            t = self._i18n.get_text
            self.log_message.emit(
                t("log.playlist_video").format(
                    current=self._playlist_current,
                    total=self._playlist_total,
                )
            )
            self.status_changed.emit(
                f"Video {self._playlist_current}/{self._playlist_total}"
            )

        elif parsed["type"] == "playlist_finished":
            self._playlist_is_active = False
            self.log_message.emit(line)

        elif parsed["type"] == "download_progress":
            pct = int(float(str(parsed.get("percent", 0))))
            speed = parsed.get("speed")
            eta = parsed.get("eta")

            if self._playlist_is_active and self._playlist_total > 1:
                overall = _playlist_overall(
                    self._playlist_current, self._playlist_total, pct
                )
                self.progress_changed.emit(overall)
                parts = [
                    f"Video {self._playlist_current}/{self._playlist_total}",
                    f"{pct}%",
                ]
            else:
                self.progress_changed.emit(pct)
                parts = [f"{pct}%"]

            total = parsed.get("total")
            if speed is not None:
                speed = speed.replace("MiB", "Mb").replace("KiB", "Kb").replace("GiB", "Gb")
                parts.append(f"{speed}")
            if eta is not None:
                parts.append(f"Kalan {eta}")
            if total is not None:
                import re
                m = re.match(r"([\d\.]+)([a-zA-Z]+)", total)
                if m:
                    try:
                        val = int(float(m.group(1)))
                        unit = m.group(2).upper()
                        if "K" in unit: u = "Kb"
                        elif "M" in unit: u = "Mb"
                        elif "G" in unit: u = "Gb"
                        else: u = "b"
                        parts.append(f"Boyut: {val} {u}")
                    except:
                        parts.append(f"Boyut: {total}")
                else:
                    parts.append(f"Boyut: {total}")
            self.status_changed.emit(" | ".join(parts))

        elif parsed["type"] == "download_completed":
            if self._playlist_is_active:
                overall = _playlist_overall(
                    self._playlist_current, self._playlist_total, 100
                )
                self.progress_changed.emit(overall)
            else:
                self.progress_changed.emit(100)
            self.status_changed.emit(self._i18n.get_text("status.completed"))

        elif parsed["type"] == "postprocess":
            self.log_message.emit(line)

        else:
            if line.strip():
                self.log_message.emit(line)
                lower = line.lower()
                if any(kw in lower for kw in (
                    "error", "unable", "fail", "403", "404", "429",
                    "unavailable", "not found", "forbidden",
                )):
                    self._error_lines.append(line.strip())

    def _clear_sensitive_state(self) -> None:
        """Remove any lingering cookie path references from memory."""
        if self._request.cookie_file is not None:
            self._request.cookie_file = Path(".")


def _playlist_overall(current: int, total: int, video_pct: float) -> int:
    """Combine per-video and playlist progress into a single percentage."""
    if total <= 1:
        return int(video_pct)
    base = (current - 1) / total * 100.0
    increment = video_pct / total
    return int(base + increment)

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


class YtdlpSubtitleDownloadWorker(QObject):
    """Downloads YouTube subtitles via yt-dlp asynchronously."""
    progress = Signal(int)
    log_message = Signal(str)
    finished = Signal(bool, str, str)  # (success, message, saved_file_path)

    def __init__(
        self,
        url: str,
        lang: str,
        sub_format: str,
        output_folder: Path,
        ytdlp_path: Path,
        cookie_file: Path | None = None,
    ) -> None:
        super().__init__()
        self._url = url
        self._lang = lang
        self._sub_format = sub_format
        self._output_folder = output_folder
        self._ytdlp_path = ytdlp_path
        self._cookie_file = cookie_file
        self._cancelled = False
        self._process = None

    @Slot()
    def run(self) -> None:
        import os
        import subprocess

        cmd = [
            str(self._ytdlp_path),
            "--skip-download",
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs", self._lang,
            "--convert-subs", self._sub_format,
            "-P", str(self._output_folder),
        ]
        if self._cookie_file and self._cookie_file.is_file():
            cmd.extend(["--cookies", str(self._cookie_file)])
        cmd.append(self._url)

        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        try:
            self.progress.emit(20)
            self.log_message.emit(f"Altyazı indiriliyor ({self._lang}, {self._sub_format.upper()})...")

            kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "text": True,
                "encoding": "utf-8",
                "errors": "replace",
                "env": env,
            }
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            self._process = subprocess.Popen(cmd, **kwargs)
            saved_files: list[str] = []

            if self._process.stdout:
                for line in self._process.stdout:
                    if self._cancelled:
                        break
                    line_str = line.strip()
                    if line_str:
                        self.log_message.emit(line_str)
                        if "Destination:" in line_str:
                            parts = line_str.split("Destination:", 1)
                            if len(parts) > 1:
                                saved_files.append(parts[1].strip())
                        elif "Writing video subtitles to:" in line_str:
                            parts = line_str.split("Writing video subtitles to:", 1)
                            if len(parts) > 1:
                                saved_files.append(parts[1].strip())

            self._process.wait()
            if self._cancelled:
                self.finished.emit(False, "Altyazı indirme iptal edildi", "")
                return

            if self._process.returncode == 0:
                self.progress.emit(100)
                target_ext = f".{self._sub_format.lower()}"
                actual_path = ""
                if saved_files:
                    for sf in saved_files:
                        p = Path(sf)
                        if p.is_file():
                            actual_path = str(p.resolve())
                            break

                if not actual_path and self._output_folder.is_dir():
                    matching = [
                        f for f in self._output_folder.iterdir()
                        if f.is_file() and f.suffix.lower() == target_ext
                    ]
                    if matching:
                        newest = max(matching, key=lambda f: f.stat().st_mtime)
                        actual_path = str(newest.resolve())

                if actual_path:
                    self.finished.emit(True, f"Altyazı başarıyla indirildi: {actual_path}", actual_path)
                else:
                    self.finished.emit(True, "Altyazı indirme tamamlandı", "")
            else:
                self.finished.emit(False, f"Altyazı indirilemedi (Çıkış kodu {self._process.returncode})", "")
        except Exception as exc:
            self.finished.emit(False, f"Hata: {exc}", "")

    def cancel(self) -> None:
        self._cancelled = True
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass

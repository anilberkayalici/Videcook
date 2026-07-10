"""Screen for creating an English SRT file from an audio file."""

from pathlib import Path

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QProgressBar,
    QPushButton, QVBoxLayout, QWidget,
)

from videcook.services.binary_locator import check_binaries
from videcook.services.groq_transcription import GroqTranscriptionClient
from videcook.services.secure_store import load_groq_api_key
from videcook.services.subtitle_pipeline import SubtitlePipeline
from videcook.ui.subtitle_worker import SubtitleWorker
from videcook.utils.i18n import LanguageManager


class SubtitlePage(QWidget):
    """User-facing English audio to SRT workflow."""

    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._source: Path | None = None
        self._destination: Path | None = None
        self._thread: QThread | None = None
        self._worker: SubtitleWorker | None = None
        self._build_ui()
        self.retranslate()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 30)
        layout.setSpacing(18)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        card = QWidget()
        card.setObjectName("settingsCard")
        form = QVBoxLayout(card)
        form.setContentsMargins(24, 22, 24, 24)
        form.setSpacing(14)
        self._title = QLabel(); self._title.setObjectName("pageTitle"); form.addWidget(self._title)
        self._hint = QLabel(); self._hint.setObjectName("appTagline"); self._hint.setWordWrap(True); form.addWidget(self._hint)
        self._source_label = QLabel(); self._source_label.setObjectName("fieldLabel"); form.addWidget(self._source_label)
        self._source_input = QLineEdit(); self._source_input.setReadOnly(True); self._source_input.setMinimumHeight(44)
        self._source_browse = QPushButton(); self._source_browse.setObjectName("output_browse_button"); self._source_browse.clicked.connect(self._browse_source)
        source_row = QHBoxLayout(); source_row.addWidget(self._source_input, 1); source_row.addWidget(self._source_browse); form.addLayout(source_row)
        self._output_label = QLabel(); self._output_label.setObjectName("fieldLabel"); form.addWidget(self._output_label)
        self._output_input = QLineEdit(); self._output_input.setReadOnly(True); self._output_input.setMinimumHeight(44)
        self._output_browse = QPushButton(); self._output_browse.setObjectName("output_browse_button"); self._output_browse.clicked.connect(self._browse_output)
        output_row = QHBoxLayout(); output_row.addWidget(self._output_input, 1); output_row.addWidget(self._output_browse); form.addLayout(output_row)
        self._status = QLabel(); self._status.setObjectName("status_label"); form.addWidget(self._status)
        self._progress = QProgressBar(); self._progress.setRange(0, 100); self._progress.setValue(0); self._progress.setMinimumHeight(30); form.addWidget(self._progress)
        actions = QHBoxLayout(); actions.addStretch(1)
        self._cancel = QPushButton(); self._cancel.setObjectName("cancel_button"); self._cancel.setEnabled(False); self._cancel.clicked.connect(self._cancel_job); actions.addWidget(self._cancel)
        self._start = QPushButton(); self._start.setObjectName("download_button"); self._start.clicked.connect(self._start_job); actions.addWidget(self._start)
        form.addLayout(actions); layout.addWidget(card)

    def set_i18n(self, i18n: LanguageManager) -> None:
        self._i18n = i18n; self.retranslate()

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._title.setText(t("subtitle.title")); self._hint.setText(t("subtitle.hint")); self._source_label.setText(t("subtitle.source")); self._output_label.setText(t("subtitle.output")); self._source_browse.setText(t("action.browse")); self._output_browse.setText(t("action.browse")); self._start.setText(t("subtitle.create")); self._cancel.setText(t("action.cancel"))
        if not self._worker: self._status.setText(t("status.ready"))

    def _browse_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select audio", "", "Audio files (*.mp3 *.m4a *.wav *.ogg *.flac *.webm);;All files (*)")
        if path:
            self._source = Path(path); self._source_input.setText(path)
            self._destination = self._source.with_suffix(".srt"); self._output_input.setText(str(self._destination))

    def _browse_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save SRT", str(self._destination or "subtitles.srt"), "SRT files (*.srt)")
        if path:
            self._destination = Path(path); self._output_input.setText(path)

    def _start_job(self) -> None:
        t = self._i18n.get_text
        if not self._source or not self._destination:
            QMessageBox.warning(self, t("app.name"), t("subtitle.select_source")); return
        api_key = load_groq_api_key()
        if not api_key:
            QMessageBox.warning(self, t("app.name"), t("subtitle.api_key_missing")); return
        binaries = check_binaries()
        if not binaries.ffmpeg_exists or not binaries.ffprobe_exists:
            QMessageBox.warning(self, t("app.name"), t("error.ffmpeg_missing")); return

        self._cancel_previous_job()

        pipeline = SubtitlePipeline(
            binaries.ffmpeg_path,
            binaries.ffprobe_path,
            GroqTranscriptionClient(api_key, get_text=self._i18n.get_text),
            get_text=self._i18n.get_text,
        )
        self._thread = QThread()
        self._worker = SubtitleWorker(pipeline, self._source, self._destination)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress_changed.connect(self._progress.setValue)
        self._worker.status_changed.connect(self._status.setText)
        self._worker.finished.connect(self._finish_job)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker)
        self._start.setEnabled(False)
        self._cancel.setEnabled(True)
        self._thread.start()

    def _cancel_previous_job(self) -> None:
        if self._worker:
            self._worker.cancel()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(5000)
        self._worker = None
        self._thread = None

    def _cancel_job(self) -> None:
        if self._worker: self._worker.cancel()
        self._cancel.setEnabled(False)

    def _finish_job(self, success: bool, message: str) -> None:
        self._start.setEnabled(True); self._cancel.setEnabled(False)
        if success:
            self._status.setText(self._i18n.get_text("subtitle.done")); QMessageBox.information(self, self._i18n.get_text("app.name"), self._i18n.get_text("subtitle.done_message").format(path=message))
        else:
            self._status.setText(self._i18n.get_text("status.error")); QMessageBox.warning(self, self._i18n.get_text("app.name"), message)

    def _clear_worker(self) -> None:
        self._worker = None; self._thread = None

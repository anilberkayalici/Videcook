"""Screen for creating an English SRT file from an audio file."""

from pathlib import Path

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QProgressBar,
    QPushButton, QVBoxLayout, QWidget, QScrollArea, QFrame, QSpacerItem, QSizePolicy
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
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("settingsScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        self._scroll.setWidget(content)
        outer_layout.addWidget(self._scroll)

        # Center everything inside the scroll area
        page_layout = QVBoxLayout(content)
        page_layout.setContentsMargins(40, 40, 40, 40)
        page_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        from videcook.ui.widgets import ModernCard
        self._card = ModernCard()
        self._card.setMaximumWidth(600)
        self._card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        
        card_layout = self._card.layout()
        card_layout.setSpacing(24)
        card_layout.setContentsMargins(32, 32, 32, 32)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        self._title = QLabel()
        self._title.setObjectName("appTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint = QLabel()
        self._hint.setObjectName("mutedText")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setWordWrap(True)
        header_layout.addWidget(self._title)
        header_layout.addWidget(self._hint)
        card_layout.addLayout(header_layout)

        # File Selection Panel
        file_panel = QWidget()
        file_panel.setObjectName("advPanel")
        file_layout = QVBoxLayout(file_panel)
        file_layout.setContentsMargins(16, 16, 16, 16)
        file_layout.setSpacing(16)

        # Source Audio
        source_layout = QVBoxLayout()
        source_layout.setSpacing(6)
        self._source_label = QLabel()
        self._source_label.setObjectName("fieldLabel")
        source_layout.addWidget(self._source_label)
        
        source_row = QHBoxLayout()
        source_row.setSpacing(8)
        self._source_input = QLineEdit()
        self._source_input.setObjectName("output_path_input")
        self._source_input.setReadOnly(True)
        self._source_input.setMinimumHeight(44)
        self._source_browse = QPushButton()
        self._source_browse.setObjectName("cookie_browse_button")
        self._source_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self._source_browse.setFixedSize(100, 44)
        self._source_browse.clicked.connect(self._browse_source)
        source_row.addWidget(self._source_input, stretch=1)
        source_row.addWidget(self._source_browse)
        source_layout.addLayout(source_row)
        file_layout.addLayout(source_layout)

        # Output SRT
        output_layout = QVBoxLayout()
        output_layout.setSpacing(6)
        self._output_label = QLabel()
        self._output_label.setObjectName("fieldLabel")
        output_layout.addWidget(self._output_label)
        
        output_row = QHBoxLayout()
        output_row.setSpacing(8)
        self._output_input = QLineEdit()
        self._output_input.setObjectName("output_path_input")
        self._output_input.setReadOnly(True)
        self._output_input.setMinimumHeight(44)
        self._output_browse = QPushButton()
        self._output_browse.setObjectName("cookie_browse_button")
        self._output_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self._output_browse.setFixedSize(100, 44)
        self._output_browse.clicked.connect(self._browse_output)
        output_row.addWidget(self._output_input, stretch=1)
        output_row.addWidget(self._output_browse)
        output_layout.addLayout(output_row)
        file_layout.addLayout(output_layout)

        card_layout.addWidget(file_panel)

        # Status & Progress
        status_layout = QVBoxLayout()
        status_layout.setSpacing(12)
        self._status = QLabel()
        self._status.setObjectName("pageTitle")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self._status)
        
        self._progress = QProgressBar()
        self._progress.setObjectName("modern_progress_bar")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setMinimumHeight(24)
        status_layout.addWidget(self._progress)
        card_layout.addLayout(status_layout)

        # Actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)
        
        self._cancel = QPushButton()
        self._cancel.setObjectName("ghostButton")
        self._cancel.setMinimumHeight(56)
        self._cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel.setEnabled(False)
        self._cancel.clicked.connect(self._cancel_job)
        
        self._start = QPushButton()
        self._start.setObjectName("modern_download_button")
        self._start.setMinimumHeight(56)
        self._start.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start.clicked.connect(self._start_job)
        
        actions_layout.addWidget(self._cancel, stretch=1)
        actions_layout.addWidget(self._start, stretch=2)
        card_layout.addLayout(actions_layout)

        # Center card in layout
        row = QHBoxLayout()
        row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        row.addWidget(self._card, stretch=1)
        row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        page_layout.addLayout(row)
        page_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))


    def set_i18n(self, i18n: LanguageManager) -> None:
        self._i18n = i18n
        self.retranslate()

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._title.setText(t("subtitle.title") if t("subtitle.title") != "subtitle.title" else "Otomatik Altyazı Oluştur")
        self._hint.setText(t("subtitle.hint") if t("subtitle.hint") != "subtitle.hint" else "Ses dosyasını seçin. Orijinal dili otomatik algılanıp SRT altyazısı oluşturulur.")
        self._source_label.setText(t("subtitle.source") if t("subtitle.source") != "subtitle.source" else "Ses Dosyası (.mp3, .wav)")
        self._output_label.setText(t("subtitle.output") if t("subtitle.output") != "subtitle.output" else "Çıktı (SRT Dosyası)")
        self._source_browse.setText(t("action.browse"))
        self._output_browse.setText(t("action.browse"))
        self._start.setText(t("subtitle.create") if t("subtitle.create") != "subtitle.create" else "Çevir ve Altyazı Oluştur")
        self._cancel.setText(t("action.cancel"))
        if not self._worker:
            self._status.setText(t("status.ready"))

    def _browse_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select audio", "", "Audio files (*.mp3 *.m4a *.wav *.ogg *.flac *.webm);;All files (*)")
        if path:
            self._source = Path(path)
            self._source_input.setText(path)
            self._destination = self._source.with_suffix(".srt")
            self._output_input.setText(str(self._destination))

    def _browse_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save SRT", str(self._destination or "subtitles.srt"), "SRT files (*.srt)")
        if path:
            self._destination = Path(path)
            self._output_input.setText(path)

    def _start_job(self) -> None:
        t = self._i18n.get_text
        if not self._source or not self._destination:
            QMessageBox.warning(self, t("app.name"), t("subtitle.select_source"))
            return
        api_key = load_groq_api_key()
        if not api_key:
            QMessageBox.warning(self, t("app.name"), t("subtitle.api_key_missing"))
            return
        binaries = check_binaries()
        if not binaries.ffmpeg_exists or not binaries.ffprobe_exists:
            QMessageBox.warning(self, t("app.name"), t("error.ffmpeg_missing"))
            return

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
        self._start.setEnabled(True)
        self._cancel.setEnabled(False)
        if success:
            self._status.setText(self._i18n.get_text("subtitle.done"))
            QMessageBox.information(self, self._i18n.get_text("app.name"), self._i18n.get_text("subtitle.done_message").format(path=message))
        else:
            self._status.setText(self._i18n.get_text("status.error"))
            QMessageBox.warning(self, self._i18n.get_text("app.name"), message)

    def _clear_worker(self) -> None:
        self._worker = None
        self._thread = None

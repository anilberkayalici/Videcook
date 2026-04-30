"""Download page — the main form for video downloading."""

from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from videcook.core.models import DownloadMode, DownloadRequest, QualityOption
from videcook.core.playlist import detect_playlist_intent
from videcook.core.validators import (
    InvalidCookieFileError,
    InvalidOutputFolderError,
    InvalidUrlError,
    validate_cookie_file,
    validate_output_folder,
    validate_url,
)
from videcook.services.binary_locator import check_binaries
from videcook.ui.download_worker import DownloadWorker
from videcook.utils.i18n import LanguageManager


class DownloadPage(QWidget):
    """Main download form with URL, cookies, output folder, quality, and controls."""

    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._quality_map: dict[str, QualityOption] = {}
        self._cookie_path: Path | None = None
        self._output_path: Path | None = None
        self._worker: DownloadWorker | None = None
        self._thread: QThread | None = None

        self._build_ui()
        self.retranslate()

    # ------------------------------------------------------------------
    # UI construction — QGridLayout form card — no overlap possible
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        page_layout = QVBoxLayout(self)
        page_layout.setSpacing(22)
        page_layout.setContentsMargins(28, 28, 28, 28)

        # ================================================================
        # Form Card — QGridLayout
        # ================================================================
        form_card = QWidget()
        form_card.setObjectName("card")
        form_layout = QGridLayout(form_card)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setHorizontalSpacing(14)
        form_layout.setVerticalSpacing(8)
        # Ensure rows don't collapse
        for row in range(1, 5):
            form_layout.setRowMinimumHeight(row, 44)

        # Column minimum widths
        form_layout.setColumnMinimumWidth(0, 180)  # label column
        # col 1 stretches (input column)
        form_layout.setColumnMinimumWidth(2, 120)  # browse button column
        form_layout.setColumnStretch(0, 0)   # label: no stretch
        form_layout.setColumnStretch(1, 1)   # input: stretch
        form_layout.setColumnStretch(2, 0)   # button: no stretch

        # --- Row 0: Section title (spans 3 columns) ---
        self._source_title = QLabel()
        self._source_title.setObjectName("sectionLabel")
        form_layout.addWidget(self._source_title, 0, 0, 1, 3)

        # --- Row 1: Video URL ---
        self._url_label = QLabel()
        self._url_label.setObjectName("fieldLabel")
        self._url_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        form_layout.addWidget(self._url_label, 1, 0)

        self._url_input = QLineEdit()
        self._url_input.setObjectName("video_url_input")
        self._url_input.setPlaceholderText("https://...")
        self._url_input.setMinimumHeight(44)
        form_layout.addWidget(self._url_input, 1, 1, 1, 2)

        # --- Row 2: Cookie File ---
        self._cookie_label = QLabel()
        self._cookie_label.setObjectName("fieldLabel")
        self._cookie_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        form_layout.addWidget(self._cookie_label, 2, 0)

        self._cookie_display = QLineEdit()
        self._cookie_display.setObjectName("cookie_path_input")
        self._cookie_display.setReadOnly(True)
        self._cookie_display.setPlaceholderText("cookies.txt")
        self._cookie_display.setMinimumHeight(44)
        form_layout.addWidget(self._cookie_display, 2, 1)

        self._cookie_browse = QPushButton()
        self._cookie_browse.setObjectName("cookie_browse_button")
        self._cookie_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cookie_browse.setFixedSize(120, 44)
        self._cookie_browse.clicked.connect(self._browse_cookie)
        form_layout.addWidget(self._cookie_browse, 2, 2)

        # --- Row 3: Output Folder ---
        self._out_label = QLabel()
        self._out_label.setObjectName("fieldLabel")
        self._out_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        form_layout.addWidget(self._out_label, 3, 0)

        self._out_display = QLineEdit()
        self._out_display.setObjectName("output_path_input")
        self._out_display.setReadOnly(True)
        self._out_display.setPlaceholderText("C:\\Users\\...")
        self._out_display.setMinimumHeight(44)
        form_layout.addWidget(self._out_display, 3, 1)

        self._out_browse = QPushButton()
        self._out_browse.setObjectName("output_browse_button")
        self._out_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self._out_browse.setFixedSize(120, 44)
        self._out_browse.clicked.connect(self._browse_output)
        form_layout.addWidget(self._out_browse, 3, 2)

        # --- Row 4: Quality ---
        self._qual_label = QLabel()
        self._qual_label.setObjectName("fieldLabel")
        self._qual_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        form_layout.addWidget(self._qual_label, 4, 0)

        self._qual_combo = QComboBox()
        self._qual_combo.setObjectName("quality_combo")
        self._qual_combo.setMinimumHeight(44)
        form_layout.addWidget(self._qual_combo, 4, 1)

        page_layout.addWidget(form_card)

        # ================================================================
        # Progress & Status Card
        # ================================================================
        prog_card = QWidget()
        prog_card.setObjectName("card")
        prog_layout = QVBoxLayout(prog_card)
        prog_layout.setSpacing(12)
        prog_layout.setContentsMargins(28, 24, 28, 24)

        self._status = QLabel()
        self._status.setObjectName("status_label")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prog_layout.addWidget(self._status)

        self._progress = QProgressBar()
        self._progress.setObjectName("progress_bar")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setMinimumHeight(28)
        prog_layout.addWidget(self._progress)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._cancel_btn = QPushButton()
        self._cancel_btn.setObjectName("cancel_button")
        self._cancel_btn.setFixedSize(140, 48)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        btn_row.addWidget(self._cancel_btn)

        self._download_btn = QPushButton()
        self._download_btn.setObjectName("download_button")
        self._download_btn.setFixedSize(180, 48)
        self._download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._download_btn.clicked.connect(self._on_download_clicked)
        btn_row.addWidget(self._download_btn)

        prog_layout.addLayout(btn_row)
        page_layout.addWidget(prog_card)

        # ================================================================
        # Log Card
        # ================================================================
        log_card = QWidget()
        log_card.setObjectName("logPanel")
        log_layout = QVBoxLayout(log_card)
        log_layout.setSpacing(8)
        log_layout.setContentsMargins(16, 16, 16, 16)

        self._log_title = QLabel()
        self._log_title.setObjectName("logTitle")
        log_layout.addWidget(self._log_title)

        self._log = QPlainTextEdit()
        self._log.setObjectName("operation_log")
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(500)
        self._log.setMinimumHeight(130)
        self._log.setFrameShape(QPlainTextEdit.Shape.NoFrame)
        log_layout.addWidget(self._log, stretch=1)

        page_layout.addWidget(log_card, stretch=1)

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._source_title.setText(t("download.source_title"))
        self._url_label.setText(t("label.video_url"))
        self._cookie_label.setText(t("label.cookie_file"))
        self._cookie_browse.setText(t("action.browse"))
        self._out_label.setText(t("label.output_folder"))
        self._out_browse.setText(t("action.browse"))
        self._qual_label.setText(t("label.quality"))
        self._download_btn.setText(t("action.download"))
        self._cancel_btn.setText(t("action.cancel"))
        self._log_title.setText(t("log.title"))
        if not self._worker:
            self._status.setText(t("status.ready"))

        prev = self._qual_combo.currentText()
        self._quality_map.clear()
        self._qual_combo.clear()
        for key, enum in [
            ("quality.best", QualityOption.BEST),
            ("quality.1080p", QualityOption.P1080),
            ("quality.720p", QualityOption.P720),
            ("quality.480p", QualityOption.P480),
        ]:
            text = t(key)
            self._quality_map[text] = enum
            self._qual_combo.addItem(text)
        idx = self._qual_combo.findText(prev)
        if idx >= 0:
            self._qual_combo.setCurrentIndex(idx)

    # ------------------------------------------------------------------
    # Browse actions
    # ------------------------------------------------------------------

    def _browse_cookie(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select cookies.txt", "", "Text files (*.txt);;All files (*)"
        )
        if path:
            self._cookie_path = Path(path)
            self._cookie_display.setText(self._cookie_path.name)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self._output_path = Path(path)
            self._out_display.setText(str(self._output_path))

    # ------------------------------------------------------------------
    # Download / Cancel
    # ------------------------------------------------------------------

    def _on_download_clicked(self) -> None:
        t = self._i18n.get_text
        url = self._url_input.text().strip()

        if not url:
            self._append_log(t("log.select_cookie_first"))
            return
        if self._cookie_path is None:
            self._append_log(t("log.select_cookie_first"))
            return
        if self._output_path is None:
            self._append_log(t("log.select_output_first"))
            return

        try:
            validate_url(url)
        except InvalidUrlError as exc:
            self._append_log(t("log.validation_error").format(message=str(exc)))
            return

        try:
            validate_cookie_file(self._cookie_path)
        except InvalidCookieFileError as exc:
            self._append_log(t("log.validation_error").format(message=str(exc)))
            return

        try:
            validate_output_folder(self._output_path)
        except InvalidOutputFolderError as exc:
            self._append_log(t("log.validation_error").format(message=str(exc)))
            return

        # Playlist detection
        mode = DownloadMode.SINGLE_VIDEO
        if detect_playlist_intent(url):
            choice = self._ask_playlist_choice()
            if choice is None:
                self._append_log(t("status.cancelled"))
                return
            mode = DownloadMode.PLAYLIST if choice else DownloadMode.SINGLE_VIDEO

        # Binary check
        self._append_log(t("log.checking_binaries"))
        status = check_binaries()
        self._append_log(status.to_display())
        if not status.is_ready:
            msg = t("error.binaries_missing").format(
                bin_dir=str(status.ytdlp_path.parent)
            )
            self._append_log(msg)
            self._status.setText(t("status.error"))
            return

        # Build request and launch worker
        quality_text = self._qual_combo.currentText()
        quality = self._quality_map.get(quality_text, QualityOption.BEST)

        request = DownloadRequest(
            url=url,
            cookie_file=self._cookie_path,
            output_folder=self._output_path,
            quality=quality,
            mode=mode,
        )

        self._log.clear()
        cookie_name = self._cookie_path.name
        self._append_log(t("log.building_command"))
        self._append_log(f"URL: {url}")
        self._append_log(f"Cookie: {cookie_name}")
        self._append_log(f"Output: {self._output_path}")

        self._start_worker(request)

    def _start_worker(self, request: DownloadRequest) -> None:
        t = self._i18n.get_text

        self._progress.setValue(0)
        self._status.setText(t("status.downloading"))
        self._download_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)

        self._cleanup_worker()

        self._thread = QThread()
        self._worker = DownloadWorker(request, self._i18n)
        self._worker.moveToThread(self._thread)

        self._worker.progress_changed.connect(self._on_progress)
        self._worker.status_changed.connect(self._on_status)
        self._worker.log_message.connect(self._append_log)
        self._worker.error_message.connect(self._on_error)
        self._worker.finished.connect(self._on_finished)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_progress(self, percent: int) -> None:
        self._progress.setValue(percent)

    def _on_status(self, text: str) -> None:
        self._status.setText(text)

    def _on_error(self, message: str) -> None:
        self._append_log(message)

    def _on_finished(self, success: bool, message: str) -> None:
        t = self._i18n.get_text
        self._download_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)

        if success:
            self._progress.setValue(100)
            self._status.setText(t("status.completed"))
            self._append_log(t("log.download_completed"))
        else:
            self._status.setText(t("status.error"))
            self._append_log(message)

        if not self._worker:
            self._status.setText(t("status.ready"))

        self._cookie_path = None

    def _ask_playlist_choice(self) -> bool | None:
        box = QMessageBox(self)
        box.setWindowTitle("Videcook")
        box.setText(self._i18n.get_text("dialog.playlist.title"))
        box.setIcon(QMessageBox.Icon.Question)
        box.addButton(
            self._i18n.get_text("dialog.playlist.download_this"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        playlist_btn = box.addButton(
            self._i18n.get_text("dialog.playlist.download_all"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        cancel_btn = box.addButton(
            self._i18n.get_text("action.cancel"),
            QMessageBox.ButtonRole.RejectRole,
        )
        box.exec()
        clicked = box.clickedButton()
        if clicked == cancel_btn:
            return None
        return clicked == playlist_btn

    def _on_cancel_clicked(self) -> None:
        if self._worker:
            self._worker.cancel()
        self._cancel_btn.setEnabled(False)
        self._cleanup_worker()
        self._progress.setValue(0)
        self._status.setText(self._i18n.get_text("status.cancelled"))
        self._append_log(self._i18n.get_text("log.download_cancelled"))
        self._download_btn.setEnabled(True)
        self._cookie_path = None
        self._cookie_display.clear()

    # ------------------------------------------------------------------
    # Worker management
    # ------------------------------------------------------------------

    def _cleanup_worker(self) -> None:
        if self._worker:
            self._worker.progress_changed.disconnect()
            self._worker.status_changed.disconnect()
            self._worker.log_message.disconnect()
            self._worker.error_message.disconnect()
            self._worker.finished.disconnect()
            self._worker = None
        self._thread = None

    def _append_log(self, message: str) -> None:
        self._log.appendPlainText(message)

    def set_i18n(self, i18n: LanguageManager) -> None:
        self._i18n = i18n
        self.retranslate()

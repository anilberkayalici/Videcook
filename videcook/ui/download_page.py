"""Download page — clean, modern download form."""

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, QThread
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from videcook.core.models import (
    AudioFormat,
    DownloadMode,
    DownloadRequest,
    DownloadType,
    QualityOption,
)
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
from videcook.utils.preferences import load_preferences, save_preferences


class DownloadPage(QWidget):
    """Main download form — URL, optional cookies, quality/audio, output."""

    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._quality_map: dict[str, QualityOption] = {}
        self._audio_format_map: dict[str, AudioFormat] = {}
        self._cookie_path: Path | None = None
        self._output_path: Path | None = None
        self._download_type: DownloadType = DownloadType.VIDEO
        self._worker: DownloadWorker | None = None
        self._thread: QThread | None = None

        self._build_ui()
        self._apply_preferences()
        self.retranslate()

    def _apply_preferences(self) -> None:
        prefs = load_preferences()
        if prefs.last_output_folder:
            p = Path(prefs.last_output_folder)
            if p.exists() and p.is_dir():
                self._output_path = p
                self._out_display.setText(str(p))

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("downloadScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._content.setObjectName("downloadContent")
        self._scroll.setWidget(self._content)
        outer_layout.addWidget(self._scroll)

        page_layout = QVBoxLayout(self._content)
        page_layout.setSpacing(18)
        page_layout.setContentsMargins(32, 28, 32, 30)

        top_row = QHBoxLayout()
        top_row.setSpacing(18)

        # ================================================================
        # Primary command card
        # ================================================================
        form_card = QWidget()
        form_card.setObjectName("primaryCard")
        form = QVBoxLayout(form_card)
        form.setSpacing(14)
        form.setContentsMargins(22, 22, 22, 22)

        self._source_title = QLabel()
        self._source_title.setObjectName("sectionLabel")
        form.addWidget(self._source_title)

        url_panel = QWidget()
        url_panel.setObjectName("fieldPanel")
        url_layout = QVBoxLayout(url_panel)
        url_layout.setSpacing(8)
        url_layout.setContentsMargins(14, 12, 14, 14)

        self._url_label = QLabel()
        self._url_label.setObjectName("fieldLabel")
        url_layout.addWidget(self._url_label)

        self._url_input = QLineEdit()
        self._url_input.setObjectName("video_url_input")
        self._url_input.setPlaceholderText("https://...")
        self._url_input.setMinimumHeight(46)
        url_layout.addWidget(self._url_input)
        form.addWidget(url_panel)

        mode_format_row = QHBoxLayout()
        mode_format_row.setSpacing(14)

        mode_panel = QWidget()
        mode_panel.setObjectName("inlinePanel")
        mode_panel.setMinimumHeight(108)
        mode_layout = QVBoxLayout(mode_panel)
        mode_layout.setSpacing(10)
        mode_layout.setContentsMargins(14, 12, 14, 14)
        self._type_label = QLabel()
        self._type_label.setObjectName("fieldLabel")
        mode_layout.addWidget(self._type_label)

        type_buttons = QHBoxLayout()
        type_buttons.setSpacing(8)

        self._video_btn = QPushButton()
        self._video_btn.setObjectName("segButton")
        self._video_btn.setCheckable(True)
        self._video_btn.setChecked(True)
        self._video_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._video_btn.setMinimumSize(104, 38)
        self._video_btn.clicked.connect(lambda: self._set_download_type(DownloadType.VIDEO))
        type_buttons.addWidget(self._video_btn)

        self._audio_btn = QPushButton()
        self._audio_btn.setObjectName("segButton")
        self._audio_btn.setCheckable(True)
        self._audio_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._audio_btn.setMinimumSize(126, 38)
        self._audio_btn.clicked.connect(lambda: self._set_download_type(DownloadType.AUDIO))
        type_buttons.addWidget(self._audio_btn)
        type_buttons.addStretch(1)
        mode_layout.addLayout(type_buttons)
        mode_format_row.addWidget(mode_panel, stretch=1)

        format_panel = QWidget()
        format_panel.setObjectName("inlinePanel")
        format_panel.setMinimumHeight(108)
        format_layout = QVBoxLayout(format_panel)
        format_layout.setSpacing(10)
        format_layout.setContentsMargins(14, 12, 14, 14)
        self._qual_label = QLabel()
        self._qual_label.setObjectName("fieldLabel")
        format_layout.addWidget(self._qual_label)

        self._qual_combo = QComboBox()
        self._qual_combo.setObjectName("quality_combo")
        self._qual_combo.setMinimumHeight(42)
        format_layout.addWidget(self._qual_combo)
        mode_format_row.addWidget(format_panel, stretch=1)
        form.addLayout(mode_format_row)

        self._embed_panel = QWidget()
        self._embed_panel.setObjectName("embedPanel")
        self._embed_panel.setMinimumHeight(58)
        self._embed_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        embed_layout = QHBoxLayout(self._embed_panel)
        embed_layout.setContentsMargins(14, 10, 14, 10)
        embed_layout.setSpacing(10)

        self._embed_check = QCheckBox()
        self._embed_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self._embed_check.setMinimumHeight(34)
        embed_layout.addWidget(self._embed_check)
        embed_layout.addStretch(1)

        self._embed_panel.setVisible(False)
        form.addWidget(self._embed_panel)

        auth_panel = QWidget()
        auth_panel.setObjectName("fieldPanel")
        auth_panel.setMinimumHeight(72)
        auth_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self._auth_panel = auth_panel
        auth_layout = QVBoxLayout(auth_panel)
        auth_layout.setSpacing(10)
        auth_layout.setContentsMargins(14, 12, 14, 14)

        self._members_toggle = QPushButton()
        self._members_toggle.setObjectName("membersToggle")
        self._members_toggle.setCheckable(True)
        self._members_toggle.setMinimumHeight(46)
        self._members_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._members_toggle.toggled.connect(self._on_members_toggled)
        auth_layout.addWidget(self._members_toggle)

        cookie_wrapper = QWidget()
        cookie_wrapper.setObjectName("cookieWrapper")
        cookie_wrapper.setMinimumHeight(64)
        cookie_wrapper.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self._cookie_wrapper = cookie_wrapper
        cookie_layout = QVBoxLayout(cookie_wrapper)
        cookie_layout.setContentsMargins(0, 2, 0, 0)
        cookie_layout.setSpacing(8)

        self._cookie_label = QLabel()
        self._cookie_label.setObjectName("fieldLabel")
        self._cookie_label.setWordWrap(True)
        cookie_layout.addWidget(self._cookie_label)

        cookie_row = QHBoxLayout()
        cookie_row.setContentsMargins(0, 0, 0, 0)
        cookie_row.setSpacing(10)

        self._cookie_display = QLineEdit()
        self._cookie_display.setObjectName("cookie_path_input")
        self._cookie_display.setReadOnly(True)
        self._cookie_display.setPlaceholderText("cookies.txt")
        self._cookie_display.setMinimumHeight(42)
        cookie_row.addWidget(self._cookie_display, stretch=1)

        self._cookie_browse = QPushButton()
        self._cookie_browse.setObjectName("cookie_browse_button")
        self._cookie_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cookie_browse.setFixedSize(112, 42)
        self._cookie_browse.clicked.connect(self._browse_cookie)
        cookie_row.addWidget(self._cookie_browse)
        cookie_layout.addLayout(cookie_row)

        cookie_wrapper.setVisible(False)
        auth_layout.addWidget(cookie_wrapper)
        form.addWidget(auth_panel)

        output_panel = QWidget()
        output_panel.setObjectName("fieldPanel")
        output_panel.setMinimumHeight(92)
        self._output_panel = output_panel
        output_layout = QVBoxLayout(output_panel)
        output_layout.setSpacing(8)
        output_layout.setContentsMargins(14, 12, 14, 14)
        self._out_label = QLabel()
        self._out_label.setObjectName("fieldLabel")
        output_layout.addWidget(self._out_label)

        out_row = QHBoxLayout()
        out_row.setSpacing(10)

        self._out_display = QLineEdit()
        self._out_display.setObjectName("output_path_input")
        self._out_display.setReadOnly(True)
        self._out_display.setPlaceholderText("C:\\Users\\...")
        self._out_display.setMinimumHeight(42)
        out_row.addWidget(self._out_display, stretch=1)

        self._out_browse = QPushButton()
        self._out_browse.setObjectName("output_browse_button")
        self._out_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self._out_browse.setFixedSize(112, 42)
        self._out_browse.clicked.connect(self._browse_output)
        out_row.addWidget(self._out_browse)

        output_layout.addLayout(out_row)
        form.addWidget(output_panel)

        top_row.addWidget(form_card, stretch=5)

        # ================================================================
        # Progress & Status Card
        # ================================================================
        prog_card = QWidget()
        prog_card.setObjectName("statusCard")
        prog_layout = QVBoxLayout(prog_card)
        prog_layout.setSpacing(16)
        prog_layout.setContentsMargins(22, 22, 22, 22)

        self._status = QLabel()
        self._status.setObjectName("status_label")
        self._status.setAlignment(Qt.AlignmentFlag.AlignLeft)
        prog_layout.addWidget(self._status)

        self._progress = QProgressBar()
        self._progress.setObjectName("progress_bar")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setMinimumHeight(30)
        prog_layout.addWidget(self._progress)
        prog_layout.addStretch(1)

        self._cancel_btn = QPushButton()
        self._cancel_btn.setObjectName("cancel_button")
        self._cancel_btn.setMinimumSize(140, 46)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)

        self._download_btn = QPushButton()
        self._download_btn.setObjectName("download_button")
        self._download_btn.setMinimumSize(160, 50)
        self._download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._download_btn.clicked.connect(self._on_download_clicked)
        prog_layout.addWidget(self._download_btn)
        prog_layout.addWidget(self._cancel_btn)

        top_row.addWidget(prog_card, stretch=2)
        page_layout.addLayout(top_row)

        # ================================================================
        # Log Card
        # ================================================================
        log_card = QWidget()
        log_card.setObjectName("logPanel")
        log_layout = QVBoxLayout(log_card)
        log_layout.setSpacing(10)
        log_layout.setContentsMargins(18, 16, 18, 18)

        self._log_title = QLabel()
        self._log_title.setObjectName("logTitle")
        log_layout.addWidget(self._log_title)

        self._log = QPlainTextEdit()
        self._log.setObjectName("operation_log")
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(500)
        self._log.setMinimumHeight(100)
        self._log.setMaximumHeight(110)
        self._log.setFrameShape(QPlainTextEdit.Shape.NoFrame)
        log_layout.addWidget(self._log, stretch=1)

        log_card.setMaximumHeight(170)
        page_layout.addWidget(log_card, stretch=0)

    # ------------------------------------------------------------------
    # Type toggle (Video / Audio)
    # ------------------------------------------------------------------

    def _set_download_type(self, dtype: DownloadType) -> None:
        self._download_type = dtype
        self._video_btn.setChecked(dtype is DownloadType.VIDEO)
        self._audio_btn.setChecked(dtype is DownloadType.AUDIO)
        self._refresh_format_combo()

    def _save_current_preferences(self) -> None:
        prefs = load_preferences()
        prefs.embed_thumbnail = self._embed_check.isChecked()
        if self._output_path is not None:
            prefs.last_output_folder = str(self._output_path)
        combo_text = self._qual_combo.currentText()
        if self._download_type is DownloadType.AUDIO:
            for key, fmt in self._audio_format_map.items():
                if key == combo_text:
                    for lkey in ("audio_format.mp3", "audio_format.m4a",
                                 "audio_format.opus", "audio_format.aac",
                                 "audio_format.flac", "audio_format.wav"):
                        if self._i18n.get_text(lkey) == key:
                            prefs.last_audio_format = lkey
                            break
                    break
        else:
            for key, _enum in self._quality_map.items():
                if key == combo_text:
                    for lkey in ("quality.best", "quality.1080p",
                                 "quality.720p", "quality.480p"):
                        if self._i18n.get_text(lkey) == key:
                            prefs.last_quality = lkey
                            break
                    break
        save_preferences(prefs)

    # ------------------------------------------------------------------
    # Cookie row
    # ------------------------------------------------------------------

    def _on_members_toggled(self, checked: bool) -> None:
        self._cookie_wrapper.setVisible(checked)
        self._auth_panel.setMinimumHeight(158 if checked else 72)
        if not checked:
            self._cookie_path = None
            self._cookie_display.clear()
        self._auth_panel.updateGeometry()
        self._content.updateGeometry()
        if checked:
            QTimer.singleShot(0, self._reveal_cookie_picker)

    def _reveal_cookie_picker(self) -> None:
        """Keep the expanded cookie picker within the user's current view."""
        if self._cookie_wrapper.isVisible():
            self._scroll.ensureWidgetVisible(self._cookie_wrapper, 0, 18)

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._source_title.setText(t("download.source_title"))
        self._url_label.setText(t("label.video_url"))
        self._type_label.setText(t("label.type"))
        self._video_btn.setText(t("label.video_mode"))
        self._audio_btn.setText(t("label.audio_mode"))
        self._members_toggle.setText(t("label.members_only"))
        self._cookie_label.setText(t("label.cookie_file"))
        self._cookie_browse.setText(t("action.browse"))
        self._out_label.setText(t("label.output_folder"))
        self._out_browse.setText(t("action.browse"))
        self._embed_check.setText(t("label.embed_thumbnail"))
        self._download_btn.setText(t("action.download"))
        self._cancel_btn.setText(t("action.cancel"))
        self._log_title.setText(t("log.title"))
        if not self._worker:
            self._status.setText(t("status.ready"))

        self._refresh_format_combo()

    def _refresh_format_combo(self) -> None:
        t = self._i18n.get_text
        prefs = load_preferences()
        self._qual_combo.clear()

        if self._download_type is DownloadType.AUDIO:
            self._qual_label.setText(t("label.audio_format"))
            self._embed_panel.setVisible(True)
            self._audio_format_map.clear()
            for key, fmt in [
                ("audio_format.mp3", AudioFormat.MP3),
                ("audio_format.m4a", AudioFormat.M4A),
                ("audio_format.opus", AudioFormat.OPUS),
                ("audio_format.aac", AudioFormat.AAC),
                ("audio_format.flac", AudioFormat.FLAC),
                ("audio_format.wav", AudioFormat.WAV),
            ]:
                text = t(key)
                self._audio_format_map[text] = fmt
                self._qual_combo.addItem(text)
            idx = self._qual_combo.findText(t(prefs.last_audio_format))
            if idx >= 0:
                self._qual_combo.setCurrentIndex(idx)
            self._embed_check.setChecked(prefs.embed_thumbnail)
        else:
            self._qual_label.setText(t("label.quality"))
            self._embed_panel.setVisible(False)
            self._quality_map.clear()
            for key, enum in [
                ("quality.best", QualityOption.BEST),
                ("quality.1080p", QualityOption.P1080),
                ("quality.720p", QualityOption.P720),
                ("quality.480p", QualityOption.P480),
            ]:
                text = t(key)
                self._quality_map[text] = enum
                self._qual_combo.addItem(text)
            idx = self._qual_combo.findText(t(prefs.last_quality))
            if idx >= 0:
                self._qual_combo.setCurrentIndex(idx)

        self._embed_panel.updateGeometry()
        self._content.updateGeometry()

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
            prefs = load_preferences()
            prefs.last_output_folder = str(self._output_path)
            save_preferences(prefs)

    # ------------------------------------------------------------------
    # Download / Cancel
    # ------------------------------------------------------------------

    def _on_download_clicked(self) -> None:
        t = self._i18n.get_text
        url = self._url_input.text().strip()

        if not url:
            self._append_log(t("log.select_url_first"))
            return
        if self._output_path is None:
            self._append_log(t("log.select_output_first"))
            return

        try:
            validate_url(url)
        except InvalidUrlError as exc:
            self._append_log(t("log.validation_error").format(message=str(exc)))
            return

        if self._members_toggle.isChecked() and self._cookie_path is None:
            self._append_log(t("log.select_cookie_first"))
            return

        if self._members_toggle.isChecked() and self._cookie_path is not None:
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

        mode = DownloadMode.SINGLE_VIDEO
        if detect_playlist_intent(url):
            choice = self._ask_playlist_choice()
            if choice is None:
                self._append_log(t("status.cancelled"))
                return
            mode = DownloadMode.PLAYLIST if choice else DownloadMode.SINGLE_VIDEO

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

        # Persist user choices
        self._save_current_preferences()

        quality_text = self._qual_combo.currentText()
        quality = self._quality_map.get(quality_text, QualityOption.BEST)
        audio_fmt = self._audio_format_map.get(quality_text, AudioFormat.MP3)

        request = DownloadRequest(
            url=url,
            cookie_file=self._cookie_path if self._members_toggle.isChecked() else None,
            output_folder=self._output_path,
            quality=quality,
            mode=mode,
            download_type=self._download_type,
            audio_format=audio_fmt,
            embed_thumbnail=self._embed_check.isChecked(),
        )

        self._log.clear()
        self._append_log(t("log.building_command"))
        self._append_log(f"URL: {url}")
        if request.cookie_file is not None:
            self._append_log(f"Cookie: {request.cookie_file.name}")
        self._append_log(f"Output: {self._output_path}")
        if request.download_type is DownloadType.AUDIO:
            self._append_log(f"Audio: {request.audio_format.value.upper()}")
            if request.embed_thumbnail:
                self._append_log("Embed: thumbnail + metadata")

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
        if self._members_toggle.isChecked():
            self._cookie_display.clear()

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
            try:
                self._worker.progress_changed.disconnect()
                self._worker.status_changed.disconnect()
                self._worker.log_message.disconnect()
                self._worker.error_message.disconnect()
                self._worker.finished.disconnect()
            except RuntimeError:
                pass
            self._worker = None
        self._thread = None

    def _append_log(self, message: str) -> None:
        self._log.appendPlainText(message)

    def set_i18n(self, i18n: LanguageManager) -> None:
        self._i18n = i18n
        self.retranslate()

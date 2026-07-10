"""Setup wizard — first-run experience that downloads missing helper binaries."""


from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from videcook.paths import get_bin_dir
from videcook.services.binary_downloader import (
    BinaryDownloadWorker,
    DownloadProgress,
    get_total_size_mb,
)
from videcook.services.binary_locator import BinaryStatus, check_binaries
from videcook.services.update_checker import (
    UpdateStatus,
    check_for_updates,
    perform_update,
)
from videcook.utils.i18n import LanguageManager


class SetupWizard(QWidget):
    """Full-page widget shown when required binaries are missing."""

    # signal emitted when binaries become ready
    binaries_ready = None  # will be set by MainWindow

    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._status: BinaryStatus | None = None
        self._download_thread: QThread | None = None
        self._download_worker: BinaryDownloadWorker | None = None
        self._update_status: UpdateStatus | None = None

        self._build_ui()
        self.retranslate()
        self._refresh_status()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(32, 28, 32, 30)

        hero = QWidget()
        hero.setObjectName("heroStrip")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(20, 18, 20, 18)
        hero_layout.setSpacing(8)

        self._title = QLabel()
        self._title.setObjectName("pageTitle")
        hero_layout.addWidget(self._title)

        self._subtitle = QLabel()
        self._subtitle.setObjectName("appTagline")
        self._subtitle.setWordWrap(True)
        hero_layout.addWidget(self._subtitle)
        layout.addWidget(hero)

        # --- Binary Status Card ---
        card = QWidget()
        card.setObjectName("setupCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(22, 22, 22, 22)

        self._status_title = QLabel()
        self._status_title.setObjectName("sectionLabel")
        card_layout.addWidget(self._status_title)

        self._rows: list[tuple[QLabel, QLabel, QLabel]] = []
        for _ in range(3):
            row_widget = QWidget()
            row_widget.setObjectName("binaryRow")
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(14, 11, 14, 11)
            row.setSpacing(12)
            name = QLabel()
            name.setObjectName("fieldLabel")
            name.setMinimumWidth(130)
            badge = QLabel()
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setMinimumWidth(110)
            source = QLabel()
            source.setObjectName("appTagline")
            source.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(name)
            row.addWidget(badge)
            row.addWidget(source, stretch=1)
            card_layout.addWidget(row_widget)
            self._rows.append((name, badge, source))

        # Separator + download info
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #2A1A21;")
        line.setFixedHeight(1)
        card_layout.addWidget(line)

        self._info_text = QLabel()
        self._info_text.setWordWrap(True)
        self._info_text.setObjectName("stepText")
        card_layout.addWidget(self._info_text)

        # Source trust checkbox
        self._trust_check = QCheckBox()
        self._trust_check.setCursor(Qt.CursorShape.PointingHandCursor)
        card_layout.addWidget(self._trust_check)

        layout.addWidget(card)

        # --- Progress card (hidden by default) ---
        self._progress_card = QWidget()
        self._progress_card.setObjectName("statusCard")
        self._progress_card.setVisible(False)
        pc_layout = QVBoxLayout(self._progress_card)
        pc_layout.setSpacing(12)
        pc_layout.setContentsMargins(22, 20, 22, 20)

        self._progress_status = QLabel()
        self._progress_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pc_layout.addWidget(self._progress_status)

        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("progress_bar")
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setMinimumHeight(28)
        pc_layout.addWidget(self._progress_bar)

        layout.addWidget(self._progress_card)

        # --- Action buttons ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        self._retry_btn = QPushButton()
        self._retry_btn.setObjectName("cancel_button")
        self._retry_btn.setFixedSize(160, 46)
        self._retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._retry_btn.setVisible(False)
        self._retry_btn.clicked.connect(self._on_retry)
        btn_row.addWidget(self._retry_btn)

        self._manual_btn = QPushButton()
        self._manual_btn.setObjectName("cancel_button")
        self._manual_btn.setFixedSize(180, 46)
        self._manual_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._manual_btn.setVisible(False)
        self._manual_btn.clicked.connect(self._open_manual_links)
        btn_row.addWidget(self._manual_btn)

        self._skip_btn = QPushButton()
        self._skip_btn.setObjectName("cancel_button")
        self._skip_btn.setFixedSize(150, 46)
        self._skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._skip_btn.clicked.connect(self._on_skip)
        btn_row.addWidget(self._skip_btn)

        self._download_btn = QPushButton()
        self._download_btn.setObjectName("download_button")
        self._download_btn.setFixedSize(210, 48)
        self._download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._download_btn.clicked.connect(self._on_download)
        self._download_btn.setEnabled(False)
        btn_row.addWidget(self._download_btn)

        layout.addLayout(btn_row)

        # Trust checkbox enables download button
        self._trust_check.toggled.connect(self._update_button_state)

        layout.addStretch(1)

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._title.setText(t("setup.title"))
        self._status_title.setText(t("setup.binary_status"))
        self._info_text.setText(t("setup.info").format(
            size=f"{get_total_size_mb():.0f}",
            ytdlp_source="github.com/yt-dlp/yt-dlp",
            ffmpeg_source="github.com/BtbN/FFmpeg-Builds",
        ))
        self._trust_check.setText(t("setup.trust_check"))
        self._download_btn.setText(t("setup.download_btn"))
        self._skip_btn.setText(t("setup.skip_btn"))
        self._retry_btn.setText(t("setup.retry_btn"))
        self._manual_btn.setText(t("setup.manual_btn"))

        if self._download_worker is not None:
            self._progress_status.setText(t("setup.downloading"))
        else:
            self._progress_status.clear()

        self._refresh_status()

    # ------------------------------------------------------------------
    # Status refresh
    # ------------------------------------------------------------------

    def _refresh_status(self) -> None:
        t = self._i18n.get_text
        self._status = check_binaries()

        labels = [
            (t("setup.ytdlp"), self._status.ytdlp_exists, self._status.ytdlp_source),
            (t("setup.ffmpeg"), self._status.ffmpeg_exists, self._status.ffmpeg_source),
            (t("setup.ffprobe"), self._status.ffprobe_exists, self._status.ffprobe_source),
        ]

        for (name_label, badge_label, source_label), (label_text, exists, source) in zip(
            self._rows, labels
        ):
            name_label.setText(label_text)
            badge_label.setText(t("status.ok") if exists else t("status.missing"))
            badge_label.setStyleSheet(self._badge_style(exists))
            source_label.setText(f"[{self._source_display(source, t)}]")

        self._update_button_state()
        self._update_subtitle()

    def _source_display(self, source: str, t) -> str:
        if source == "PATH":
            return t("setup.source_path")
        if source in {"managed", "bundled"}:
            return t("setup.source_bundled")
        return t("setup.source_missing")

    def _badge_style(self, ok: bool) -> str:
        if ok:
            return (
                "background-color: #102018;"
                "color: #A5E8BD;"
                "border: 1px solid #275E3C;"
                "border-radius: 7px;"
                "padding: 4px 12px;"
                "font-weight: 700;"
                "font-size: 12px;"
            )
        return (
            "background-color: #251019;"
            "color: #F3A0B1;"
            "border: 1px solid #7F1D2D;"
            "border-radius: 7px;"
            "padding: 4px 12px;"
            "font-weight: 700;"
            "font-size: 12px;"
        )

    def _update_subtitle(self) -> None:
        t = self._i18n.get_text
        if self._status and self._status.is_ready:
            self._subtitle.setText(t("setup.all_ready"))
            self._download_btn.setVisible(False)
            self._trust_check.setVisible(False)
            self._info_text.setVisible(False)
            self._skip_btn.setText(t("setup.continue_btn"))
        else:
            self._subtitle.setText(t("setup.subtitle"))
            self._download_btn.setVisible(True)
            self._trust_check.setVisible(True)
            self._info_text.setVisible(True)
            self._skip_btn.setText(t("setup.skip_btn"))

    def _update_button_state(self, *args) -> None:
        if self._status and self._status.is_ready:
            self._download_btn.setEnabled(False)
            self._skip_btn.setEnabled(True)
        else:
            self._download_btn.setEnabled(
                self._trust_check.isChecked() and self._download_btn.isVisible() is not False  # noqa
            )
            self._download_btn.setEnabled(self._trust_check.isChecked())
            self._skip_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Download flow
    # ------------------------------------------------------------------

    def _on_download(self) -> None:
        self._download_btn.setVisible(False)
        self._trust_check.setVisible(False)
        self._skip_btn.setEnabled(False)
        self._retry_btn.setVisible(False)
        self._manual_btn.setVisible(False)
        self._progress_card.setVisible(True)
        self._progress_bar.setValue(0)

        t = self._i18n.get_text
        self._progress_status.setText(t("setup.downloading"))

        s = self._status
        need_ytdlp = not (s and s.ytdlp_exists)
        need_ffmpeg = not (s and (s.ffmpeg_exists and s.ffprobe_exists))

        self._download_thread = QThread()
        self._download_worker = BinaryDownloadWorker(
            get_bin_dir(),
            download_ytdlp=need_ytdlp,
            download_ffmpeg=need_ffmpeg,
        )
        self._download_worker.moveToThread(self._download_thread)

        self._download_worker.progress_changed.connect(self._on_download_progress)
        self._download_worker.status_changed.connect(self._progress_status.setText)
        self._download_worker.file_progress.connect(self._on_file_progress)
        self._download_worker.finished.connect(self._on_download_finished)

        self._download_thread.started.connect(self._download_worker.run)
        self._download_worker.finished.connect(self._download_thread.quit)
        self._download_worker.finished.connect(self._download_worker.deleteLater)
        self._download_thread.finished.connect(self._download_thread.deleteLater)

        self._download_thread.start()

    def _on_download_progress(self, percent: float) -> None:
        self._progress_bar.setValue(int(percent))

    def _on_file_progress(self, dp: DownloadProgress) -> None:
        speed = self._format_speed(dp.speed_bytes)
        eta = self._format_eta(dp.eta_seconds)
        parts = [f"{dp.label}: {dp.percent:.0f}%"]
        if speed:
            parts.append(speed)
        if eta:
            parts.append(f"ETA {eta}")
        self._progress_status.setText(" | ".join(parts))

    def _on_download_finished(self, success: bool, message: str) -> None:
        t = self._i18n.get_text
        self._download_thread = None
        self._download_worker = None

        if success:
            self._progress_bar.setValue(100)
            self._progress_status.setText(t("setup.download_complete"))
            self._refresh_status()
            self._skip_btn.setText(t("setup.continue_btn"))
            self._skip_btn.setEnabled(True)
            self._retry_btn.setVisible(False)
            self._manual_btn.setVisible(False)
        else:
            self._progress_status.setText(t("setup.download_failed"))
            self._retry_btn.setVisible(True)
            self._manual_btn.setVisible(True)
            self._skip_btn.setEnabled(True)

    def _on_retry(self) -> None:
        self._on_download()

    def _on_skip(self) -> None:
        self._refresh_status()
        if self._status and self._status.is_ready:
            self._notify_ready()

    def _open_manual_links(self) -> None:
        import webbrowser
        webbrowser.open("https://github.com/yt-dlp/yt-dlp/releases")
        webbrowser.open("https://github.com/BtbN/FFmpeg-Builds/releases")

    def _notify_ready(self) -> None:
        if self.binaries_ready is not None:
            self.binaries_ready.emit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_speed(bytes_per_sec: float) -> str:
        if bytes_per_sec <= 0:
            return ""
        if bytes_per_sec >= 1_000_000:
            return f"{bytes_per_sec / 1_000_000:.1f} MB/s"
        if bytes_per_sec >= 1_000:
            return f"{bytes_per_sec / 1_000:.0f} KB/s"
        return f"{bytes_per_sec:.0f} B/s"

    @staticmethod
    def _format_eta(seconds: float) -> str:
        if seconds <= 0:
            return ""
        m, s = divmod(int(seconds), 60)
        if m > 0:
            return f"{m}m {s}s"
        return f"{s}s"

    def set_i18n(self, i18n: LanguageManager) -> None:
        self._i18n = i18n
        self.retranslate()

    # ------------------------------------------------------------------
    # Update check (called after binaries are ready)
    # ------------------------------------------------------------------

    def check_ytdlp_update(self) -> UpdateStatus | None:
        s = check_binaries()
        if not s.ytdlp_exists or s.ytdlp_path is None:
            return None
        self._update_status = check_for_updates(s.ytdlp_path)
        return self._update_status

    def update_ytdlp(self) -> tuple[bool, str]:
        s = check_binaries()
        if not s.ytdlp_exists or s.ytdlp_path is None:
            return False, "yt-dlp not found."
        return perform_update(s.ytdlp_path)

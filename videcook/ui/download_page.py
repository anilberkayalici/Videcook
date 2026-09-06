"""Download page — 4KTUBE-inspired layout with video info panel.

The page layout (top to bottom):
1. URL input bar (full width)
2. Video info panel: thumbnail on the left, metadata on the right
3. Download options row: mode toggles (Video/Audio/Thumbnail) on the left,
   quality/format selectors on the right
4. Output folder + cookies row
5. Action bar: progress + cancel/download buttons
6. Log area
"""

from dataclasses import dataclass
import base64
import os
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, QThread, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from videcook.core.models import (
    AudioFormat,
    DownloadMode,
    DownloadRequest,
    DownloadType,
)
from videcook.services.history_service import add_history_entry
from videcook.ui.video_info_worker import VideoInfoWorker, VideoInfo
from videcook.core.playlist import detect_playlist_intent
from videcook.core.thumbnail import ThumbnailSize, extract_video_id
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
from videcook.ui.subtitle_worker import YtdlpSubtitleDownloadWorker
from videcook.ui.thumbnail_worker import ThumbnailDownloadWorker
from videcook.utils.i18n import LanguageManager
from videcook.utils.preferences import load_preferences, save_preferences


@dataclass
class QueueItem:
    url: str
    title: str
    download_type: DownloadType
    quality: str
    audio_format: AudioFormat
    audio_quality: str
    cookie_file: Path | None
    output_folder: Path
    file_size_approx: int = 0
    duration_seconds: int = 0
    thumbnail_b64: str = ""


class DownloadPage(QWidget):
    """Main download form — URL, video info panel, download options."""

    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n

        self._audio_format_map: dict[str, AudioFormat] = {}
        self._quality_map: dict[str, str] = {}

        # Fast responsive debounce timer for video info + format extraction
        self._info_timer = QTimer(self)
        self._info_timer.setSingleShot(True)
        self._info_timer.setInterval(350)
        self._info_timer.timeout.connect(self._fetch_video_info)

        # Video info worker state
        self._info_thread: QThread | None = None
        self._info_worker: VideoInfoWorker | None = None
        self._current_video_info: VideoInfo | None = None

        self._cookie_path: Path | None = None
        self._output_path: Path | None = None
        self._download_type: DownloadType = DownloadType.VIDEO
        self._worker: DownloadWorker | None = None
        self._thread: QThread | None = None
        self._video_downloading: bool = False
        self._download_counter: int = 0

        # Thumbnail state
        self._thumbnail_only: bool = False
        self._thumbnail_size: str = ThumbnailSize.MAXRES
        self._thumb_download_thread: QThread | None = None
        self._thumb_download_worker: ThumbnailDownloadWorker | None = None
        self._thumbnail_downloading: bool = False

        # Subtitle state
        self._sub_thread: QThread | None = None
        self._sub_worker: YtdlpSubtitleDownloadWorker | None = None
        self._subtitle_downloading: bool = False

        # Secret videos / cookies mode
        self._secret_mode: bool = False

        # Queue / batch download state
        self._download_queue: list[QueueItem] = []
        self._is_queue_downloading: bool = False
        self._queue_current_index: int = 0
        self._queue_total_items: int = 0

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

        # Always start with Video mode by default on startup
        self._set_app_mode("video")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        from videcook.ui.widgets import ModernCard, ToggleSwitch

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
        page_layout.setSpacing(10)
        page_layout.setContentsMargins(32, 8, 32, 18)

        # =============================================
        # 1. URL INPUT WITH "URL:" LABEL
        # =============================================
        url_row = QHBoxLayout()
        url_row.setSpacing(12)

        self._url_prefix_label = QLabel("URL:")
        self._url_prefix_label.setObjectName("urlPrefixLabel")
        url_row.addWidget(self._url_prefix_label)

        self._url_input = QLineEdit()
        self._url_input.setObjectName("video_url_input")
        self._url_input.setPlaceholderText("https://youtube.com/watch?v=...")
        self._url_input.setMinimumHeight(50)
        self._url_input.textChanged.connect(self._on_url_changed)
        self._url_input.returnPressed.connect(self._fetch_video_info)
        url_row.addWidget(self._url_input, stretch=1)

        page_layout.addLayout(url_row)

        # =============================================
        # 2. VIDEO INFO PANEL (Thumbnail left + Info right)
        # =============================================
        self._info_card = QWidget()
        self._info_card.setObjectName("videoInfoCard")
        self._info_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        info_card_layout = QHBoxLayout(self._info_card)
        info_card_layout.setContentsMargins(14, 12, 14, 12)
        info_card_layout.setSpacing(16)

        # -- Thumbnail area (left side) --
        self._thumbnail_frame = QWidget()
        self._thumbnail_frame.setObjectName("thumbnailFrame")
        self._thumbnail_frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._thumbnail_frame.setFixedSize(384, 216)
        thumb_frame_layout = QVBoxLayout(self._thumbnail_frame)
        thumb_frame_layout.setContentsMargins(0, 0, 0, 0)
        thumb_frame_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._thumbnail_img = QLabel()
        self._thumbnail_img.setObjectName("thumbnailLabel")
        self._thumbnail_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumbnail_img.setScaledContents(False)
        self._thumbnail_img.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        thumb_frame_layout.addWidget(self._thumbnail_img)

        info_card_layout.addWidget(self._thumbnail_frame)

        # -- Info area (right side) --
        info_right = QVBoxLayout()
        info_right.setSpacing(6)

        # Title
        title_row = QHBoxLayout()
        self._info_title_label = QLabel()
        self._info_title_label.setObjectName("infoFieldLabel")
        title_row.addWidget(self._info_title_label)
        self._info_title_value = QLabel()
        self._info_title_value.setObjectName("infoFieldValue")
        self._info_title_value.setWordWrap(False)
        self._info_title_value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title_row.addWidget(self._info_title_value, stretch=1)
        info_right.addLayout(title_row)

        # File size
        size_row = QHBoxLayout()
        self._info_size_label = QLabel()
        self._info_size_label.setObjectName("infoFieldLabel")
        size_row.addWidget(self._info_size_label)
        self._info_size_value = QLabel()
        self._info_size_value.setObjectName("infoFieldValue")
        size_row.addWidget(self._info_size_value, stretch=1)
        info_right.addLayout(size_row)

        # Duration
        dur_row = QHBoxLayout()
        self._info_dur_label = QLabel()
        self._info_dur_label.setObjectName("infoFieldLabel")
        dur_row.addWidget(self._info_dur_label)
        self._info_dur_value = QLabel()
        self._info_dur_value.setObjectName("infoFieldValue")
        dur_row.addWidget(self._info_dur_value, stretch=1)
        info_right.addLayout(dur_row)

        # Channel
        chan_row = QHBoxLayout()
        self._info_chan_label = QLabel()
        self._info_chan_label.setObjectName("infoFieldLabel")
        chan_row.addWidget(self._info_chan_label)
        self._info_chan_value = QLabel()
        self._info_chan_value.setObjectName("infoFieldValue")
        self._info_chan_value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        chan_row.addWidget(self._info_chan_value, stretch=1)
        info_right.addLayout(chan_row)

        # Watch URL
        url_row = QHBoxLayout()
        self._info_url_label = QLabel()
        self._info_url_label.setObjectName("infoFieldLabel")
        url_row.addWidget(self._info_url_label)
        self._info_url_value = QLabel()
        self._info_url_value.setObjectName("infoFieldValue")
        self._info_url_value.setOpenExternalLinks(True)
        self._info_url_value.setCursor(Qt.CursorShape.PointingHandCursor)
        self._info_url_value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        url_row.addWidget(self._info_url_value, stretch=1)
        info_right.addLayout(url_row)

        # Description
        desc_header = QHBoxLayout()
        self._info_desc_label = QLabel()
        self._info_desc_label.setObjectName("infoFieldLabel")
        desc_header.addWidget(self._info_desc_label)
        desc_header.addStretch(1)
        info_right.addLayout(desc_header)

        self._info_desc_box = QTextEdit()
        self._info_desc_box.setObjectName("descriptionBox")
        self._info_desc_box.setReadOnly(True)
        self._info_desc_box.setMinimumHeight(85)
        self._info_desc_box.setMaximumHeight(105)
        self._info_desc_box.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._info_desc_box.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        info_right.addWidget(self._info_desc_box)

        info_right.addStretch(1)
        info_card_layout.addLayout(info_right, stretch=1)

        # -- Email & Social Media Contact area (far right side in black space) --
        self._email_card = QWidget()
        self._email_card.setObjectName("emailInfoCard")
        self._email_card.setMinimumWidth(220)
        self._email_card.setMaximumWidth(280)
        self._email_card.setFixedHeight(216)
        self._email_card.setStyleSheet("""
            #emailInfoCard {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
        """)
        email_card_outer = QVBoxLayout(self._email_card)
        email_card_outer.setContentsMargins(12, 10, 12, 10)
        email_card_outer.setSpacing(4)

        self._email_header_label = QLabel("🌐 İletişim & Sosyal Medya")
        self._email_header_label.setStyleSheet("font-weight: 700; color: #38BDF8; font-size: 12px;")
        email_card_outer.addWidget(self._email_header_label)

        # Scrollable area inside the small contact box
        self._contact_scroll = QScrollArea()
        self._contact_scroll.setWidgetResizable(True)
        self._contact_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._contact_scroll.setStyleSheet("background: transparent; border: none;")
        self._contact_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._contact_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._contact_content = QWidget()
        self._contact_content.setStyleSheet("background: transparent;")
        self._contact_layout = QVBoxLayout(self._contact_content)
        self._contact_layout.setContentsMargins(0, 0, 0, 0)
        self._contact_layout.setSpacing(6)

        self._insta_container = QWidget()
        self._insta_container.setStyleSheet("background: transparent;")
        self._insta_container_layout = QVBoxLayout(self._insta_container)
        self._insta_container_layout.setContentsMargins(0, 0, 0, 0)
        self._insta_container_layout.setSpacing(4)
        self._contact_layout.addWidget(self._insta_container)

        self._email_status_label = QLabel("")
        self._email_status_label.setWordWrap(True)
        self._email_status_label.setStyleSheet("color: #64748B; font-size: 10px; font-style: italic; margin-top: 2px;")
        self._contact_layout.addWidget(self._email_status_label)
        self._contact_layout.addStretch(1)

        self._contact_scroll.setWidget(self._contact_content)
        email_card_outer.addWidget(self._contact_scroll)

        info_card_layout.addWidget(self._email_card)

        self._info_loading_label = QLabel()
        self._info_loading_label.setObjectName("infoLoadingLabel")
        self._info_loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        page_layout.addWidget(self._info_card)

        # =============================================
        # 3. DOWNLOAD OPTIONS ROW
        # =============================================
        options_card = QWidget()
        options_card.setObjectName("downloadOptionsCard")
        options_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        options_layout = QHBoxLayout(options_card)
        options_layout.setContentsMargins(16, 12, 16, 12)
        options_layout.setSpacing(16)

        # Left side: mode buttons stacked vertically
        mode_col = QVBoxLayout()
        mode_col.setSpacing(8)

        self._video_btn = QPushButton("🎬 Video")
        self._video_btn.setObjectName("segButton")
        self._video_btn.setCheckable(True)
        self._video_btn.setChecked(True)
        self._video_btn.setMinimumHeight(40)
        self._video_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._video_btn.clicked.connect(lambda: self._set_app_mode("video"))
        mode_col.addWidget(self._video_btn)

        self._audio_btn = QPushButton("🎵 Sadece Ses")
        self._audio_btn.setObjectName("segButton")
        self._audio_btn.setCheckable(True)
        self._audio_btn.setMinimumHeight(40)
        self._audio_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._audio_btn.clicked.connect(lambda: self._set_app_mode("audio"))
        mode_col.addWidget(self._audio_btn)

        self._thumb_toggle = QPushButton("🖼️ Thumbnail İndir")
        self._thumb_toggle.setObjectName("segButton")
        self._thumb_toggle.setCheckable(True)
        self._thumb_toggle.setMinimumHeight(40)
        self._thumb_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._thumb_toggle.clicked.connect(lambda: self._set_app_mode("thumbnail"))
        mode_col.addWidget(self._thumb_toggle)

        self._secret_btn = QPushButton("🔒 Gizli Videolar")
        self._secret_btn.setObjectName("segButton")
        self._secret_btn.setCheckable(True)
        self._secret_btn.setMinimumHeight(40)
        self._secret_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._secret_btn.clicked.connect(lambda: self._set_app_mode("secret"))
        mode_col.addWidget(self._secret_btn)

        options_layout.addLayout(mode_col)

        # Right side: quality / format / thumbnail size controls
        quality_col = QVBoxLayout()
        quality_col.setSpacing(8)

        # Format/Quality Row
        self._qual_label = QLabel()
        self._qual_label.setObjectName("fieldLabel")
        quality_col.addWidget(self._qual_label)

        self._qual_combo = QComboBox()
        self._qual_combo.setObjectName("quality_combo")
        self._qual_combo.setMaxVisibleItems(8)
        self._qual_combo.setMinimumHeight(40)
        self._qual_combo.setMaximumWidth(260)
        self._qual_combo.currentIndexChanged.connect(self._on_qual_combo_changed)
        quality_col.addWidget(self._qual_combo)

        # Subtitle Row (for Video mode - placed directly under video quality dropdown)
        self._video_sub_panel = QWidget()
        self._video_sub_panel.setObjectName("videoSubPanel")
        sub_layout = QHBoxLayout(self._video_sub_panel)
        sub_layout.setContentsMargins(0, 4, 0, 0)
        sub_layout.setSpacing(8)

        self._sub_label = QLabel("Altyazı:")
        self._sub_label.setObjectName("fieldLabel")
        sub_layout.addWidget(self._sub_label)

        self._sub_lang_combo = QComboBox()
        self._sub_lang_combo.setObjectName("subLangCombo")
        self._sub_lang_combo.setMinimumHeight(38)
        self._sub_lang_combo.addItem("🇹🇷 Türkçe", "tr,tr-orig")
        self._sub_lang_combo.addItem("🇬🇧 English", "en,en-orig")
        self._sub_lang_combo.addItem("🌐 Tüm Diller (All)", "all,-live_chat")
        self._sub_lang_combo.addItem("🇩🇪 Deutsch", "de")
        self._sub_lang_combo.addItem("🇫🇷 Français", "fr")
        self._sub_lang_combo.addItem("🇪🇸 Español", "es")
        self._sub_lang_combo.addItem("🇷🇺 Русский", "ru")
        self._sub_lang_combo.addItem("🇸🇦 العربية", "ar")
        sub_layout.addWidget(self._sub_lang_combo, stretch=2)

        self._sub_format_combo = QComboBox()
        self._sub_format_combo.setObjectName("subFormatCombo")
        self._sub_format_combo.setMinimumHeight(38)
        self._sub_format_combo.addItem("SRT (.srt)", "srt")
        self._sub_format_combo.addItem("VTT (.vtt)", "vtt")
        self._sub_format_combo.addItem("TXT (.txt)", "txt")
        self._sub_format_combo.addItem("ASS (.ass)", "ass")
        sub_layout.addWidget(self._sub_format_combo, stretch=1)

        self._sub_download_btn = QPushButton("📥 Altyazıyı İndir")
        self._sub_download_btn.setObjectName("subDownloadBtn")
        self._sub_download_btn.setMinimumHeight(38)
        self._sub_download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sub_download_btn.clicked.connect(self._start_subtitle_download)
        sub_layout.addWidget(self._sub_download_btn, stretch=2)

        quality_col.addWidget(self._video_sub_panel)

        # Thumbnail Size (hidden by default)
        self._thumb_panel = QWidget()
        thumb_layout = QVBoxLayout(self._thumb_panel)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        self._thumb_size_label = QLabel()
        self._thumb_size_label.setObjectName("fieldLabel")
        thumb_layout.addWidget(self._thumb_size_label)
        self._thumb_size_combo = QComboBox()
        self._thumb_size_combo.setMinimumHeight(40)
        self._thumb_size_combo.setMaximumWidth(260)
        for size in ThumbnailSize.ALL:
            self._thumb_size_combo.addItem(ThumbnailSize.LABELS[size], size)
        self._thumb_size_combo.currentIndexChanged.connect(self._on_thumb_size_changed)
        thumb_layout.addWidget(self._thumb_size_combo)
        self._thumb_panel.setVisible(False)
        quality_col.addWidget(self._thumb_panel)

        # Audio Quality (Bitrate) Row (for audio mode)
        self._audio_qual_panel = QWidget()
        self._audio_qual_panel.setObjectName("audioQualityPanel")
        audio_qual_layout = QVBoxLayout(self._audio_qual_panel)
        audio_qual_layout.setContentsMargins(0, 0, 0, 0)
        self._audio_qual_label = QLabel()
        self._audio_qual_label.setObjectName("fieldLabel")
        audio_qual_layout.addWidget(self._audio_qual_label)
        self._audio_qual_combo = QComboBox()
        self._audio_qual_combo.setObjectName("audio_quality_combo")
        self._audio_qual_combo.setMaxVisibleItems(8)
        self._audio_qual_combo.setMinimumHeight(40)
        self._audio_qual_combo.setMaximumWidth(260)
        self._audio_qual_combo.currentIndexChanged.connect(self._on_audio_qual_changed)
        audio_qual_layout.addWidget(self._audio_qual_combo)
        self._audio_qual_panel.setVisible(False)
        quality_col.addWidget(self._audio_qual_panel)

        # Secret / Cookies panel (for secret videos mode)
        self._secret_panel = QWidget()
        self._secret_panel.setObjectName("secretPanel")
        secret_layout = QVBoxLayout(self._secret_panel)
        secret_layout.setContentsMargins(0, 4, 0, 0)
        secret_layout.setSpacing(6)

        self._cookie_label = QLabel()
        self._cookie_label.setObjectName("fieldLabel")
        secret_layout.addWidget(self._cookie_label)

        cookie_row = QHBoxLayout()
        cookie_row.setSpacing(8)
        self._cookie_display = QLineEdit()
        self._cookie_display.setObjectName("cookie_path_input")
        self._cookie_display.setReadOnly(True)
        self._cookie_display.setMinimumHeight(40)
        cookie_row.addWidget(self._cookie_display, stretch=1)

        self._cookie_browse = QPushButton("Gözat")
        self._cookie_browse.setObjectName("cookie_browse_button")
        self._cookie_browse.setFixedSize(110, 40)
        self._cookie_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cookie_browse.clicked.connect(self._browse_cookie)
        cookie_row.addWidget(self._cookie_browse)
        secret_layout.addLayout(cookie_row)

        self._secret_hint = QLabel()
        self._secret_hint.setObjectName("mutedText")
        self._secret_hint.setWordWrap(True)
        secret_layout.addWidget(self._secret_hint)

        self._secret_panel.setVisible(False)
        quality_col.addWidget(self._secret_panel)

        quality_col.addStretch(1)
        options_layout.addLayout(quality_col)

        # Music Analysis Column (placed to the right of format/quality controls for audio mode)
        self._music_col = QVBoxLayout()
        self._music_col.setSpacing(8)

        self._music_analysis_label = QLabel("Müzik Analizi:")
        self._music_analysis_label.setObjectName("fieldLabel")
        self._music_col.addWidget(self._music_analysis_label)

        self._music_analysis_btn = QPushButton("🎵 BPM & Nota Analizi")
        self._music_analysis_btn.setObjectName("musicAnalysisBtn")
        self._music_analysis_btn.setMinimumHeight(40)
        self._music_analysis_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._music_analysis_btn.setStyleSheet("""
            QPushButton#musicAnalysisBtn {
                background-color: #2D144F;
                color: #E9D5FF;
                border: 1px solid #7C3AED;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                padding: 8px 18px;
            }
            QPushButton#musicAnalysisBtn:hover {
                background-color: #4C1D95;
                color: #FFFFFF;
                border-color: #A78BFA;
            }
        """)
        self._music_analysis_btn.clicked.connect(self._on_music_analysis_clicked)
        self._music_col.addWidget(self._music_analysis_btn)

        self._pitch_tempo_label = QLabel("Müzik Ayarlama:")
        self._pitch_tempo_label.setObjectName("fieldLabel")
        self._music_col.addWidget(self._pitch_tempo_label)

        self._pitch_tempo_btn = QPushButton("🎛️ Ton & BPM Değiştir")
        self._pitch_tempo_btn.setObjectName("pitchTempoBtn")
        self._pitch_tempo_btn.setMinimumHeight(40)
        self._pitch_tempo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pitch_tempo_btn.setStyleSheet("""
            QPushButton#pitchTempoBtn {
                background-color: #1E1B4B;
                color: #C7D2FE;
                border: 1px solid #6366F1;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                padding: 8px 18px;
            }
            QPushButton#pitchTempoBtn:hover {
                background-color: #312E81;
                color: #FFFFFF;
                border-color: #818CF8;
            }
        """)
        self._pitch_tempo_btn.clicked.connect(self._on_pitch_tempo_clicked)
        self._music_col.addWidget(self._pitch_tempo_btn)

        self._music_analysis_label.setVisible(False)
        self._music_analysis_btn.setVisible(False)
        self._pitch_tempo_label.setVisible(False)
        self._pitch_tempo_btn.setVisible(False)
        self._music_col.addStretch(1)

        options_layout.addLayout(self._music_col)
        options_layout.addStretch(1)

        page_layout.addWidget(options_card)

        # =============================================
        # 4. OUTPUT FOLDER (Settings Card)
        # =============================================
        self._settings_card = ModernCard()

        # Output folder row
        out_layout = QVBoxLayout()
        self._out_label = QLabel()
        self._out_label.setObjectName("fieldLabel")
        out_layout.addWidget(self._out_label)
        out_row = QHBoxLayout()
        self._out_display = QLineEdit()
        self._out_display.setObjectName("output_path_input")
        self._out_display.setReadOnly(True)
        self._out_display.setMinimumHeight(44)
        out_row.addWidget(self._out_display, stretch=1)
        self._out_browse = QPushButton("Gözat")
        self._out_browse.setObjectName("output_browse_button")
        self._out_browse.setFixedSize(110, 44)
        self._out_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self._out_browse.clicked.connect(self._browse_output)
        out_row.addWidget(self._out_browse)
        out_layout.addLayout(out_row)
        self._settings_card.addLayout(out_layout)

        page_layout.addWidget(self._settings_card)

        # =============================================
        # 5. ACTION BAR (Progress + Cancel + Queue + Download)
        # =============================================
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        self._progress = QProgressBar()
        self._progress.setObjectName("progress_bar")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setMinimumHeight(10)
        self._progress.setTextVisible(False)

        self._status = QLabel()
        self._status.setObjectName("status_label")

        status_vbox = QVBoxLayout()
        status_vbox.setSpacing(6)
        status_vbox.addWidget(self._status)
        status_vbox.addWidget(self._progress)

        self._cancel_btn = QPushButton()
        self._cancel_btn.setObjectName("cancel_button")
        self._cancel_btn.setMinimumSize(100, 46)
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)

        self._show_folder_btn = QPushButton("Klasörde Göster")
        self._show_folder_btn.setObjectName("ghostButton")
        self._show_folder_btn.setMinimumSize(120, 46)
        self._show_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._show_folder_btn.setVisible(False)
        self._show_folder_btn.clicked.connect(self._on_show_folder_clicked)

        self._queue_add_btn = QPushButton("➕ Sıraya Ekle")
        self._queue_add_btn.setObjectName("queue_add_button")
        self._queue_add_btn.setMinimumSize(125, 46)
        self._queue_add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._queue_add_btn.clicked.connect(self._on_queue_add_clicked)

        self._queue_start_btn = QPushButton("🚀 Sırayı İndir")
        self._queue_start_btn.setObjectName("queue_start_button")
        self._queue_start_btn.setMinimumSize(140, 46)
        self._queue_start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._queue_start_btn.setVisible(False)
        self._queue_start_btn.clicked.connect(self._on_queue_start_clicked)

        self._download_btn = QPushButton("İndir")
        self._download_btn.setObjectName("download_button")
        self._download_btn.setMinimumSize(110, 46)
        self._download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._download_btn.clicked.connect(self._on_download_clicked)

        action_layout.addLayout(status_vbox, stretch=1)
        action_layout.addWidget(self._show_folder_btn)
        action_layout.addWidget(self._cancel_btn)
        action_layout.addWidget(self._queue_add_btn)
        action_layout.addWidget(self._queue_start_btn)
        action_layout.addWidget(self._download_btn)

        page_layout.addLayout(action_layout)

        # =============================================
        # 6. LOG AREA
        # =============================================
        self._log_title = QLabel()
        self._log_title.setObjectName("logTitle")
        self._log = QPlainTextEdit()
        self._log.setObjectName("operation_log")
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(100)
        self._log.setMinimumHeight(100)
        self._log.setMaximumHeight(160)
        page_layout.addWidget(self._log_title)
        page_layout.addWidget(self._log)

        page_layout.addStretch(1)

        # Hidden labels referenced in retranslate
        self._source_title = QLabel()
        self._type_label = QLabel()
        self._mode_format_row = QWidget()
        self._url_label = QLabel()

        # Set initial empty state for info panel
        self._clear_video_info()

    # ------------------------------------------------------------------
    # App mode switching
    # ------------------------------------------------------------------

    def _set_app_mode(self, mode: str) -> None:
        self._video_btn.setChecked(mode == "video")
        self._audio_btn.setChecked(mode == "audio")
        self._thumb_toggle.setChecked(mode == "thumbnail")
        self._secret_btn.setChecked(mode == "secret")

        if mode == "video":
            self._set_download_type(DownloadType.VIDEO)
            self._thumbnail_only = False
            self._secret_mode = False
            self._qual_combo.setVisible(True)
            self._qual_label.setVisible(True)
            self._video_sub_panel.setVisible(True)
            self._audio_qual_panel.setVisible(False)
            self._thumb_panel.setVisible(False)
            self._secret_panel.setVisible(False)
            self._update_thumbnail_button_text()
        elif mode == "audio":
            self._set_download_type(DownloadType.AUDIO)
            self._thumbnail_only = False
            self._secret_mode = False
            self._qual_combo.setVisible(True)
            self._qual_label.setVisible(True)
            self._video_sub_panel.setVisible(False)
            self._audio_qual_panel.setVisible(True)
            self._thumb_panel.setVisible(False)
            self._secret_panel.setVisible(False)
            self._refresh_audio_qual_combo()
            self._update_thumbnail_button_text()
        elif mode == "thumbnail":
            self._thumbnail_only = True
            self._secret_mode = False
            self._qual_combo.setVisible(False)
            self._qual_label.setVisible(False)
            self._video_sub_panel.setVisible(False)
            self._audio_qual_panel.setVisible(False)
            self._thumb_panel.setVisible(True)
            self._secret_panel.setVisible(False)
            self._update_thumbnail_button_text()
        elif mode == "secret":
            self._set_download_type(DownloadType.VIDEO)
            self._thumbnail_only = False
            self._secret_mode = True
            self._qual_combo.setVisible(True)
            self._qual_label.setVisible(True)
            self._video_sub_panel.setVisible(False)
            self._audio_qual_panel.setVisible(False)
            self._thumb_panel.setVisible(False)
            self._secret_panel.setVisible(True)
            self._update_thumbnail_button_text()

        self._update_displayed_filesize()

    # ------------------------------------------------------------------
    # URL change handling
    # ------------------------------------------------------------------

    def _on_url_changed(self, text: str) -> None:
        stripped = text.strip()
        if stripped:
            self._info_timer.start()
        else:
            self._info_timer.stop()
            self._clear_video_info()
            if self._download_type is DownloadType.VIDEO:
                self._refresh_format_combo()

    # ------------------------------------------------------------------
    # Video info fetch
    # ------------------------------------------------------------------

    def _fetch_video_info(self) -> None:
        """Start fetching video metadata & formats for the current URL."""
        url = self._url_input.text().strip()
        if not url:
            return

        # Show loading state
        self._show_info_loading()

        # Cancel previous fetch
        self._cleanup_info_worker()

        status = check_binaries()
        if not status.is_ready or status.ytdlp_path is None:
            self._show_info_error()
            return

        self._info_thread = QThread()
        self._info_worker = VideoInfoWorker(url, status.ytdlp_path)
        self._info_worker.moveToThread(self._info_thread)
        self._info_thread.started.connect(self._info_worker.run)
        self._info_worker.info_ready.connect(self._on_video_info_ready)
        self._info_worker.thumbnail_ready.connect(self._on_video_thumbnail_ready)
        self._info_worker.info_failed.connect(self._on_video_info_failed)
        self._info_worker.info_ready.connect(self._info_thread.quit)
        self._info_worker.info_failed.connect(self._info_thread.quit)
        self._info_thread.finished.connect(self._on_info_thread_done)
        self._info_thread.start()

    def _on_video_info_ready(self, info: VideoInfo) -> None:
        """Populate the info panel with video metadata and update quality dropdown."""
        self._current_video_info = info

        # Title (truncate with ellipsis if long to protect UI layout)
        raw_title = (info.title or "").strip()
        if len(raw_title) > 65:
            display_title = raw_title[:62] + "..."
        else:
            display_title = raw_title or "—"
        self._info_title_value.setText(display_title)
        self._info_title_value.setToolTip(raw_title)

        raw_chan = (info.channel or "").strip()
        if len(raw_chan) > 42:
            display_chan = raw_chan[:39] + "..."
        else:
            display_chan = raw_chan or "—"
        self._info_chan_value.setText(display_chan)
        self._info_chan_value.setToolTip(raw_chan)

        # Watch URL (clickable, truncate with ellipsis if long to protect UI layout)
        current_url = self._url_input.text().strip() or getattr(info, "url", "")
        if current_url:
            display_url = current_url if len(current_url) <= 50 else current_url[:47] + "..."
            self._info_url_value.setText(
                f'<a href="{current_url}" style="color: #38BDF8; text-decoration: underline;">{display_url}</a>'
            )
            self._info_url_value.setToolTip(current_url)
        else:
            self._info_url_value.setText("—")

        # Duration: format as HH:MM:SS or MM:SS
        if info.duration_seconds > 0:
            hours = info.duration_seconds // 3600
            minutes = (info.duration_seconds % 3600) // 60
            seconds = info.duration_seconds % 60
            if hours > 0:
                self._info_dur_value.setText(f"{hours:02d}h{minutes:02d}m{seconds:02d}s")
            else:
                self._info_dur_value.setText(f"{minutes:02d}m{seconds:02d}s")
        else:
            self._info_dur_value.setText("—")

        # File size: format as MB or GB
        if info.filesize_approx > 0:
            if info.filesize_approx >= 1_073_741_824:  # 1 GB
                self._info_size_value.setText(f"{info.filesize_approx / 1_073_741_824:.2f} GB")
            else:
                self._info_size_value.setText(f"{info.filesize_approx / 1_048_576:.2f} MB")
        else:
            self._info_size_value.setText("—")

        # Description
        if info.description:
            desc = info.description[:500]
            if len(info.description) > 500:
                desc += "..."
            self._info_desc_box.setPlainText(desc)
        else:
            self._info_desc_box.setPlainText("—")

        # Social Media & Contact Links
        self._clear_insta_container()
        social_links = getattr(info, "social_links", [])

        # Fallback to email & instagram_handles if social_links is empty
        if not social_links:
            social_links = []
            email = getattr(info, "email", "")
            if email:
                social_links.append({"platform": "email", "label": f"📧 {email}", "url": f"mailto:{email}"})
            for h in getattr(info, "instagram_handles", []):
                social_links.append({"platform": "instagram", "label": f"📸 Instagram (@{h})", "url": f"https://instagram.com/{h}"})

        if social_links:
            color_map = {
                "email": "#4ADE80",
                "instagram": "#F472B6",
                "tiktok": "#22D3EE",
                "discord": "#818CF8",
                "twitter": "#38BDF8",
                "twitch": "#A855F7",
                "patreon": "#F97316",
                "linktree": "#34D399",
                "buymeacoffee": "#FBBF24",
                "website": "#38BDF8",
            }
            for link in social_links:
                platform = link.get("platform", "website")
                label_text = link.get("label", "")
                target_url = link.get("url", "")
                color = color_map.get(platform, "#38BDF8")

                if platform == "email" and target_url.startswith("mailto:"):
                    raw_email = target_url.replace("mailto:", "")
                    lbl = QLabel(f'<span style="color: {color}; font-weight: bold;">📧 {raw_email}</span>')
                    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                else:
                    lbl = QLabel(f'<a href="{target_url}" style="color: {color}; font-weight: bold; text-decoration: underline;">{label_text}</a>')
                    lbl.setOpenExternalLinks(True)
                    lbl.setCursor(Qt.CursorShape.PointingHandCursor)

                lbl.setWordWrap(True)
                lbl.setStyleSheet("font-size: 11px;")
                self._insta_container_layout.addWidget(lbl)

            self._email_status_label.setText("✅ Otomatik tespit edildi")
        else:
            no_link = QLabel("Belirtilmemiş")
            no_link.setStyleSheet("color: #94A3B8; font-size: 11px;")
            self._insta_container_layout.addWidget(no_link)
            self._email_status_label.setText("ℹ️ Açıklamada bulunamadı")

        # Show the info fields
        self._set_info_fields_visible(True)
        self._info_loading_label.setVisible(False)

        # Update quality combo dynamically for video mode
        if self._download_type is DownloadType.VIDEO:
            self._qual_combo.blockSignals(True)
            self._qual_combo.clear()
            self._quality_map.clear()

            best_label = self._i18n.get_text("quality.best")
            self._quality_map[best_label] = "best"
            self._qual_combo.addItem(best_label)

            if info.formats:
                for opt in info.formats:
                    self._quality_map[opt.label] = opt.quality_value
                    self._qual_combo.addItem(opt.label)
            else:
                for label, val in [
                    ("1080p", "1080"),
                    ("720p", "720"),
                    ("480p", "480"),
                ]:
                    self._quality_map[label] = val
                    self._qual_combo.addItem(label)

            self._qual_combo.setEnabled(True)
            self._qual_combo.setCurrentIndex(0)
            self._qual_combo.blockSignals(False)

        self._update_displayed_filesize()

    def _clear_insta_container(self) -> None:
        if not hasattr(self, "_insta_container_layout"):
            return
        while self._insta_container_layout.count():
            item = self._insta_container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _on_qual_combo_changed(self, _index: int) -> None:
        """Handle format or quality dropdown selection changes."""
        if self._download_type is DownloadType.AUDIO:
            self._refresh_audio_qual_combo()
        self._update_displayed_filesize()

    def _on_audio_qual_changed(self, _index: int) -> None:
        """Handle audio bitrate selection changes."""
        self._update_displayed_filesize()

    def _refresh_audio_qual_combo(self) -> None:
        """Populate the audio quality (bitrate) dropdown based on selected audio format."""
        t = self._i18n.get_text
        cur_fmt_text = self._qual_combo.currentText()
        fmt = self._audio_format_map.get(cur_fmt_text, AudioFormat.MP3)

        self._audio_qual_combo.blockSignals(True)
        self._audio_qual_combo.clear()

        if fmt is AudioFormat.WAV:
            self._audio_qual_combo.addItem(t("audio_quality.wav"), "1411")
        elif fmt is AudioFormat.FLAC:
            self._audio_qual_combo.addItem(t("audio_quality.flac"), "lossless")
        else:
            options = [
                (t("audio_quality.320"), "320"),
                (t("audio_quality.256"), "256"),
                (t("audio_quality.192"), "192"),
                (t("audio_quality.160"), "160"),
                (t("audio_quality.128"), "128"),
                (t("audio_quality.96"), "96"),
                (t("audio_quality.64"), "64"),
                (t("audio_quality.48"), "48"),
            ]
            for label, val in options:
                self._audio_qual_combo.addItem(label, val)

        self._audio_qual_combo.setEnabled(True)
        self._audio_qual_combo.setCurrentIndex(0)
        self._audio_qual_combo.blockSignals(False)

    def _update_displayed_filesize(self) -> None:
        """Dynamically calculate and display the estimated file size for the currently selected mode/quality."""
        if not self._current_video_info or (
            self._current_video_info.duration_seconds <= 0
            and self._current_video_info.filesize_approx <= 0
        ):
            return

        dur = self._current_video_info.duration_seconds
        size_bytes = 0

        # Mode 1: Sadece Thumbnail İndir
        if self._thumbnail_only:
            sz = self._thumb_size_combo.currentData() or self._thumbnail_size
            if sz == ThumbnailSize.MAXRES:
                size_bytes = 180_000  # ~180 KB
            elif sz == ThumbnailSize.HIGH:
                size_bytes = 70_000   # ~70 KB
            elif sz == ThumbnailSize.MEDIUM:
                size_bytes = 35_000   # ~35 KB
            else:
                size_bytes = 15_000   # ~15 KB

        # Mode 2: Sadece Ses
        elif self._download_type is DownloadType.AUDIO:
            cur_text = self._qual_combo.currentText()
            fmt = self._audio_format_map.get(cur_text)
            if fmt is AudioFormat.WAV:
                # 16-bit 44.1kHz stereo PCM = 176,400 bytes/sec
                size_bytes = int(dur * 176_400) if dur > 0 else 50_000_000
            elif fmt is AudioFormat.FLAC:
                # Lossless compressed audio ~ 55% of WAV
                size_bytes = int(dur * 176_400 * 0.55) if dur > 0 else 25_000_000
            else:
                aq = self._audio_qual_combo.currentData() or "320"
                try:
                    kbps = int(aq)
                except Exception:
                    kbps = 320
                size_bytes = int(dur * (kbps * 1000) / 8) if dur > 0 else int(kbps * 1000 * 300 / 8)

        # Mode 3: Video
        else:
            cur_text = self._qual_combo.currentText()
            best_label = self._i18n.get_text("quality.best")

            # Match from extracted formats list
            matched_opt = None
            if self._current_video_info and self._current_video_info.formats:
                if cur_text == best_label:
                    matched_opt = self._current_video_info.formats[0]
                else:
                    for opt in self._current_video_info.formats:
                        if opt.label == cur_text:
                            matched_opt = opt
                            break

            if matched_opt and matched_opt.filesize_approx > 0:
                size_bytes = matched_opt.filesize_approx
            elif self._current_video_info.filesize_approx > 0 and cur_text == best_label:
                size_bytes = self._current_video_info.filesize_approx
            elif dur > 0:
                m = re.search(r"(\d+)p", cur_text)
                h = int(m.group(1)) if m else 720
                bitrate_bps = {
                    4320: 25_000_000,
                    2160: 12_000_000,
                    1440: 6_000_000,
                    1080: 3_200_000,
                    720: 1_600_000,
                    480: 800_000,
                    360: 450_000,
                    240: 220_000,
                    144: 100_000,
                }.get(h, 1_600_000)
                size_bytes = int(dur * (bitrate_bps + 160_000) / 8)

        # Update the UI label
        if size_bytes > 0:
            if size_bytes >= 1_073_741_824:
                self._info_size_value.setText(f"{size_bytes / 1_073_741_824:.2f} GB")
            elif size_bytes >= 1_048_576:
                self._info_size_value.setText(f"{size_bytes / 1_048_576:.2f} MB")
            elif size_bytes >= 1024:
                self._info_size_value.setText(f"{size_bytes / 1024:.1f} KB")
            else:
                self._info_size_value.setText(f"{size_bytes} B")
        else:
            self._info_size_value.setText("—")

    def _on_video_thumbnail_ready(self, data: bytes) -> None:
        """Display the thumbnail image in the info panel, filling the 300x168 container."""
        if not data:
            return

        self._current_video_thumb_b64 = base64.b64encode(data).decode("ascii")

        pixmap = QPixmap()
        pixmap.loadFromData(data)
        if pixmap.isNull():
            return

        # Target dimensions (interior of 384x216 frame)
        target_w, target_h = 380, 212
        # Scale to completely cover the target area (no empty margins/letterbox)
        scaled = pixmap.scaled(
            QSize(target_w, target_h),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        # Center-crop to exact frame
        x = max(0, (scaled.width() - target_w) // 2)
        y = max(0, (scaled.height() - target_h) // 2)
        cropped = scaled.copy(x, y, min(target_w, scaled.width()), min(target_h, scaled.height()))
        self._thumbnail_img.setPixmap(cropped)

    def _on_video_info_failed(self, error: str) -> None:
        """Show error state in the info panel and restore default formats."""
        self._show_info_error()
        if self._download_type is DownloadType.VIDEO:
            self._refresh_format_combo()

    def _on_info_thread_done(self) -> None:
        old_worker = self._info_worker
        old_thread = self._info_thread
        QTimer.singleShot(
            500,
            lambda w=old_worker, t=old_thread: self._finalize_info_refs(w, t),
        )

    def _finalize_info_refs(self, old_worker, old_thread) -> None:
        if self._info_worker is old_worker:
            self._info_worker = None
        if self._info_thread is old_thread:
            self._info_thread = None

    def _cleanup_info_worker(self) -> None:
        if self._info_worker:
            try:
                self._info_worker.cancel()
            except Exception:
                pass
        if self._info_thread:
            try:
                if self._info_thread.isRunning():
                    self._info_thread.quit()
                    self._info_thread.wait(2000)
            except Exception:
                pass
        self._info_worker = None
        self._info_thread = None

    def _clear_video_info(self) -> None:
        """Reset the info panel to empty/placeholder state."""
        self._current_video_info = None
        self._thumbnail_img.clear()
        self._thumbnail_img.setText("🖼️")
        self._info_url_value.setText("—")
        self._clear_insta_container()
        self._email_status_label.setText("")
        self._set_info_fields_visible(False)
        self._info_loading_label.setVisible(False)

    def _show_info_loading(self) -> None:
        """Show loading indicator in the info panel."""
        t = self._i18n.get_text
        self._thumbnail_img.clear()
        self._thumbnail_img.setText("⏳")
        self._info_title_value.setText(t("info.loading"))
        self._info_size_value.setText("...")
        self._info_dur_value.setText("...")
        self._info_chan_value.setText("...")
        self._info_url_value.setText("...")
        self._info_desc_box.setPlainText("")
        self._clear_insta_container()
        loading_insta = QLabel("...")
        loading_insta.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self._insta_container_layout.addWidget(loading_insta)
        self._email_status_label.setText("Açıklama taranıyor...")
        self._set_info_fields_visible(True)

    def _show_info_error(self) -> None:
        """Show error state in the info panel."""
        t = self._i18n.get_text
        self._thumbnail_img.clear()
        self._thumbnail_img.setText("⚠️")
        self._info_title_value.setText(t("info.failed"))
        self._info_size_value.setText("—")
        self._info_dur_value.setText("—")
        self._info_chan_value.setText("—")
        self._info_url_value.setText("—")
        self._info_desc_box.setPlainText("")
        self._clear_insta_container()
        err_insta = QLabel("—")
        err_insta.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self._insta_container_layout.addWidget(err_insta)
        self._email_status_label.setText("")
        self._set_info_fields_visible(True)

    def _set_info_fields_visible(self, visible: bool) -> None:
        """Show or hide all info field rows."""
        for widget in (
            self._info_title_label, self._info_title_value,
            self._info_size_label, self._info_size_value,
            self._info_dur_label, self._info_dur_value,
            self._info_chan_label, self._info_chan_value,
            self._info_url_label, self._info_url_value,
            self._info_desc_label, self._info_desc_box,
            self._email_card,
        ):
            widget.setVisible(visible)

    def _set_download_type(self, dtype: DownloadType) -> None:
        self._download_type = dtype
        self._video_btn.setChecked(dtype is DownloadType.VIDEO and not self._thumbnail_only and not self._secret_mode)
        self._audio_btn.setChecked(dtype is DownloadType.AUDIO)
        self._video_sub_panel.setVisible(dtype is DownloadType.VIDEO and not self._thumbnail_only and not self._secret_mode)
        self._audio_qual_panel.setVisible(dtype is DownloadType.AUDIO)
        self._music_analysis_label.setVisible(dtype is DownloadType.AUDIO)
        self._music_analysis_btn.setVisible(dtype is DownloadType.AUDIO)
        if hasattr(self, "_pitch_tempo_label"):
            self._pitch_tempo_label.setVisible(dtype is DownloadType.AUDIO)
        if hasattr(self, "_pitch_tempo_btn"):
            self._pitch_tempo_btn.setVisible(dtype is DownloadType.AUDIO)
        self._refresh_format_combo()

    def _save_current_preferences(self) -> None:
        prefs = load_preferences()
        prefs.last_download_type = (
            "audio" if self._download_type is DownloadType.AUDIO else "video"
        )
        if self._output_path is not None:
            prefs.last_output_folder = str(self._output_path)
        combo_text = self._qual_combo.currentText()
        if self._download_type is DownloadType.AUDIO:
            for key, fmt in self._audio_format_map.items():
                if key == combo_text:
                    for lkey in ("audio_format.wav",
                                 "audio_format.mp3",
                                 "audio_format.opus",
                                 "audio_format.aac",
                                 "audio_format.flac"):
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
    # Thumbnail pipeline
    # ------------------------------------------------------------------

    def _on_thumb_size_changed(self, _index: int) -> None:
        data = self._thumb_size_combo.currentData()
        if isinstance(data, str) and data in ThumbnailSize.ALL:
            self._thumbnail_size = data
        self._update_displayed_filesize()

    def _update_thumbnail_button_text(self) -> None:
        if self._thumb_toggle.isChecked():
            key = "thumbnail.download_started" if self._thumbnail_downloading else "thumbnail.download_button"
        else:
            key = "action.start_download"
        self._download_btn.setText(self._i18n.get_text(key))

    def _on_thumbnail_download_finished(self, success: bool, message: str) -> None:
        t = self._i18n.get_text
        self._progress.setValue(100 if success else 0)
        self._status.setText(t("status.completed") if success else t("status.error"))
        self._append_log(message)
        self._thumbnail_downloading = False
        self._reset_thumbnail_ui()
        if success:
            self._cancel_btn.setVisible(False)
            self._show_folder_btn.setVisible(True)
            try:
                title = ""
                if self._current_video_info and self._current_video_info.title:
                    title = self._current_video_info.title

                # 1. Prefer exact path from thumbnail worker
                file_path = ""
                file_size = 0
                if self._thumb_download_worker and getattr(self._thumb_download_worker, "saved_path", None):
                    sp = self._thumb_download_worker.saved_path
                    if sp and sp.is_file():
                        file_path = str(sp.resolve())
                        file_size = sp.stat().st_size

                # 2. Fallback to smart search in output folder
                if not file_path:
                    url = self._url_input.text().strip()
                    file_path = self._find_actual_downloaded_file(url=url, title=title, is_thumbnail=True)
                    if file_path and os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)

                if not title and file_path:
                    title = Path(file_path).stem
                if not title:
                    title = "YouTube Thumbnail"

                add_history_entry(
                    title=title,
                    file_path=file_path,
                    file_size_bytes=file_size,
                    duration_seconds=0,
                    download_type="thumbnail",
                    format_label=f"THUMBNAIL: {self._thumb_size_combo.currentText()}",
                    url=self._url_input.text().strip(),
                    thumbnail_b64=getattr(self, "_current_video_thumb_b64", ""),
                )
            except Exception:
                pass

        old_worker = self._thumb_download_worker
        old_thread = self._thumb_download_thread
        QTimer.singleShot(
            0,
            lambda w=old_worker, t=old_thread: self._finalize_thumbnail_refs(w, t),
        )

    def _finalize_thumbnail_refs(
        self,
        old_worker: object | None,
        old_thread: object | None,
    ) -> None:
        if self._thumb_download_worker is old_worker:
            self._thumb_download_worker = None
        if self._thumb_download_thread is old_thread:
            self._thumb_download_thread = None

    def _reset_thumbnail_ui(self) -> None:
        self._download_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._update_thumbnail_button_text()
        if not self._worker:
            self._status.setText(self._i18n.get_text("status.ready"))

    def _on_thumbnail_progress(self, percent: int) -> None:
        self._progress.setValue(percent)

    def _on_thumbnail_started(self, video_id: str) -> None:
        t = self._i18n.get_text
        self._status.setText(t("status.downloading"))

    def _on_thumbnail_metadata(self, video_id: str, title: str) -> None:
        if title:
            self._append_log(f"Başlık: {title}")

    def _cleanup_thumbnail_download(self) -> None:
        if self._thumb_download_worker is not None:
            self._thumb_download_worker.cancel()
        if self._thumb_download_thread is not None and self._thumb_download_thread.isRunning():
            self._thumb_download_thread.quit()
        self._thumb_download_worker = None
        self._thumb_download_thread = None

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._source_title.setText(t("download.source_title"))
        self._url_label.setText(t("label.video_url"))
        self._type_label.setText(t("label.type"))
        self._video_btn.setText("🎬 " + t("label.video_mode"))
        self._audio_btn.setText("🎵 " + t("label.audio_mode"))
        self._thumb_toggle.setText("🖼️ " + t("label.thumbnail_only"))
        self._secret_btn.setText("🔒 " + t("label.secret_videos"))
        self._cookie_label.setText(t("label.cookie_file"))
        self._secret_hint.setText(t("label.secret_hint"))
        self._cookie_browse.setText(t("action.browse"))
        self._out_label.setText(t("label.output_folder"))
        self._out_browse.setText(t("action.browse"))
        self._audio_qual_label.setText(t("label.audio_quality"))
        self._sub_label.setText(t("label.subtitles"))
        self._sub_download_btn.setText("📥 " + t("action.download_sub"))
        self._download_btn.setText(t("action.start_download"))
        self._queue_add_btn.setText(t("action.queue_add"))
        if len(self._download_queue) > 0:
            self._queue_start_btn.setText(t("action.queue_start").format(count=len(self._download_queue)))
        self._cancel_btn.setText(t("action.cancel"))
        self._show_folder_btn.setText(t("action.show_folder"))
        if hasattr(self, "_music_analysis_label"):
            self._music_analysis_label.setText("Müzik Analizi:" if self._i18n.current_language == "tr" else "Music Analysis:")
        if hasattr(self, "_music_analysis_btn"):
            self._music_analysis_btn.setText("🎵 " + ("BPM & Nota Analizi" if self._i18n.current_language == "tr" else "BPM & Key Analysis"))
        if hasattr(self, "_pitch_tempo_label"):
            self._pitch_tempo_label.setText("Müzik Ayarlama:" if self._i18n.current_language == "tr" else "Audio Shifter:")
        if hasattr(self, "_pitch_tempo_btn"):
            self._pitch_tempo_btn.setText("🎛️ " + ("Ton & BPM Değiştir" if self._i18n.current_language == "tr" else "Pitch & BPM Shifter"))
        self._log_title.setText(t("log.title"))
        self._thumb_size_label.setText(t("label.thumbnail_size"))
        if not self._worker and not self._is_queue_downloading:
            self._status.setText(t("status.ready"))

        # Video info labels
        self._info_title_label.setText(t("info.title"))
        self._info_size_label.setText(t("info.filesize"))
        self._info_dur_label.setText(t("info.duration"))
        self._info_chan_label.setText(t("info.channel"))
        self._info_url_label.setText(t("info.url"))
        self._info_desc_label.setText(t("info.description"))
        self._email_header_label.setText(t("label.channel_email"))
        self._info_loading_label.setText(t("info.loading"))

        self._refresh_format_combo()

    def _refresh_format_combo(self) -> None:
        """Populate the quality/format dropdown."""
        t = self._i18n.get_text
        prefs = load_preferences()
        self._qual_combo.blockSignals(True)

        if self._download_type is DownloadType.AUDIO:
            self._qual_label.setText(t("label.audio_format"))
            self._audio_qual_panel.setVisible(True)
            self._video_sub_panel.setVisible(False)
            self._qual_combo.clear()
            self._audio_format_map.clear()
            for key, fmt in [
                ("audio_format.mp3", AudioFormat.MP3),
                ("audio_format.wav", AudioFormat.WAV),
                ("audio_format.opus", AudioFormat.OPUS),
                ("audio_format.aac", AudioFormat.AAC),
                ("audio_format.flac", AudioFormat.FLAC),
            ]:
                text = t(key)
                self._audio_format_map[text] = fmt
                self._qual_combo.addItem(text)
            idx = self._qual_combo.findText(t(prefs.last_audio_format))
            if idx >= 0:
                self._qual_combo.setCurrentIndex(idx)
            self._refresh_audio_qual_combo()
        else:
            self._qual_label.setText(t("label.quality"))
            self._audio_qual_panel.setVisible(False)
            self._video_sub_panel.setVisible(not self._thumbnail_only and not self._secret_mode)
            self._qual_combo.clear()
            self._quality_map.clear()

            best_label = t("quality.best")
            self._quality_map[best_label] = "best"
            self._qual_combo.addItem(best_label)

            # If we already have fetched video formats, use them!
            if self._current_video_info and self._current_video_info.formats:
                for opt in self._current_video_info.formats:
                    self._quality_map[opt.label] = opt.quality_value
                    self._qual_combo.addItem(opt.label)
            else:
                for label, val in [
                    ("1080p", "1080"),
                    ("720p", "720"),
                    ("480p", "480"),
                ]:
                    self._quality_map[label] = val
                    self._qual_combo.addItem(label)

            idx = self._qual_combo.findText(t(prefs.last_quality))
            if idx >= 0:
                self._qual_combo.setCurrentIndex(idx)
            else:
                self._qual_combo.setCurrentIndex(0)
            self._qual_combo.setEnabled(True)

        self._qual_combo.blockSignals(False)
        self._update_displayed_filesize()
        self._audio_qual_panel.updateGeometry()
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

        if self._thumbnail_only:
            self._start_thumbnail_download(url)
            return

        try:
            validate_url(url)
        except InvalidUrlError as exc:
            self._append_log(t("log.validation_error").format(message=str(exc)))
            return

        if self._secret_mode and self._cookie_path is None:
            self._append_log(t("log.select_cookie_first"))
            return

        if self._secret_mode and self._cookie_path is not None:
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

        self._save_current_preferences()

        quality_text = self._qual_combo.currentText()
        audio_fmt = self._audio_format_map.get(quality_text, AudioFormat.MP3)
        quality = self._quality_map.get(quality_text, "best")
        audio_qual = self._audio_qual_combo.currentData() or "320"

        prefs = load_preferences()
        self._download_counter += 1
        request = DownloadRequest(
            url=url,
            cookie_file=self._cookie_path if self._secret_mode else None,
            output_folder=self._output_path,
            quality=quality,
            mode=mode,
            download_type=self._download_type,
            audio_format=audio_fmt,
            audio_quality=str(audio_qual),
            embed_thumbnail=False,
            force_h264_transcode=prefs.h264_compat_mode,
            download_counter=self._download_counter,
        )

        self._log.clear()
        self._append_log(t("log.building_command"))
        self._append_log(f"URL: {url}")
        if request.cookie_file is not None:
            self._append_log(f"Cookie: {request.cookie_file.name}")
        self._append_log(f"Output: {self._output_path}")
        if request.download_type is DownloadType.AUDIO:
            self._append_log(f"Audio: {request.audio_format.value.upper()} ({request.audio_quality} kbps)")
        if request.force_h264_transcode and request.download_type is DownloadType.VIDEO:
            self._append_log(t("download.transcode_notice"))

        self._start_worker(request)

    def _start_thumbnail_download(self, url: str) -> None:
        t = self._i18n.get_text
        video_id = extract_video_id(url)
        if not video_id:
            self._append_log(t("log.validation_error").format(message="Sadece YouTube linkleri desteklenir"))
            return

        self._cleanup_thumbnail_download()
        self._progress.setValue(0)
        self._status.setText(t("status.downloading"))
        self._thumbnail_downloading = True
        self._download_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._update_thumbnail_button_text()
        self._log.clear()
        self._append_log(f"URL: {url}")
        self._append_log(f"Video ID: {video_id}")

        self._thumb_download_thread = QThread()
        self._thumb_download_worker = ThumbnailDownloadWorker(
            video_id=video_id,
            output_dir=self._output_path,
            size=self._thumbnail_size,
        )
        self._thumb_download_worker.moveToThread(self._thumb_download_thread)
        self._thumb_download_thread.started.connect(self._thumb_download_worker.run)
        self._thumb_download_worker.download_started.connect(self._on_thumbnail_started)
        self._thumb_download_worker.metadata_fetched.connect(self._on_thumbnail_metadata)
        self._thumb_download_worker.download_progress.connect(self._on_thumbnail_progress)
        self._thumb_download_worker.log_message.connect(self._append_log)
        self._thumb_download_worker.finished.connect(self._on_thumbnail_download_finished)
        self._thumb_download_worker.finished.connect(self._thumb_download_thread.quit)
        self._thumb_download_thread.finished.connect(self._thumb_download_thread.deleteLater)
        self._thumb_download_thread.start()

    def _start_worker(self, request: DownloadRequest) -> None:
        t = self._i18n.get_text
        self._progress.setValue(0)
        if not self._is_queue_downloading:
            self._status.setText(t("status.downloading"))
        self._video_downloading = True
        self._download_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._cancel_btn.setVisible(True)
        self._show_folder_btn.setVisible(False)
        if hasattr(self, "_music_analysis_label"):
            self._music_analysis_label.setVisible(self._download_type is DownloadType.AUDIO)
        if hasattr(self, "_music_analysis_btn"):
            self._music_analysis_btn.setVisible(self._download_type is DownloadType.AUDIO)
        if hasattr(self, "_pitch_tempo_label"):
            self._pitch_tempo_label.setVisible(self._download_type is DownloadType.AUDIO)
        if hasattr(self, "_pitch_tempo_btn"):
            self._pitch_tempo_btn.setVisible(self._download_type is DownloadType.AUDIO)
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

        self._thread.start()

    def _on_progress(self, percent: int) -> None:
        self._progress.setValue(percent)

    def _on_status(self, text: str) -> None:
        if self._is_queue_downloading:
            curr_title = self._download_queue[0].title if self._download_queue else ""
            self._status.setText(f"({self._queue_current_index}/{self._queue_total_items}) {text}: {curr_title[:30]}")
        else:
            self._status.setText(text)

    def _on_error(self, message: str) -> None:
        self._append_log(message)

    # ------------------------------------------------------------------
    # Queue / Batch Download
    # ------------------------------------------------------------------

    def _on_queue_add_clicked(self) -> None:
        t = self._i18n.get_text
        url = self._url_input.text().strip()
        if not url:
            self._append_log(t("log.select_url_first"))
            return

        try:
            validate_url(url)
        except InvalidUrlError as exc:
            self._append_log(t("log.validation_error").format(message=str(exc)))
            return

        if self._secret_mode and self._cookie_path is None:
            self._append_log(t("log.select_cookie_first"))
            return

        out_folder = self._output_path or (Path.home() / "Desktop")
        quality_text = self._qual_combo.currentText()
        audio_fmt = self._audio_format_map.get(quality_text, AudioFormat.MP3)
        quality = self._quality_map.get(quality_text, "best")
        audio_qual = self._audio_qual_combo.currentData() or "320"

        if self._current_video_info and self._current_video_info.title:
            title = self._current_video_info.title
        else:
            title_text = self._info_title_value.text().strip()
            loading_text = t("info.loading")
            if not title_text or title_text in ("—", loading_text, "Video bilgileri yükleniyor..."):
                title = url
            else:
                title = title_text

        dur = self._current_video_info.duration_seconds if self._current_video_info else 0
        size_approx = self._current_video_info.filesize_approx if self._current_video_info else 0
        thumb_b64 = getattr(self, "_current_video_thumb_b64", "")

        item = QueueItem(
            url=url,
            title=title,
            download_type=self._download_type,
            quality=quality,
            audio_format=audio_fmt,
            audio_quality=str(audio_qual),
            cookie_file=self._cookie_path if self._secret_mode else None,
            output_folder=out_folder,
            file_size_approx=size_approx,
            duration_seconds=dur,
            thumbnail_b64=thumb_b64,
        )
        self._download_queue.append(item)
        count = len(self._download_queue)

        fmt_str = f"SES: {quality_text}" if self._download_type is DownloadType.AUDIO else f"VIDEO: {quality_text}"
        self._append_log(f"[Kuyruk] #{count} sıraya eklendi: {item.title[:45]} ({fmt_str})")
        self._status.setText(t("status.queued").format(count=count))

        self._queue_start_btn.setText(t("action.queue_start").format(count=count))
        self._queue_start_btn.setVisible(True)
        self._queue_start_btn.setEnabled(True)

        # Clear URL input and preview info so the user can easily paste the next one
        self._url_input.clear()
        self._clear_video_info()

    def _on_queue_start_clicked(self) -> None:
        t = self._i18n.get_text
        if not self._download_queue:
            return

        status = check_binaries()
        if not status.is_ready or status.ytdlp_path is None:
            msg = t("error.binaries_missing").format(bin_dir=str(status.ytdlp_path.parent if status.ytdlp_path else ""))
            self._append_log(msg)
            self._status.setText(t("status.error"))
            return

        self._is_queue_downloading = True
        self._queue_total_items = len(self._download_queue)
        self._queue_current_index = 0

        self._queue_add_btn.setEnabled(False)
        self._download_btn.setEnabled(False)
        self._queue_start_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._cancel_btn.setVisible(True)
        self._show_folder_btn.setVisible(False)

        self._download_next_queue_item()

    def _download_next_queue_item(self) -> None:
        t = self._i18n.get_text
        if not self._download_queue or not self._is_queue_downloading:
            self._is_queue_downloading = False
            self._status.setText(t("status.queue_finished"))
            self._append_log("✨ " + t("status.queue_finished"))
            self._queue_start_btn.setVisible(False)
            self._queue_start_btn.setEnabled(True)
            self._queue_add_btn.setEnabled(True)
            self._download_btn.setEnabled(True)
            self._cancel_btn.setEnabled(False)
            self._show_folder_btn.setVisible(True)
            return

        item = self._download_queue[0]
        self._queue_current_index += 1
        self._download_counter += 1
        prefs = load_preferences()

        self._status.setText(
            f"İndiriliyor ({self._queue_current_index}/{self._queue_total_items}): {item.title[:35]}"
        )
        self._progress.setValue(0)
        self._append_log(
            f"\n>>> Sıradaki İndirme Başlıyor ({self._queue_current_index}/{self._queue_total_items}): {item.title}"
        )

        request = DownloadRequest(
            url=item.url,
            cookie_file=item.cookie_file,
            output_folder=item.output_folder,
            quality=item.quality,
            mode=DownloadMode.SINGLE_VIDEO,
            download_type=item.download_type,
            audio_format=item.audio_format,
            audio_quality=item.audio_quality,
            embed_thumbnail=False,
            force_h264_transcode=prefs.h264_compat_mode,
            download_counter=self._download_counter,
        )

        self._start_worker(request)

    def _on_finished(self, success: bool, message: str) -> None:
        t = self._i18n.get_text
        self._video_downloading = False

        if self._is_queue_downloading:
            curr_item = self._download_queue[0] if self._download_queue else None
            if success:
                self._progress.setValue(100)
                self._append_log(f"✅ İndirme tamamlandı: {curr_item.title if curr_item else ''}")
                if curr_item:
                    try:
                        file_path = self._find_actual_downloaded_file(url=curr_item.url, title=curr_item.title)
                        file_size = os.path.getsize(file_path) if file_path and os.path.isfile(file_path) else curr_item.file_size_approx
                        dtype = "audio" if curr_item.download_type is DownloadType.AUDIO else "video"
                        fmt_label = f"SES: {curr_item.quality}" if dtype == "audio" else f"VIDEO: {curr_item.quality} - MP4"
                        add_history_entry(
                            title=curr_item.title,
                            file_path=file_path,
                            file_size_bytes=file_size,
                            duration_seconds=curr_item.duration_seconds,
                            download_type=dtype,
                            format_label=fmt_label,
                            url=curr_item.url,
                            thumbnail_b64=curr_item.thumbnail_b64,
                        )
                    except Exception:
                        pass
            else:
                self._append_log(f"❌ Sıradaki video indirilemedi: {message}")

            if self._download_queue:
                self._download_queue.pop(0)

            count = len(self._download_queue)
            if count > 0:
                self._queue_start_btn.setText(t("action.queue_start").format(count=count))
            self._cleanup_worker()
            QTimer.singleShot(400, self._download_next_queue_item)
            return

        self._download_btn.setEnabled(True)
        self._queue_add_btn.setEnabled(True)
        if len(self._download_queue) > 0:
            self._queue_start_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        if success:
            self._cancel_btn.setVisible(False)
            self._show_folder_btn.setVisible(True)
            self._progress.setValue(100)
            self._status.setText(t("status.completed"))
            self._append_log(t("log.download_completed"))

            # Record in history
            try:
                title = ""
                dur = 0
                if self._current_video_info:
                    title = self._current_video_info.title
                    dur = self._current_video_info.duration_seconds

                url = self._url_input.text().strip()
                file_path = self._find_actual_downloaded_file(url=url, title=title)
                file_size = 0
                if file_path and os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                elif self._current_video_info:
                    file_size = self._current_video_info.filesize_approx

                if not title and file_path:
                    title = Path(file_path).stem

                q_text = self._qual_combo.currentText()
                if self._download_type is DownloadType.AUDIO:
                    dtype = "audio"
                    fmt_label = f"SES: {q_text}"
                    if file_path and os.path.isfile(file_path):
                        self._last_downloaded_audio_path = Path(file_path)
                        if hasattr(self, "_music_analysis_label"):
                            self._music_analysis_label.setVisible(True)
                        if hasattr(self, "_music_analysis_btn"):
                            self._music_analysis_btn.setVisible(True)
                else:
                    dtype = "video"
                    fmt_label = f"VIDEO: {q_text} - MP4"

                add_history_entry(
                    title=title,
                    file_path=file_path,
                    file_size_bytes=file_size,
                    duration_seconds=dur,
                    download_type=dtype,
                    format_label=fmt_label,
                    url=url,
                    thumbnail_b64=getattr(self, "_current_video_thumb_b64", ""),
                )
            except Exception:
                pass
        else:
            self._status.setText(t("status.error"))
            self._append_log(message)
        self._cookie_path = None
        self._cookie_display.clear()

    def _find_actual_downloaded_file(
        self, url: str = "", title: str = "", is_thumbnail: bool = False
    ) -> str:
        """Find the real, verified on-disk path of the downloaded file."""
        import re

        raw_path = getattr(self, "_last_downloaded_file", "")
        img_exts = (".jpg", ".jpeg", ".webp", ".png")
        media_exts = (
            ".mp4",
            ".mkv",
            ".webm",
            ".avi",
            ".mov",
            ".mp3",
            ".wav",
            ".m4a",
            ".opus",
            ".flac",
        )
        allowed_exts = img_exts if is_thumbnail else media_exts

        if raw_path and os.path.isfile(raw_path):
            if Path(raw_path).suffix.lower() in allowed_exts:
                return os.path.abspath(raw_path)

        out_dir = self._output_path
        if not out_dir or not out_dir.is_dir():
            out_dir = Path.home() / "Desktop"

        video_id = extract_video_id(url)
        if out_dir and out_dir.is_dir():
            try:
                # 1. Search by video_id in output folder with matching extensions
                if video_id:
                    for f in out_dir.iterdir():
                        if (
                            f.is_file()
                            and f.suffix.lower() in allowed_exts
                            and video_id in f.name
                        ):
                            return str(f.resolve())

                # 2. Search by title in output folder with matching extensions
                if title:
                    clean = re.sub(r"[^\w\s]", "", title).strip().lower()
                    if clean:
                        words = clean.split()[:2]
                        for f in out_dir.iterdir():
                            if (
                                f.is_file()
                                and f.suffix.lower() in allowed_exts
                                and all(w in f.name.lower() for w in words)
                            ):
                                return str(f.resolve())

                # 3. Newest file in output folder matching allowed extensions
                matching_files = [
                    f
                    for f in out_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in allowed_exts
                ]
                if matching_files:
                    newest = max(matching_files, key=lambda f: f.stat().st_mtime)
                    return str(newest.resolve())
            except Exception:
                pass

        return raw_path or (str(self._output_path) if self._output_path else "")

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
        if self._is_queue_downloading:
            self._is_queue_downloading = False
            self._download_queue.clear()
            self._queue_start_btn.setVisible(False)
            self._queue_start_btn.setEnabled(True)
            self._queue_add_btn.setEnabled(True)
            self._download_btn.setEnabled(True)
            self._cancel_btn.setEnabled(False)
            self._progress.setValue(0)
            self._cleanup_worker()
            self._video_downloading = False
            self._status.setText(self._i18n.get_text("status.cancelled"))
            self._append_log("İndirme sırası kullanıcı tarafından iptal edildi.")
            self._cookie_path = None
            self._cookie_display.clear()
            return
        if self._worker:
            self._cleanup_worker()
            self._video_downloading = False
            self._cancel_btn.setEnabled(False)
            self._progress.setValue(0)
            self._status.setText(self._i18n.get_text("status.cancelled"))
            self._append_log(self._i18n.get_text("log.download_cancelled"))
            self._download_btn.setEnabled(True)
            self._cookie_path = None
            self._cookie_display.clear()
            return
        if self._thumb_download_worker is not None:
            self._thumb_download_worker.cancel()
            self._cleanup_thumbnail_download()
            self._thumbnail_downloading = False
            self._progress.setValue(0)
            self._append_log(self._i18n.get_text("log.download_cancelled"))
            self._reset_thumbnail_ui()
        if self._sub_worker is not None:
            self._sub_worker.cancel()
            self._subtitle_downloading = False
            self._progress.setValue(0)
            self._sub_download_btn.setEnabled(True)
            self._sub_download_btn.setText("📥 " + self._i18n.get_text("action.download_sub"))
            self._append_log(self._i18n.get_text("log.download_cancelled"))

    # ------------------------------------------------------------------
    # Subtitle download handling
    # ------------------------------------------------------------------

    def _start_subtitle_download(self) -> None:
        """Download subtitle for the current video asynchronously."""
        t = self._i18n.get_text
        url = self._url_input.text().strip()
        if not url:
            self._append_log("Lütfen geçerli bir YouTube video URL'si girin.")
            return

        out_dir = self._output_path
        if not out_dir or not out_dir.is_dir():
            out_dir = Path.home() / "Desktop"

        status = check_binaries()
        if not status.is_ready or status.ytdlp_path is None:
            self._append_log("Hata: yt-dlp bulunamadı.")
            return

        lang = self._sub_lang_combo.currentData() or "tr,tr-orig"
        fmt = self._sub_format_combo.currentData() or "srt"
        cookie = self._cookie_path if self._secret_mode else None

        self._subtitle_downloading = True
        self._sub_download_btn.setEnabled(False)
        self._sub_download_btn.setText("İndiriliyor...")
        self._status.setText("Altyazı indiriliyor...")
        self._progress.setValue(10)

        self._sub_thread = QThread()
        self._sub_worker = YtdlpSubtitleDownloadWorker(
            url=url,
            lang=lang,
            sub_format=fmt,
            output_folder=out_dir,
            ytdlp_path=status.ytdlp_path,
            cookie_file=cookie,
        )
        self._sub_worker.moveToThread(self._sub_thread)
        self._sub_thread.started.connect(self._sub_worker.run)
        self._sub_worker.log_message.connect(self._append_log)
        self._sub_worker.progress.connect(self._progress.setValue)
        self._sub_worker.finished.connect(self._on_subtitle_download_finished)
        self._sub_worker.finished.connect(self._sub_thread.quit)
        self._sub_thread.finished.connect(self._on_sub_thread_done)
        self._sub_thread.start()

    def _on_subtitle_download_finished(self, success: bool, message: str, saved_path: str) -> None:
        self._subtitle_downloading = False
        self._sub_download_btn.setEnabled(True)
        self._sub_download_btn.setText("📥 " + self._i18n.get_text("action.download_sub"))
        self._status.setText(self._i18n.get_text("status.completed") if success else self._i18n.get_text("status.error"))
        self._append_log(message)

        if success and saved_path and os.path.isfile(saved_path):
            try:
                title = ""
                if self._current_video_info and self._current_video_info.title:
                    title = self._current_video_info.title + " (Altyazı)"
                else:
                    title = Path(saved_path).stem

                file_size = os.path.getsize(saved_path)
                fmt_text = self._sub_format_combo.currentText()
                lang_text = self._sub_lang_combo.currentText()

                add_history_entry(
                    title=title,
                    file_path=str(Path(saved_path).resolve()),
                    file_size_bytes=file_size,
                    duration_seconds=0,
                    download_type="subtitle",
                    format_label=f"ALTYAZI: {fmt_text} ({lang_text})",
                    url=self._url_input.text().strip(),
                    thumbnail_b64=getattr(self, "_current_video_thumb_b64", ""),
                )
            except Exception:
                pass

    def _on_sub_thread_done(self) -> None:
        old_worker = getattr(self, "_sub_worker", None)
        old_thread = getattr(self, "_sub_thread", None)
        self._sub_worker = None
        self._sub_thread = None
        if old_worker:
            old_worker.deleteLater()
        if old_thread:
            old_thread.deleteLater()

    # ------------------------------------------------------------------
    # Worker management
    # ------------------------------------------------------------------

    def _cleanup_worker(self) -> None:
        if self._worker:
            self._worker.cancel()
            try:
                self._worker.progress_changed.disconnect()
                self._worker.status_changed.disconnect()
                self._worker.log_message.disconnect()
                self._worker.error_message.disconnect()
                self._worker.finished.disconnect(self._on_finished)
            except RuntimeError:
                pass
        self._worker = None
        if self._thread is not None and not self._thread.isRunning():
            self._thread = None

    def _append_log(self, message: str) -> None:
        self._log.appendPlainText(message)
        import re
        if "Destination: " in message:
            path = message.split("Destination: ", 1)[-1].strip()
            if not path.endswith(".ytdl"):
                self._last_downloaded_file = path
        elif "Merging formats into " in message:
            self._last_downloaded_file = message.split("Merging formats into ", 1)[-1].strip().strip('"')
        elif "has already been downloaded" in message:
            m = re.search(r'\[download\]\s+(.*?)\s+has already been downloaded', message)
            if m:
                self._last_downloaded_file = m.group(1).strip()

    def _on_show_folder_clicked(self) -> None:
        import os
        import subprocess
        import glob

        fallback_dir = None
        if self._output_path and self._output_path.exists():
            fallback_dir = str(self._output_path)

        if fallback_dir:
            try:
                list_of_files = glob.glob(os.path.join(fallback_dir, '*'))
                if list_of_files:
                    latest_file = max(list_of_files, key=os.path.getmtime)
                    if os.name == "nt":
                        subprocess.Popen(f'explorer /select,"{os.path.normpath(latest_file)}"')
                        return
            except Exception:
                pass

            if os.name == "nt":
                os.startfile(fallback_dir)
            else:
                subprocess.Popen(["xdg-open", fallback_dir])

    def _on_music_analysis_clicked(self) -> None:
        path = getattr(self, "_last_downloaded_audio_path", None)
        if not path or not Path(path).is_file():
            url = self._url_input.text().strip()
            title = self._current_video_info.title if self._current_video_info else ""
            if url:
                found = self._find_actual_downloaded_file(url=url, title=title)
                if found and Path(found).is_file():
                    path = Path(found)
        else:
            path = Path(path)

        if not path or not Path(path).is_file():
            # If no audio file from URL exists, let user select any file from PC
            file_path_str, _ = QFileDialog.getOpenFileName(
                self,
                "Ses Dosyası Seç (BPM ve Ton Analizi İçin)",
                str(self._output_path or Path.home() / "Desktop"),
                "Ses Dosyaları (*.wav *.mp3 *.flac *.opus *.m4a *.aac *.ogg);;Tüm Dosyalar (*.*)",
            )
            if not file_path_str:
                return
            path = Path(file_path_str)

        from videcook.ui.music_analysis_dialog import MusicAnalysisDialog
        dialog = MusicAnalysisDialog(file_path=path, parent=self)
        dialog.exec()

    def _on_pitch_tempo_clicked(self) -> None:
        path = getattr(self, "_last_downloaded_audio_path", None)
        if not path or not Path(path).is_file():
            url = self._url_input.text().strip()
            title = self._current_video_info.title if self._current_video_info else ""
            if url:
                found = self._find_actual_downloaded_file(url=url, title=title)
                if found and Path(found).is_file():
                    path = Path(found)
        else:
            path = Path(path)

        if not path or not Path(path).is_file():
            file_path_str, _ = QFileDialog.getOpenFileName(
                self,
                "Ses Dosyası Seç (Ton ve BPM Ayarlamak İçin)",
                str(self._output_path or Path.home() / "Desktop"),
                "Ses Dosyaları (*.wav *.mp3 *.flac *.opus *.m4a *.aac *.ogg);;Tüm Dosyalar (*.*)",
            )
            if not file_path_str:
                return
            path = Path(file_path_str)

        from videcook.ui.pitch_tempo_dialog import PitchTempoDialog
        dialog = PitchTempoDialog(file_path=path, parent=self)
        dialog.exec()

    def set_i18n(self, i18n: LanguageManager) -> None:
        self._i18n = i18n
        self.retranslate()

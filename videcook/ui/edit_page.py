"""AI Edit Page — AI Shorts / Reels Generator UI + Backend Connection.

Layout structure (top to bottom):
1. Page Header & Tagline
2. Video File Selection Card
3. AI Prompt & Quick Preset Badges Card
4. Output Format & Subtitle Customization Card
5. Output Folder Selection & Show in Folder Card
6. Action Button, Progress Bar & Process Log Card
"""

import os
import subprocess
from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot, QThread, QUrl
from PySide6.QtGui import QDesktopServices
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
    QVBoxLayout,
    QWidget,
)

from videcook.core.preset_manager import get_edit_presets
from videcook.ui.edit_worker import EditWorker
from videcook.ui.preset_dialogs import AddPresetDialog, ManagePresetsDialog
from videcook.utils.i18n import LanguageManager
from videcook.utils.preferences import load_preferences, save_preferences


def get_default_downloads_dir() -> Path:
    """Return user's default Downloads directory."""
    return Path.home() / "Downloads"


class EditPage(QWidget):
    """AI Edit / Shorts Generator Page."""

    log_emitted = Signal(str)

    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._worker: EditWorker | None = None
        self._thread: QThread | None = None
        self._last_output_file: Path | None = None

        self._setup_ui()
        self._load_default_output_folder()
        self.retranslate()

    def _setup_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setObjectName("editPageContainer")
        page_layout = QVBoxLayout(container)
        page_layout.setContentsMargins(24, 20, 24, 24)
        page_layout.setSpacing(16)

        # =============================================
        # 1. HEADER
        # =============================================
        header_box = QVBoxLayout()
        header_box.setSpacing(4)

        self._title_label = QLabel("🎬 AI Editör / Shorts Üretici")
        self._title_label.setObjectName("editPageTitle")
        self._title_label.setStyleSheet("font-size: 22px; font-weight: 800; color: #F8FAFC;")

        self._subtitle_label = QLabel("Yapay zeka ile uzun videolarınızdan dikey Shorts, Reels ve TikTok içerikleri üretin.")
        self._subtitle_label.setStyleSheet("font-size: 13px; color: #94A3B8;")

        header_box.addWidget(self._title_label)
        header_box.addWidget(self._subtitle_label)
        page_layout.addLayout(header_box)

        # =============================================
        # 2. CARD 1: VIDEO SELECTION
        # =============================================
        video_card = QWidget()
        video_card.setObjectName("editVideoCard")
        video_card.setStyleSheet("""
            #editVideoCard {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        video_layout = QVBoxLayout(video_card)
        video_layout.setSpacing(10)

        self._video_header = QLabel("📁 Video Dosyası Seçin")
        self._video_header.setStyleSheet("font-weight: 700; color: #38BDF8; font-size: 14px;")
        video_layout.addWidget(self._video_header)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self._video_input = QLineEdit()
        self._video_input.setObjectName("editVideoInput")
        self._video_input.setPlaceholderText("İşlemek istediğiniz video dosyasını seçin (.mp4, .mkv, .mov)...")
        self._video_input.setMinimumHeight(42)
        self._video_input.setStyleSheet("""
            QLineEdit#editVideoInput {
                background-color: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 0 12px;
                color: #F8FAFC;
                font-size: 13px;
            }
        """)
        input_row.addWidget(self._video_input, stretch=1)

        self._browse_btn = QPushButton("📁 Gözat")
        self._browse_btn.setMinimumSize(110, 42)
        self._browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 8px;
                color: #38BDF8;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.25);
            }
        """)
        self._browse_btn.clicked.connect(self._on_browse_clicked)
        input_row.addWidget(self._browse_btn)

        video_layout.addLayout(input_row)

        self._video_info_badge = QLabel("Henüz dosya seçilmedi")
        self._video_info_badge.setStyleSheet("color: #64748B; font-size: 11px; font-style: italic;")
        video_layout.addWidget(self._video_info_badge)

        # Translation / Dubbing File Selection
        self._trans_header = QLabel("📄 Çeviri / Dublaj Dosyası Seçin (İsteğe Bağlı)")
        self._trans_header.setStyleSheet("font-weight: 700; color: #38BDF8; font-size: 14px; margin-top: 14px;")
        video_layout.addWidget(self._trans_header)

        trans_row = QHBoxLayout()
        trans_row.setSpacing(10)

        self._trans_input = QLineEdit()
        self._trans_input.setObjectName("editTransInput")
        self._trans_input.setPlaceholderText("Dublaj çeviri dosyasını seçin (.md, .txt, .srt)... (İsteğe bağlı)")
        self._trans_input.setMinimumHeight(42)
        self._trans_input.setStyleSheet("""
            QLineEdit#editTransInput {
                background-color: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 0 12px;
                color: #F8FAFC;
                font-size: 13px;
            }
        """)
        trans_row.addWidget(self._trans_input, stretch=1)

        self._trans_browse_btn = QPushButton("📁 Gözat")
        self._trans_browse_btn.setMinimumSize(110, 42)
        self._trans_browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._trans_browse_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 8px;
                color: #38BDF8;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.25);
            }
        """)
        self._trans_browse_btn.clicked.connect(self._on_trans_browse_clicked)
        trans_row.addWidget(self._trans_browse_btn)

        self._trans_clear_btn = QPushButton("✕")
        self._trans_clear_btn.setMinimumSize(42, 42)
        self._trans_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._trans_clear_btn.setToolTip("Çeviri dosyasını kaldır")
        self._trans_clear_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.15);
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 8px;
                color: #F87171;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.25);
            }
        """)
        self._trans_clear_btn.clicked.connect(self._on_trans_clear_clicked)
        trans_row.addWidget(self._trans_clear_btn)

        video_layout.addLayout(trans_row)

        self._trans_info_badge = QLabel("Dublaj dosyası seçilirse altyazı ve sahneler otomatik olarak dublaj metninizden alınır.")
        self._trans_info_badge.setStyleSheet("color: #64748B; font-size: 11px; font-style: italic;")
        video_layout.addWidget(self._trans_info_badge)

        page_layout.addWidget(video_card)

        # =============================================
        # 3. CARD 2: AI PROMPT & QUICK PRESETS
        # =============================================
        prompt_card = QWidget()
        prompt_card.setObjectName("editPromptCard")
        prompt_card.setStyleSheet("""
            #editPromptCard {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        prompt_layout = QVBoxLayout(prompt_card)
        prompt_layout.setSpacing(10)

        self._prompt_header = QLabel("🤖 AI Prompt & Sahne İsteği")
        self._prompt_header.setStyleSheet("font-weight: 700; color: #A855F7; font-size: 14px;")
        prompt_layout.addWidget(self._prompt_header)

        self._prompt_input = QPlainTextEdit()
        self._prompt_input.setPlaceholderText(
            "Yapay zekaya nasıl bir kesit üretmesini istediğinizi yazın...\n"
            "Örn: 'Videonun en komik 30 saniyelik sahnesini dikey kes, kelime kelime renkli altyazı koy...'"
        )
        self._prompt_input.setMinimumHeight(75)
        self._prompt_input.setMaximumHeight(100)
        self._prompt_input.setStyleSheet("""
            QPlainTextEdit {
                background-color: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 8px 12px;
                color: #F8FAFC;
                font-size: 13px;
            }
        """)
        prompt_layout.addWidget(self._prompt_input)

        # Quick preset header & management buttons
        preset_header_row = QHBoxLayout()
        preset_header = QLabel("Hızlı Şablon İstemleri:")
        preset_header.setStyleSheet("font-weight: 600; color: #94A3B8; font-size: 11px;")
        preset_header_row.addWidget(preset_header)
        preset_header_row.addStretch(1)

        self._add_preset_btn = QPushButton("➕ Şablon Ekle")
        self._add_preset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_preset_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(16, 185, 129, 0.12);
                border: 1px dashed rgba(16, 185, 129, 0.5);
                border-radius: 6px;
                color: #34D399;
                font-size: 11px;
                font-weight: 700;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: rgba(16, 185, 129, 0.25);
            }
        """)
        self._add_preset_btn.clicked.connect(self._on_add_preset_clicked)
        preset_header_row.addWidget(self._add_preset_btn)

        self._manage_presets_btn = QPushButton("⚙️ Şablonları Yönet")
        self._manage_presets_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._manage_presets_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                color: #94A3B8;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                color: #F1F5F9;
            }
        """)
        self._manage_presets_btn.clicked.connect(self._on_manage_presets_clicked)
        preset_header_row.addWidget(self._manage_presets_btn)

        prompt_layout.addLayout(preset_header_row)

        # Dynamic presets container with scroll support
        self._presets_scroll = QScrollArea()
        self._presets_scroll.setWidgetResizable(True)
        self._presets_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._presets_scroll.setStyleSheet("background: transparent; border: none;")
        self._presets_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._presets_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._presets_scroll.setFixedHeight(46)

        self._presets_widget = QWidget()
        self._presets_widget.setStyleSheet("background: transparent;")
        self._presets_row = QHBoxLayout(self._presets_widget)
        self._presets_row.setContentsMargins(0, 2, 0, 2)
        self._presets_row.setSpacing(8)

        self._presets_scroll.setWidget(self._presets_widget)
        prompt_layout.addWidget(self._presets_scroll)

        self._refresh_presets_ui()

        page_layout.addWidget(prompt_card)

        # =============================================
        # 4. CARD 3: FORMAT & SUBTITLE OPTIONS
        # =============================================
        opts_card = QWidget()
        opts_card.setObjectName("editOptsCard")
        opts_card.setStyleSheet("""
            #editOptsCard {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        opts_layout = QHBoxLayout(opts_card)
        opts_layout.setSpacing(20)

        # Combo 1: Aspect Ratio
        aspect_vbox = QVBoxLayout()
        aspect_vbox.setSpacing(6)
        self._aspect_label = QLabel("📱 En Boy Oranı:")
        self._aspect_label.setStyleSheet("font-weight: 700; color: #E2E8F0; font-size: 12px;")
        self._aspect_combo = QComboBox()
        self._aspect_combo.setMinimumHeight(38)
        self._aspect_combo.addItems([
            "📱 9:16 Bulanık Arka Plan (CapCut / Reels Stili)",
            "📱 9:16 Dikey Kırpma (Tam Ekran)",
            "🔲 1:1 Kare (Instagram Post)",
            "🎬 16:9 Yatay (YouTube)",
        ])
        aspect_vbox.addWidget(self._aspect_label)
        aspect_vbox.addWidget(self._aspect_combo)
        opts_layout.addLayout(aspect_vbox, stretch=1)

        # Combo 2: Subtitle Style
        sub_vbox = QVBoxLayout()
        sub_vbox.setSpacing(6)
        self._sub_label = QLabel("✨ Altyazı Stili:")
        self._sub_label.setStyleSheet("font-weight: 700; color: #E2E8F0; font-size: 12px;")
        self._sub_combo = QComboBox()
        self._sub_combo.setMinimumHeight(38)
        self._sub_combo.addItems([
            "🎸 Metal Family (Büyük Beyaz Vurgulu)",
            "✨ CapCut Vurgulu (Sarı / Kırmızı)",
            "📝 Klasik Beyaz Altyazı",
            "🚫 Altyazısız",
        ])
        sub_vbox.addWidget(self._sub_label)
        sub_vbox.addWidget(self._sub_combo)
        opts_layout.addLayout(sub_vbox, stretch=1)

        # Combo 3: Target Duration
        dur_vbox = QVBoxLayout()
        dur_vbox.setSpacing(6)
        self._dur_label = QLabel("⏱️ Hedef Süre:")
        self._dur_label.setStyleSheet("font-weight: 700; color: #E2E8F0; font-size: 12px;")
        self._dur_combo = QComboBox()
        self._dur_combo.setMinimumHeight(38)
        self._dur_combo.addItems([
            "15 Saniye",
            "30 Saniye",
            "60 Saniye",
        ])
        self._dur_combo.setCurrentIndex(1)
        dur_vbox.addWidget(self._dur_label)
        dur_vbox.addWidget(self._dur_combo)
        opts_layout.addLayout(dur_vbox, stretch=1)

        page_layout.addWidget(opts_card)

        # =============================================
        # 5. CARD 4: OUTPUT FOLDER SELECTION
        # =============================================
        out_card = QWidget()
        out_card.setObjectName("editOutCard")
        out_card.setStyleSheet("""
            #editOutCard {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        out_layout = QVBoxLayout(out_card)
        out_layout.setSpacing(10)

        self._out_header = QLabel("📁 Çıktı Klasörü")
        self._out_header.setStyleSheet("font-weight: 700; color: #4ADE80; font-size: 14px;")
        out_layout.addWidget(self._out_header)

        out_row = QHBoxLayout()
        out_row.setSpacing(10)

        self._out_input = QLineEdit()
        self._out_input.setObjectName("editOutInput")
        self._out_input.setMinimumHeight(40)
        self._out_input.setStyleSheet("""
            QLineEdit#editOutInput {
                background-color: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 0 12px;
                color: #F8FAFC;
                font-size: 13px;
            }
        """)
        out_row.addWidget(self._out_input, stretch=1)

        self._out_browse_btn = QPushButton("📁 Gözat")
        self._out_browse_btn.setMinimumSize(100, 40)
        self._out_browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._out_browse_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(74, 222, 128, 0.15);
                border: 1px solid rgba(74, 222, 128, 0.4);
                border-radius: 8px;
                color: #4ADE80;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(74, 222, 128, 0.25);
            }
        """)
        self._out_browse_btn.clicked.connect(self._on_out_browse_clicked)
        out_row.addWidget(self._out_browse_btn)

        self._show_folder_btn = QPushButton("📂 Klasörde Göster")
        self._show_folder_btn.setMinimumSize(130, 40)
        self._show_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._show_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: #E2E8F0;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self._show_folder_btn.clicked.connect(self._on_show_folder_clicked)
        out_row.addWidget(self._show_folder_btn)

        out_layout.addLayout(out_row)
        page_layout.addWidget(out_card)

        # =============================================
        # 6. CARD 5: ACTION & PROGRESS LOG
        # =============================================
        action_card = QWidget()
        action_card.setObjectName("editActionCard")
        action_layout = QVBoxLayout(action_card)
        action_layout.setSpacing(12)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._start_btn = QPushButton("🚀 AI Editi Üret")
        self._start_btn.setMinimumHeight(48)
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.setStyleSheet("""
            QPushButton {
                background: linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%);
                background-color: #8B5CF6;
                border: none;
                border-radius: 10px;
                color: #FFFFFF;
                font-weight: 800;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #7C3AED;
            }
            QPushButton:disabled {
                background-color: #4C1D95;
                color: #A78BFA;
            }
        """)
        self._start_btn.clicked.connect(self._on_start_clicked)
        btn_row.addWidget(self._start_btn, stretch=1)

        self._cancel_btn = QPushButton("🛑 İptal Et")
        self._cancel_btn.setMinimumHeight(48)
        self._cancel_btn.setMinimumWidth(120)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.15);
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 10px;
                color: #EF4444;
                font-weight: 800;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.3);
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.03);
                border-color: rgba(255, 255, 255, 0.08);
                color: #64748B;
            }
        """)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        btn_row.addWidget(self._cancel_btn)

        action_layout.addLayout(btn_row)

        self._progress = QProgressBar()
        self._progress.setMinimumHeight(8)
        self._progress.setMaximumHeight(8)
        self._progress.setTextVisible(False)
        self._progress.setValue(0)
        action_layout.addWidget(self._progress)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(100)
        self._log.setMinimumHeight(90)
        self._log.setMaximumHeight(130)
        self._log.setStyleSheet("""
            QPlainTextEdit {
                background-color: rgba(15, 23, 42, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: #94A3B8;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)
        action_layout.addWidget(self._log)

        page_layout.addWidget(action_card)
        page_layout.addStretch(1)

        scroll.setWidget(container)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def _load_default_output_folder(self) -> None:
        prefs = load_preferences()
        default_dir = prefs.last_output_folder or str(get_default_downloads_dir())
        self._out_input.setText(default_dir)

    def _on_browse_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Video Dosyası Seç",
            "",
            "Video Dosyaları (*.mp4 *.mkv *.mov *.avi *.webm)",
        )
        if file_path:
            self._video_input.setText(file_path)
            path_obj = Path(file_path)
            self._video_info_badge.setText(f"✅ Seçildi: {path_obj.name}")
            self._append_log(f"Video seçildi: {path_obj.name}")

    def _on_trans_browse_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Dublaj / Çeviri Dosyası Seç",
            "",
            "Çeviri Dosyaları (*.md *.txt *.srt);;Markdown Dosyaları (*.md);;Metin Dosyaları (*.txt);;SRT Altyazı (*.srt);;Tüm Dosyalar (*.*)",
        )
        if file_path:
            self._trans_input.setText(file_path)
            path_obj = Path(file_path)
            self._trans_info_badge.setText(f"✅ Çeviri Dosyası: {path_obj.name}")
            self._append_log(f"Dublaj çeviri dosyası seçildi: {path_obj.name}")

    def _on_trans_clear_clicked(self) -> None:
        self._trans_input.clear()
        self._trans_info_badge.setText("Dublaj dosyası seçilirse altyazı ve sahneler otomatik olarak dublaj metninizden alınır.")

    def _on_out_browse_clicked(self) -> None:
        current = self._out_input.text().strip() or str(get_default_downloads_dir())
        folder = QFileDialog.getExistingDirectory(self, "Çıktı Klasörünü Seç", current)
        if folder:
            self._out_input.setText(folder)
            prefs = load_preferences()
            prefs.last_output_folder = folder
            save_preferences(prefs)

    def _on_show_folder_clicked(self) -> None:
        import glob
        import subprocess

        path_str = self._out_input.text().strip()
        fallback_dir = Path(path_str) if path_str else get_default_downloads_dir()

        # 1. If we have a tracked output file from a completed edit, highlight it directly
        if self._last_output_file and self._last_output_file.is_file():
            if os.name == "nt":
                subprocess.Popen(f'explorer /select,"{os.path.normpath(str(self._last_output_file))}"')
                return
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_output_file.parent)))
                return

        # 2. If fallback directory exists, try to highlight the most recently created/modified file in that folder
        if fallback_dir.is_dir():
            try:
                list_of_files = glob.glob(os.path.join(str(fallback_dir), "*"))
                if list_of_files:
                    latest_file = max(list_of_files, key=os.path.getmtime)
                    if os.name == "nt" and os.path.isfile(latest_file):
                        subprocess.Popen(f'explorer /select,"{os.path.normpath(latest_file)}"')
                        return
            except Exception:
                pass

        # 3. Fallback to simply opening the directory
        fallback_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(fallback_dir))
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(fallback_dir)))

    def _set_prompt_preset(self, text: str) -> None:
        self._prompt_input.setPlainText(text)

    def _refresh_presets_ui(self) -> None:
        """Clear and repopulate preset buttons from persistent storage."""
        while self._presets_row.count():
            item = self._presets_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        presets = get_edit_presets()
        for p in presets:
            btn = QPushButton(p["name"])
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(p.get("prompt", "")[:120])
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(168, 85, 247, 0.12);
                    border: 1px solid rgba(168, 85, 247, 0.3);
                    border-radius: 6px;
                    color: #C084FC;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: rgba(168, 85, 247, 0.25);
                    border-color: rgba(168, 85, 247, 0.6);
                }
            """)
            btn.clicked.connect(lambda _, prompt_text=p["prompt"]: self._set_prompt_preset(prompt_text))
            self._presets_row.addWidget(btn)

        self._presets_row.addStretch(1)

    def _on_add_preset_clicked(self) -> None:
        """Open popup to create and save a new template."""
        dlg = AddPresetDialog(self, initial_prompt=self._prompt_input.toPlainText())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_presets_ui()

    def _on_manage_presets_clicked(self) -> None:
        """Open popup to reorder or delete templates."""
        dlg = ManagePresetsDialog(self)
        dlg.exec()
        self._refresh_presets_ui()

    def _on_start_clicked(self) -> None:
        video_path_str = self._video_input.text().strip()
        if not video_path_str:
            self._append_log("⚠️ UYARI: Lütfen önce bir video dosyası seçin.")
            QMessageBox.warning(self, "AI Edit", "Lütfen bir video dosyası seçin.")
            return

        video_path = Path(video_path_str)
        if not video_path.is_file():
            self._append_log("⚠️ UYARI: Seçilen video dosyası bulunamadı.")
            return

        prompt = self._prompt_input.toPlainText().strip()
        if not prompt:
            self._append_log("⚠️ UYARI: Lütfen bir AI prompt veya istem yazın.")
            QMessageBox.warning(self, "AI Edit", "Lütfen bir AI prompt yazın.")
            return

        out_dir_str = self._out_input.text().strip() or str(get_default_downloads_dir())
        out_dir = Path(out_dir_str)

        # Parse duration
        dur_text = self._dur_combo.currentText()
        if "15" in dur_text:
            target_dur = 15
        elif "60" in dur_text:
            target_dur = 60
        else:
            target_dur = 30

        aspect_ratio = self._aspect_combo.currentText()
        sub_style = self._sub_combo.currentText()

        # Disable UI controls during process
        self._start_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._progress.setValue(0)

        # Check translation file path
        trans_path_str = self._trans_input.text().strip()
        trans_path = Path(trans_path_str) if trans_path_str and Path(trans_path_str).is_file() else None

        self._append_log("🚀 AI Edit İşlemi Başlatılıyor...")
        self._append_log(f"📹 Video: {video_path.name}")
        if trans_path:
            self._append_log(f"📄 Dublaj Çeviri Metni: {trans_path.name}")
        self._append_log(f"📌 İstem: {prompt}")

        # Start QThread Worker
        self._thread = QThread()
        self._worker = EditWorker(
            video_path=video_path,
            output_dir=out_dir,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            subtitle_style=sub_style,
            target_duration_sec=target_dur,
            translation_path=trans_path,
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.log.connect(self._append_log)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)

        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_worker)

        self._thread.start()

    def _on_cancel_clicked(self) -> None:
        if self._worker:
            self._append_log("🛑 İşlem iptal ediliyor...")
            self._worker.cancel()
            self._cancel_btn.setEnabled(False)

    @Slot(str)
    def _on_worker_finished(self, output_path_str: str) -> None:
        self._start_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress.setValue(100)
        self._last_output_file = Path(output_path_str)
        self._append_log(f"🎉 İşlem Tamamlandı! Çıktı Dosyası: {self._last_output_file.name}")

    @Slot(str)
    def _on_worker_failed(self, error_msg: str) -> None:
        self._start_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress.setValue(0)
        self._append_log(f"❌ {error_msg}")
        if "iptal" not in error_msg.lower():
            QMessageBox.critical(self, "AI Edit Hata", error_msg)

    def _cleanup_worker(self) -> None:
        self._worker = None
        self._thread = None

    def _append_log(self, text: str) -> None:
        self._log.appendPlainText(text)
        self.log_emitted.emit(text)

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._title_label.setText("🎬 AI Editör / Shorts Üretici")
        self._subtitle_label.setText("Yapay zeka ile uzun videolarınızdan dikey Shorts, Reels ve TikTok içerikleri üretin.")
        self._video_header.setText("📁 Video Dosyası Seçin")
        self._browse_btn.setText("📁 " + t("action.browse"))
        self._out_header.setText("📁 Çıktı Klasörü")
        self._out_browse_btn.setText("📁 " + t("action.browse"))
        self._show_folder_btn.setText(t("action.show_folder"))
        self._prompt_header.setText("🤖 AI Prompt & Sahne İsteği")
        self._start_btn.setText("🚀 AI Editi Üret")

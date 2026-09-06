"""Modern studio-grade music analysis dialog for BPM, Musical Key, and Camelot detection."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QClipboard, QCursor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from videcook.core.audio_analyzer import AudioAnalysisResult, analyze_audio_file


class AudioAnalysisWorker(QThread):
    """Background worker for non-blocking DSP audio analysis."""
    result_ready = Signal(object)
    failed = Signal(str)

    def __init__(self, file_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._file_path = file_path

    def run(self) -> None:
        try:
            res = analyze_audio_file(self._file_path)
            self.result_ready.emit(res)
        except Exception as exc:
            self.failed.emit(str(exc))


class MusicAnalysisDialog(QDialog):
    """Modern dark popup window showing BPM, Key, Camelot, and technical audio stats."""

    def __init__(self, file_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._file_path = file_path
        self._analysis_result: AudioAnalysisResult | None = None
        self._worker: AudioAnalysisWorker | None = None

        self.setWindowTitle("🎵 Müzik & Ton Analizörü")
        self.setFixedSize(560, 460)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.setStyleSheet("""
            QDialog {
                background-color: #0B0713;
                color: #F8FAFC;
                border: 1px solid #271A40;
                border-radius: 14px;
            }
            QFrame#card {
                background-color: #130B21;
                border: 1px solid #2C1B4D;
                border-radius: 12px;
            }
            QFrame#heroBox {
                background-color: #170E2B;
                border: 1px solid #3B2268;
                border-radius: 10px;
            }
            QLabel {
                color: #E2E8F0;
            }
            QPushButton {
                background-color: #1A112E;
                color: #F1F5F9;
                border: 1px solid #3C2665;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2B1B4A;
                border-color: #7C3AED;
            }
            QPushButton#primaryAction {
                background-color: #6D28D9;
                color: #FFFFFF;
                border: 1px solid #8B5CF6;
            }
            QPushButton#primaryAction:hover {
                background-color: #7C3AED;
                border-color: #A78BFA;
            }
            QPushButton#copyBtn {
                background-color: #0F2A3F;
                color: #38BDF8;
                border: 1px solid #0284C7;
            }
            QPushButton#copyBtn:hover {
                background-color: #0369A1;
                color: #FFFFFF;
            }
        """)

        self._setup_ui()
        self._start_analysis(self._file_path)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Header
        header_layout = QHBoxLayout()
        header_icon = QLabel("🎧")
        header_icon.setFont(QFont("Segoe UI Emoji", 22))
        header_layout.addWidget(header_icon)

        header_text_vbox = QVBoxLayout()
        header_text_vbox.setSpacing(2)

        self._title_label = QLabel("MÜZİK VE TON ANALİZİ")
        self._title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self._title_label.setStyleSheet("color: #FFFFFF; letter-spacing: 0.5px;")
        header_text_vbox.addWidget(self._title_label)

        self._file_name_label = QLabel(self._file_path.name if self._file_path else "")
        self._file_name_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        header_text_vbox.addWidget(self._file_name_label)

        header_layout.addLayout(header_text_vbox, stretch=1)

        self._browse_btn = QPushButton("📁 Başka Dosya")
        self._browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_btn.clicked.connect(self._on_browse_clicked)
        header_layout.addWidget(self._browse_btn)

        main_layout.addLayout(header_layout)

        # Status / Spinner Label
        self._status_label = QLabel("⚡ Parça taranıyor ve analiz ediliyor...")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #A855F7; font-weight: 600; font-size: 13px; margin: 6px 0;")
        main_layout.addWidget(self._status_label)

        # Hero Grid (BPM & Key)
        self._hero_container = QFrame()
        self._hero_container.setObjectName("card")
        hero_layout = QGridLayout(self._hero_container)
        hero_layout.setContentsMargins(16, 16, 16, 16)
        hero_layout.setSpacing(14)

        # BPM Box
        bpm_box = QFrame()
        bpm_box.setObjectName("heroBox")
        bpm_vbox = QVBoxLayout(bpm_box)
        bpm_vbox.setContentsMargins(14, 12, 14, 12)
        bpm_vbox.setSpacing(4)

        bpm_header = QLabel("⚡ TEMPO")
        bpm_header.setStyleSheet("color: #38BDF8; font-weight: 800; font-size: 11px; letter-spacing: 1px;")
        bpm_vbox.addWidget(bpm_header)

        self._bpm_value = QLabel("-- BPM")
        self._bpm_value.setFont(QFont("Arial Black", 24, QFont.Weight.Bold))
        self._bpm_value.setStyleSheet("color: #FFFFFF;")
        bpm_vbox.addWidget(self._bpm_value)

        self._bpm_sub = QLabel("Yarım: -- | Çift: --")
        self._bpm_sub.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500;")
        bpm_vbox.addWidget(self._bpm_sub)

        hero_layout.addWidget(bpm_box, 0, 0)

        # Key Box
        key_box = QFrame()
        key_box.setObjectName("heroBox")
        key_vbox = QVBoxLayout(key_box)
        key_vbox.setContentsMargins(14, 12, 14, 12)
        key_vbox.setSpacing(4)

        key_header = QLabel("🎹 MÜZİKAL TON (KEY)")
        key_header.setStyleSheet("color: #C084FC; font-weight: 800; font-size: 11px; letter-spacing: 1px;")
        key_vbox.addWidget(key_header)

        self._key_value = QLabel("--")
        self._key_value.setFont(QFont("Arial Black", 22, QFont.Weight.Bold))
        self._key_value.setStyleSheet("color: #FFFFFF;")
        key_vbox.addWidget(self._key_value)

        self._camelot_badge = QLabel("CAMELOT: --")
        self._camelot_badge.setStyleSheet(
            "background-color: #3B1866; color: #E9D5FF; padding: 2px 6px; "
            "border-radius: 4px; font-size: 11px; font-weight: 700; max-width: 110px;"
        )
        key_vbox.addWidget(self._camelot_badge)

        hero_layout.addWidget(key_box, 0, 1)

        main_layout.addWidget(self._hero_container)

        # Technical Parameters Bar
        self._tech_box = QFrame()
        self._tech_box.setObjectName("card")
        tech_hbox = QHBoxLayout(self._tech_box)
        tech_hbox.setContentsMargins(16, 10, 16, 10)
        tech_hbox.setSpacing(16)

        self._tech_format = QLabel("Format: --")
        self._tech_format.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        tech_hbox.addWidget(self._tech_format)

        self._tech_sr = QLabel("Örnekleme: --")
        self._tech_sr.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        tech_hbox.addWidget(self._tech_sr)

        self._tech_dur = QLabel("Süre: --")
        self._tech_dur.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        tech_hbox.addWidget(self._tech_dur)

        self._tech_br = QLabel("Bitrate: --")
        self._tech_br.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        tech_hbox.addWidget(self._tech_br)

        main_layout.addWidget(self._tech_box)

        # Bottom Actions
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)

        self._copy_btn = QPushButton("📋 Bilgileri Kopyala")
        self._copy_btn.setObjectName("copyBtn")
        self._copy_btn.setMinimumHeight(38)
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.clicked.connect(self._on_copy_clicked)
        self._copy_btn.setEnabled(False)
        action_layout.addWidget(self._copy_btn)

        self._tag_filename_btn = QPushButton("🏷️ Dosya Adına Ekle")
        self._tag_filename_btn.setMinimumHeight(38)
        self._tag_filename_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tag_filename_btn.clicked.connect(self._on_tag_filename_clicked)
        self._tag_filename_btn.setEnabled(False)
        action_layout.addWidget(self._tag_filename_btn)

        self._folder_btn = QPushButton("📂 Klasörde Göster")
        self._folder_btn.setMinimumHeight(38)
        self._folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._folder_btn.clicked.connect(self._on_folder_clicked)
        action_layout.addWidget(self._folder_btn)

        self._close_btn = QPushButton("Kapat")
        self._close_btn.setMinimumHeight(38)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self.accept)
        action_layout.addWidget(self._close_btn)

        main_layout.addLayout(action_layout)

    def _start_analysis(self, path: Path) -> None:
        if not path or not path.is_file():
            self._status_label.setText("⚠️ Geçerli bir ses dosyası bulunamadı.")
            return

        self._file_path = path
        self._file_name_label.setText(path.name)
        self._file_name_label.setToolTip(str(path))
        self._status_label.setText("⚡ Vuruşlar (BPM) ve armonik ton (Key) analiz ediliyor...")
        self._copy_btn.setEnabled(False)
        self._tag_filename_btn.setEnabled(False)

        self._worker = AudioAnalysisWorker(path, self)
        self._worker.result_ready.connect(self._on_analysis_done)
        self._worker.failed.connect(self._on_analysis_failed)
        self._worker.start()

    def _on_analysis_done(self, result: AudioAnalysisResult) -> None:
        self._analysis_result = result
        self._status_label.setText("✅ Analiz Başarıyla Tamamlandı")
        self._status_label.setStyleSheet("color: #10B981; font-weight: 700; font-size: 13px; margin: 6px 0;")

        # BPM
        self._bpm_value.setText(f"{round(result.bpm)} BPM")
        self._bpm_sub.setText(f"Yarım: {result.bpm_half} | Çift: {result.bpm_double}")

        # Key & Camelot
        self._key_value.setText(result.key_display)
        if result.camelot_code:
            self._camelot_badge.setText(f"CAMELOT: {result.camelot_code}")
            self._camelot_badge.setVisible(True)
        else:
            self._camelot_badge.setVisible(False)

        # Technical
        self._tech_format.setText(f"Format: {result.format_name}")
        sr_khz = f"{result.sample_rate / 1000:.1f} kHz"
        self._tech_sr.setText(f"Örnekleme: {sr_khz}")

        m, s = divmod(int(result.duration_sec), 60)
        self._tech_dur.setText(f"Süre: {m:02d}:{s:02d}")
        br_str = f"{result.bitrate_kbps} Kbps" if result.bitrate_kbps else "Kayıpsız"
        self._tech_br.setText(f"Kalite: {br_str}")

        self._copy_btn.setEnabled(True)
        self._tag_filename_btn.setEnabled(True)

    def _on_analysis_failed(self, error: str) -> None:
        self._status_label.setText(f"❌ Analiz Hatası: {error}")
        self._status_label.setStyleSheet("color: #EF4444; font-weight: 600; font-size: 12px; margin: 6px 0;")

    def _on_copy_clicked(self) -> None:
        if not self._analysis_result:
            return
        text = self._analysis_result.summary_tag
        QApplication.clipboard().setText(text)
        self._copy_btn.setText("✓ Panoya Kopyalandı!")
        self._copy_btn.setStyleSheet("background-color: #065F46; color: #A7F3D0; border: 1px solid #10B981;")

    def _on_tag_filename_clicked(self) -> None:
        if not self._analysis_result or not self._file_path.is_file():
            return
        tag = f"[{round(self._analysis_result.bpm)} BPM - {self._analysis_result.key_display}]"
        old_stem = self._file_path.stem

        if tag in old_stem:
            QMessageBox.information(self, "Bilgi", "Bu dosya adı zaten BPM ve Ton etiketini içeriyor.")
            return

        new_name = f"{old_stem} {tag}{self._file_path.suffix}"
        new_path = self._file_path.parent / new_name

        try:
            self._file_path.rename(new_path)
            self._file_path = new_path
            self._file_name_label.setText(new_path.name)
            self._tag_filename_btn.setText("✓ Dosya Adına Eklendi")
            self._tag_filename_btn.setEnabled(False)
            QMessageBox.information(self, "Başarılı", f"Dosya adı güncellendi:\n{new_path.name}")
        except Exception as exc:
            QMessageBox.warning(self, "Hata", f"Dosya adı değiştirilemedi: {exc}")

    def _on_folder_clicked(self) -> None:
        if not self._file_path:
            return
        folder = self._file_path.parent
        if os.name == "nt" and self._file_path.is_file():
            subprocess.Popen(f'explorer /select,"{self._file_path}"')
        elif folder.is_dir():
            if os.name == "nt":
                os.startfile(str(folder))
            else:
                subprocess.Popen(["xdg-open", str(folder)])

    def _on_browse_clicked(self) -> None:
        file_path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Ses Dosyası Seç (BPM ve Ton Analizi İçin)",
            str(self._file_path.parent if self._file_path else Path.home()),
            "Ses Dosyaları (*.wav *.mp3 *.flac *.opus *.m4a *.aac *.ogg);;Tüm Dosyalar (*.*)",
        )
        if file_path_str:
            new_path = Path(file_path_str)
            if new_path.is_file():
                self._start_analysis(new_path)

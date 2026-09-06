import os
from pathlib import Path
import subprocess
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QProgressBar,
    QFrame, QComboBox, QGridLayout
)
from videcook.utils.i18n import LanguageManager
from videcook.ui.upscayl_worker import UpscaylWorker

class ModernZone(QFrame):
    file_dropped = Signal(str)
    clicked = Signal()

    def __init__(self, is_output=False, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(not is_output)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_output = is_output
        
        # 21st.dev inspired modern styling
        base_color = "#10b981" if is_output else "#6366f1" # Emerald for output, Indigo for input
        self.setStyleSheet(f"""
            QFrame {{
                border: 2px dashed rgba(255, 255, 255, 0.15);
                border-radius: 20px;
                background: rgba(20, 20, 20, 0.6);
            }}
            QFrame:hover {{
                border-color: {base_color};
                background: rgba({ '16,185,129' if is_output else '99,102,241' }, 0.08);
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon (Optional, just text for now but large)
        self.icon = QLabel("⬇️" if is_output else "🖼️")
        self.icon.setStyleSheet("font-size: 32px; background: transparent; border: none;")
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon)
        
        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("border: none; color: #e2e8f0; font-size: 16px; font-weight: 500; background: transparent;")
        layout.addWidget(self.label)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if not self.is_output and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        if not self.is_output:
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                if path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    self.file_dropped.emit(path)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

class ModernComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QComboBox {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 10px 15px;
                background: rgba(30, 30, 30, 0.8);
                color: white;
                font-size: 15px;
                min-height: 24px;
            }
            QComboBox:hover {
                border-color: #6366f1;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #888;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background: #1a1a1a;
                border: 1px solid #333;
                selection-background-color: #6366f1;
                border-radius: 5px;
                outline: 0;
            }
        """)

class UpscaylPage(QWidget):
    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._input_path: Path | None = None
        self._output_dir: Path | None = None
        self._worker: UpscaylWorker | None = None
        self._thread: QThread | None = None
        
        self._setup_ui()
        self.retranslate()
        
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(30)
        
        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        
        self._title = QLabel()
        self._title.setStyleSheet("font-size: 28px; font-weight: 800; color: white;")
        self._subtitle = QLabel()
        self._subtitle.setStyleSheet("font-size: 15px; color: #94a3b8;")
        
        header_layout.addWidget(self._title)
        header_layout.addWidget(self._subtitle)
        layout.addLayout(header_layout)
        
        # Zones
        zones_layout = QHBoxLayout()
        zones_layout.setSpacing(20)
        
        self._input_zone = ModernZone(is_output=False)
        self._input_zone.setMinimumHeight(140)
        self._input_zone.clicked.connect(self._on_select_input)
        self._input_zone.file_dropped.connect(self._on_file_dropped)
        
        self._arrow = QLabel("➜")
        self._arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._arrow.setStyleSheet("font-size: 32px; color: #475569; font-weight: bold; margin: 0 10px;")
        
        self._output_zone = ModernZone(is_output=True)
        self._output_zone.setMinimumHeight(140)
        self._output_zone.clicked.connect(self._on_select_output_folder)
        
        zones_layout.addWidget(self._input_zone, stretch=1)
        zones_layout.addWidget(self._arrow)
        zones_layout.addWidget(self._output_zone, stretch=1)
        layout.addLayout(zones_layout)
        
        # Controls Grid
        controls_layout = QGridLayout()
        controls_layout.setSpacing(20)
        
        self._model_label = QLabel()
        self._model_label.setStyleSheet("color: #cbd5e1; font-weight: bold; font-size: 14px;")
        self._model_combo = ModernComboBox()
        self._model_combo.addItems([
            "Standart (upscayl-standard-4x) - Genel Görseller",
            "Ultra Keskin (ultrasharp-4x) - Detaylı Fotoğraflar",
            "Anime (realesrgan-x4plus-anime) - Çizimler",
            "Dijital Sanat (remacri-4x) - Dijital Renderlar"
        ])
        
        self._scale_label = QLabel()
        self._scale_label.setStyleSheet("color: #cbd5e1; font-weight: bold; font-size: 14px;")
        self._scale_combo = ModernComboBox()
        self._scale_combo.addItems(["2x Büyütme", "4x Büyütme", "8x Büyütme (Çift Geçiş)"])
        self._scale_combo.setCurrentIndex(1)
        
        controls_layout.addWidget(self._model_label, 0, 0)
        controls_layout.addWidget(self._model_combo, 1, 0)
        controls_layout.addWidget(self._scale_label, 0, 1)
        controls_layout.addWidget(self._scale_combo, 1, 1)
        layout.addLayout(controls_layout)
        
        # Action Area
        action_layout = QHBoxLayout()
        
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setMinimumHeight(8)
        self._progress.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6);
                border-radius: 4px;
            }
        """)
        
        self._status = QLabel()
        self._status.setStyleSheet("color: #94a3b8; font-size: 13px;")
        
        status_vbox = QVBoxLayout()
        status_vbox.setSpacing(8)
        status_vbox.addWidget(self._status)
        status_vbox.addWidget(self._progress)
        
        self._cancel_btn = QPushButton()
        self._cancel_btn.setObjectName("ghostButton")
        self._cancel_btn.setMinimumSize(120, 60)
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._on_cancel)
        
        self._enhance_btn = QPushButton()
        self._enhance_btn.setMinimumSize(220, 60)
        self._enhance_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._enhance_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #9333ea);
                color: white;
                border-radius: 16px;
                font-weight: 800;
                font-size: 18px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #7e22ce);
            }
            QPushButton:disabled {
                background: #333;
                color: #777;
            }
        """)
        self._enhance_btn.clicked.connect(self._on_enhance)
        
        action_layout.addLayout(status_vbox, stretch=1)
        action_layout.addSpacing(20)
        action_layout.addWidget(self._cancel_btn)
        action_layout.addWidget(self._enhance_btn)
        
        layout.addLayout(action_layout)
        layout.addStretch(1)

    def set_i18n(self, i18n: LanguageManager) -> None:
        self._i18n = i18n
        self.retranslate()

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._title.setText(t("upscale.title"))
        self._subtitle.setText(t("upscale.subtitle"))
        
        if not self._input_path:
            self._input_zone.label.setText(t("upscale.drop_zone"))
        else:
            self._input_zone.label.setText(f"{t('upscale.selected_file')}\n{self._input_path.name}")
            
        if not hasattr(self, "_output_dir") or not self._output_dir:
            self._output_zone.label.setText(t("upscale.output_zone"))
        else:
            self._output_zone.label.setText(f"{t('upscale.selected_folder')}\n{self._output_dir.name}")
            
        self._model_label.setText(t("upscale.model_label"))
        self._scale_label.setText(t("upscale.scale_label"))
        self._enhance_btn.setText(t("upscale.enhance_btn"))
        self._cancel_btn.setText(t("action.cancel"))

    def _on_select_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self._i18n.get_text("converter.file_dialog"), "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            self._on_file_dropped(path)

    def _on_file_dropped(self, path: str) -> None:
        self._input_path = Path(path)
        self._input_zone.label.setText(f"{self._i18n.get_text('upscale.selected_file')}\n{self._input_path.name}")
        self._input_zone.icon.setText("✅")

    def _on_select_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self._i18n.get_text("converter.folder_dialog"))
        if folder:
            self._output_dir = Path(folder)
            self._output_zone.label.setText(f"{self._i18n.get_text('upscale.selected_folder')}\n{self._output_dir.name}")
            self._output_zone.icon.setText("📁")

    def _on_enhance(self) -> None:
        if not self._input_path or not self._input_path.exists():
            self._status.setText(self._i18n.get_text("upscale.error_no_file"))
            return
            
        if not hasattr(self, "_output_dir") or not self._output_dir:
            self._status.setText(self._i18n.get_text("upscale.error_no_folder"))
            return
            
        model_idx = self._model_combo.currentIndex()
        scale_idx = self._scale_combo.currentIndex()
        
        self._start_worker(str(self._input_path), str(self._output_dir), model_idx, scale_idx)
        
    def _start_worker(self, in_path, out_dir, model, scale) -> None:
        self._cleanup_worker()
        self._progress.setValue(0)
        self._enhance_btn.setEnabled(False)
        self._cancel_btn.setVisible(True)
        self._cancel_btn.setEnabled(True)
        
        self._thread = QThread()
        self._worker = UpscaylWorker(in_path, out_dir, model, scale, self._i18n)
        self._worker.moveToThread(self._thread)
        
        self._thread.started.connect(self._worker.run)
        self._worker.progress_changed.connect(self._progress.setValue)
        self._worker.status_changed.connect(self._status.setText)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        
        self._thread.start()
        
    def _on_cancel(self) -> None:
        if self._worker:
            self._worker.cancel()
        self._cancel_btn.setEnabled(False)
        self._status.setText("İptal ediliyor...")
        
    def _on_finished(self, success: bool, message: str, output_path: str) -> None:
        self._enhance_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        
        if success:
            self._progress.setValue(100)
            self._status.setText("İşlem başarıyla tamamlandı! " + message)
            if os.name == 'nt' and output_path:
                try:
                    subprocess.Popen(f'explorer /select,"{os.path.normpath(output_path)}"')
                except: pass
        else:
            self._progress.setValue(0)
            self._status.setText(f"Hata: {message}")
            
    def _cleanup_worker(self) -> None:
        if self._worker:
            try:
                self._worker.cancel()
            except Exception: pass
        if self._thread:
            try:
                if self._thread.isRunning():
                    self._thread.quit()
                    self._thread.wait(2000)
            except Exception: pass
        self._worker = None
        self._thread = None

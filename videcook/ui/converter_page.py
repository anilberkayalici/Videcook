import os
from pathlib import Path
import subprocess
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QProgressBar,
    QFrame, QLineEdit, QTabWidget, QGridLayout
)

from videcook.core.converter_builder import ConverterRequest, probe_audio_channels
from videcook.ui.converter_worker import ConverterWorker
from videcook.utils.i18n import LanguageManager

class DropZone(QFrame):
    file_dropped = Signal(str)
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #0078d7;
                border-radius: 10px;
                background-color: rgba(0, 120, 215, 0.02);
            }
            QFrame:hover {
                border-color: #3a96dd;
                background-color: rgba(0, 120, 215, 0.08);
            }
        """)
        
        layout = QVBoxLayout(self)
        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("border: none; color: #ccc; font-size: 16px;")
        layout.addWidget(self.label)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.file_dropped.emit(path)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class OutputFolderZone(QFrame):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #0078d7;
                border-radius: 10px;
                background-color: rgba(0, 120, 215, 0.02);
            }
            QFrame:hover {
                border-color: #3a96dd;
                background-color: rgba(0, 120, 215, 0.08);
            }
        """)
        
        layout = QVBoxLayout(self)
        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("border: none; color: #ccc; font-size: 16px;")
        layout.addWidget(self.label)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

class FormatSelector(QWidget):
    format_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._formats = {
            "Video": [".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"],
            "Ses": [".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"],
            "5.1 Ses": [".ac3", ".wav", ".flac", ".aac", ".eac3", ".m4a", ".opus"],
            "Görsel": [".jpg", ".png", ".webp", ".ico", ".bmp"],
            "Altyazı": [".srt", ".vtt", ".ass"],
            "Belge": [".pdf", ".docx", ".pptx", ".xlsx"]
        }
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.search = QLineEdit()
        self.search.setPlaceholderText("Format ara (ör. mp4)...")
        self.search.textChanged.connect(self._filter_formats)
        layout.addWidget(self.search)
        
        self.tabs = QTabWidget()
        self.tabs.setMinimumHeight(200)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                border-radius: 10px;
                background: #151515;
                top: -1px;
            }
            QTabBar::tab {
                padding: 14px 32px;
                margin-right: 4px;
                margin-bottom: 8px;
                background: transparent;
                border: 1px solid transparent;
                color: #aaa;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QTabBar::tab:hover {
                color: #fff;
                background: rgba(255, 255, 255, 0.05);
            }
            QTabBar::tab:selected {
                color: #fff;
                background: #222;
                border: 1px solid #555;
            }
            QTabBar::tab:focus { outline: none; }
        """)
        
        self.all_buttons = []
        self.selected_format = None
        
        for cat, exts in self._formats.items():
            page = QWidget()
            grid = QGridLayout(page)
            grid.setSpacing(10)
            
            for j, ext in enumerate(exts):
                btn = QPushButton(ext)
                btn.setCheckable(True)
                btn.setMinimumSize(80, 50)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton {
                        background: #222;
                        color: #eee;
                        border: 1px solid #333;
                        border-radius: 8px;
                        font-size: 16px;
                        padding: 10px;
                    }
                    QPushButton:hover {
                        background: #333;
                        border: 1px solid #555;
                    }
                    QPushButton:checked {
                        background: #fff;
                        color: #000;
                        font-weight: bold;
                        border: none;
                    }
                """)
                btn.clicked.connect(lambda checked, b=btn, e=ext: self._on_btn_clicked(b, e))
                self.all_buttons.append(btn)
                grid.addWidget(btn, j // 6, j % 6)
                
            grid.setRowStretch(grid.rowCount(), 1)
            self.tabs.addTab(page, cat)
            
        layout.addWidget(self.tabs)

    def _on_btn_clicked(self, clicked_btn: QPushButton, ext: str) -> None:
        for btn in self.all_buttons:
            if btn != clicked_btn:
                btn.setChecked(False)
        self.selected_format = ext if clicked_btn.isChecked() else None
        if self.selected_format:
            self.format_selected.emit(self.selected_format)

    def select_category_for_extension(self, ext: str) -> None:
        for i, (cat, exts) in enumerate(self._formats.items()):
            if ext in exts:
                self.tabs.setCurrentIndex(i)
                break

    def select_surround_tab(self) -> None:
        """Switch directly to the 5.1 Surround audio tab."""
        self.tabs.setCurrentIndex(2)

    def _filter_formats(self, text: str) -> None:
        text = text.lower()
        for btn in self.all_buttons:
            if text in btn.text().lower():
                btn.show()
            else:
                btn.hide()

class ConverterPage(QWidget):
    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._input_path: Path | None = None
        self._output_path: Path | None = None
        self._output_dir: Path | None = None
        
        self._worker: ConverterWorker | None = None
        self._thread: QThread | None = None
        
        self._setup_ui()
        self.retranslate()
        
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        
        self._title = QLabel()
        self._title.setObjectName("pageTitle")
        self._subtitle = QLabel()
        self._subtitle.setObjectName("pageSubtitle")
        
        layout.addWidget(self._title)
        layout.addWidget(self._subtitle)
        
        zones_layout = QHBoxLayout()
        zones_layout.setSpacing(15)
        
        self._drop_zone = DropZone()
        self._drop_zone.setMinimumHeight(80)
        self._drop_zone.clicked.connect(self._on_select_input)
        self._drop_zone.file_dropped.connect(self._on_file_dropped)
        
        self._arrow = QLabel("➔")
        self._arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._arrow.setStyleSheet("font-size: 32px; color: #555; font-weight: bold; margin: 0 10px;")
        
        self._output_zone = OutputFolderZone()
        self._output_zone.setMinimumHeight(80)
        self._output_zone.clicked.connect(self._on_select_output_folder)
        
        zones_layout.addWidget(self._drop_zone, stretch=1)
        zones_layout.addWidget(self._arrow)
        zones_layout.addWidget(self._output_zone, stretch=1)
        layout.addLayout(zones_layout)
        
        self._format_label = QLabel(self._i18n.get_text("converter.output_format"))
        self._format_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(self._format_label)
        
        self._format_selector = FormatSelector()
        self._format_selector.format_selected.connect(lambda fmt: self._format_label.setText(f"{self._i18n.get_text('converter.output_format')} <b>{fmt.upper()}</b>"))
        layout.addWidget(self._format_selector)
        
        # Audio / Video conversion mode selector (Single File vs Split Channels)
        mode_box = QHBoxLayout()
        mode_box.setSpacing(10)
        
        self._mode_label = QLabel()
        self._mode_label.setStyleSheet("font-weight: bold; color: #aaa; font-size: 14px;")
        
        self._mode_single_btn = QPushButton()
        self._mode_single_btn.setObjectName("segButton")
        self._mode_single_btn.setCheckable(True)
        self._mode_single_btn.setChecked(True)
        self._mode_single_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mode_single_btn.clicked.connect(self._on_mode_single_clicked)
        
        self._mode_split_btn = QPushButton()
        self._mode_split_btn.setObjectName("segButton")
        self._mode_split_btn.setCheckable(True)
        self._mode_split_btn.setChecked(False)
        self._mode_split_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mode_split_btn.clicked.connect(self._on_mode_split_clicked)
        
        mode_box.addWidget(self._mode_label)
        mode_box.addWidget(self._mode_single_btn)
        mode_box.addWidget(self._mode_split_btn)
        mode_box.addStretch(1)
        
        layout.addLayout(mode_box)
        
        action_layout = QHBoxLayout()
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setMinimumHeight(12)
        
        self._status = QLabel()
        
        status_vbox = QVBoxLayout()
        status_vbox.addWidget(self._status)
        status_vbox.addWidget(self._progress)
        
        self._cancel_btn = QPushButton()
        self._cancel_btn.setObjectName("ghostButton")
        self._cancel_btn.setMinimumSize(140, 64)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._on_cancel)
        
        self._show_folder_btn = QPushButton()
        self._show_folder_btn.setObjectName("ghostButton")
        self._show_folder_btn.setMinimumSize(140, 64)
        self._show_folder_btn.setVisible(False)
        self._show_folder_btn.clicked.connect(self._on_show_folder)
        
        self._convert_btn = QPushButton()
        self._convert_btn.setObjectName("modern_download_button")
        self._convert_btn.setMinimumSize(220, 64)
        self._convert_btn.clicked.connect(self._on_convert)
        
        action_layout.addLayout(status_vbox, stretch=1)
        action_layout.addWidget(self._show_folder_btn)
        action_layout.addWidget(self._cancel_btn)
        action_layout.addWidget(self._convert_btn)
        
        layout.addLayout(action_layout)
        layout.addStretch(1)
        
    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._title.setText(t("converter.title"))
        self._subtitle.setText(t("converter.subtitle"))
        
        self._mode_label.setText(t("converter.mode_label"))
        self._mode_single_btn.setText(t("converter.mode_single"))
        self._mode_split_btn.setText(t("converter.mode_split"))
        
        fmt = self._format_selector.selected_format
        if fmt:
            self._format_label.setText(f"{t('converter.output_format')} <b>{fmt.upper()}</b>")
        else:
            self._format_label.setText(t("converter.output_format"))
            
        self._convert_btn.setText(t("converter.convert_btn"))
        self._cancel_btn.setText(t("action.cancel"))
        self._show_folder_btn.setText(t("action.show_folder"))
        
        if not self._input_path:
            self._drop_zone.label.setText(t("converter.drop_zone"))
        else:
            self._drop_zone.label.setText(f"{t('converter.selected_file')}\n{self._input_path.name}")
            
        if not hasattr(self, "_output_dir") or not self._output_dir:
            self._output_zone.label.setText(t("converter.output_zone"))
        else:
            self._output_zone.label.setText(f"{t('converter.selected_folder')}\n{self._output_dir.name}")
            
        self._format_selector.search.setPlaceholderText(t("converter.search_placeholder"))
        self._format_selector.tabs.setTabText(0, t("converter.tab_video"))
        self._format_selector.tabs.setTabText(1, t("converter.tab_audio"))
        self._format_selector.tabs.setTabText(2, t("converter.tab_surround"))
        self._format_selector.tabs.setTabText(3, t("converter.tab_image"))
        self._format_selector.tabs.setTabText(4, t("converter.tab_subtitle"))
        if self._format_selector.tabs.count() > 5:
            self._format_selector.tabs.setTabText(5, t("converter.tab_document"))

    def _on_mode_single_clicked(self) -> None:
        self._mode_single_btn.setChecked(True)
        self._mode_split_btn.setChecked(False)

    def _on_mode_split_clicked(self) -> None:
        self._mode_single_btn.setChecked(False)
        self._mode_split_btn.setChecked(True)
        
    def set_i18n(self, i18n: LanguageManager) -> None:
        self._i18n = i18n
        self.retranslate()

    def _on_select_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self._i18n.get_text("converter.file_dialog"), "", "All Files (*.*)")
        if path:
            self._on_file_dropped(path)

    def _on_file_dropped(self, path: str) -> None:
        self._input_path = Path(path)
        ext = self._input_path.suffix.lower()
        t = self._i18n.get_text
        
        # Audio channel probe for 5.1 / 7.1 surround sound
        channels, layout = probe_audio_channels(self._input_path)
        audio_badge = ""
        if channels >= 8:
            audio_badge = f"\n\n{t('converter.surround_71_detected')}"
            self._format_selector.select_surround_tab()
        elif channels >= 6 or "5.1" in layout:
            audio_badge = f"\n\n{t('converter.surround_detected')}"
            self._format_selector.select_surround_tab()
        elif channels == 2:
            audio_badge = f"\n\n{t('converter.stereo_detected')}"
            self._format_selector.select_category_for_extension(ext)
        else:
            self._format_selector.select_category_for_extension(ext)
            
        self._drop_zone.label.setText(f"{t('converter.selected_file')}\n{self._input_path.name}{audio_badge}")
        self._drop_zone.label.setStyleSheet("border: none; color: #fff; font-size: 16px; font-weight: bold;")
            
    def _on_select_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self._i18n.get_text("converter.folder_dialog"))
        if folder:
            self._output_dir = Path(folder)
            self._output_zone.label.setText(f"{self._i18n.get_text('converter.selected_folder')}\n{self._output_dir.name}")
            self._output_zone.label.setStyleSheet("border: none; color: #fff; font-size: 16px; font-weight: bold;")

    def _on_convert(self) -> None:
        t = self._i18n.get_text
        if not self._input_path or not self._input_path.exists():
            self._status.setText(t("converter.error_no_file"))
            return
            
        if not hasattr(self, "_output_dir") or not self._output_dir:
            self._status.setText("Lütfen bir çıktı klasörü seçin.")
            return
            
        fmt = self._format_selector.selected_format
        if not fmt:
            self._status.setText(t("converter.error_no_format"))
            return
            
        out_path = self._output_dir / self._input_path.with_suffix(fmt).name
        if out_path == self._input_path:
            self._status.setText(t("converter.error_same_format"))
            return
            
        self._output_path = out_path
        split = self._mode_split_btn.isChecked()
        
        req = ConverterRequest(input_file=self._input_path, output_file=self._output_path, split_channels=split)
        self._start_worker(req)
        
    def _start_worker(self, req: ConverterRequest) -> None:
        self._cleanup_worker()
        self._progress.setRange(0, 0)
        self._convert_btn.setEnabled(False)
        self._cancel_btn.setVisible(True)
        self._show_folder_btn.setVisible(False)
        self._cancel_btn.setEnabled(True)
        
        self._thread = QThread()
        self._worker = ConverterWorker(req, self._i18n)
        self._worker.moveToThread(self._thread)
        
        self._thread.started.connect(self._worker.run)
        self._worker.status_changed.connect(self._status.setText)
        # Log is removed, so we ignore log_message and error_message
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        
        self._thread.start()
        
    def _on_cancel(self) -> None:
        if self._worker:
            self._worker.cancel()
        self._cancel_btn.setEnabled(False)
        
    def _on_finished(self, success: bool, message: str, output_path: str) -> None:
        self._convert_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress.setRange(0, 100)
        self._progress.setValue(100 if success else 0)
        
        if success:
            self._cancel_btn.setVisible(False)
            self._show_folder_btn.setVisible(True)
            self._last_downloaded_file = output_path
            
    def _on_show_folder(self) -> None:
        path_str = getattr(self, "_last_downloaded_file", None)
        if not path_str and hasattr(self, "_output_dir") and self._output_dir:
            path_str = str(self._output_dir)
            
        if not path_str:
            return

        p = Path(path_str)
        if os.name == "nt":
            if p.is_file():
                subprocess.Popen(f'explorer /select,"{os.path.normpath(str(p))}"')
            elif p.is_dir():
                os.startfile(os.path.normpath(str(p)))
            elif p.parent.exists():
                os.startfile(os.path.normpath(str(p.parent)))
            elif hasattr(self, "_output_dir") and self._output_dir and self._output_dir.exists():
                os.startfile(os.path.normpath(str(self._output_dir)))
        else:
            target_dir = p if p.is_dir() else p.parent
            if not target_dir.exists() and hasattr(self, "_output_dir") and self._output_dir:
                target_dir = self._output_dir
            if target_dir and target_dir.exists():
                subprocess.Popen(["xdg-open", str(target_dir)])
                
    def _cleanup_worker(self) -> None:
        if self._worker:
            try:
                self._worker.cancel()
            except Exception:
                pass
        if self._thread:
            try:
                if self._thread.isRunning():
                    self._thread.quit()
                    self._thread.wait(2000)
            except Exception:
                pass
        self._worker = None
        self._thread = None

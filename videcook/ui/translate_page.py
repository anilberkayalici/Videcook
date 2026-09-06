"""Translate page — SRT subtitle conversion to custom dubbing format.

A scrollable form with file picker, output folder selector, and a
start button. The formatted output is shown in a read-only preview
and can be copied or saved as .txt.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from videcook.core.subtitle_formatter import (
    build_export_filename,
    convert_srt,
)
from videcook.utils.i18n import LanguageManager


class TranslatePage(QWidget):
    """SRT → formatted text conversion page."""

    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._srt_path: Path | None = None
        self._output_dir: Path | None = None
        self._formatted_output: str = ""
        self._build_ui()
        self.retranslate()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        from videcook.ui.widgets import ModernCard

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("translateScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_w = QWidget()
        content_w.setObjectName("translateContent")
        self._scroll.setWidget(content_w)
        outer.addWidget(self._scroll)

        page = QVBoxLayout(content_w)
        page.setSpacing(18)
        page.setContentsMargins(40, 40, 40, 40)

        row = QHBoxLayout()
        row.setSpacing(24)

        # ---- Form (left) ----
        form_card = ModernCard()
        
        self._source_title = QLabel()
        self._source_title.setObjectName("appTitle")
        self._source_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_card.addWidget(self._source_title)

        # SRT file picker
        srt_layout = QVBoxLayout()
        self._srt_label = QLabel()
        self._srt_label.setObjectName("fieldLabel")
        srt_layout.addWidget(self._srt_label)
        srt_row = QHBoxLayout()
        self._srt_display = QLineEdit()
        self._srt_display.setReadOnly(True)
        self._srt_display.setMinimumHeight(48)
        self._srt_display.setPlaceholderText("altyazi.srt")
        srt_row.addWidget(self._srt_display, stretch=1)
        self._srt_browse = QPushButton()
        self._srt_browse.setObjectName("cookie_browse_button")
        self._srt_browse.setFixedSize(120, 48)
        self._srt_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self._srt_browse.clicked.connect(self._browse_srt)
        srt_row.addWidget(self._srt_browse)
        srt_layout.addLayout(srt_row)
        form_card.addLayout(srt_layout)

        # Output folder picker
        out_layout = QVBoxLayout()
        self._out_label = QLabel()
        self._out_label.setObjectName("fieldLabel")
        out_layout.addWidget(self._out_label)
        out_row = QHBoxLayout()
        self._out_display = QLineEdit()
        self._out_display.setReadOnly(True)
        self._out_display.setMinimumHeight(48)
        self._out_display.setPlaceholderText("C:/Users/...")
        out_row.addWidget(self._out_display, stretch=1)
        self._out_browse = QPushButton()
        self._out_browse.setObjectName("cookie_browse_button")
        self._out_browse.setFixedSize(120, 48)
        self._out_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self._out_browse.clicked.connect(self._browse_output)
        out_row.addWidget(self._out_browse)
        out_layout.addLayout(out_row)
        form_card.addLayout(out_layout)

        # Start button
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self._start_btn = QPushButton()
        self._start_btn.setObjectName("modern_download_button")
        self._start_btn.setMinimumSize(200, 56)
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.clicked.connect(self._on_start)
        btn_row.addWidget(self._start_btn)
        form_card.addLayout(btn_row)

        row.addWidget(form_card, stretch=5)

        # ---- Preview (right) ----
        preview_card = ModernCard()
        
        self._preview_title = QLabel()
        self._preview_title.setObjectName("logTitle")
        preview_card.addWidget(self._preview_title)

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setObjectName("previewOutput")
        self._preview.setMinimumHeight(200)
        self._preview.setStyleSheet(
            "QPlainTextEdit { background-color: #1a1116; color: #e8dde3;"
            " border: 1px solid #3a2530; border-radius: 8px;"
            " padding: 12px; font-family: Consolas, monospace; font-size: 14px; }"
        )
        preview_card.addWidget(self._preview)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self._copy_btn = QPushButton()
        self._copy_btn.setObjectName("ghostButton")
        self._copy_btn.setMinimumHeight(56)
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.setEnabled(False)
        self._copy_btn.clicked.connect(self._on_copy)
        actions.addWidget(self._copy_btn)
        self._save_btn = QPushButton()
        self._save_btn.setObjectName("modern_download_button")
        self._save_btn.setMinimumHeight(56)
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._on_save)
        actions.addWidget(self._save_btn)
        preview_card.addLayout(actions)

        row.addWidget(preview_card, stretch=5)
        page.addLayout(row)

        self._status = QLabel()
        self._status.setObjectName("status_label")
        page.addWidget(self._status)

    def _browse_srt(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "SRT dosyası seç", "", "SRT files (*.srt);;All files (*)"
        )
        if path:
            self._srt_path = Path(path)
            self._srt_display.setText(self._srt_path.name)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Çıktı klasörü seç")
        if path:
            self._output_dir = Path(path)
            self._out_display.setText(str(self._output_dir))

    def _on_start(self) -> None:
        t = self._i18n.get_text
        if self._srt_path is None:
            QMessageBox.warning(self, t("app.name"), t("translate.select_srt_first"))
            return
        if self._output_dir is None:
            QMessageBox.warning(
                self, t("app.name"), t("translate.select_output_first")
            )
            return

        try:
            content = self._srt_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = self._srt_path.read_text(encoding="utf-8-sig")
            except Exception:
                content = self._srt_path.read_text(
                    encoding="cp1254"
                )  # Turkish Windows fallback
        except Exception as exc:
            QMessageBox.critical(
                self,
                t("app.name"),
                t("translate.read_error").format(message=str(exc)),
            )
            return

        try:
            result = convert_srt(
                content,
                file_name=self._srt_path.name,
                encoding="utf-8",
            )
        except ValueError as exc:
            QMessageBox.critical(self, t("app.name"), str(exc))
            return

        self._formatted_output = result.output
        self._preview.setPlainText(result.output)
        self._copy_btn.setEnabled(True)
        self._save_btn.setEnabled(True)
        self._status.setText(
            t("translate.done").format(count=len(result.lines))
        )
        if result.notices:
            for n in result.notices:
                self._status.setText(
                    self._status.text()
                    + f"  [{n['severity']}] {n['message']}"
                )

    def _on_copy(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self._formatted_output)
        self._status.setText(self._i18n.get_text("translate.copied"))

    def _on_save(self) -> None:
        if not self._formatted_output or self._output_dir is None:
            return
        default_name = (
            build_export_filename(self._srt_path.name)
            if self._srt_path
            else "formatted.txt"
        )
        suggested = str(self._output_dir / default_name)
        path, _ = QFileDialog.getSaveFileName(
            self, "TXT olarak kaydet", suggested, "Text files (*.txt)"
        )
        if path:
            Path(path).write_text(self._formatted_output, encoding="utf-8")
            self._status.setText(
                self._i18n.get_text("translate.saved").format(path=path)
            )

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._source_title.setText(t("translate.title"))
        self._srt_label.setText(t("translate.srt_label"))
        self._srt_browse.setText(t("action.browse"))
        self._out_label.setText(t("label.output_folder"))
        self._out_browse.setText(t("action.browse"))
        self._start_btn.setText(t("translate.start"))
        self._preview_title.setText(t("translate.preview_title"))
        self._copy_btn.setText(t("translate.copy"))
        self._save_btn.setText(t("translate.save_txt"))

    def set_i18n(self, i18n: LanguageManager) -> None:
        self._i18n = i18n
        self.retranslate()

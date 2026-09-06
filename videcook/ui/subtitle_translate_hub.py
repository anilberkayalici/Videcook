"""Unified Subtitle & Translation Hub page.

Combines the Subtitle Generator (Groq speech-to-text SRT) and
Translate / Subtitle Formatter pages into a single view with
a top-left segmented switch control.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from videcook.ui.subtitle_page import SubtitlePage
from videcook.ui.translate_page import TranslatePage
from videcook.utils.i18n import LanguageManager


class SubtitlesTranslateHubPage(QWidget):
    """Container page with top-left switch buttons between Subtitle and Translate."""

    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._build_ui()
        self.retranslate()

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(28, 16, 28, 16)
        outer_layout.setSpacing(10)

        # Top Switcher Bar (top-left aligned)
        switch_bar = QHBoxLayout()
        switch_bar.setContentsMargins(0, 0, 0, 0)
        switch_bar.setSpacing(10)

        self._sub_switch_btn = QPushButton("🎙️ Altyazı")
        self._sub_switch_btn.setObjectName("hubSwitchButton")
        self._sub_switch_btn.setCheckable(True)
        self._sub_switch_btn.setChecked(True)
        self._sub_switch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sub_switch_btn.setMinimumSize(170, 48)
        self._sub_switch_btn.clicked.connect(lambda: self._set_mode(0))

        self._trans_switch_btn = QPushButton("🔄 Çeviri")
        self._trans_switch_btn.setObjectName("hubSwitchButton")
        self._trans_switch_btn.setCheckable(True)
        self._trans_switch_btn.setChecked(False)
        self._trans_switch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._trans_switch_btn.setMinimumSize(170, 48)
        self._trans_switch_btn.clicked.connect(lambda: self._set_mode(1))

        switch_bar.addWidget(self._sub_switch_btn)
        switch_bar.addWidget(self._trans_switch_btn)
        switch_bar.addStretch(1)

        outer_layout.addLayout(switch_bar)

        # Content pages stack
        self._hub_stack = QStackedWidget()
        self._subtitle_page = SubtitlePage(self._i18n)
        self._translate_page = TranslatePage(self._i18n)

        self._hub_stack.addWidget(self._subtitle_page)   # 0: Altyazı
        self._hub_stack.addWidget(self._translate_page)  # 1: Çeviri

        outer_layout.addWidget(self._hub_stack, stretch=1)

    def _set_mode(self, index: int) -> None:
        self._hub_stack.setCurrentIndex(index)
        self._sub_switch_btn.setChecked(index == 0)
        self._trans_switch_btn.setChecked(index == 1)

    def set_i18n(self, i18n: LanguageManager) -> None:
        self._i18n = i18n
        self._subtitle_page.set_i18n(i18n)
        self._translate_page.set_i18n(i18n)
        self.retranslate()

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._sub_switch_btn.setText(f"🎙️ {t('nav.subtitles')}")
        self._trans_switch_btn.setText(f"🔄 {t('nav.translate')}")

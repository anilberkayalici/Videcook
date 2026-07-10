"""Help page with tabbed guides for Video Download, Audio Download, and Subtitles."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from videcook.utils.i18n import LanguageManager


class HelpPage(QWidget):
    """Scrollable help page with tabbed guides for each feature."""

    GUIDES = ["video", "audio", "subtitle"]
    GUIDE_VIDEO = 0
    GUIDE_AUDIO = 1
    GUIDE_SUBTITLE = 2

    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._tab_buttons: list[QPushButton] = []
        self._guide_steps: list[list[tuple[QLabel, QLabel]]] = []
        self._guide_warnings: list[QLabel] = []
        self._build_ui()
        self.retranslate()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("helpScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        outer.addWidget(scroll)

        layout = QVBoxLayout(container)
        layout.setSpacing(18)
        layout.setContentsMargins(32, 28, 32, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        hero = QWidget()
        hero.setObjectName("heroStrip")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        hero_layout.setSpacing(6)

        self._title = QLabel()
        self._title.setObjectName("pageTitle")
        hero_layout.addWidget(self._title)
        layout.addWidget(hero)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)
        for idx in range(3):
            btn = QPushButton()
            btn.setObjectName("segButton")
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumSize(140, 38)
            btn.clicked.connect(lambda _checked=False, i=idx: self._show_guide(i))
            tab_row.addWidget(btn)
            self._tab_buttons.append(btn)
        tab_row.addStretch(1)
        layout.addLayout(tab_row)

        card = QWidget()
        card.setObjectName("settingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)
        card_layout.setContentsMargins(24, 22, 24, 24)

        self._guide_stack = QStackedWidget()
        card_layout.addWidget(self._guide_stack)

        for guide_idx in range(3):
            guide_widget = QWidget()
            guide_layout = QVBoxLayout(guide_widget)
            guide_layout.setSpacing(10)
            guide_layout.setContentsMargins(0, 0, 0, 0)

            steps_container = QWidget()
            steps_layout = QVBoxLayout(steps_container)
            steps_layout.setSpacing(10)
            steps_layout.setContentsMargins(0, 0, 0, 0)

            step_count = 7
            pairs: list[tuple[QLabel, QLabel]] = []
            for _ in range(step_count):
                row_widget = QWidget()
                row_widget.setObjectName("stepRow")
                row = QHBoxLayout(row_widget)
                row.setContentsMargins(14, 12, 14, 12)
                row.setSpacing(12)

                num = QLabel()
                num.setObjectName("stepBadge")
                num.setFixedSize(28, 28)
                num.setAlignment(Qt.AlignmentFlag.AlignCenter)

                text = QLabel()
                text.setObjectName("stepText")
                text.setWordWrap(True)
                text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

                row.addWidget(num)
                row.addWidget(text, stretch=1)
                steps_layout.addWidget(row_widget)
                pairs.append((num, text))

            guide_layout.addWidget(steps_container)

            warning_box = QWidget()
            warning_box.setObjectName("warningBox")
            warning_layout = QVBoxLayout(warning_box)
            warning_layout.setContentsMargins(16, 16, 16, 16)
            warn = QLabel()
            warn.setObjectName("warningLabel")
            warn.setWordWrap(True)
            warn.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            warning_layout.addWidget(warn)
            guide_layout.addWidget(warning_box)

            guide_layout.addStretch(1)
            self._guide_stack.addWidget(guide_widget)
            self._guide_steps.append(pairs)
            self._guide_warnings.append(warn)

        layout.addWidget(card)
        layout.addStretch(1)
        scroll.setWidget(container)

    def _show_guide(self, index: int) -> None:
        self._guide_stack.setCurrentIndex(index)
        for i, btn in enumerate(self._tab_buttons):
            btn.setChecked(i == index)

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._title.setText(t("help.title"))

        tab_labels = ["help.tab_video", "help.tab_audio", "help.tab_subtitle"]
        for btn, key in zip(self._tab_buttons, tab_labels):
            btn.setText(t(key))

        for guide_idx, guide_key in enumerate(self.GUIDES):
            pairs = self._guide_steps[guide_idx]
            for step_idx, (num_label, text_label) in enumerate(pairs, start=1):
                num_label.setText(str(step_idx))
                text_label.setText(t(f"help.{guide_key}_step_{step_idx}"))

            self._guide_warnings[guide_idx].setText(t(f"help.{guide_key}_warning"))

    def set_i18n(self, i18n: LanguageManager) -> None:
        self._i18n = i18n
        self.retranslate()

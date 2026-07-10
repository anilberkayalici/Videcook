"""Help page — integrated "Nasıl Kullanırım?" / "How to Use?" guide."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from videcook.utils.i18n import LanguageManager


class HelpPage(QWidget):
    """Scrollable help guide with numbered steps and a cookie warning."""

    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._build_ui()
        self.retranslate()

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        container.setObjectName("helpCard")
        layout = QVBoxLayout(container)
        layout.setSpacing(18)
        layout.setContentsMargins(26, 24, 26, 26)
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

        # Steps container
        steps_container = QWidget()
        steps_layout = QVBoxLayout(steps_container)
        steps_layout.setSpacing(10)
        steps_layout.setContentsMargins(0, 0, 0, 0)

        self._steps: list[tuple[QLabel, QLabel]] = []
        for _ in range(7):
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

            self._steps.append((num, text))

        layout.addWidget(steps_container)

        # Warning callout
        warning_box = QWidget()
        warning_box.setObjectName("warningBox")
        warning_layout = QVBoxLayout(warning_box)
        warning_layout.setContentsMargins(16, 16, 16, 16)
        self._warning = QLabel()
        self._warning.setObjectName("warningLabel")
        self._warning.setWordWrap(True)
        self._warning.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        warning_layout.addWidget(self._warning)
        layout.addWidget(warning_box)

        layout.addStretch(1)
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 30)
        outer.addWidget(scroll)

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._title.setText(t("help.title"))

        for i, (num_label, text_label) in enumerate(self._steps, start=1):
            num_label.setText(str(i))
            text_label.setText(t(f"help.step_{i}"))

        self._warning.setText(t("help.warning_cookie"))

    def set_i18n(self, i18n: LanguageManager) -> None:
        self._i18n = i18n
        self.retranslate()

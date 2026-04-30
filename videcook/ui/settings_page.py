"""Settings page — helper binary status and requirements note."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from videcook.services.binary_locator import check_binaries
from videcook.utils.i18n import LanguageManager


class SettingsPage(QWidget):
    """Settings page showing real-time binary status from bin/."""

    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._build_ui()
        self.retranslate()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Card
        card = QWidget()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(20)
        card_layout.setContentsMargins(24, 24, 24, 24)

        self._title = QLabel()
        self._title.setObjectName("appTitle")
        card_layout.addWidget(self._title)

        self._section = QLabel()
        self._section.setObjectName("sectionLabel")
        card_layout.addWidget(self._section)

        # Binary rows
        self._rows: list[tuple[QLabel, QLabel]] = []
        for _ in range(3):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)

            name_label = QLabel()
            name_label.setObjectName("fieldLabel")

            status_label = QLabel()
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_label.setMinimumWidth(80)

            row_layout.addWidget(name_label)
            row_layout.addStretch(1)
            row_layout.addWidget(status_label)

            card_layout.addWidget(row_widget)
            self._rows.append((name_label, status_label))

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #262636;")
        line.setFixedHeight(1)
        card_layout.addWidget(line)

        self._note = QLabel()
        self._note.setObjectName("warningLabel")
        self._note.setWordWrap(True)
        card_layout.addWidget(self._note)

        layout.addWidget(card)
        layout.addStretch(1)

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._title.setText(t("settings.title"))
        self._section.setText(t("settings.binary_status"))

        labels = [
            t("settings.ytdlp"),
            t("settings.ffmpeg"),
            t("settings.ffprobe"),
        ]

        # Check binaries and update rows
        status = check_binaries()
        exists_list = [
            status.ytdlp_exists,
            status.ffmpeg_exists,
            status.ffprobe_exists,
        ]
        for (name_label, status_label), label_text, exists in zip(
            self._rows, labels, exists_list
        ):
            name_label.setText(label_text)
            self._update_status_badge(status_label, exists)

        self._note.setText(t("settings.note"))

    def set_i18n(self, i18n: LanguageManager) -> None:
        self._i18n = i18n
        self.retranslate()

    def _update_status_badge(self, label: QLabel, exists: bool) -> None:
        t = self._i18n.get_text
        if exists:
            label.setText(t("status.ok"))
            label.setStyleSheet(
                "background-color: rgba(166, 227, 161, 0.12);"
                "color: #a6e3a1;"
                "border-radius: 6px;"
                "padding: 4px 12px;"
                "font-weight: 600;"
                "font-size: 12px;"
            )
        else:
            label.setText(t("status.missing"))
            label.setStyleSheet(
                "background-color: rgba(243, 139, 168, 0.12);"
                "color: #f38ba8;"
                "border-radius: 6px;"
                "padding: 4px 12px;"
                "font-weight: 600;"
                "font-size: 12px;"
            )

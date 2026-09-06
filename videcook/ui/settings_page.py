"""Settings page — helper binary status, update check, and advanced yt-dlp args."""

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from videcook.services.binary_locator import check_binaries
from videcook.services.update_checker import check_for_updates, get_current_version
from videcook.services.secure_store import load_groq_api_key, remove_groq_api_key, save_groq_api_key
from videcook.ui.theme import (
    THEMES,
    THEME_KEYS,
    apply_theme,
    build_theme_swatch_stylesheet,
    normalize_theme_key,
)
from videcook.utils.i18n import LanguageManager
from videcook.utils.preferences import load_preferences, save_preferences


class SettingsPage(QWidget):
    """Settings page showing real-time binary status from bin/ and PATH."""

    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._build_ui()
        self.retranslate()

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("settingsScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        self._scroll.setWidget(content)
        outer_layout.addWidget(self._scroll)

        layout = QVBoxLayout(content)
        layout.setSpacing(18)
        layout.setContentsMargins(32, 28, 32, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        card = QWidget()
        card.setObjectName("settingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)
        card_layout.setContentsMargins(24, 22, 24, 24)

        hero = QWidget()
        hero.setObjectName("heroStrip")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        hero_layout.setSpacing(8)

        self._title = QLabel()
        self._title.setObjectName("pageTitle")
        hero_layout.addWidget(self._title)

        self._section = QLabel()
        self._section.setObjectName("sectionLabel")
        hero_layout.addWidget(self._section)
        card_layout.addWidget(hero)

        self._rows: list[tuple[QLabel, QLabel, QLabel]] = []
        for _ in range(3):
            row_widget = QWidget()
            row_widget.setObjectName("binaryRow")
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(14, 11, 14, 11)
            row_layout.setSpacing(12)

            name_label = QLabel()
            name_label.setObjectName("fieldLabel")
            name_label.setMinimumWidth(130)

            status_label = QLabel()
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_label.setMinimumWidth(110)

            source_label = QLabel()
            source_label.setObjectName("appTagline")
            source_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            source_label.setWordWrap(True)
            source_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

            row_layout.addWidget(name_label)
            row_layout.addWidget(status_label)
            row_layout.addWidget(source_label, stretch=1)

            card_layout.addWidget(row_widget)
            self._rows.append((name_label, status_label, source_label))

        # yt-dlp version row
        self._version_label = QLabel()
        self._version_label.setObjectName("fieldLabel")
        self._version_label.setWordWrap(True)
        card_layout.addWidget(self._version_label)

        self._update_btn = QPushButton()
        self._update_btn.setObjectName("download_button")
        self._update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_btn.setFixedSize(260, 46)
        self._update_btn.clicked.connect(self._on_check_update)
        card_layout.addWidget(self._update_btn)

        card_layout.addWidget(self._make_separator())

        # Theme selector
        self._theme_label = QLabel()
        self._theme_label.setObjectName("sectionLabel")
        card_layout.addWidget(self._theme_label)

        self._theme_row = QHBoxLayout()
        self._theme_row.setSpacing(10)
        self._theme_swatches: list[QPushButton] = []
        for theme_key in THEME_KEYS:
            p = THEMES[theme_key]
            btn = QPushButton()
            btn.setObjectName("themeSwatch")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(p["name"])
            btn.setStyleSheet(build_theme_swatch_stylesheet(p))
            btn.clicked.connect(
                lambda _checked=False, k=theme_key: self._on_theme_changed(k)
            )
            self._theme_row.addWidget(btn)
            self._theme_swatches.append(btn)
        self._theme_row.addStretch(1)
        card_layout.addLayout(self._theme_row)

        card_layout.addWidget(self._make_separator())

        # Advanced yt-dlp args
        self._advanced_label = QLabel()
        self._advanced_label.setObjectName("sectionLabel")
        card_layout.addWidget(self._advanced_label)

        self._advanced_input = QLineEdit()
        self._advanced_input.setObjectName("advanced_args_input")
        self._advanced_input.setPlaceholderText("--limit-rate 5M --sleep-interval 3")
        self._advanced_input.setMinimumHeight(44)
        self._advanced_input.textChanged.connect(self._on_advanced_changed)
        card_layout.addWidget(self._advanced_input)

        self._advanced_hint = QLabel()
        self._advanced_hint.setObjectName("appTagline")
        self._advanced_hint.setWordWrap(True)
        card_layout.addWidget(self._advanced_hint)

        line_key = QFrame()
        line_key.setFrameShape(QFrame.Shape.HLine)
        line_key.setObjectName("settingsSeparator")
        card_layout.addWidget(line_key)
        self._groq_label = QLabel()
        self._groq_label.setObjectName("sectionLabel")
        card_layout.addWidget(self._groq_label)
        self._groq_hint = QLabel()
        self._groq_hint.setObjectName("appTagline")
        self._groq_hint.setWordWrap(True)
        card_layout.addWidget(self._groq_hint)
        self._groq_input = QLineEdit()
        self._groq_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._groq_input.setPlaceholderText("gsk_...")
        self._groq_input.setMinimumHeight(44)
        card_layout.addWidget(self._groq_input)
        key_actions = QHBoxLayout()
        self._save_groq_btn = QPushButton()
        self._save_groq_btn.setObjectName("download_button")
        self._save_groq_btn.setMinimumHeight(42)
        self._save_groq_btn.clicked.connect(self._save_groq_key)
        self._remove_groq_btn = QPushButton()
        self._remove_groq_btn.setObjectName("cancel_button")
        self._remove_groq_btn.setMinimumHeight(42)
        self._remove_groq_btn.clicked.connect(self._remove_groq_key)
        key_actions.addWidget(self._save_groq_btn)
        key_actions.addWidget(self._remove_groq_btn)
        key_actions.addStretch(1)
        card_layout.addLayout(key_actions)
        self._groq_status = QLabel()
        self._groq_status.setObjectName("appTagline")
        card_layout.addWidget(self._groq_status)

        card_layout.addWidget(self._make_separator())

        self._releases_btn = QPushButton()
        self._releases_btn.setObjectName("download_button")
        self._releases_btn.setMinimumHeight(42)
        self._releases_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._releases_btn.clicked.connect(
            lambda: webbrowser.open(
                "https://github.com/anilberkayalici/Videcook/releases"
            )
        )
        card_layout.addWidget(self._releases_btn)

        card_layout.addWidget(self._make_separator())

        self._note = QLabel()
        self._note.setObjectName("warningLabel")
        self._note.setWordWrap(True)
        card_layout.addWidget(self._note)

        layout.addWidget(card)
        layout.addStretch(1)

    def _make_separator(self) -> QFrame:
        line = QFrame()
        line.setObjectName("settingsSeparator")
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        return line

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._title.setText(t("settings.title"))
        self._section.setText(t("settings.binary_status"))
        self._update_btn.setText(t("settings.check_updates"))
        self._advanced_label.setText(t("settings.advanced_args"))
        self._advanced_hint.setText(t("settings.advanced_hint"))
        self._groq_label.setText(t("settings.groq_key"))
        self._groq_hint.setText(t("settings.groq_hint"))
        self._save_groq_btn.setText(t("settings.groq_save"))
        self._remove_groq_btn.setText(t("settings.groq_remove"))
        self._groq_status.setText(t("settings.groq_saved") if load_groq_api_key() else t("settings.groq_not_saved"))
        self._releases_btn.setText(t("settings.previous_releases"))
        self._note.setText(t("settings.note"))

        prefs = load_preferences()
        self._advanced_input.blockSignals(True)
        self._advanced_input.setText(prefs.advanced_args)
        self._advanced_input.blockSignals(False)

        self._theme_label.setText(t("settings.theme"))

        active_theme = normalize_theme_key(prefs.theme)
        for i, key in enumerate(THEME_KEYS):
            self._theme_swatches[i].setChecked(key == active_theme)

        status = check_binaries()
        labels = [
            (t("settings.ytdlp"), status.ytdlp_exists, status.ytdlp_path),
            (t("settings.ffmpeg"), status.ffmpeg_exists, status.ffmpeg_path),
            (t("settings.ffprobe"), status.ffprobe_exists, status.ffprobe_path),
        ]

        for (name_label, status_label, source_label), (label_text, exists, path) in zip(
            self._rows, labels
        ):
            name_label.setText(label_text)
            self._update_status_badge(status_label, exists)
            if exists and path is not None:
                path_str = str(path)
                source_label.setText(path_str)
                source_label.setToolTip(path_str)
            else:
                source_label.setText(t("settings.source_missing"))
                source_label.setToolTip("")

        if status.ytdlp_exists and status.ytdlp_path is not None:
            ver = get_current_version(status.ytdlp_path)
            self._version_label.setText(t("settings.version").format(version=ver))
        else:
            self._version_label.setText("")

    def set_i18n(self, i18n: LanguageManager) -> None:
        self._i18n = i18n
        self.retranslate()

    def _update_status_badge(self, label: QLabel, exists: bool) -> None:
        t = self._i18n.get_text
        if exists:
            label.setText(t("status.ok"))
            label.setStyleSheet(
                "background-color: #102018;"
                "color: #A5E8BD;"
                "border: 1px solid #275E3C;"
                "border-radius: 7px;"
                "padding: 4px 12px;"
                "font-weight: 700;"
                "font-size: 12px;"
            )
        else:
            label.setText(t("status.missing"))
            label.setStyleSheet(
                "background-color: #251019;"
                "color: #F3A0B1;"
                "border: 1px solid #7F1D2D;"
                "border-radius: 7px;"
                "padding: 4px 12px;"
                "font-weight: 700;"
                "font-size: 12px;"
            )

    def _source_name(self, source: str, t) -> str:
        if source == "PATH":
            return t("settings.source_path")
        if source in {"managed", "bundled"}:
            return t("settings.source_bundled")
        return t("settings.source_missing")

    def _on_check_update(self) -> None:
        t = self._i18n.get_text
        status = check_binaries()
        if not status.ytdlp_exists or status.ytdlp_path is None:
            QMessageBox.warning(self, t("app.name"), t("settings.no_ytdlp"))
            return

        result = check_for_updates(status.ytdlp_path)
        if result.update_available:
            reply = QMessageBox.question(
                self,
                t("app.name"),
                t("settings.update_available").format(
                    current=result.current_version,
                    latest=result.latest_version,
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                from videcook.services.update_checker import prepare_ytdlp_update, perform_update
                ok, msg = perform_update(prepare_ytdlp_update(status.ytdlp_path))
                if ok:
                    QMessageBox.information(self, t("app.name"), t("settings.update_ok"))
                else:
                    QMessageBox.warning(
                        self, t("app.name"),
                        t("settings.update_failed").format(message=msg),
                    )
                self.retranslate()
        else:
            QMessageBox.information(
                self,
                t("app.name"),
                self._format_update_message(result),
            )

    def _on_advanced_changed(self, text: str) -> None:
        prefs = load_preferences()
        prefs.advanced_args = text.strip()
        save_preferences(prefs)

    def _on_theme_changed(self, theme_key: str) -> None:
        from PySide6.QtWidgets import QApplication

        theme_key = normalize_theme_key(theme_key)
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, theme_key)
        # Update checked state on swatches
        for i, key in enumerate(THEME_KEYS):
            self._theme_swatches[i].setChecked(key == theme_key)
        # Persist
        prefs = load_preferences()
        prefs.theme = theme_key
        save_preferences(prefs)

    def _save_groq_key(self) -> None:
        try:
            save_groq_api_key(self._groq_input.text())
        except Exception as exc:
            QMessageBox.warning(self, self._i18n.get_text("app.name"), str(exc))
            return
        self._groq_input.clear()
        self._groq_status.setText(self._i18n.get_text("settings.groq_saved"))

    def _remove_groq_key(self) -> None:
        remove_groq_api_key()
        self._groq_input.clear()
        self._groq_status.setText(self._i18n.get_text("settings.groq_not_saved"))

    def _format_update_message(self, result) -> str:
        t = self._i18n.get_text
        template = t(result.message)
        if template == result.message:
            return result.message
        return template.format(
            current=result.current_version,
            latest=result.latest_version,
            message=result.detail,
        )

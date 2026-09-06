"""Main window for Videcook — sidebar navigation, stacked pages, language toggle."""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from videcook.services.binary_locator import check_binaries
from videcook.ui.converter_page import ConverterPage
from videcook.ui.edit_page import EditPage
from videcook.ui.history_page import HistoryPage
from videcook.ui.upscayl_page import UpscaylPage
from videcook.ui.download_page import DownloadPage
from videcook.ui.help_page import HelpPage
from videcook.ui.settings_page import SettingsPage
from videcook.ui.setup_wizard import SetupWizard
from videcook.ui.subtitle_page import SubtitlePage
from videcook.ui.subtitle_translate_hub import SubtitlesTranslateHubPage
from videcook.ui.theme import apply_theme
from videcook.ui.translate_page import TranslatePage
from videcook.utils.i18n import LanguageManager
from videcook.utils.preferences import load_preferences, save_preferences
from videcook import __version__


class MainWindow(QMainWindow):
    """Primary application window with sidebar nav and stacked content pages."""

    MIN_SIZE = QSize(1200, 760)

    # Index constants for the stacked widget
    PAGE_SETUP = 0
    PAGE_DOWNLOAD = 1
    PAGE_TRANSLATE_HUB = 2
    PAGE_SUBTITLES = 2  # Compatibility alias
    PAGE_TRANSLATE = 2  # Compatibility alias
    PAGE_CONVERTER = 3
    PAGE_EDIT = 4
    PAGE_UPSCAYL = 5
    PAGE_HISTORY = 6
    PAGE_SETTINGS = 7
    PAGE_HELP = 8

    binaries_ready = Signal()

    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._setup_needed = False
        self.setWindowTitle(i18n.get_text("app.name"))
        self.setMinimumSize(self.MIN_SIZE)
        self.resize(self.MIN_SIZE)

        self._build_ui()
        self.retranslate()

        if self._setup_needed:
            self._show_page(self.PAGE_SETUP)
        else:
            self._show_page(self.PAGE_DOWNLOAD)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- Sidebar ----
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(248)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(14, 18, 14, 18)
        sb_layout.setSpacing(10)
        sb_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Hidden brand labels — kept so retranslate() doesn't break
        self._sidebar_title = QLabel()
        self._sidebar_title.setVisible(False)
        self._sidebar_hint = QLabel()
        self._sidebar_hint.setVisible(False)

        self._nav_buttons: list[QPushButton] = []
        for idx in range(8):
            btn = QPushButton()
            btn.setObjectName("sidebarButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if idx == 0:
                btn.clicked.connect(self._on_download_nav)
            elif idx == 1:
                btn.clicked.connect(lambda _checked=False: self._show_page(self.PAGE_TRANSLATE_HUB))
            elif idx == 2:
                btn.clicked.connect(lambda _checked=False: self._show_page(self.PAGE_CONVERTER))
            elif idx == 3:
                btn.clicked.connect(lambda _checked=False: self._show_page(self.PAGE_EDIT))
            elif idx == 4:
                btn.clicked.connect(lambda _checked=False: self._show_page(self.PAGE_UPSCAYL))
            elif idx == 5:
                btn.clicked.connect(lambda _checked=False: self._show_page(self.PAGE_HISTORY))
            elif idx == 6:
                btn.clicked.connect(lambda _checked=False: self._show_page(self.PAGE_SETTINGS))
            else:
                btn.clicked.connect(lambda _checked=False: self._show_page(self.PAGE_HELP))
            sb_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        sb_layout.addStretch(1)

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 0, 0, 0)
        footer_row.setSpacing(8)

        self._sidebar_footer = QLabel()
        self._sidebar_footer.setObjectName("sidebarFooter")
        self._sidebar_footer.setWordWrap(True)
        footer_row.addWidget(self._sidebar_footer, stretch=1)

        self._lang_toggle = QPushButton()
        self._lang_toggle.setObjectName("langToggle")
        self._lang_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lang_toggle.setFixedSize(58, 30)
        self._lang_toggle.clicked.connect(self._toggle_language)
        footer_row.addWidget(self._lang_toggle)

        sb_layout.addLayout(footer_row)

        outer.addWidget(sidebar)

        # ---- Content area ----
        right = QWidget()
        right.setObjectName("contentRoot")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Hidden labels — kept so retranslate() doesn't break
        self._app_title = QLabel()
        self._app_title.setVisible(False)
        self._app_tagline = QLabel()
        self._app_tagline.setVisible(False)

        # Determine if setup is needed
        status = check_binaries()
        self._setup_needed = not status.is_ready

        # Stacked pages
        self._stack = QStackedWidget()

        self._setup_wizard = SetupWizard(self._i18n)
        self._setup_wizard.binaries_ready = self.binaries_ready
        self.binaries_ready.connect(self._on_binaries_ready)

        self._download_page = DownloadPage(self._i18n)
        self._translate_hub_page = SubtitlesTranslateHubPage(self._i18n)
        self._subtitle_page = self._translate_hub_page._subtitle_page
        self._translate_page = self._translate_hub_page._translate_page
        self._converter_page = ConverterPage(self._i18n)
        self._edit_page = EditPage(self._i18n)
        self._upscayl_page = UpscaylPage(self._i18n)
        self._history_page = HistoryPage(self._i18n)
        self._settings_page = SettingsPage(self._i18n)
        self._help_page = HelpPage(self._i18n)

        self._stack.addWidget(self._setup_wizard)         # index 0 (PAGE_SETUP)
        self._stack.addWidget(self._download_page)        # index 1 (PAGE_DOWNLOAD)
        self._stack.addWidget(self._translate_hub_page)   # index 2 (PAGE_TRANSLATE_HUB)
        self._stack.addWidget(self._converter_page)       # index 3 (PAGE_CONVERTER)
        self._stack.addWidget(self._edit_page)            # index 4 (PAGE_EDIT)
        self._stack.addWidget(self._upscayl_page)         # index 5 (PAGE_UPSCAYL)
        self._stack.addWidget(self._history_page)         # index 6 (PAGE_HISTORY)
        self._stack.addWidget(self._settings_page)        # index 7 (PAGE_SETTINGS)
        self._stack.addWidget(self._help_page)            # index 8 (PAGE_HELP)

        right_layout.addWidget(self._stack, stretch=1)
        outer.addWidget(right, stretch=1)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _show_page(self, index: int) -> None:
        """Show a page. Skips download page if setup is still needed."""
        if index == self.PAGE_DOWNLOAD and self._setup_needed:
            index = self.PAGE_SETUP

        self._stack.setCurrentIndex(index)

        is_setup = index == self.PAGE_SETUP
        for i, btn in enumerate(self._nav_buttons):
            btn.setVisible(not is_setup)
            if not is_setup:
                btn.setChecked(i == max(0, index - 1))

    def _on_download_nav(self) -> None:
        if self._setup_needed:
            self._show_page(self.PAGE_SETUP)
        else:
            self._show_page(self.PAGE_DOWNLOAD)

    def _on_binaries_ready(self) -> None:
        self._setup_needed = False
        t = self._i18n.get_text
        self._show_page(self.PAGE_DOWNLOAD)
        QMessageBox.information(
            self,
            t("app.name"),
            t("setup.ready_message"),
        )

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------

    def _toggle_language(self) -> None:
        current = self._i18n.current_language
        new_lang = "en" if current == "tr" else "tr"
        self._i18n.set_language(new_lang)
        prefs = load_preferences()
        prefs.language = new_lang
        save_preferences(prefs)
        self.retranslate()

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self.setWindowTitle(t("app.name"))
        self._app_title.setText(t("app.name"))
        self._app_tagline.setText(t("app.tagline"))
        self._sidebar_title.setText(t("app.name"))
        self._sidebar_hint.setText(t("app.tagline"))
        self._sidebar_footer.setText(f"v{__version__}")

        nav_labels = [
            "nav.download",
            "nav.translate",
            "nav.converter",
            "nav.edit",
            "nav.upscale",
            "nav.history",
            "nav.settings",
            "nav.help",
        ]
        for btn, key in zip(self._nav_buttons, nav_labels):
            btn.setText(t(key))

        lang_text = "EN" if self._i18n.current_language == "tr" else "TR"
        self._lang_toggle.setText(lang_text)

        self._setup_wizard.set_i18n(self._i18n)
        self._download_page.set_i18n(self._i18n)
        self._translate_hub_page.set_i18n(self._i18n)
        self._help_page.set_i18n(self._i18n)
        self._converter_page.set_i18n(self._i18n)
        self._edit_page.retranslate()
        self._upscayl_page.set_i18n(self._i18n)
        self._history_page.set_i18n(self._i18n)
        self._settings_page.set_i18n(self._i18n)

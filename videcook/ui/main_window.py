"""Main window for Videcook — sidebar navigation, stacked pages, language toggle."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from videcook.ui.download_page import DownloadPage
from videcook.ui.help_page import HelpPage
from videcook.ui.settings_page import SettingsPage
from videcook.utils.i18n import LanguageManager


class MainWindow(QMainWindow):
    """Primary application window with sidebar nav and stacked content pages."""

    MIN_SIZE = QSize(1200, 760)

    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self.setWindowTitle(i18n.get_text("app.name"))
        self.setMinimumSize(self.MIN_SIZE)
        self.resize(self.MIN_SIZE)

        self._build_ui()
        self.retranslate()
        self._show_page(0)

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
        sidebar.setFixedWidth(220)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(8, 16, 8, 16)
        sb_layout.setSpacing(6)
        sb_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._nav_buttons: list[QPushButton] = []
        for idx in range(3):
            btn = QPushButton()
            btn.setObjectName("sidebarButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, i=idx: self._show_page(i))  # type: ignore[misc]
            sb_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        sb_layout.addStretch(1)
        outer.addWidget(sidebar)

        # ---- Content area ----
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(90)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(32, 0, 32, 0)
        hl.setSpacing(16)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self._app_title = QLabel()
        self._app_title.setObjectName("appTitle")
        self._app_tagline = QLabel()
        self._app_tagline.setObjectName("appTagline")
        title_col.addWidget(self._app_title)
        title_col.addWidget(self._app_tagline)
        hl.addLayout(title_col)
        hl.addStretch(1)

        self._lang_toggle = QPushButton()
        self._lang_toggle.setObjectName("langToggle")
        self._lang_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lang_toggle.setFixedSize(72, 44)
        self._lang_toggle.clicked.connect(self._toggle_language)
        hl.addWidget(self._lang_toggle)

        right_layout.addWidget(header)

        # Stacked pages
        self._stack = QStackedWidget()
        self._download_page = DownloadPage(self._i18n)
        self._help_page = HelpPage(self._i18n)
        self._settings_page = SettingsPage(self._i18n)

        self._stack.addWidget(self._download_page)
        self._stack.addWidget(self._help_page)
        self._stack.addWidget(self._settings_page)

        right_layout.addWidget(self._stack, stretch=1)
        outer.addWidget(right, stretch=1)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _show_page(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------

    def _toggle_language(self) -> None:
        current = self._i18n.current_language
        new_lang = "en" if current == "tr" else "tr"
        self._i18n.set_language(new_lang)
        self.retranslate()

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self.setWindowTitle(t("app.name"))
        self._app_title.setText(t("app.name"))
        self._app_tagline.setText(t("app.tagline"))

        nav_labels = ["nav.download", "nav.help", "nav.settings"]
        for btn, key in zip(self._nav_buttons, nav_labels):
            btn.setText(t(key))

        lang_text = "EN" if self._i18n.current_language == "tr" else "TR"
        self._lang_toggle.setText(lang_text)

        self._download_page.set_i18n(self._i18n)
        self._help_page.set_i18n(self._i18n)
        self._settings_page.set_i18n(self._i18n)

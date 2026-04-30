"""QApplication bootstrap for Videcook."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from videcook.ui.main_window import MainWindow
from videcook.ui.theme import apply_theme
from videcook.utils.i18n import LanguageManager


def create_app(argv: list[str] | None = None) -> QApplication:
    """Create and configure the QApplication."""
    if argv is None:
        argv = sys.argv
    app = QApplication(argv)
    app.setApplicationName("Videcook")
    app.setApplicationDisplayName("Videcook")
    app.setOrganizationName("videcook")

    # Enable high-DPI scaling
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    apply_theme(app)
    return app


def run_app() -> int:
    """Run the full GUI application and return the exit code."""
    app = create_app()
    i18n = LanguageManager()
    window = MainWindow(i18n)
    window.show()
    return app.exec()

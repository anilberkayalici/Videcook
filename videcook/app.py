"""QApplication bootstrap for Videcook."""

import logging
import sys
import traceback
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from videcook.paths import get_asset_path, get_user_data_dir
from videcook.ui.main_window import MainWindow
from videcook.ui.theme import apply_theme
from videcook.utils.i18n import LanguageManager


def _setup_logging() -> None:
    """Configure file logging in Videcook's writable user data directory."""
    log_path = get_user_data_dir() / "videcook.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )
    logging.info("Videcook starting — log session %s", datetime.now().isoformat())


def _excepthook(exc_type, exc_value, exc_tb):
    """Log unhandled exceptions to the log file."""
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.critical("Unhandled exception:\n%s", msg)
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = _excepthook


def create_app(argv: list[str] | None = None) -> QApplication:
    """Create and configure the QApplication."""
    _setup_logging()
    if argv is None:
        argv = sys.argv
    app = QApplication(argv)
    app.setApplicationName("Videcook")
    app.setApplicationDisplayName("Videcook")
    app.setOrganizationName("videcook")

    # Application icon (taskbar, Alt+Tab, title bar)
    icon_path = get_asset_path("videcook.ico")
    app.setWindowIcon(QIcon(str(icon_path)))

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

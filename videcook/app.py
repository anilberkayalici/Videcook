"""QApplication bootstrap for Videcook."""

import logging
import os
import sys
import traceback
import webbrowser
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from videcook.paths import get_asset_path, get_user_data_dir
from videcook.ui.main_window import MainWindow
from videcook.ui.theme import apply_theme
from videcook.utils.i18n import LanguageManager
from videcook.utils.preferences import load_preferences


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

    apply_theme(app, load_preferences().theme)
    return app


def run_app() -> int:
    """Run the full GUI application and return the exit code."""
    app = create_app()
    i18n = LanguageManager()
    window = MainWindow(i18n)
    window.showMaximized()

    # Fire the update check half a second after the window appears so
    # startup feels instant regardless of network speed.
    QTimer.singleShot(500, lambda: _check_app_update(window, i18n))

    return app.exec()


def _check_app_update(window: MainWindow, i18n: LanguageManager) -> None:
    """Query GitHub for a newer Videcook release; show a dialog if found."""
    from videcook.services.app_updater import check_for_app_update

    result = check_for_app_update()
    if result is None or not result.update_available:
        return

    t = i18n.get_text
    reply = QMessageBox.question(
        window,
        t("app.name"),
        t("app.update_available").format(
            current=result.current_version,
            latest=result.latest_version,
        ),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply == QMessageBox.StandardButton.Yes:
        webbrowser.open(
            "https://github.com/anilberkayalici/Videcook/releases"
        )

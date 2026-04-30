"""Lightweight UI smoke tests for Videcook.

These tests instantiate PySide6 widgets via pytest-qt but do not
open long-lived windows or call external binaries.
"""

import pytest

pytest.importorskip("PySide6")

from videcook.ui.main_window import MainWindow
from videcook.utils.i18n import LanguageManager


@pytest.fixture
def lm() -> LanguageManager:
    return LanguageManager()


class TestMainWindow:
    def test_instantiates(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        assert window.windowTitle() == "Videcook"

    def test_default_language_turkish(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        assert lm.current_language == "tr"

    def test_language_toggle_changes_nav(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        # Default: Turkish
        assert "İndir" in window._nav_buttons[0].text()
        # Toggle to English
        window._toggle_language()
        assert lm.current_language == "en"
        assert "Download" in window._nav_buttons[0].text()
        # Toggle back
        window._toggle_language()
        assert lm.current_language == "tr"
        assert "İndir" in window._nav_buttons[0].text()


class TestDownloadPage:
    def test_controls_exist(self, qtbot, lm: LanguageManager) -> None:
        """All download-page controls should exist and have sane minimum sizes."""
        from videcook.ui.main_window import MainWindow

        window = MainWindow(lm)
        qtbot.addWidget(window)
        page = window._download_page

        assert page._url_input is not None
        assert page._url_input.objectName() == "video_url_input"
        assert page._url_input.minimumHeight() >= 34

        assert page._cookie_display is not None
        assert page._cookie_display.objectName() == "cookie_path_input"
        assert page._cookie_display.minimumHeight() >= 34

        assert page._cookie_browse is not None
        assert page._cookie_browse.objectName() == "cookie_browse_button"
        assert page._cookie_browse.minimumWidth() >= 80
        assert page._cookie_browse.minimumHeight() >= 34

        assert page._out_display is not None
        assert page._out_display.objectName() == "output_path_input"
        assert page._out_display.minimumHeight() >= 34

        assert page._out_browse is not None
        assert page._out_browse.objectName() == "output_browse_button"
        assert page._out_browse.minimumWidth() >= 80
        assert page._out_browse.minimumHeight() >= 34

        assert page._qual_combo is not None
        assert page._qual_combo.objectName() == "quality_combo"
        assert page._qual_combo.minimumHeight() >= 34

        assert page._download_btn is not None
        assert page._download_btn.objectName() == "download_button"
        assert page._download_btn.minimumWidth() >= 100
        assert page._download_btn.minimumHeight() >= 38

        assert page._cancel_btn is not None
        assert page._cancel_btn.objectName() == "cancel_button"
        assert page._cancel_btn.minimumWidth() >= 100
        assert page._cancel_btn.minimumHeight() >= 38

        assert page._progress is not None
        assert page._progress.objectName() == "progress_bar"

        assert page._status is not None
        assert page._status.objectName() == "status_label"

        assert page._log is not None
        assert page._log.objectName() == "operation_log"

    def test_labels_localized_turkish(self, qtbot, lm: LanguageManager) -> None:
        """Labels should be in Turkish by default."""
        from videcook.ui.main_window import MainWindow

        window = MainWindow(lm)
        qtbot.addWidget(window)
        page = window._download_page

        assert "Gözat" in page._cookie_browse.text()
        assert "İndir" in page._download_btn.text()
        assert "İşlem Günlüğü" in page._log_title.text()

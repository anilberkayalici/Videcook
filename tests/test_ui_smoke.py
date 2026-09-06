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

        assert hasattr(page, "_music_analysis_btn")
        assert page._music_analysis_btn.objectName() == "musicAnalysisBtn"
        assert page._music_analysis_btn.isHidden() is True

        assert hasattr(page, "_pitch_tempo_btn")
        assert page._pitch_tempo_btn.objectName() == "pitchTempoBtn"
        assert page._pitch_tempo_btn.isHidden() is True

        # Switching to Audio mode makes both visible
        page._audio_btn.click()
        assert page._music_analysis_btn.isHidden() is False
        assert page._pitch_tempo_btn.isHidden() is False

    def test_labels_localized_turkish(self, qtbot, lm: LanguageManager) -> None:
        """Labels should be in Turkish by default."""
        from videcook.ui.main_window import MainWindow

        window = MainWindow(lm)
        qtbot.addWidget(window)
        page = window._download_page

        assert "Gözat" in page._cookie_browse.text()
        assert "İndir" in page._download_btn.text()
        assert "İşlem Günlüğü" in page._log_title.text()


class TestTranslateHubPage:
    def test_hub_switch_buttons(self, qtbot, lm: LanguageManager) -> None:
        """Hub page should default to Subtitles and allow switching to Translate."""
        from videcook.ui.main_window import MainWindow

        window = MainWindow(lm)
        qtbot.addWidget(window)
        window._show_page(MainWindow.PAGE_TRANSLATE_HUB)

        hub = window._translate_hub_page
        assert hub._sub_switch_btn.isChecked() is True
        assert hub._trans_switch_btn.isChecked() is False
        assert hub._hub_stack.currentIndex() == 0

        # Switch to Translate
        hub._trans_switch_btn.click()
        assert hub._sub_switch_btn.isChecked() is False
        assert hub._trans_switch_btn.isChecked() is True
        assert hub._hub_stack.currentIndex() == 1

        # Switch back to Subtitles
        hub._sub_switch_btn.click()
        assert hub._sub_switch_btn.isChecked() is True
        assert hub._trans_switch_btn.isChecked() is False
        assert hub._hub_stack.currentIndex() == 0


class TestEditPage:
    def test_edit_page_controls(self, qtbot, lm: LanguageManager) -> None:
        """EditPage controls and preset buttons should function correctly."""
        from videcook.ui.main_window import MainWindow

        window = MainWindow(lm)
        qtbot.addWidget(window)
        window._show_page(MainWindow.PAGE_EDIT)

        edit_page = window._edit_page
        assert edit_page._video_input is not None
        assert edit_page._prompt_input is not None
        assert edit_page._aspect_combo.count() == 4
        assert edit_page._sub_combo.count() == 4
        assert edit_page._dur_combo.count() == 3

        # Preset test
        edit_page._set_prompt_preset("Test prompt")
        assert edit_page._prompt_input.toPlainText() == "Test prompt"



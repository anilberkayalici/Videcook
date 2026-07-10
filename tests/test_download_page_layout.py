"""Download page layout tests — updated for QVBoxLayout-based form."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QScrollArea, QWidget

from videcook.core.models import DownloadType
from videcook.ui.main_window import MainWindow
from videcook.utils.i18n import LanguageManager


@pytest.fixture
def lm() -> LanguageManager:
    return LanguageManager()


class TestDownloadPageGeometry:

    def test_controls_visible(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page

        assert page._url_input.objectName() == "video_url_input"
        assert page._cookie_display.objectName() == "cookie_path_input"
        assert page._cookie_browse.objectName() == "cookie_browse_button"
        assert page._out_display.objectName() == "output_path_input"
        assert page._out_browse.objectName() == "output_browse_button"
        assert page._qual_combo.objectName() == "quality_combo"
        assert page._download_btn.objectName() == "download_button"
        assert page._cancel_btn.objectName() == "cancel_button"
        assert page._progress.objectName() == "progress_bar"
        assert page._status.objectName() == "status_label"
        assert page._log.objectName() == "operation_log"
        assert page._video_btn.objectName() == "segButton"
        assert page._audio_btn.objectName() == "segButton"

    def test_input_heights(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page
        page._members_toggle.setChecked(True)

        for name, widget in [
            ("url_input", page._url_input),
            ("output_input", page._out_display),
            ("quality_combo", page._qual_combo),
        ]:
            h = widget.height()
            assert 34 <= h <= 60, f"{name} height={h}"

        cw = page.findChild(QWidget, "cookieWrapper")
        assert cw is not None

    def test_button_sizes(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page

        assert page._download_btn.height() >= 38
        assert page._cancel_btn.height() >= 38
        assert page._video_btn.height() >= 30
        assert page._audio_btn.height() >= 30

    def test_cookie_row_toggle(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page
        cw = page.findChild(QWidget, "cookieWrapper")
        assert cw is not None
        assert not cw.isVisible()

        page._members_toggle.setChecked(True)
        assert cw.isVisible()

        page._members_toggle.setChecked(False)
        assert not cw.isVisible()

    def test_expanded_options_scroll_without_overlapping(self, qtbot, lm: LanguageManager) -> None:
        """Expanded audio and cookie options must remain reachable in a short window."""
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.resize(1200, 760)
        window.show()

        page = window._download_page
        page._audio_btn.click()
        page._members_toggle.setChecked(True)
        qtbot.wait(20)

        scroll = page.findChild(QScrollArea, "downloadScroll")
        assert scroll is not None
        assert scroll.verticalScrollBar().maximum() > 0
        assert page._cookie_wrapper.isVisible()
        assert page._auth_panel.geometry().bottom() < page._out_display.parentWidget().geometry().top()

    def test_mode_toggle_switches_format(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page

        assert page._download_type is DownloadType.VIDEO
        assert not page._embed_check.isVisible()

        page._audio_btn.click()
        assert page._download_type is DownloadType.AUDIO
        assert page._embed_check.isVisible()

        page._video_btn.click()
        assert page._download_type is DownloadType.VIDEO
        assert not page._embed_check.isVisible()

    def test_log_view_has_min_height(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page
        assert page._log.height() >= 100, f"log_view height={page._log.height()}"

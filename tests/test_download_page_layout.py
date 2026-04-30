"""Download page layout geometry tests.

These tests verify that the Download page widgets do not overlap,
are reasonably sized, and that browse buttons align with their inputs.
"""

import pytest

pytest.importorskip("PySide6")

from videcook.ui.main_window import MainWindow
from videcook.utils.i18n import LanguageManager


@pytest.fixture
def lm() -> LanguageManager:
    return LanguageManager()


class TestDownloadPageGeometry:
    """Geometric layout checks for the Download page."""

    def test_controls_visible(self, qtbot, lm: LanguageManager) -> None:
        """All key controls must be accessible via page attributes."""
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page

        # Verify object names on key widgets
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

    def test_browse_button_sizes(self, qtbot, lm: LanguageManager) -> None:
        """Browse buttons must have reasonable fixed sizes."""
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page

        assert 80 <= page._cookie_browse.width() <= 150, (
            f"cookie_browse width={page._cookie_browse.width()}"
        )
        assert 38 <= page._cookie_browse.height() <= 56, (
            f"cookie_browse height={page._cookie_browse.height()}"
        )
        assert 80 <= page._out_browse.width() <= 150, (
            f"out_browse width={page._out_browse.width()}"
        )
        assert 38 <= page._out_browse.height() <= 56, (
            f"out_browse height={page._out_browse.height()}"
        )

    def test_input_heights(self, qtbot, lm: LanguageManager) -> None:
        """Inputs must have reasonable heights."""
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page

        for name, widget in [
            ("url_input", page._url_input),
            ("cookie_input", page._cookie_display),
            ("output_input", page._out_display),
            ("quality_combo", page._qual_combo),
        ]:
            h = widget.height()
            assert 34 <= h <= 60, f"{name} height={h}"

    def test_button_sizes(self, qtbot, lm: LanguageManager) -> None:
        """Download and cancel buttons must be reasonably sized."""
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page

        assert page._download_btn.width() >= 100
        assert page._download_btn.height() >= 38
        assert page._cancel_btn.width() >= 100
        assert page._cancel_btn.height() >= 38

    def test_browse_button_right_of_input(self, qtbot, lm: LanguageManager) -> None:
        """Browse buttons must be to the right of their corresponding inputs."""
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page

        cr = page._cookie_browse.geometry().x()
        ci = page._cookie_display.geometry().x()
        assert cr > ci, "cookie_browse should be right of cookie_input"

        orr = page._out_browse.geometry().x()
        oi = page._out_display.geometry().x()
        assert orr > oi, "out_browse should be right of output_input"

    def test_controls_no_overlap(self, qtbot, lm: LanguageManager) -> None:
        """Controls in consecutive rows must not overlap."""
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page

        def bottom(w):
            return w.geometry().y() + w.geometry().height()

        # row1_url → row2_cookie
        assert bottom(page._url_input) <= page._cookie_display.geometry().y() + 6
        # row2_cookie → row3_output
        assert bottom(page._cookie_display) <= page._out_display.geometry().y() + 6
        # row3_output → row4_quality
        assert bottom(page._out_display) <= page._qual_combo.geometry().y() + 6

    def test_no_absurd_heights(self, qtbot, lm: LanguageManager) -> None:
        """No form control should be taller than 80px."""
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page

        for name, widget in [
            ("url_input", page._url_input),
            ("cookie_input", page._cookie_display),
            ("output_input", page._out_display),
            ("quality_combo", page._qual_combo),
            ("cookie_browse_button", page._cookie_browse),
            ("output_browse_button", page._out_browse),
            ("download_button", page._download_btn),
            ("cancel_button", page._cancel_btn),
        ]:
            assert widget.height() <= 80, f"{name} too tall: {widget.height()}"

    def test_log_view_has_min_height(self, qtbot, lm: LanguageManager) -> None:
        """Log view must have at least 100px height."""
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page
        assert page._log.height() >= 100, f"log_view height={page._log.height()}"

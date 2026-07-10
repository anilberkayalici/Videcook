"""Regression tests for the settings page's vertical layout."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QScrollArea

from videcook.ui.main_window import MainWindow
from videcook.utils.i18n import LanguageManager


def test_settings_scrolls_instead_of_compressing_controls(qtbot) -> None:
    window = MainWindow(LanguageManager())
    qtbot.addWidget(window)
    window.resize(1200, 760)
    window.show()
    window._show_page(MainWindow.PAGE_SETTINGS)
    qtbot.wait(20)

    page = window._settings_page
    scroll = page.findChild(QScrollArea, "settingsScroll")

    assert scroll is not None
    assert scroll.verticalScrollBar().maximum() > 0
    assert page._save_groq_btn.geometry().top() > page._groq_input.geometry().bottom()
    assert page._save_groq_btn.height() >= 38
    assert page._remove_groq_btn.height() >= 38

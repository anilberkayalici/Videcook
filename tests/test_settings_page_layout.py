"""Regression tests for the settings page's vertical layout."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QCheckBox, QScrollArea

from videcook.ui.main_window import MainWindow
from videcook.ui.theme import (
    THEME_KEYS,
    THEMES,
    build_theme_swatch_stylesheet,
    normalize_theme_key,
)
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


def test_theme_swatches_use_calm_split_gradients() -> None:
    """Theme picker previews should use the dedicated muted swatch colours."""
    assert len(THEME_KEYS) == 5

    for theme_key in THEME_KEYS:
        palette = THEMES[theme_key]
        stylesheet = build_theme_swatch_stylesheet(palette)

        assert "qlineargradient(x1:0, y1:0, x2:1, y2:1" in stylesheet
        assert f"stop:0 {palette['swatch_start']}" in stylesheet
        assert f"stop:0.46 {palette['swatch_start']}" in stylesheet
        assert f"stop:0.52 {palette['swatch_blend']}" in stylesheet
        assert f"stop:1 {palette['swatch_end']}" in stylesheet
        assert f"border-color: {palette['swatch_ring']}" in stylesheet


def test_legacy_theme_key_maps_to_visible_theme() -> None:
    assert normalize_theme_key("monokai") == "dracula"
    assert normalize_theme_key("unknown-theme") == THEME_KEYS[0]

"""Tests for the i18n localization module."""

import pytest

from videcook.utils.i18n import LanguageError, LanguageManager


class TestLanguageManager:
    def test_default_language_is_turkish(self) -> None:
        lm = LanguageManager()
        assert lm.current_language == "tr"

    def test_switch_to_english(self) -> None:
        lm = LanguageManager()
        lm.set_language("en")
        assert lm.current_language == "en"

    def test_invalid_language_raises_error(self) -> None:
        lm = LanguageManager()
        with pytest.raises(LanguageError):
            lm.set_language("de")

    def test_get_text_returns_turkish_by_default(self) -> None:
        lm = LanguageManager()
        assert lm.get_text("app.name") == "Videcook"
        assert lm.get_text("action.download") == "İndir"

    def test_get_text_returns_english_after_switch(self) -> None:
        lm = LanguageManager()
        lm.set_language("en")
        assert lm.get_text("action.download") == "Download"
        assert lm.get_text("action.cancel") == "Cancel"

    def test_missing_key_falls_back_to_english(self) -> None:
        lm = LanguageManager()
        # Inject a key that only exists in English, simulating a drift scenario
        lm._translations["en"]["_test_only_en"] = "Only English"
        result = lm.get_text("_test_only_en")
        assert result == "Only English"

    def test_fully_missing_key_returns_key_itself(self) -> None:
        lm = LanguageManager()
        assert lm.get_text("nonexistent.key.xyz") == "nonexistent.key.xyz"

    def test_has_key(self) -> None:
        lm = LanguageManager()
        assert lm.has_key("app.name") is True
        assert lm.has_key("nonexistent") is False

    def test_available_languages(self) -> None:
        langs = LanguageManager.available_languages()
        assert "tr" in langs
        assert "en" in langs

    def test_all_keys_match_between_languages(self) -> None:
        """Every key in tr.json must exist in en.json and vice versa."""
        lm = LanguageManager()
        tr_keys = set(lm._translations["tr"].keys())
        en_keys = set(lm._translations["en"].keys())

        tr_only = tr_keys - en_keys
        en_only = en_keys - tr_keys

        assert not tr_only, f"Keys only in tr.json: {tr_only}"
        assert not en_only, f"Keys only in en.json: {en_only}"

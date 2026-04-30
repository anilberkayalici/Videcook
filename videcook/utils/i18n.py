"""Internationalization (i18n) module for Videcook.

Provides a LanguageManager that loads localized strings from JSON files
in the project-level locales/ directory. Supports Turkish (default) and English.
"""

import json
from pathlib import Path

SUPPORTED_LANGUAGES = ("tr", "en")
DEFAULT_LANGUAGE = "tr"
FALLBACK_LANGUAGE = "en"


class LanguageError(Exception):
    """Raised when an invalid or unsupported language code is used."""


class LanguageManager:
    """Manages localized UI strings for Videcook.

    Loads translations from JSON files at startup. Falls back from
    current language → English → raw key on missing lookups.
    """

    def __init__(self, locales_dir: str | Path | None = None) -> None:
        self._translations: dict[str, dict[str, str]] = {}
        self._current_language = DEFAULT_LANGUAGE

        if locales_dir is None:
            locales_dir = Path(__file__).resolve().parent.parent.parent / "locales"
        self._locales_dir = Path(locales_dir)

        for lang in SUPPORTED_LANGUAGES:
            filepath = self._locales_dir / f"{lang}.json"
            with open(filepath, encoding="utf-8") as f:
                self._translations[lang] = json.load(f)

    @property
    def current_language(self) -> str:
        """Return the currently active language code."""
        return self._current_language

    def set_language(self, language_code: str) -> None:
        """Switch to a supported language.

        Raises:
            LanguageError: If the language code is not in SUPPORTED_LANGUAGES.
        """
        if language_code not in SUPPORTED_LANGUAGES:
            raise LanguageError(
                f"Unsupported language: '{language_code}'. "
                f"Supported: {', '.join(SUPPORTED_LANGUAGES)}"
            )
        self._current_language = language_code

    def get_text(self, key: str) -> str:
        """Return localized text for *key*.

        Resolution order:
        1. Current language
        2. English (fallback)
        3. Raw key (last resort)
        """
        translation = self._translations.get(self._current_language, {})
        if key in translation:
            return translation[key]

        fallback = self._translations.get(FALLBACK_LANGUAGE, {})
        if key in fallback:
            return fallback[key]

        return key

    def has_key(self, key: str) -> bool:
        """Check whether *key* exists in the current language."""
        return key in self._translations.get(self._current_language, {})

    @staticmethod
    def available_languages() -> tuple[str, ...]:
        """Return the tuple of supported language codes."""
        return SUPPORTED_LANGUAGES

"""Tests for videcook.utils.preferences.

Critical: older preference files (without h264_compat_mode and
format_cache) must still load correctly with sensible defaults.
"""

import json
from pathlib import Path

from videcook.utils.preferences import UserPreferences, load_preferences, save_preferences


class TestLoadPreferences:
    def test_missing_file_returns_defaults(self, tmp_path: Path, monkeypatch) -> None:
        # Force the prefs path to a non-existent location.
        from videcook.utils import preferences as prefs_mod

        fake_path = tmp_path / "nope" / "prefs.json"

        def _fake_path() -> Path:
            return fake_path

        monkeypatch.setattr(prefs_mod, "_prefs_path", _fake_path)
        result = load_preferences()
        assert isinstance(result, UserPreferences)
        assert result.language == "tr"
        # Default for the new field must be True (H.264 compat on by default).
        assert result.h264_compat_mode is True
        assert result.format_cache == {}

    def test_old_format_file_loads_with_new_defaults(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from videcook.utils import preferences as prefs_mod

        fake_path = tmp_path / "prefs.json"
        # An "old" prefs file that doesn't have h264_compat_mode or
        # format_cache. This simulates a user upgrading from v0.2.0.
        old_data = {
            "language": "en",
            "last_output_folder": "",
            "last_quality": "quality.best",
            "last_audio_format": "audio_format.mp3",
            "embed_thumbnail": True,
            "advanced_args": "",
        }
        fake_path.write_text(json.dumps(old_data), encoding="utf-8")

        monkeypatch.setattr(prefs_mod, "_prefs_path", lambda: fake_path)
        result = load_preferences()
        assert result.language == "en"
        # Missing fields must default, not raise.
        assert result.h264_compat_mode is True
        assert result.format_cache == {}

    def test_corrupt_file_returns_defaults(self, tmp_path: Path, monkeypatch) -> None:
        from videcook.utils import preferences as prefs_mod

        fake_path = tmp_path / "prefs.json"
        fake_path.write_text("not valid json {{{", encoding="utf-8")

        monkeypatch.setattr(prefs_mod, "_prefs_path", lambda: fake_path)
        result = load_preferences()
        # Should not raise; should return defaults.
        assert result.h264_compat_mode is True
        assert result.format_cache == {}

    def test_round_trip(self, tmp_path: Path, monkeypatch) -> None:
        from videcook.utils import preferences as prefs_mod

        fake_path = tmp_path / "prefs.json"

        monkeypatch.setattr(prefs_mod, "_prefs_path", lambda: fake_path)
        prefs = UserPreferences(
            language="en",
            h264_compat_mode=False,
            format_cache={"https://x.com/v=1": "137"},
        )
        save_preferences(prefs)

        loaded = load_preferences()
        assert loaded.h264_compat_mode is False
        assert loaded.format_cache == {"https://x.com/v=1": "137"}

    def test_format_cache_is_capped(self, tmp_path: Path, monkeypatch) -> None:
        from videcook.utils import preferences as prefs_mod

        fake_path = tmp_path / "prefs.json"
        monkeypatch.setattr(prefs_mod, "_prefs_path", lambda: fake_path)

        # Build a cache far larger than the cap.
        big_cache = {f"https://x.com/v={i}": str(i) for i in range(100)}
        prefs = UserPreferences(format_cache=big_cache)
        save_preferences(prefs)

        loaded = load_preferences()
        # Capped to _CACHE_MAX_ENTRIES.
        assert len(loaded.format_cache) == prefs_mod._CACHE_MAX_ENTRIES

"""Tests for edit prompt preset manager and storage."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import pytest

from videcook.core.preset_manager import (
    DEFAULT_PRESETS,
    add_edit_preset,
    delete_edit_preset,
    get_edit_presets,
    move_edit_preset,
    save_edit_presets,
)


def test_get_edit_presets_returns_defaults_or_saved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_file = tmp_path / "edit_presets.json"
    monkeypatch.setattr("videcook.core.preset_manager.get_presets_file_path", lambda: test_file)

    # Initial load creates file with defaults
    presets = get_edit_presets()
    assert len(presets) >= 4
    assert test_file.is_file()

    # Add custom preset
    ok = add_edit_preset("Custom Test", "Test prompt description")
    assert ok is True

    updated = get_edit_presets()
    assert any(p["name"] == "Custom Test" for p in updated)


def test_delete_and_move_preset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_file = tmp_path / "edit_presets.json"
    monkeypatch.setattr("videcook.core.preset_manager.get_presets_file_path", lambda: test_file)

    presets = [
        {"name": "P1", "prompt": "Prompt 1"},
        {"name": "P2", "prompt": "Prompt 2"},
        {"name": "P3", "prompt": "Prompt 3"},
    ]
    save_edit_presets(presets)

    # Move P3 to top
    move_edit_preset(2, 0)
    current = get_edit_presets()
    assert current[0]["name"] == "P3"
    assert current[1]["name"] == "P1"

    # Delete first
    delete_edit_preset(0)
    current2 = get_edit_presets()
    assert len(current2) == 2
    assert current2[0]["name"] == "P1"

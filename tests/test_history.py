"""Tests for download history service and history page."""

import json
from pathlib import Path

import pytest

from videcook.services.history_service import (
    HistoryItem,
    add_history_entry,
    clear_history_entries,
    delete_history_entry,
    load_history,
    save_history,
)
from videcook.utils.i18n import LanguageManager


def test_add_and_load_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_file = tmp_path / "test_history.json"
    monkeypatch.setattr("videcook.services.history_service._history_file_path", lambda: test_file)

    assert load_history() == []

    item = add_history_entry(
        title="Test Video",
        file_path=str(tmp_path / "test.mp4"),
        file_size_bytes=1048576,
        duration_seconds=120,
        download_type="video",
        format_label="VIDEO: 1080p - MP4",
        url="https://youtube.com/watch?v=123",
    )

    items = load_history()
    assert len(items) == 1
    assert items[0].title == "Test Video"
    assert items[0].formatted_size() == "1.00 MB"
    assert items[0].formatted_duration() == "02m:00s"
    assert items[0].download_type == "video"


def test_delete_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_file = tmp_path / "test_history.json"
    monkeypatch.setattr("videcook.services.history_service._history_file_path", lambda: test_file)

    target_media = tmp_path / "media.mp4"
    target_media.write_text("dummy")

    item = add_history_entry(
        title="Delete Me",
        file_path=str(target_media),
        file_size_bytes=5,
    )

    assert target_media.exists()
    assert len(load_history()) == 1

    # Delete with file
    deleted = delete_history_entry(item.id, delete_file=True)
    assert deleted
    assert not target_media.exists()
    assert len(load_history()) == 0


def test_clear_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_file = tmp_path / "test_history.json"
    monkeypatch.setattr("videcook.services.history_service._history_file_path", lambda: test_file)

    add_history_entry(title="Item 1", file_path="path1")
    add_history_entry(title="Item 2", file_path="path2")
    assert len(load_history()) == 2

    clear_history_entries(delete_files=False)
    assert len(load_history()) == 0


def test_history_page_ui(qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_file = tmp_path / "test_history.json"
    monkeypatch.setattr("videcook.services.history_service._history_file_path", lambda: test_file)

    add_history_entry(title="My Video", file_path="my_video.mp4", format_label="1080p")
    add_history_entry(title="My Audio", file_path="my_audio.mp3", download_type="audio", format_label="MP3")

    lm = LanguageManager()
    from videcook.ui.history_page import HistoryPage

    page = HistoryPage(lm)
    qtbot.addWidget(page)
    page.show()

    page._load_and_refresh()
    assert page._list_widget.count() == 2

    # Search filter
    page._search_input.setText("audio")
    assert page._list_widget.count() == 1

    page._search_input.clear()
    assert page._list_widget.count() == 2

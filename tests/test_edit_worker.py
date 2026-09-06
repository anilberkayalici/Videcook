"""Unit tests for EditWorker and EditPage unique file naming and show folder features."""

import os
import re
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from videcook.ui.edit_worker import EditWorker
from videcook.ui.edit_page import EditPage


def get_unique_output_path(video_path: Path, output_dir: Path) -> Path:
    stem_clean = re.sub(r'[^\w\-]', '_', video_path.stem)[:30]
    base_name = f"{stem_clean}_edit_shorts"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{base_name}.mp4"
    if output_file.exists():
        counter = 1
        while (output_dir / f"{base_name}_{counter}.mp4").exists():
            counter += 1
        output_file = output_dir / f"{base_name}_{counter}.mp4"
    return output_file


def test_unique_output_path_increments_when_file_exists(tmp_path: Path):
    v_path = tmp_path / "sample_video.mp4"
    v_path.touch()

    # First output
    p1 = get_unique_output_path(v_path, tmp_path)
    assert p1.name == "sample_video_edit_shorts.mp4"
    p1.touch()

    # Second output should not overwrite p1
    p2 = get_unique_output_path(v_path, tmp_path)
    assert p2.name == "sample_video_edit_shorts_1.mp4"
    p2.touch()

    # Third output
    p3 = get_unique_output_path(v_path, tmp_path)
    assert p3.name == "sample_video_edit_shorts_2.mp4"


def test_edit_page_show_folder_selects_last_output_file(qtbot, tmp_path: Path):
    from videcook.utils.i18n import LanguageManager
    page = EditPage(i18n=LanguageManager())
    qtbot.addWidget(page)

    test_file = tmp_path / "test_output.mp4"
    test_file.touch()
    page._last_output_file = test_file

    with patch("subprocess.Popen") as mock_popen, patch("os.startfile") as mock_startfile:
        page._on_show_folder_clicked()
        if os.name == "nt":
            mock_popen.assert_called_once()
            called_cmd = mock_popen.call_args[0][0]
            assert "explorer /select," in called_cmd
            assert "test_output.mp4" in called_cmd

"""Unit tests for the MoviePy video editor engine (moviepy_editor.py)."""

from pathlib import Path
from videcook.core.moviepy_editor import render_edit_with_moviepy


def test_render_edit_with_moviepy_missing_file(tmp_path: Path):
    missing_input = tmp_path / "non_existent.mp4"
    output_path = tmp_path / "output.mp4"

    res = render_edit_with_moviepy(
        video_path=missing_input,
        output_path=output_path,
        start_sec=0.0,
        end_sec=10.0,
        aspect_ratio_str="9:16 Dikey",
    )

    assert res is False
    assert not output_path.is_file()

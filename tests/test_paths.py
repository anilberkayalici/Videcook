"""Tests for videcook.paths — source and frozen-mode resolution."""

import sys
from pathlib import Path

from videcook.paths import (
    get_asset_path,
    get_assets_dir,
    get_bin_dir,
    get_ffmpeg_path,
    get_ffprobe_path,
    get_project_root,
    get_ytdlp_path,
)


class TestPaths:
    def test_get_project_root_returns_directory(self) -> None:
        root = get_project_root()
        assert isinstance(root, Path)
        assert root.is_dir()

    def test_get_project_root_contains_videcook(self) -> None:
        root = get_project_root()
        assert (root / "videcook").is_dir()

    def test_bin_dir_returns_paths_subdir(self) -> None:
        bin_dir = get_bin_dir()
        assert bin_dir.name == "bin"
        assert bin_dir.parent == get_project_root()

    def test_ytdlp_path_ends_correctly(self) -> None:
        path = get_ytdlp_path()
        assert path.name == "yt-dlp.exe"
        assert path.parent == get_bin_dir()

    def test_ffmpeg_path_ends_correctly(self) -> None:
        path = get_ffmpeg_path()
        assert path.name == "ffmpeg.exe"
        assert path.parent == get_bin_dir()

    def test_ffprobe_path_ends_correctly(self) -> None:
        path = get_ffprobe_path()
        assert path.name == "ffprobe.exe"
        assert path.parent == get_bin_dir()

    def test_frozen_mode_uses_meipass(self, monkeypatch) -> None:
        """When frozen, get_project_root() returns sys._MEIPASS."""
        fake_root = Path("C:/fake/meipass")
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(fake_root), raising=False)
        assert get_project_root() == fake_root

    def test_bin_dir_does_not_require_exe_files(self) -> None:
        """get_bin_dir() returns a Path regardless of file existence."""
        bin_dir = get_bin_dir()
        assert isinstance(bin_dir, Path)


class TestAssetPaths:
    def test_assets_dir_returns_paths_subdir(self) -> None:
        assets_dir = get_assets_dir()
        assert assets_dir.name == "assets"
        assert assets_dir.parent == get_project_root()

    def test_asset_dir_exists(self) -> None:
        assert get_assets_dir().is_dir()

    def test_get_asset_path_videcook_ico(self) -> None:
        path = get_asset_path("videcook.ico")
        assert path.name == "videcook.ico"
        assert path.parent == get_assets_dir()

    def test_get_asset_path_videcook_png(self) -> None:
        path = get_asset_path("videcook.png")
        assert path.name == "videcook.png"
        assert path.parent == get_assets_dir()

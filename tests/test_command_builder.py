"""Tests for videcook.core.command_builder."""

from pathlib import Path

import pytest

from videcook.core.command_builder import build_ytdlp_command
from videcook.core.models import DownloadMode, DownloadRequest, QualityOption

_COOKIE_REDACTED = "[COOKIE_PATH_REDACTED]"


def _make_request(
    tmp_path: Path, mode: DownloadMode = DownloadMode.SINGLE_VIDEO
) -> DownloadRequest:
    cookie = tmp_path / "cookies.txt"
    cookie.touch()
    outdir = tmp_path / "videos"
    outdir.mkdir()
    return DownloadRequest(
        url="https://example.com/video?id=123",
        cookie_file=cookie,
        output_folder=outdir,
        quality=QualityOption.BEST,
        mode=mode,
    )


def _dummy_ytdlp(tmp_path: Path) -> Path:
    p = tmp_path / "yt-dlp.exe"
    p.touch()
    return p


def _dummy_ffmpeg(tmp_path: Path) -> Path:
    d = tmp_path / "ffmpeg_bin"
    d.mkdir()
    return d


class TestBuildYtdlpCommand:
    def test_returns_list_not_string(self, tmp_path: Path) -> None:
        result = build_ytdlp_command(
            _make_request(tmp_path),
            _dummy_ytdlp(tmp_path),
            _dummy_ffmpeg(tmp_path),
        )
        assert isinstance(result.args, list)
        for arg in result.args:
            assert isinstance(arg, str)

    def test_includes_cookies_arg(self, tmp_path: Path) -> None:
        result = build_ytdlp_command(
            _make_request(tmp_path),
            _dummy_ytdlp(tmp_path),
            _dummy_ffmpeg(tmp_path),
        )
        assert "--cookies" in result.args
        idx = result.args.index("--cookies")
        assert result.args[idx + 1].endswith("cookies.txt")

    def test_includes_ffmpeg_location(self, tmp_path: Path) -> None:
        ff = _dummy_ffmpeg(tmp_path)
        result = build_ytdlp_command(
            _make_request(tmp_path),
            _dummy_ytdlp(tmp_path),
            ff,
        )
        assert "--ffmpeg-location" in result.args
        idx = result.args.index("--ffmpeg-location")
        assert result.args[idx + 1] == str(ff)

    def test_includes_format_selector(self, tmp_path: Path) -> None:
        result = build_ytdlp_command(
            _make_request(tmp_path),
            _dummy_ytdlp(tmp_path),
            _dummy_ffmpeg(tmp_path),
        )
        assert "-f" in result.args

    def test_includes_mp4_merge_flags(self, tmp_path: Path) -> None:
        result = build_ytdlp_command(
            _make_request(tmp_path),
            _dummy_ytdlp(tmp_path),
            _dummy_ffmpeg(tmp_path),
        )
        assert "--merge-output-format" in result.args
        idx = result.args.index("--merge-output-format")
        assert result.args[idx + 1] == "mp4"
        assert "--remux-video" in result.args

    def test_includes_output_folder(self, tmp_path: Path) -> None:
        req = _make_request(tmp_path)
        result = build_ytdlp_command(
            req,
            _dummy_ytdlp(tmp_path),
            _dummy_ffmpeg(tmp_path),
        )
        assert "-P" in result.args
        idx = result.args.index("-P")
        assert result.args[idx + 1] == str(req.output_folder)

    def test_includes_newline_flag(self, tmp_path: Path) -> None:
        result = build_ytdlp_command(
            _make_request(tmp_path),
            _dummy_ytdlp(tmp_path),
            _dummy_ffmpeg(tmp_path),
        )
        assert "--newline" in result.args

    def test_includes_url_last(self, tmp_path: Path) -> None:
        req = _make_request(tmp_path)
        result = build_ytdlp_command(
            req,
            _dummy_ytdlp(tmp_path),
            _dummy_ffmpeg(tmp_path),
        )
        assert result.args[-1] == req.url

    def test_no_playlist_for_single_video(self, tmp_path: Path) -> None:
        result = build_ytdlp_command(
            _make_request(tmp_path, mode=DownloadMode.SINGLE_VIDEO),
            _dummy_ytdlp(tmp_path),
            _dummy_ffmpeg(tmp_path),
        )
        assert "--no-playlist" in result.args

    def test_no_playlist_absent_for_playlist_mode(self, tmp_path: Path) -> None:
        result = build_ytdlp_command(
            _make_request(tmp_path, mode=DownloadMode.PLAYLIST),
            _dummy_ytdlp(tmp_path),
            _dummy_ffmpeg(tmp_path),
        )
        assert "--no-playlist" not in result.args

    def test_redacted_display_hides_cookie(self, tmp_path: Path) -> None:
        req = _make_request(tmp_path)
        result = build_ytdlp_command(
            req, _dummy_ytdlp(tmp_path), _dummy_ffmpeg(tmp_path)
        )
        assert _COOKIE_REDACTED in result.redacted_display
        assert str(req.cookie_file) not in result.redacted_display

    def test_raises_for_missing_ytdlp(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            build_ytdlp_command(
                _make_request(tmp_path),
                ytdlp_path=tmp_path / "nonexistent.exe",
                ffmpeg_location=_dummy_ffmpeg(tmp_path),
            )

    def test_raises_for_missing_ffmpeg(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            build_ytdlp_command(
                _make_request(tmp_path),
                ytdlp_path=_dummy_ytdlp(tmp_path),
                ffmpeg_location=tmp_path / "no_ffmpeg",
            )

    def test_raises_for_invalid_url(self, tmp_path: Path) -> None:
        req = _make_request(tmp_path)
        req.url = ""
        with pytest.raises(Exception):  # ValidationError or subclass
            build_ytdlp_command(
                req,
                _dummy_ytdlp(tmp_path),
                _dummy_ffmpeg(tmp_path),
            )

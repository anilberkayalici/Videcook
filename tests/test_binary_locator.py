"""Tests for videcook.services.binary_locator."""

from videcook.services.binary_locator import BinaryStatus, check_binaries


class TestBinaryStatus:
    def test_is_ready_when_both_exist(self, tmp_path) -> None:
        yt = tmp_path / "yt-dlp.exe"
        ff = tmp_path / "ffmpeg.exe"
        yt.touch()
        ff.touch()
        status = BinaryStatus(ytdlp_path=yt, ffmpeg_path=ff, ffprobe_path=tmp_path / "ffprobe.exe")
        assert status.is_ready is True

    def test_not_ready_when_ytdlp_missing(self, tmp_path) -> None:
        ff = tmp_path / "ffmpeg.exe"
        ff.touch()
        status = BinaryStatus(
            ytdlp_path=tmp_path / "nonexistent.exe",
            ffmpeg_path=ff,
            ffprobe_path=tmp_path / "ffprobe.exe",
        )
        assert status.is_ready is False

    def test_not_ready_when_ffmpeg_missing(self, tmp_path) -> None:
        yt = tmp_path / "yt-dlp.exe"
        yt.touch()
        status = BinaryStatus(
            ytdlp_path=yt,
            ffmpeg_path=tmp_path / "nonexistent.exe",
            ffprobe_path=tmp_path / "ffprobe.exe",
        )
        assert status.is_ready is False

    def test_to_display_shows_ok_and_missing(self, tmp_path) -> None:
        yt = tmp_path / "yt-dlp.exe"
        yt.touch()
        ff = tmp_path / "ffmpeg.exe"
        ff.touch()
        status = BinaryStatus(
            ytdlp_path=yt, ffmpeg_path=ff, ffprobe_path=tmp_path / "ffprobe.exe"
        )
        display = status.to_display()
        assert "OK" in display
        assert "MISSING" in display  # ffprobe

    def test_check_binaries_returns_status(self) -> None:
        result = check_binaries()
        assert isinstance(result, BinaryStatus)

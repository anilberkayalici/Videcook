"""Tests for videcook.services.binary_locator."""

from videcook.services import binary_locator
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

    def test_managed_binary_has_priority_over_bundled(self, monkeypatch, tmp_path) -> None:
        managed = tmp_path / "managed" / "yt-dlp.exe"
        bundled = tmp_path / "bundled" / "yt-dlp.exe"
        managed.parent.mkdir()
        bundled.parent.mkdir()
        managed.touch()
        bundled.touch()

        monkeypatch.setattr(binary_locator, "find_on_path", lambda _: None)
        result = binary_locator._resolve_binary("yt-dlp", [managed, bundled], "ytdlp")

        assert result["ytdlp_path"] == managed
        assert result["ytdlp_source"] == "managed"

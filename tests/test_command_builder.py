"""Tests for videcook.core.command_builder."""

from pathlib import Path

import pytest

from videcook.core.command_builder import build_ytdlp_command
from videcook.core.models import (
    AudioFormat,
    DownloadMode,
    DownloadRequest,
    DownloadType,
    QualityOption,
)

_COOKIE_REDACTED = "[COOKIE_PATH_REDACTED]"


def _make_request(
    tmp_path: Path, mode: DownloadMode = DownloadMode.SINGLE_VIDEO
) -> DownloadRequest:
    cookie = tmp_path / "cookies.txt"
    cookie.touch()
    outdir = tmp_path / "videos"
    outdir.mkdir(exist_ok=True)
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
    d.mkdir(exist_ok=True)
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


# ---------------------------------------------------------------------------
# H.264 compatibility / dynamic format integration
# ---------------------------------------------------------------------------


class TestForceH264Transcode:
    def test_transcode_args_added_when_requested(self, tmp_path: Path) -> None:
        req = _make_request(tmp_path)
        req.force_h264_transcode = True
        result = build_ytdlp_command(
            req, _dummy_ytdlp(tmp_path), _dummy_ffmpeg(tmp_path)
        )
        assert "--postprocessor-args" in result.args
        idx = result.args.index("--postprocessor-args")
        args_value = result.args[idx + 1]
        assert "libx264" in args_value
        assert "crf 20" in args_value or "crf=20" in args_value
        assert "preset medium" in args_value or "preset=medium" in args_value
        assert "c:a copy" in args_value

    def test_no_transcode_args_when_not_requested(self, tmp_path: Path) -> None:
        req = _make_request(tmp_path)
        req.force_h264_transcode = False
        result = build_ytdlp_command(
            req, _dummy_ytdlp(tmp_path), _dummy_ffmpeg(tmp_path)
        )
        assert "--postprocessor-args" not in result.args

    def test_transcode_in_redacted_display(self, tmp_path: Path) -> None:
        req = _make_request(tmp_path)
        req.force_h264_transcode = True
        result = build_ytdlp_command(
            req, _dummy_ytdlp(tmp_path), _dummy_ffmpeg(tmp_path)
        )
        assert "postprocessor-args" in result.redacted_display
        assert "libx264" in result.redacted_display

    def test_audio_path_unaffected_by_transcode_flag(self, tmp_path: Path) -> None:
        req = _make_request(tmp_path)
        req.download_type = DownloadType.AUDIO
        req.force_h264_transcode = True  # even if someone sets it
        result = build_ytdlp_command(
            req, _dummy_ytdlp(tmp_path), _dummy_ffmpeg(tmp_path)
        )
        # Audio extraction has its own pipeline; H.264 transcode is
        # meaningless for audio-only and must not be added.
        assert "--postprocessor-args" not in result.args


class TestAudioFormatSelection:
    """Verify the --audio-format flag for every AudioFormat enum value.

    WAV and FLAC are dublajcıların (dubbing artists) kullandığı temel
    formatlar — bunların kusursuz çalıştığından emin olalım.
    """

    def _run_audio(
        self, tmp_path: Path, audio_format: AudioFormat
    ) -> list[str]:
        req = _make_request(tmp_path)
        req.download_type = DownloadType.AUDIO
        req.audio_format = audio_format
        result = build_ytdlp_command(
            req, _dummy_ytdlp(tmp_path), _dummy_ffmpeg(tmp_path)
        )
        return result.args

    def test_mp3_passes_audio_format_mp3(self, tmp_path: Path) -> None:
        args = self._run_audio(tmp_path, AudioFormat.MP3)
        idx = args.index("--audio-format")
        assert args[idx + 1] == "mp3"

    def test_opus_passes_audio_format_opus(self, tmp_path: Path) -> None:
        args = self._run_audio(tmp_path, AudioFormat.OPUS)
        idx = args.index("--audio-format")
        assert args[idx + 1] == "opus"

    def test_aac_passes_audio_format_aac(self, tmp_path: Path) -> None:
        """AAC produces an M4A container with AAC inside. The dropdown
        labels this as 'AAC (M4A)' to make that explicit."""
        args = self._run_audio(tmp_path, AudioFormat.AAC)
        idx = args.index("--audio-format")
        assert args[idx + 1] == "aac"

    def test_flac_passes_audio_format_flac(self, tmp_path: Path) -> None:
        """FLAC is lossless — critical for dubbing work where the source
        audio is re-encoded many times."""
        args = self._run_audio(tmp_path, AudioFormat.FLAC)
        idx = args.index("--audio-format")
        assert args[idx + 1] == "flac"

    def test_wav_passes_audio_format_wav(self, tmp_path: Path) -> None:
        """WAV is uncompressed PCM — the gold standard for editing."""
        args = self._run_audio(tmp_path, AudioFormat.WAV)
        idx = args.index("--audio-format")
        assert args[idx + 1] == "wav"

    def test_m4a_format_does_not_exist(self) -> None:
        """M4A was removed because yt-dlp's --audio-format aac already
        produces M4A. A separate M4A entry would be redundant."""
        assert not hasattr(AudioFormat, "M4A")

    def test_audio_quality_zero_for_lossless(self, tmp_path: Path) -> None:
        """WAV and FLAC should request the highest quality (0) from
        yt-dlp, not a lossy default."""
        for fmt in (AudioFormat.WAV, AudioFormat.FLAC):
            args = self._run_audio(tmp_path, fmt)
            idx = args.index("--audio-quality")
            assert args[idx + 1] == "0", f"{fmt.value} should use quality 0"

    def test_audio_command_uses_extract_mode(self, tmp_path: Path) -> None:
        """Audio mode always passes -x (extract audio) regardless of
        the chosen container."""
        for fmt in AudioFormat:
            args = self._run_audio(tmp_path, fmt)
            assert "-x" in args, f"{fmt.value} should use -x"

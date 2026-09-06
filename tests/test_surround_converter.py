"""Tests for 5.1 Surround Sound detection and audio conversion in Dönüştürücü."""
from pathlib import Path
from videcook.core.converter_builder import ConverterRequest, build_ffmpeg_command, probe_audio_channels


def test_build_ffmpeg_command_ac3_51() -> None:
    req = ConverterRequest(input_file=Path("movie.mkv"), output_file=Path("movie.ac3"))
    ffmpeg = Path("bin/ffmpeg.exe") if Path("bin/ffmpeg.exe").exists() else Path("ffmpeg")
    result = build_ffmpeg_command(req, ffmpeg)
    assert "-vn" in result.args
    assert "-c:a" in result.args
    assert "ac3" in result.args
    assert "640k" in result.args


def test_build_ffmpeg_command_wav_51() -> None:
    req = ConverterRequest(input_file=Path("movie.mp4"), output_file=Path("movie.wav"))
    ffmpeg = Path("bin/ffmpeg.exe") if Path("bin/ffmpeg.exe").exists() else Path("ffmpeg")
    result = build_ffmpeg_command(req, ffmpeg)
    assert "-vn" in result.args
    assert "pcm_s16le" in result.args


def test_build_ffmpeg_command_flac_51() -> None:
    req = ConverterRequest(input_file=Path("movie.mp4"), output_file=Path("movie.flac"))
    ffmpeg = Path("bin/ffmpeg.exe") if Path("bin/ffmpeg.exe").exists() else Path("ffmpeg")
    result = build_ffmpeg_command(req, ffmpeg)
    assert "-vn" in result.args
    assert "flac" in result.args


def test_probe_audio_channels_missing_file() -> None:
    channels, layout = probe_audio_channels(Path("non_existent_file.mp4"))
    assert channels == 0
    assert layout == ""


def test_get_channel_suffixes() -> None:
    from videcook.core.converter_builder import get_channel_suffixes
    assert get_channel_suffixes(6, "5.1(side)") == ["FL", "FR", "FC", "LFE", "SL", "SR"]
    assert get_channel_suffixes(8, "7.1") == ["FL", "FR", "FC", "LFE", "BL", "BR", "SL", "SR"]
    assert get_channel_suffixes(2, "stereo") == ["FL", "FR"]
    assert get_channel_suffixes(1, "mono") == ["FC"]
    assert get_channel_suffixes(4, "4.0") == ["Ch1", "Ch2", "Ch3", "Ch4"]


def test_build_ffmpeg_command_split_channels_wav() -> None:
    req = ConverterRequest(
        input_file=Path("movie.mkv"),
        output_file=Path("output/movie.wav"),
        split_channels=True
    )
    ffmpeg = Path("bin/ffmpeg.exe") if Path("bin/ffmpeg.exe").exists() else Path("ffmpeg")
    result = build_ffmpeg_command(req, ffmpeg)
    assert "-filter_complex" in result.args
    args_str = " ".join(result.args)
    assert "asplit=" in args_str
    assert "pan=1c|c0=c0" in args_str
    assert "movie_FL.wav" in args_str
    assert "movie_FR.wav" in args_str
    assert "movie_FC.wav" in args_str
    assert "movie_LFE.wav" in args_str


def test_build_ffmpeg_command_split_channels_mp3() -> None:
    req = ConverterRequest(
        input_file=Path("movie.mkv"),
        output_file=Path("output/song.mp3"),
        split_channels=True
    )
    ffmpeg = Path("bin/ffmpeg.exe") if Path("bin/ffmpeg.exe").exists() else Path("ffmpeg")
    result = build_ffmpeg_command(req, ffmpeg)
    assert "-filter_complex" in result.args
    args_str = " ".join(result.args)
    assert "libmp3lame" in args_str
    assert "song_FL.mp3" in args_str


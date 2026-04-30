"""Tests for videcook.core.progress_parser."""

import pytest

from videcook.core.progress_parser import parse_progress_line


class TestParseProgressLine:
    def test_extracts_percent_speed_eta(self) -> None:
        line = "[download]  12.3% of 50.00MiB at 1.23MiB/s ETA 00:35"
        result = parse_progress_line(line)
        assert result["type"] == "download_progress"
        assert result["percent"] == pytest.approx(12.3)
        assert result["speed"] == "1.23MiB/s"
        assert result["eta"] == "00:35"

    def test_download_without_speed_eta(self) -> None:
        line = "[download]  45.0% of 120.00MiB"
        result = parse_progress_line(line)
        assert result["type"] == "download_progress"
        assert result["percent"] == pytest.approx(45.0)
        assert "speed" not in result
        assert "eta" not in result

    def test_download_completed(self) -> None:
        line = "[download] 100% of 50.00MiB in 00:41"
        result = parse_progress_line(line)
        assert result["type"] == "download_completed"
        assert result["percent"] == 100.0

    def test_download_completed_exact_100(self) -> None:
        line = "[download] 100% of 50.00MiB in 00:05"
        result = parse_progress_line(line)
        assert result["type"] == "download_completed"

    def test_merger_line(self) -> None:
        line = '[Merger] Merging formats into "video.mp4"'
        result = parse_progress_line(line)
        assert result["type"] == "postprocess"
        assert result["stage"] == "merger"

    def test_extract_audio_line(self) -> None:
        line = "[ExtractAudio] Destination: audio.m4a"
        result = parse_progress_line(line)
        assert result["type"] == "postprocess"
        assert result["stage"] == "extractaudio"

    def test_destination_line(self) -> None:
        line = "[download] Destination: some-file.webm"
        result = parse_progress_line(line)
        assert result["type"] == "destination"

    def test_unrecognized_line_returns_log(self) -> None:
        line = "Some random debug output"
        result = parse_progress_line(line)
        assert result["type"] == "log"
        assert result["raw"] == line

    def test_empty_line_returns_log(self) -> None:
        result = parse_progress_line("")
        assert result["type"] == "log"

    def test_raw_is_preserved(self) -> None:
        raw = "[download]  50.0% of 10.00MiB at 2.00MiB/s ETA 00:03"
        result = parse_progress_line(raw)
        assert result["raw"] == raw

    def test_percent_with_tilde_prefix(self) -> None:
        line = "[download]  12.3% of ~ 50.00MiB at 1.23MiB/s ETA 00:35"
        result = parse_progress_line(line)
        assert result["type"] == "download_progress"
        assert result["percent"] == pytest.approx(12.3)

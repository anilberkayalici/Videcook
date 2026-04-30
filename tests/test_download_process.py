"""Tests for videcook.services.download_process.

No real subprocess calls — all tests use iterables of fake lines.
"""

from videcook.services.download_process import DownloadProcessResult, stream_lines


class TestStreamLines:
    def test_calls_callback_for_each_line(self) -> None:
        lines = ["line 1\n", "line 2\n", "line 3\n"]
        results: list[str] = []
        stream_lines(lines, on_line=results.append)
        assert results == ["line 1", "line 2", "line 3"]

    def test_stops_on_cancellation(self) -> None:
        lines = ["a\n", "b\n", "c\n", "d\n", "e\n"]
        results: list[str] = []
        call_count = 0

        def cancelled() -> bool:
            nonlocal call_count
            call_count += 1
            return call_count >= 3

        stream_lines(lines, on_line=results.append, check_cancelled=cancelled)
        # Should stop after processing "b" — the third check returns True
        assert len(results) <= 3
        assert results[:2] == ["a", "b"]

    def test_strips_newlines(self) -> None:
        lines = ["hello\r\n", "world\n"]
        results: list[str] = []
        stream_lines(lines, on_line=results.append)
        assert results == ["hello", "world"]

    def test_no_cancellation_callback_means_full_iteration(self) -> None:
        lines = ["1\n", "2\n", "3\n"]
        results: list[str] = []
        stream_lines(lines, on_line=results.append)
        assert results == ["1", "2", "3"]


class TestDownloadProcessResult:
    def test_dataclass_fields(self) -> None:
        r = DownloadProcessResult(success=True, return_code=0, cancelled=False, message="ok")
        assert r.success is True
        assert r.return_code == 0
        assert r.cancelled is False
        assert r.message == "ok"

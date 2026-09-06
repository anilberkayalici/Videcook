"""Tests for videcook.core.thumbnail — video ID parsing, URL building,
filename sanitisation, and download (with fallback to smaller sizes).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from videcook.core.thumbnail import (
    ThumbnailSize,
    build_filename,
    download_thumbnail,
    extract_video_id,
    fetch_metadata,
    sanitize_filename,
    thumbnail_url,
)


# ---------------------------------------------------------------------------
# extract_video_id
# ---------------------------------------------------------------------------


class TestExtractVideoId:
    def test_watch_query(self) -> None:
        assert (
            extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_watch_query_with_extra_params(self) -> None:
        assert (
            extract_video_id(
                "https://www.youtube.com/watch?feature=share&v=dQw4w9WgXcQ&t=42s"
            )
            == "dQw4w9WgXcQ"
        )

    def test_short_url(self) -> None:
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self) -> None:
        assert (
            extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_embed_url(self) -> None:
        assert (
            extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_legacy_v_url(self) -> None:
        assert (
            extract_video_id("https://www.youtube.com/v/dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_live_url(self) -> None:
        assert (
            extract_video_id("https://www.youtube.com/live/dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_music_url(self) -> None:
        assert (
            extract_video_id("https://music.youtube.com/watch?v=dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_with_trailing_whitespace(self) -> None:
        assert (
            extract_video_id("   https://youtu.be/dQw4w9WgXcQ   ")
            == "dQw4w9WgXcQ"
        )

    def test_invalid_url(self) -> None:
        assert extract_video_id("https://example.com/some/page") is None

    def test_empty_url(self) -> None:
        assert extract_video_id("") is None

    def test_too_short_id_rejected(self) -> None:
        # IDs under 11 characters shouldn't match.
        assert extract_video_id("https://youtu.be/short") is None

    def test_extra_chars_after_id_are_ignored(self) -> None:
        # Real YouTube URLs sometimes have trailing path segments; the
        # extractor only looks at the first 11-char alphanumeric run.
        # (yt-dlp does the same.)
        assert (
            extract_video_id("https://youtu.be/dQw4w9WgXcQextra")
            == "dQw4w9WgXcQ"
        )

    def test_http_variant(self) -> None:
        # Both http and https should be accepted.
        assert (
            extract_video_id("http://www.youtube.com/watch?v=dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )


# ---------------------------------------------------------------------------
# thumbnail_url
# ---------------------------------------------------------------------------


class TestThumbnailUrl:
    def test_maxres(self) -> None:
        assert (
            thumbnail_url("dQw4w9WgXcQ", ThumbnailSize.MAXRES)
            == "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
        )

    def test_sd(self) -> None:
        assert (
            thumbnail_url("dQw4w9WgXcQ", ThumbnailSize.SD)
            == "https://img.youtube.com/vi/dQw4w9WgXcQ/sddefault.jpg"
        )

    def test_hq(self) -> None:
        assert (
            thumbnail_url("dQw4w9WgXcQ", ThumbnailSize.HQ)
            == "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
        )

    def test_mq(self) -> None:
        assert (
            thumbnail_url("dQw4w9WgXcQ", ThumbnailSize.MQ)
            == "https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg"
        )

    def test_default(self) -> None:
        assert (
            thumbnail_url("dQw4w9WgXcQ", ThumbnailSize.DEFAULT)
            == "https://img.youtube.com/vi/dQw4w9WgXcQ/default.jpg"
        )

    def test_invalid_size_raises(self) -> None:
        with pytest.raises(ValueError):
            thumbnail_url("dQw4w9WgXcQ", "bogus")

    def test_all_sizes_known(self) -> None:
        for size in ThumbnailSize.ALL:
            url = thumbnail_url("dQw4w9WgXcQ", size)
            assert "img.youtube.com" in url
            assert url.endswith(".jpg")


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------


class TestSanitizeFilename:
    def test_plain_text_unchanged(self) -> None:
        assert sanitize_filename("hello world") == "hello world"

    def test_windows_invalid_chars_removed(self) -> None:
        assert sanitize_filename('a<b>c:d/e\\f|g?h*i"j') == "abcdefghij"

    def test_control_chars_removed(self) -> None:
        assert sanitize_filename("hello\x00world\x1f") == "helloworld"

    def test_whitespace_collapsed(self) -> None:
        assert sanitize_filename("hello   world") == "hello world"
        assert sanitize_filename("hello\t\nworld") == "hello world"

    def test_unicode_normalized(self) -> None:
        # NFKD strips combining marks; "café" becomes "cafe".
        result = sanitize_filename("café")
        assert result == "cafe"

    def test_leading_trailing_dots_and_spaces_stripped(self) -> None:
        assert sanitize_filename("  ...hello...  ") == "hello"

    def test_max_length_truncation(self) -> None:
        long_text = "a" * 200
        result = sanitize_filename(long_text, max_length=50)
        assert len(result) == 50

    def test_empty_string_returns_empty(self) -> None:
        assert sanitize_filename("") == ""

    def test_all_invalid_chars_removed_returns_empty(self) -> None:
        assert sanitize_filename('<<<>>>') == ""


# ---------------------------------------------------------------------------
# build_filename
# ---------------------------------------------------------------------------


class TestBuildFilename:
    def test_with_title(self) -> None:
        name = build_filename("Rick Astley - Never Gonna Give You Up", ThumbnailSize.MAXRES, "fallback")
        assert name == "Rick Astley - Never Gonna Give You Up - maxresdefault.jpg"

    def test_without_title_falls_back_to_id(self) -> None:
        name = build_filename("", ThumbnailSize.MAXRES, "dQw4w9WgXcQ")
        assert name == "dQw4w9WgXcQ - maxresdefault.jpg"

    def test_title_with_invalid_chars_is_sanitized(self) -> None:
        # Invalid characters get stripped; remaining words are
        # collapsed to single spaces and the size label is appended.
        name = build_filename('Bad/Name: Test?', ThumbnailSize.HQ, "vid")
        assert "/" not in name
        assert ":" not in name
        assert "?" not in name
        assert name.endswith(" - hqdefault.jpg")
        # The sanitised title "BadName Test" should be present.
        assert "BadName Test" in name

    def test_filename_always_has_jpg_extension(self) -> None:
        name = build_filename("Title", ThumbnailSize.SD, "vid")
        assert name.endswith(".jpg")

    def test_different_sizes(self) -> None:
        for size in ThumbnailSize.ALL:
            name = build_filename("Title", size, "vid")
            assert size in name
            assert name.endswith(".jpg")


# ---------------------------------------------------------------------------
# download_thumbnail (network mocked)
# ---------------------------------------------------------------------------


_FAKE_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 100


class TestDownloadThumbnail:
    def test_successful_download(self, tmp_path: Path) -> None:
        url_to_size = {
            thumbnail_url("dQw4w9WgXcQ", ThumbnailSize.MAXRES): ThumbnailSize.MAXRES,
        }

        def fake_urlopen(req, timeout=15.0):
            url = req.full_url
            if url in url_to_size:
                resp = mock.MagicMock()
                resp.__enter__ = lambda self: self
                resp.__exit__ = lambda *a: None
                resp.read.return_value = _FAKE_JPEG
                return resp
            raise AssertionError(f"Unexpected URL: {url}")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = download_thumbnail(
                video_id="dQw4w9WgXcQ",
                output_dir=tmp_path,
                filename="video - maxresdefault.jpg",
                requested_size=ThumbnailSize.MAXRES,
            )
        assert result.success is True
        assert result.used_size == ThumbnailSize.MAXRES
        assert result.saved_path is not None
        assert result.saved_path.exists()
        assert result.saved_path.read_bytes() == _FAKE_JPEG
        assert result.bytes_written == len(_FAKE_JPEG)

    def test_falls_back_to_smaller_size_on_404(self, tmp_path: Path) -> None:
        """When MaxRes returns 404, the worker should try SD next."""
        import urllib.error

        url_maxres = thumbnail_url("dQw4w9WgXcQ", ThumbnailSize.MAXRES)
        url_sd = thumbnail_url("dQw4w9WgXcQ", ThumbnailSize.SD)

        def fake_urlopen(req, timeout=15.0):
            url = req.full_url
            if url == url_maxres:
                raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
            if url == url_sd:
                resp = mock.MagicMock()
                resp.__enter__ = lambda self: self
                resp.__exit__ = lambda *a: None
                resp.read.return_value = _FAKE_JPEG
                return resp
            raise AssertionError(f"Unexpected URL: {url}")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = download_thumbnail(
                video_id="dQw4w9WgXcQ",
                output_dir=tmp_path,
                filename="video - maxresdefault.jpg",
                requested_size=ThumbnailSize.MAXRES,
            )
        assert result.success is True
        assert result.used_size == ThumbnailSize.SD
        assert result.saved_path is not None
        assert ThumbnailSize.SD in result.saved_path.name

    def test_all_sizes_404_returns_failure(self, tmp_path: Path) -> None:
        import urllib.error

        def fake_urlopen(req, timeout=15.0):
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = download_thumbnail(
                video_id="dQw4w9WgXcQ",
                output_dir=tmp_path,
                filename="video.jpg",
                requested_size=ThumbnailSize.MAXRES,
            )
        assert result.success is False
        assert result.saved_path is None
        assert "mevcut değil" in result.error_message

    def test_empty_video_id(self, tmp_path: Path) -> None:
        result = download_thumbnail(
            video_id="",
            output_dir=tmp_path,
            filename="video.jpg",
            requested_size=ThumbnailSize.MAXRES,
        )
        assert result.success is False
        assert "Video ID" in result.error_message

    def test_invalid_size(self, tmp_path: Path) -> None:
        result = download_thumbnail(
            video_id="dQw4w9WgXcQ",
            output_dir=tmp_path,
            filename="video.jpg",
            requested_size="bogus",
        )
        assert result.success is False
        assert "boyut" in result.error_message

    def test_non_jpeg_data_rejected(self, tmp_path: Path) -> None:
        """If the response doesn't start with the JPEG magic, the
        download is rejected even if the HTTP call succeeded."""
        fake_html = b"<html>not an image</html>"

        def fake_urlopen(req, timeout=15.0):
            resp = mock.MagicMock()
            resp.__enter__ = lambda self: self
            resp.__exit__ = lambda *a: None
            resp.read.return_value = fake_html
            return resp

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = download_thumbnail(
                video_id="dQw4w9WgXcQ",
                output_dir=tmp_path,
                filename="video.jpg",
                requested_size=ThumbnailSize.MAXRES,
            )
        assert result.success is False
        assert "JPEG" in result.error_message

    def test_timeout_raises(self, tmp_path: Path) -> None:
        def fake_urlopen(req, timeout=15.0):
            raise TimeoutError("slow")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = download_thumbnail(
                video_id="dQw4w9WgXcQ",
                output_dir=tmp_path,
                filename="video.jpg",
                requested_size=ThumbnailSize.MAXRES,
            )
        assert result.success is False
        assert "Zaman aşımı" in result.error_message

    def test_filename_safety(self, tmp_path: Path) -> None:
        """A filename with bad chars should be sanitised on disk."""
        def fake_urlopen(req, timeout=15.0):
            resp = mock.MagicMock()
            resp.__enter__ = lambda self: self
            resp.__exit__ = lambda *a: None
            resp.read.return_value = _FAKE_JPEG
            return resp

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = download_thumbnail(
                video_id="dQw4w9WgXcQ",
                output_dir=tmp_path,
                filename='bad/name:test?.jpg',
                requested_size=ThumbnailSize.MAXRES,
            )
        assert result.success is True
        assert result.saved_path is not None
        # The file was written and has no path separators in the name.
        assert "/" not in result.saved_path.name
        assert ":" not in result.saved_path.name

    def test_output_dir_created(self, tmp_path: Path) -> None:
        nested = tmp_path / "does" / "not" / "exist" / "yet"
        def fake_urlopen(req, timeout=15.0):
            resp = mock.MagicMock()
            resp.__enter__ = lambda self: self
            resp.__exit__ = lambda *a: None
            resp.read.return_value = _FAKE_JPEG
            return resp
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = download_thumbnail(
                video_id="dQw4w9WgXcQ",
                output_dir=nested,
                filename="video.jpg",
                requested_size=ThumbnailSize.MAXRES,
            )
        assert result.success is True
        assert result.saved_path is not None
        assert nested.exists()


# ---------------------------------------------------------------------------
# fetch_metadata
# ---------------------------------------------------------------------------


class TestFetchMetadata:
    def test_parses_yt_dlp_json_output(self, tmp_path: Path) -> None:
        ytdlp = tmp_path / "yt-dlp.exe"
        ytdlp.touch()

        yt_output = json.dumps({
            "title": "Rick Astley - Never Gonna Give You Up",
            "id": "dQw4w9WgXcQ",
        })

        fake_proc = mock.MagicMock()
        fake_proc.returncode = 0
        fake_proc.communicate.return_value = (yt_output, "")

        with mock.patch("subprocess.Popen", return_value=fake_proc):
            meta = fetch_metadata(ytdlp, "dQw4w9WgXcQ", timeout=5.0)

        assert meta.title == "Rick Astley - Never Gonna Give You Up"
        assert meta.video_id == "dQw4w9WgXcQ"

    def test_empty_ytdlp_output(self, tmp_path: Path) -> None:
        ytdlp = tmp_path / "yt-dlp.exe"
        ytdlp.touch()

        fake_proc = mock.MagicMock()
        fake_proc.returncode = 0
        fake_proc.communicate.return_value = ("", "")

        with mock.patch("subprocess.Popen", return_value=fake_proc):
            meta = fetch_metadata(ytdlp, "dQw4w9WgXcQ", timeout=5.0)

        assert meta.title == ""
        assert meta.video_id == "dQw4w9WgXcQ"

    def test_nonzero_exit(self, tmp_path: Path) -> None:
        ytdlp = tmp_path / "yt-dlp.exe"
        ytdlp.touch()

        fake_proc = mock.MagicMock()
        fake_proc.returncode = 1
        fake_proc.communicate.return_value = ("", "error")

        with mock.patch("subprocess.Popen", return_value=fake_proc):
            meta = fetch_metadata(ytdlp, "dQw4w9WgXcQ", timeout=5.0)

        assert meta.title == ""
        assert meta.video_id == "dQw4w9WgXcQ"

    def test_missing_ytdlp_returns_empty(self, tmp_path: Path) -> None:
        ytdlp = tmp_path / "yt-dlp.exe"  # does not exist
        meta = fetch_metadata(ytdlp, "dQw4w9WgXcQ", timeout=5.0)
        assert meta.title == ""
        assert meta.video_id == "dQw4w9WgXcQ"

    def test_timeout_falls_back(self, tmp_path: Path) -> None:
        ytdlp = tmp_path / "yt-dlp.exe"
        ytdlp.touch()

        fake_proc = mock.MagicMock()
        fake_proc.communicate.side_effect = TimeoutError("slow")

        with mock.patch("subprocess.Popen", return_value=fake_proc):
            meta = fetch_metadata(ytdlp, "dQw4w9WgXcQ", timeout=5.0)

        # Even on timeout, video_id is preserved.
        assert meta.video_id == "dQw4w9WgXcQ"


# ---------------------------------------------------------------------------
# ThumbnailSize ordering
# ---------------------------------------------------------------------------


class TestThumbnailSizeOrdering:
    def test_all_includes_five_sizes(self) -> None:
        assert len(ThumbnailSize.ALL) == 5

    def test_maxres_is_largest(self) -> None:
        # MAXRES label should mention 1280x720.
        assert "1280" in ThumbnailSize.LABELS[ThumbnailSize.MAXRES]

    def test_default_is_smallest(self) -> None:
        # DEFAULT label should mention 120x90.
        assert "120" in ThumbnailSize.LABELS[ThumbnailSize.DEFAULT]

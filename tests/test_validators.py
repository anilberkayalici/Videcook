"""Tests for videcook.core.validators."""

from pathlib import Path

import pytest

from videcook.core.models import DownloadMode, DownloadRequest, QualityOption
from videcook.core.validators import (
    InvalidCookieFileError,
    InvalidOutputFolderError,
    InvalidUrlError,
    validate_cookie_file,
    validate_download_request,
    validate_output_folder,
    validate_url,
)


class TestValidateUrl:
    def test_accepts_http(self) -> None:
        validate_url("http://example.com/video")

    def test_accepts_https(self) -> None:
        validate_url("https://youtube.com/watch?v=abc123")

    def test_rejects_empty(self) -> None:
        with pytest.raises(InvalidUrlError):
            validate_url("")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(InvalidUrlError):
            validate_url("   ")

    def test_rejects_ftp_scheme(self) -> None:
        with pytest.raises(InvalidUrlError):
            validate_url("ftp://files.example.com/video.mp4")

    def test_rejects_plain_text(self) -> None:
        with pytest.raises(InvalidUrlError):
            validate_url("not-a-url")

    def test_strips_and_accepts(self) -> None:
        validate_url("  https://example.com  ")


class TestValidateCookieFile:
    def test_rejects_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.txt"
        with pytest.raises(InvalidCookieFileError):
            validate_cookie_file(missing)

    def test_rejects_directory(self, tmp_path: Path) -> None:
        with pytest.raises(InvalidCookieFileError):
            validate_cookie_file(tmp_path)

    def test_rejects_wrong_extension(self, tmp_path: Path) -> None:
        f = tmp_path / "cookies.json"
        f.touch()
        with pytest.raises(InvalidCookieFileError):
            validate_cookie_file(f)

    def test_accepts_txt(self, tmp_path: Path) -> None:
        f = tmp_path / "cookies.txt"
        f.touch()
        validate_cookie_file(f)  # does not raise


class TestValidateOutputFolder:
    def test_rejects_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "no_such_dir"
        with pytest.raises(InvalidOutputFolderError):
            validate_output_folder(missing)

    def test_rejects_file(self, tmp_path: Path) -> None:
        f = tmp_path / "afile.txt"
        f.touch()
        with pytest.raises(InvalidOutputFolderError):
            validate_output_folder(f)

    def test_accepts_directory(self, tmp_path: Path) -> None:
        validate_output_folder(tmp_path)


class TestValidateDownloadRequest:
    def test_valid_request_passes(self, tmp_path: Path) -> None:
        cookie = tmp_path / "cookies.txt"
        cookie.touch()
        outdir = tmp_path / "videos"
        outdir.mkdir()

        req = DownloadRequest(
            url="https://example.com/video",
            cookie_file=cookie,
            output_folder=outdir,
            quality=QualityOption.BEST,
            mode=DownloadMode.SINGLE_VIDEO,
        )
        validate_download_request(req)  # does not raise

    def test_invalid_url_fails(self, tmp_path: Path) -> None:
        cookie = tmp_path / "cookies.txt"
        cookie.touch()
        outdir = tmp_path / "videos"
        outdir.mkdir()

        req = DownloadRequest(
            url="",
            cookie_file=cookie,
            output_folder=outdir,
            quality=QualityOption.BEST,
            mode=DownloadMode.SINGLE_VIDEO,
        )
        with pytest.raises(InvalidUrlError):
            validate_download_request(req)

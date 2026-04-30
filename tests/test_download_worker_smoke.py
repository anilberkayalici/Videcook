"""Smoke tests for videcook.ui.download_worker.

These tests verify the worker can be constructed and handles sensitive state
without launching real binaries or network downloads.  DownloadWorker is a
QObject, not a QWidget, so qtbot.addWidget is not applicable.
"""

from videcook.core.models import DownloadMode, DownloadRequest, QualityOption
from videcook.ui.download_worker import DownloadWorker
from videcook.utils.i18n import LanguageManager


class TestDownloadWorker:
    def test_worker_constructs(self, tmp_path) -> None:
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
        i18n = LanguageManager()
        worker = DownloadWorker(req, i18n)

        assert worker is not None
        worker.cancel()

    def test_worker_clear_sensitive_state(self, tmp_path) -> None:
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
        i18n = LanguageManager()
        worker = DownloadWorker(req, i18n)

        worker._clear_sensitive_state()
        assert str(req.cookie_file) != str(cookie)

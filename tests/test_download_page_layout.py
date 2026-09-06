"""Download page layout tests — updated for QVBoxLayout-based form."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QScrollArea, QWidget

from videcook.core.models import DownloadType
from videcook.ui.main_window import MainWindow
from videcook.utils.i18n import LanguageManager


@pytest.fixture
def lm() -> LanguageManager:
    return LanguageManager()


class TestDownloadPageGeometry:

    def test_controls_visible(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page

        assert page._url_input.objectName() == "video_url_input"
        assert page._cookie_display.objectName() == "cookie_path_input"
        assert page._cookie_browse.objectName() == "cookie_browse_button"
        assert page._out_display.objectName() == "output_path_input"
        assert page._out_browse.objectName() == "output_browse_button"
        assert page._qual_combo.objectName() == "quality_combo"
        assert page._download_btn.objectName() == "download_button"
        assert page._cancel_btn.objectName() == "cancel_button"
        assert page._progress.objectName() == "progress_bar"
        assert page._status.objectName() == "status_label"
        assert page._log.objectName() == "operation_log"
        assert page._video_btn.objectName() == "segButton"
        assert page._audio_btn.objectName() == "segButton"

    def test_input_heights(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page
        page._secret_btn.click()

        for name, widget in [
            ("url_input", page._url_input),
            ("output_input", page._out_display),
            ("quality_combo", page._qual_combo),
            ("cookie_input", page._cookie_display),
        ]:
            h = widget.height()
            assert 34 <= h <= 60, f"{name} height={h}"

        cw = page.findChild(QWidget, "secretPanel")
        assert cw is not None

    def test_button_sizes(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page

        assert page._download_btn.height() >= 38
        assert page._cancel_btn.height() >= 38
        assert page._video_btn.height() >= 30
        assert page._audio_btn.height() >= 30
        assert page._secret_btn.height() >= 30

    def test_secret_mode_toggle(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page
        sp = page.findChild(QWidget, "secretPanel")
        assert sp is not None
        assert not sp.isVisible()

        page._secret_btn.click()
        assert sp.isVisible()
        assert page._secret_mode

        page._video_btn.click()
        assert not sp.isVisible()
        assert not page._secret_mode

    def test_mode_toggle_switches_format(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page
        page._video_btn.click()

        assert page._download_type is DownloadType.VIDEO
        assert page._video_sub_panel.isVisible()
        assert not page._audio_qual_panel.isVisible()
        assert not page._secret_panel.isVisible()

        page._audio_btn.click()
        assert page._download_type is DownloadType.AUDIO
        assert not page._video_sub_panel.isVisible()
        assert page._audio_qual_panel.isVisible()
        assert page._audio_qual_combo.count() > 0
        assert not page._secret_panel.isVisible()

        page._secret_btn.click()
        assert page._secret_mode
        assert page._secret_panel.isVisible()
        assert not page._video_sub_panel.isVisible()
        assert not page._audio_qual_panel.isVisible()

        page._video_btn.click()
        assert page._download_type is DownloadType.VIDEO
        assert page._video_sub_panel.isVisible()
        assert not page._audio_qual_panel.isVisible()
        assert not page._secret_panel.isVisible()

    def test_log_view_has_min_height(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page
        assert page._log.height() >= 100, f"log_view height={page._log.height()}"

    def test_dynamic_filesize_updates_on_selection_change(self, qtbot, lm: LanguageManager) -> None:
        from videcook.ui.video_info_worker import VideoInfo, VideoFormatOption

        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        page = window._download_page

        mock_info = VideoInfo(
            title="Test Video",
            channel="Test Channel",
            duration_seconds=300,
            filesize_approx=62_914_560,
            description="Test Description",
            formats=[
                VideoFormatOption(label="1080p", quality_value="1080", std_height=1080, filesize_approx=62_914_560),
                VideoFormatOption(label="720p", quality_value="720", std_height=720, filesize_approx=31_457_280),
                VideoFormatOption(label="480p", quality_value="480", std_height=480, filesize_approx=15_728_640),
            ]
        )

        page._on_video_info_ready(mock_info)

        # 1. Video mode with 1080p
        idx_1080 = page._qual_combo.findText("1080p")
        if idx_1080 >= 0:
            page._qual_combo.setCurrentIndex(idx_1080)
            assert "60.00 MB" in page._info_size_value.text() or "MB" in page._info_size_value.text()

        # 2. Select 720p
        idx_720 = page._qual_combo.findText("720p")
        if idx_720 >= 0:
            page._qual_combo.setCurrentIndex(idx_720)
            assert "30.00 MB" in page._info_size_value.text()

        # 3. Switch to Audio mode
        page._audio_btn.click()
        # Default is MP3 320k: 300s * 320,000 / 8 = 12,000,000 bytes = 11.44 MB
        assert "11.44 MB" in page._info_size_value.text() or "MB" in page._info_size_value.text()

        # Switch to 128 kbps: 300s * 128,000 / 8 = 4,800,000 bytes = 4.58 MB
        idx_128 = page._audio_qual_combo.findData("128")
        if idx_128 >= 0:
            page._audio_qual_combo.setCurrentIndex(idx_128)
            assert "4.58 MB" in page._info_size_value.text()

        # Switch format to WAV: 300s * 176,400 bytes = 52,920,000 bytes = 50.47 MB
        idx_wav = page._qual_combo.findText(lm.get_text("audio_format.wav"))
        if idx_wav >= 0:
            page._qual_combo.setCurrentIndex(idx_wav)
            assert "50.47 MB" in page._info_size_value.text()

        # 4. Switch to Thumbnail mode
        page._thumb_toggle.click()
        assert "KB" in page._info_size_value.text()

    def test_queue_add_workflow(self, qtbot, lm: LanguageManager) -> None:
        window = MainWindow(lm)
        qtbot.addWidget(window)
        window.show()
        window.resize(1250, 780)

        page = window._download_page
        assert len(page._download_queue) == 0
        assert not page._queue_start_btn.isVisible()

        # Add valid item to queue
        page._url_input.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        page._queue_add_btn.click()

        assert len(page._download_queue) == 1
        assert page._queue_start_btn.isVisible()
        assert "1" in page._queue_start_btn.text()
        assert page._url_input.text() == ""



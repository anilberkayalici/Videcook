"""Tests for videcook.core.playlist."""

from videcook.core.playlist import detect_playlist_intent


class TestDetectPlaylistIntent:
    def test_youtube_watch_with_list_param(self) -> None:
        url = "https://www.youtube.com/watch?v=abc123&list=PLxyz"
        assert detect_playlist_intent(url) is True

    def test_youtube_playlist_url(self) -> None:
        url = "https://www.youtube.com/playlist?list=PLxyz"
        assert detect_playlist_intent(url) is True

    def test_youtube_watch_without_list(self) -> None:
        url = "https://www.youtube.com/watch?v=abc123"
        assert detect_playlist_intent(url) is False

    def test_plain_http_url(self) -> None:
        url = "https://example.com/video.mp4"
        assert detect_playlist_intent(url) is False

    def test_empty_url(self) -> None:
        assert detect_playlist_intent("") is False

    def test_whitespace_only_url(self) -> None:
        assert detect_playlist_intent("   ") is False

    def test_youtu_be_with_list(self) -> None:
        url = "https://youtu.be/abc123?list=PLxyz"
        assert detect_playlist_intent(url) is True

    def test_youtu_be_without_list(self) -> None:
        url = "https://youtu.be/abc123"
        assert detect_playlist_intent(url) is False

    def test_non_youtube_url_with_list(self) -> None:
        # Other sites may use 'list' for other things; we currently
        # only flag YouTube URLs. This keeps detection conservative.
        url = "https://vimeo.com/123?list=something"
        assert detect_playlist_intent(url) is False

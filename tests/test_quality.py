"""Tests for videcook.core.quality."""

from videcook.core.models import QualityOption
from videcook.core.quality import get_format_selector


class TestGetFormatSelector:
    def test_best(self) -> None:
        sel = get_format_selector(QualityOption.BEST)
        assert "bv" in sel
        assert "ba" in sel

    def test_1080p_includes_height_limit(self) -> None:
        sel = get_format_selector(QualityOption.P1080)
        assert "height<=1080" in sel

    def test_720p_includes_height_limit(self) -> None:
        sel = get_format_selector(QualityOption.P720)
        assert "height<=720" in sel

    def test_480p_includes_height_limit(self) -> None:
        sel = get_format_selector(QualityOption.P480)
        assert "height<=480" in sel

    def test_every_quality_has_selector(self) -> None:
        for q in QualityOption:
            sel = get_format_selector(q)
            assert isinstance(sel, str)
            assert len(sel) > 0

"""Unit tests for the AI Editor core module (ai_editor.py)."""

from pathlib import Path
from videcook.core.subtitles import SubtitleSegment
from videcook.core.ai_editor import (
    format_transcript_for_llm,
    generate_ass_subtitles,
    build_edit_ffmpeg_command,
)


def test_format_transcript_for_llm():
    segments = [
        SubtitleSegment(start=10.0, end=15.5, text="Merhaba dünya"),
        SubtitleSegment(start=15.5, end=22.0, text="Mahito vs Itadori sahnesi"),
    ]
    formatted = format_transcript_for_llm(segments)
    assert "[00:00:10.00 -> 00:00:15.50]" in formatted
    assert "Merhaba dünya" in formatted
    assert "Mahito vs Itadori sahnesi" in formatted


def test_generate_ass_subtitles(tmp_path: Path):
    segments = [
        SubtitleSegment(start=5.0, end=10.0, text="İlk diyalog"),
        SubtitleSegment(start=12.0, end=18.0, text="İkinci diyalog"),
        SubtitleSegment(start=25.0, end=30.0, text="Üçüncü diyalog"),
    ]
    ass_path = tmp_path / "sub.ass"

    # Select clip window between 10.0 and 20.0 seconds
    ok = generate_ass_subtitles(
        segments=segments,
        start_sec=10.0,
        end_sec=20.0,
        style="CapCut Vurgulu (Sarı / Kırmızı)",
        ass_path=ass_path,
    )

    assert ok is True
    assert ass_path.is_file()
    content = ass_path.read_text(encoding="utf-8")
    assert "Dialogue:" in content
    assert "İkinci diyalog" in content
    assert "İlk diyalog" not in content  # Out of range

    # Test 1:1 Kare aspect ratio
    ass_path_square = tmp_path / "sub_square.ass"
    ok_sq = generate_ass_subtitles(
        segments=segments,
        start_sec=10.0,
        end_sec=20.0,
        style="Metal Family",
        ass_path=ass_path_square,
        aspect_ratio_str="1:1 Kare (Instagram)",
    )
    assert ok_sq is True
    content_sq = ass_path_square.read_text(encoding="utf-8")
    assert "PlayResX: 1080" in content_sq
    assert "PlayResY: 1080" in content_sq
    assert "Fontsize, 92" in content_sq or "Default,Arial,92" in content_sq


def test_build_edit_ffmpeg_command():
    video_path = Path("/tmp/video.mp4")
    output_path = Path("/tmp/output.mp4")
    ffmpeg_path = Path("/usr/bin/ffmpeg")
    ass_path = Path("/tmp/sub.ass")

    cmd = build_edit_ffmpeg_command(
        video_path=video_path,
        output_path=output_path,
        start_sec=15.0,
        end_sec=45.0,
        aspect_ratio_str="9:16 Dikey",
        ass_subtitle_path=ass_path,
        ffmpeg_path=ffmpeg_path,
    )

    assert cmd[0] == str(ffmpeg_path)
    assert "-ss" in cmd
    assert "15.00" in cmd
    assert "-t" in cmd
    assert "30.00" in cmd
    assert "crop=ih*9/16:ih" in ",".join(cmd)


def test_split_segment_into_short_phrases_proportional():
    from videcook.core.ai_editor import split_segment_into_short_phrases
    seg = SubtitleSegment(start=10.0, end=20.0, text="No. Pretty please. Hi there dentist.")
    phrases = split_segment_into_short_phrases(seg)
    assert len(phrases) == 3
    assert phrases[0].text == "No."
    assert phrases[1].text == "Pretty please."
    assert phrases[2].text == "Hi there dentist."
    # Proportional durations: 1 word < 2 words < 3 words
    dur0 = phrases[0].end - phrases[0].start
    dur1 = phrases[1].end - phrases[1].start
    dur2 = phrases[2].end - phrases[2].start
    assert dur0 < dur1 < dur2


def test_align_translation_fallback():
    from videcook.core.ai_editor import align_translation_to_audio_segments
    audio_segs = [
        SubtitleSegment(start=10.0, end=14.0, text="Hello world"),
    ]
    trans_segs = [
        SubtitleSegment(start=10.0, end=14.0, text="Merhaba dünya"),
    ]
    # Without valid API key, should safely fall back
    res = align_translation_to_audio_segments("", audio_segs, trans_segs, 10.0, 15.0)
    assert len(res) >= 1
    assert res[0].text == "Merhaba dünya"

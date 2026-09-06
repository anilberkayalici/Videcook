"""Unit tests for background music detection and audio mixing command builder (bg_music.py)."""

from pathlib import Path
from videcook.core.bg_music import (
    detect_music_category_from_prompt,
    build_edit_ffmpeg_command_with_bg_music,
)


def test_detect_music_category_from_prompt():
    assert detect_music_category_from_prompt("Bana gaza getiren bir phonk müzikli edit yap") == "phonk"
    assert detect_music_category_from_prompt("Hüzünlü başlayan anime lofi şarkılı bir video olsun") == "sad_anime"
    assert detect_music_category_from_prompt("Epik savaş sahnesi arkaya müzik koy") == "epic_action"
    assert detect_music_category_from_prompt("Komik meme fon müziği ekle") == "funny_comedy"
    assert detect_music_category_from_prompt("Sadece 30 saniye kes") is None
    assert detect_music_category_from_prompt("müzik koyma") is None


def test_build_edit_ffmpeg_command_with_bg_music(tmp_path: Path):
    video_path = tmp_path / "video.mp4"
    output_path = tmp_path / "output.mp4"
    ffmpeg_path = Path("/usr/bin/ffmpeg")
    bg_music_path = tmp_path / "music.mp3"
    bg_music_path.write_bytes(b"mock mp3 data")

    cmd = build_edit_ffmpeg_command_with_bg_music(
        video_path=video_path,
        output_path=output_path,
        start_sec=10.0,
        end_sec=40.0,
        aspect_ratio_str="9:16 Dikey",
        ass_subtitle_path=None,
        bg_music_path=bg_music_path,
        ffmpeg_path=ffmpeg_path,
    )

    cmd_str = " ".join(cmd)
    assert "temp_videcook_bg.mp3" in cmd_str
    assert "amix=inputs=2" in cmd_str
    assert "crop=ih*9/16:ih" in cmd_str

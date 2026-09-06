"""Background Music Engine — Royalty-free edit music fetcher, prompt sentiment mapping, and FFmpeg audio mixing."""

from __future__ import annotations

import os
import re
import urllib.request
from pathlib import Path
from typing import Any

from videcook.paths import get_user_data_dir

# Royalty-free edit music tracks (Hosted on public, royalty-free Pixabay/Archive CDNs)
BUILTIN_MUSIC_TRACKS: dict[str, dict[str, str]] = {
    "phonk": {
        "title": "Phonk / High Energy Edit Beat",
        "url": "https://cdn.pixabay.com/download/audio/2022/11/06/audio_c1e6c464b5.mp3?filename=phonk-energy-125638.mp3",
        "filename": "phonk_energy.mp3",
    },
    "sad_anime": {
        "title": "Sad to Happy Anime Lofi",
        "url": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3?filename=sad-lofi-anime-11234.mp3",
        "filename": "sad_anime_lofi.mp3",
    },
    "epic_action": {
        "title": "Epic Cinematic Action",
        "url": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a8264e.mp3?filename=epic-action-trailer-10972.mp3",
        "filename": "epic_action.mp3",
    },
    "funny_comedy": {
        "title": "Funny / Goofy Meme BGM",
        "url": "https://cdn.pixabay.com/download/audio/2022/03/24/audio_34b35e6939.mp3?filename=funny-comedy-groove-110292.mp3",
        "filename": "funny_comedy.mp3",
    },
    "ambient_lofi": {
        "title": "Chill Ambient Lofi",
        "url": "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0a13f69d2.mp3?filename=chill-lofi-song-8444.mp3",
        "filename": "chill_lofi.mp3",
    },
}


NEGATIVE_MUSIC_KEYWORDS = [
    "müzik koyma",
    "müzik ekleme",
    "müziksiz",
    "şarkı koyma",
    "şarkı ekleme",
    "şarkısız",
    "müzik istemiyorum",
    "fon müziği olmasın",
    "müzik olmasın",
    "no music",
    "müziğe gerek yok",
    "müzik olmadan",
    "şarkı olmadan",
    "müzik kullanma",
    "arkaya müzik ekleme",
    "arka plan müziği ekleme",
]


def detect_music_category_from_prompt(prompt: str) -> str | None:
    """Analyze user prompt text to detect requested background music mood."""
    p_lower = prompt.lower()

    # 1. If user explicitly asked NOT to include music, return None immediately
    if any(k in p_lower for k in NEGATIVE_MUSIC_KEYWORDS):
        return None

    # 2. Check if user explicitly asked FOR background music / song / beat
    has_music_intent = any(k in p_lower for k in [
        "müzik", "şarkı", "fon müziği", "arkaya müzik", "arka plan müziği",
        "phonk", "lofi", "soundtrack", "bgm", "beat", "melodi"
    ])
    if not has_music_intent:
        return None

    # 3. Categorize music mood
    if any(k in p_lower for k in ["phonk", "gaza", "hype", "yüksek tempo", "aksiyon", "hızlı"]):
        return "phonk"
    if any(k in p_lower for k in ["hüzün", "dram", "mutlu", "anime", "duygusal", "üzgün"]):
        return "sad_anime"
    if any(k in p_lower for k in ["epik", "savaş", "dövüş", "film", "fragman"]):
        return "epic_action"
    if any(k in p_lower for k in ["komik", "espri", "şaka", "meme", "eğlenceli"]):
        return "funny_comedy"
    if any(k in p_lower for k in ["şarkı", "müzik", "fon müziği", "arkaya müzik", "lofi", "chill"]):
        return "ambient_lofi"

    return None


def get_music_dir() -> Path:
    """Return local directory for cached royalty-free background music."""
    path = get_user_data_dir() / "music"
    path.mkdir(parents=True, exist_ok=True)
    return path


def fetch_or_get_music_track(category: str) -> Path | None:
    """Retrieve local cached audio file or download it from CDN."""
    info = BUILTIN_MUSIC_TRACKS.get(category)
    if not info:
        return None

    music_dir = get_music_dir()
    local_file = music_dir / info["filename"]
    if local_file.is_file() and local_file.stat().st_size > 10000:
        return local_file

    url = info["url"]
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp, local_file.open("wb") as out_f:
            out_f.write(resp.read())
        if local_file.is_file() and local_file.stat().st_size > 10000:
            return local_file
    except Exception:
        pass

    return None


import shutil


def build_edit_ffmpeg_command_with_bg_music(
    video_path: Path,
    output_path: Path,
    start_sec: float,
    end_sec: float,
    aspect_ratio_str: str,
    ass_subtitle_path: Path | None,
    bg_music_path: Path | None,
    ffmpeg_path: Path,
) -> list[str]:
    """Build FFmpeg command with video trimming, cropping, ASS subtitles, and background music amix."""
    out_dir = output_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    duration_sec = max(1.0, end_sec - start_sec)

    cmd = [
        str(ffmpeg_path),
        "-y",
        "-v", "error",
        "-ss", f"{start_sec:.2f}",
        "-i", str(video_path),
        "-t", f"{duration_sec:.2f}",
        "-avoid_negative_ts", "make_zero",
    ]

    has_bg_music = bg_music_path is not None and bg_music_path.is_file()
    if has_bg_music:
        rel_bg = out_dir / "temp_videcook_bg.mp3"
        try:
            shutil.copy2(bg_music_path, rel_bg)
            cmd.extend(["-t", f"{duration_sec:.2f}", "-i", "temp_videcook_bg.mp3"])
        except Exception:
            cmd.extend(["-t", f"{duration_sec:.2f}", "-i", str(bg_music_path)])

    video_filters: list[str] = []

    # Aspect ratio crop
    if "9:16" in aspect_ratio_str or "Dikey" in aspect_ratio_str:
        video_filters.append("crop=ih*9/16:ih")
    elif "1:1" in aspect_ratio_str or "Kare" in aspect_ratio_str:
        video_filters.append("crop=ih:ih")

    # Burn subtitles if ASS file provided
    if ass_subtitle_path and ass_subtitle_path.is_file():
        # Copy ASS subtitle file to simple relative file in output directory
        # This completely avoids Windows colon/backslash escaping & non-ASCII path bugs in libass!
        rel_ass = out_dir / "temp_videcook_sub.ass"
        try:
            shutil.copy2(ass_subtitle_path, rel_ass)
            video_filters.append("subtitles=temp_videcook_sub.ass")
        except Exception:
            escaped_ass = str(ass_subtitle_path.resolve()).replace("\\", "/").replace(":", "\\:")
            video_filters.append(f"subtitles={escaped_ass}")

    if has_bg_music:
        vf_str = ",".join(video_filters) if video_filters else "null"
        filter_complex = (
            f"[0:v]{vf_str}[outv];"
            f"[0:a]volume=1.0[maina];"
            f"[1:a]volume=0.22[bgmusic];"
            f"[maina][bgmusic]amix=inputs=2:duration=first:dropout_transition=0[outa]"
        )
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
        ])
    else:
        if video_filters:
            cmd.extend(["-vf", ",".join(video_filters)])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_path),
    ])

    return cmd

"""MoviePy-based video rendering engine for AI Shorts / Reels generation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from moviepy import AudioFileClip, CompositeAudioClip, VideoFileClip


import shutil


def render_edit_with_moviepy(
    video_path: Path,
    output_path: Path,
    start_sec: float,
    end_sec: float,
    aspect_ratio_str: str,
    ass_subtitle_path: Path | None = None,
    bg_music_path: Path | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> bool:
    """Render video clip with MoviePy: trimming, 9:16/1:1 cropping, subtitle burning, and dual audio mixing."""
    if not video_path.is_file():
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration_sec = max(1.0, end_sec - start_sec)

    clip = None
    sub = None
    bg_clip = None
    mixed_audio = None
    rel_ass_file = None

    try:
        if progress_callback:
            progress_callback(f"🎬 MoviePy ile video açılıyor ({video_path.name})...")

        clip = VideoFileClip(str(video_path))
        actual_end = min(clip.duration, max(start_sec + 1.0, end_sec))
        actual_start = min(start_sec, actual_end - 1.0)

        if progress_callback:
            progress_callback(f"✂️ Kesit alınıyor: {actual_start:.1f}s ➔ {actual_end:.1f}s")

        sub = clip.subclipped(actual_start, actual_end)

        # 1. Apply Aspect Ratio & Composition
        is_blurred_bg = "Bulanık" in aspect_ratio_str or "Blur" in aspect_ratio_str
        w, h = sub.w, sub.h

        if is_blurred_bg:
            if progress_callback:
                progress_callback("🎨 9:16 Bulanık sinematik arka plan kompozisyonu hazırlanıyor...")
        elif "9:16" in aspect_ratio_str or "Dikey" in aspect_ratio_str:
            target_w = int(h * 9 / 16)
            if target_w < w:
                x1 = (w - target_w) // 2
                sub = sub.cropped(x1=x1, width=target_w)
                if progress_callback:
                    progress_callback(f"📱 9:16 Dikey kırpma uygulandı ({target_w}x{h})")
        elif "1:1" in aspect_ratio_str or "Kare" in aspect_ratio_str:
            target_size = min(w, h)
            x1 = (w - target_size) // 2
            y1 = (h - target_size) // 2
            sub = sub.cropped(x1=x1, y1=y1, width=target_size, height=target_size)
            if progress_callback:
                progress_callback(f"🔲 1:1 Kare kırpma uygulandı ({target_size}x{target_size})")

        # 2. Dual Audio Mixing (Original Video Audio + Background Music)
        if bg_music_path and bg_music_path.is_file():
            try:
                if progress_callback:
                    progress_callback("🎧 Arka plan edit müziği miksleniyor...")

                bg_clip = AudioFileClip(str(bg_music_path))
                # Subclip background audio to match video duration
                bg_sub = bg_clip.subclipped(0, min(sub.duration, bg_clip.duration))
                bg_sub = bg_sub.with_volume_scaled(0.22)

                if sub.audio is not None:
                    mixed_audio = CompositeAudioClip([sub.audio, bg_sub])
                    sub = sub.with_audio(mixed_audio)
                else:
                    sub = sub.with_audio(bg_sub)
            except Exception as e:
                if progress_callback:
                    progress_callback(f"⚠️ Müzik miksleme atlandı: {e}")

        # 3. Prepare Video Filter (Blurred Background + Subtitles)
        ffmpeg_params = ["-nostats", "-loglevel", "error", "-crf", "18"]
        sub_filename = None

        if ass_subtitle_path and ass_subtitle_path.is_file():
            try:
                sub_filename = f"temp_mpy_sub_{output_path.stem[:20]}.ass"
                rel_ass_file = Path.cwd() / sub_filename
                shutil.copy2(ass_subtitle_path, rel_ass_file)
                if progress_callback:
                    progress_callback("✨ Büyük vurgulu Türkçe altyazı videoya işleniyor...")
            except Exception as e:
                if progress_callback:
                    progress_callback(f"⚠️ Altyazı kopyalama atlandı: {e}")

        if is_blurred_bg:
            # Layer 1 (Background): Exact same video scaled to full 9:16 vertical canvas (1080x1920) and blurred
            # Layer 2 (Foreground): 50% larger center video (scale=1620:-1, centered horizontally & vertically)
            vf_filter = (
                "split=2[bg_in][fg_in];"
                "[bg_in]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:5,eq=brightness=-0.08[bg];"
                "[fg_in]scale=1620:-1[fg];"
                "[bg][fg]overlay=(1080-w)/2:(1920-h)/2"
            )
            if sub_filename:
                vf_filter += f",subtitles={sub_filename}"
            ffmpeg_params.extend(["-vf", vf_filter])
        elif sub_filename:
            ffmpeg_params.extend(["-vf", f"subtitles={sub_filename}"])

        # 4. Export Final Video
        if output_path.is_file():
            try:
                output_path.unlink(missing_ok=True)
            except Exception:
                pass

        if progress_callback:
            progress_callback("🎬 Yüksek kaliteli video kodlanıyor (CRF 18)...")

        temp_audio = str(output_path.parent / f"temp_mpy_audio_{output_path.stem}.m4a")

        sub.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            preset="fast",
            threads=4,
            ffmpeg_params=ffmpeg_params,
            temp_audiofile=temp_audio,
            remove_temp=True,
            logger=None,
        )

        if progress_callback:
            progress_callback("✅ Video ve altyazı başarıyla oluşturuldu!")

        return output_path.is_file() and output_path.stat().st_size > 1000

    except Exception as exc:
        if progress_callback:
            progress_callback(f"❌ MoviePy Hatası: {exc}")
        return False

    finally:
        if rel_ass_file is not None:
            try:
                rel_ass_file.unlink(missing_ok=True)
            except Exception:
                pass
        for c in [sub, clip, bg_clip, mixed_audio]:
            if c is not None:
                try:
                    c.close()
                except Exception:
                    pass

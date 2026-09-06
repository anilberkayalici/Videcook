"""AI Edit QThread Worker — Handles background audio extraction, Groq Whisper transcription, Groq LLM scene selection, and FFmpeg video render."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from videcook.core.ai_editor import (
    build_edit_ffmpeg_command,
    extract_audio_from_video,
    format_transcript_for_llm,
    generate_ass_subtitles,
    select_scene_with_groq_llm,
)
from videcook.services.binary_locator import check_binaries
from videcook.services.groq_transcription import GroqTranscriptionClient
from videcook.services.secure_store import load_groq_api_key


class EditWorker(QObject):
    """Background worker executing the AI Edit pipeline."""

    progress = Signal(int)
    log = Signal(str)
    finished = Signal(str)  # Output file path
    failed = Signal(str)

    def __init__(
        self,
        video_path: Path,
        output_dir: Path,
        prompt: str,
        aspect_ratio: str,
        subtitle_style: str,
        target_duration_sec: int,
        translation_path: Path | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._video_path = video_path
        self._output_dir = output_dir
        self._prompt = prompt
        self._aspect_ratio = aspect_ratio
        self._subtitle_style = subtitle_style
        self._target_duration_sec = target_duration_sec
        self._translation_path = translation_path
        self._cancelled = False
        self._proc: subprocess.Popen[str] | None = None

    def cancel(self) -> None:
        self._cancelled = True
        if self._proc is not None:
            try:
                self._proc.kill()
            except Exception:
                pass

    @Slot()
    def run(self) -> None:
        if self._cancelled:
            return

        if not self._video_path.is_file():
            self.failed.emit(f"Video dosyası bulunamadı: {self._video_path}")
            return

        # 1. Check binaries
        status = check_binaries()
        if not status.is_ready or status.ffmpeg_path is None:
            self.failed.emit("FFmpeg motoru bulunamadı. Lütfen kurulum adımlarını kontrol edin.")
            return

        ffmpeg_path = status.ffmpeg_path

        # 2. Check Groq API key
        api_key = load_groq_api_key()
        if not api_key:
            self.failed.emit(
                "Groq API anahtarı bulunamadı! Lütfen önce Ayarlar sayfasından ücretsiz Groq API anahtarınızı girin."
            )
            return

        self.log.emit("🔑 Groq API Anahtarı doğrulandı.")
        self.progress.emit(10)

        # Temp directory for intermediate files
        with tempfile.TemporaryDirectory(prefix="videcook_edit_") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            temp_audio = temp_dir / "audio.mp3"
            temp_ass = temp_dir / "subtitles.ass"

            if self._cancelled:
                return

            trans_segments = []
            if self._translation_path and self._translation_path.is_file():
                self.log.emit(f"📄 Dublaj çeviri dosyası okunuyor: {self._translation_path.name}")
                from videcook.core.translation_file_parser import parse_translation_file
                trans_segments = parse_translation_file(self._translation_path)
                if trans_segments:
                    self.log.emit(f"✅ Çeviri dosyasından {len(trans_segments)} Türkçe dublaj repliği yüklendi.")

            # Step 1: Extract Audio
            self.log.emit("🎵 Videodan ses ayrıştırılıyor...")
            ok = extract_audio_from_video(self._video_path, temp_audio, ffmpeg_path)
            if not ok or not temp_audio.is_file():
                self.failed.emit("Videodan ses dosyası ayrıştırılamadı.")
                return

            self.progress.emit(30)
            if self._cancelled:
                return

            # Step 2: Transcribe via Groq Whisper API for precise ground-truth audio timing
            self.log.emit("🎙️ Groq Whisper ile ses çözümleniyor (Milisaniyelik konuşma zamanları çıkarılıyor)...")
            try:
                trans_client = GroqTranscriptionClient(api_key=api_key)
                audio_segments = trans_client.transcribe(temp_audio)
            except Exception as exc:
                self.failed.emit(f"Groq Transkript Hatası: {exc}")
                return

            if not audio_segments and not trans_segments:
                self.failed.emit("Videoda konuşma/ses transkripti tespit edilemedi.")
                return

            active_segments = trans_segments if trans_segments else audio_segments
            self.log.emit(f"✅ Toplam {len(active_segments)} diyalog satırı ve ses zamanlaması çözümlendi.")
            self.progress.emit(50)
            if self._cancelled:
                return

            # Step 3: Scene Selection via Groq LLM
            self.log.emit("🧠 Groq AI (Llama 3.3 70B) ile sahne analizi ve prompt değerlendirmesi yapılıyor...")
            formatted_transcript = format_transcript_for_llm(active_segments)
            scene_info = select_scene_with_groq_llm(
                api_key=api_key,
                transcript_text=formatted_transcript,
                user_prompt=self._prompt,
                target_duration_sec=self._target_duration_sec,
            )

            start_sec = scene_info.get("start_sec", 0.0)
            end_sec = scene_info.get("end_sec", start_sec + self._target_duration_sec)
            clip_title = scene_info.get("title", "AI Clip")
            reasoning = scene_info.get("reasoning", "")
            hook = scene_info.get("hook_sentence", "")

            m_s, s_s = divmod(start_sec, 60)
            m_e, s_e = divmod(end_sec, 60)
            self.log.emit(f"🎯 Tespit Edilen Sahne: {int(m_s):02d}:{s_s:04.1f} ➔ {int(m_e):02d}:{s_e:04.1f} ({end_sec - start_sec:.1f} sn)")
            if reasoning:
                self.log.emit(f"💡 AI Gerekçesi: {reasoning}")
            if hook:
                self.log.emit(f"🎣 Vurucu Cümle (Hook): '{hook}'")

            self.progress.emit(70)
            if self._cancelled:
                return

            # Step 4: Subtitle Generation & Turkish Dubbing Synchronization
            ass_path_to_use: Path | None = None
            if "Altyazısız" not in self._subtitle_style:
                if trans_segments and audio_segments:
                    self.log.emit("⚡ Dublaj çeviriniz videodaki gerçek ses konuşma anlarıyla senkronize ediliyor...")
                    from videcook.core.ai_editor import align_translation_to_audio_segments
                    tr_segments = align_translation_to_audio_segments(
                        api_key=api_key,
                        audio_segments=audio_segments,
                        translation_segments=trans_segments,
                        start_sec=start_sec,
                        end_sec=end_sec,
                    )
                elif trans_segments:
                    tr_segments = [s for s in trans_segments if s.end >= start_sec + 0.4 and s.start <= end_sec]
                else:
                    clip_segments = [s for s in audio_segments if s.end >= start_sec + 0.4 and s.start <= end_sec]
                    self.log.emit("🇹🇷 Altyazılar Türkçe dublaj diline çevriliyor...")
                    from videcook.core.ai_editor import translate_segments_to_turkish_with_groq
                    tr_segments = translate_segments_to_turkish_with_groq(api_key, clip_segments)

                self.log.emit("✍️ Büyük vurgulu Türkçe altyazı stili oluşturuluyor...")
                is_blurred = "Bulanık" in self._aspect_ratio or "Blur" in self._aspect_ratio
                sub_ok = generate_ass_subtitles(
                    segments=tr_segments,
                    start_sec=start_sec,
                    end_sec=end_sec,
                    style=self._subtitle_style,
                    ass_path=temp_ass,
                    is_blurred_bg=is_blurred,
                    aspect_ratio_str=self._aspect_ratio,
                )
                if sub_ok and temp_ass.is_file():
                    ass_path_to_use = temp_ass

            if self._cancelled:
                return

            # Step 4.5: Background Music Detection & Fetching
            bg_music_path: Path | None = None
            from videcook.core.bg_music import detect_music_category_from_prompt, fetch_or_get_music_track
            music_category = detect_music_category_from_prompt(self._prompt)
            if music_category:
                self.log.emit(f"🎵 Arka plan edit müziği aranıyor ({music_category})...")
                bg_music_path = fetch_or_get_music_track(music_category)
                if bg_music_path and bg_music_path.is_file():
                    self.log.emit(f"🎧 Fon Müziği Hazırlandı: {bg_music_path.name} (Ses Miksleme Aktif)")
                else:
                    self.log.emit("⚠️ Çevrimiçi fon müziği indirilemedi, varsayılan ses ile devam ediliyor.")

            if self._cancelled:
                return

            # Step 5: Render Video with MoviePy
            self.log.emit(f"🎬 MoviePy motoru ile video kurgulanıyor (En Boy Oranı: {self._aspect_ratio})...")
            stem_clean = re.sub(r'[^\w\-]', '_', self._video_path.stem)[:30]
            base_name = f"{stem_clean}_edit_shorts"
            self._output_dir.mkdir(parents=True, exist_ok=True)

            output_file = self._output_dir / f"{base_name}.mp4"
            if output_file.exists():
                counter = 1
                while (self._output_dir / f"{base_name}_{counter}.mp4").exists():
                    counter += 1
                output_file = self._output_dir / f"{base_name}_{counter}.mp4"

            from videcook.core.moviepy_editor import render_edit_with_moviepy

            def on_moviepy_log(msg: str) -> None:
                if not self._cancelled:
                    self.log.emit(msg)

            success = render_edit_with_moviepy(
                video_path=self._video_path,
                output_path=output_file,
                start_sec=start_sec,
                end_sec=end_sec,
                aspect_ratio_str=self._aspect_ratio,
                ass_subtitle_path=ass_path_to_use,
                bg_music_path=bg_music_path,
                progress_callback=on_moviepy_log,
            )

            if self._cancelled:
                self.failed.emit("İşlem kullanıcı tarafından iptal edildi.")
                return

            if not success or not output_file.is_file():
                self.failed.emit("MoviePy video kurgulama işlemi tamamlanamadı.")
                return

            self.progress.emit(100)
            self.log.emit(f"🎉 Başarıyla Tamamlandı: {output_file.name}")
            self.finished.emit(str(output_file))

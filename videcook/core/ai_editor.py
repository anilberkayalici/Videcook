"""AI Editor Core Engine — Video extraction, Groq LLM scene selection, subtitle generation, and FFmpeg render."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from videcook.core.subtitles import SubtitleSegment
from videcook.services.groq_transcription import GroqTranscriptionClient


def extract_audio_from_video(video_path: Path, output_audio: Path, ffmpeg_path: Path) -> bool:
    """Extract audio stream as 16kHz mono MP3 or WAV file for Whisper transcription."""
    if not video_path.is_file() or not ffmpeg_path.is_file():
        return False

    output_audio.parent.mkdir(parents=True, exist_ok=True)
    is_mp3 = output_audio.suffix.lower() == ".mp3"

    cmd = [
        str(ffmpeg_path),
        "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
    ]
    if is_mp3:
        cmd.extend(["-c:a", "libmp3lame", "-b:a", "64k"])
    else:
        cmd.extend(["-c:a", "pcm_s16le"])

    cmd.append(str(output_audio))

    kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

    try:
        proc = subprocess.run(cmd, timeout=120, **kwargs)
        return proc.returncode == 0 and output_audio.is_file() and output_audio.stat().st_size > 0
    except Exception:
        return False


def format_transcript_for_llm(segments: list[SubtitleSegment]) -> str:
    """Format subtitle segments into time-stamped text lines for LLM analysis."""
    lines: list[str] = []
    for seg in segments:
        m_start, s_start = divmod(seg.start, 60)
        h_start, m_start = divmod(m_start, 60)
        m_end, s_end = divmod(seg.end, 60)
        h_end, m_end = divmod(m_end, 60)

        t_start = f"{int(h_start):02d}:{int(m_start):02d}:{s_start:05.2f}"
        t_end = f"{int(h_end):02d}:{int(m_end):02d}:{s_end:05.2f}"
        lines.append(f"[{t_start} -> {t_end}] ({seg.start:.1f}s - {seg.end:.1f}s): {seg.text}")

    return "\n".join(lines)


def select_scene_with_groq_llm(
    api_key: str,
    transcript_text: str,
    user_prompt: str,
    target_duration_sec: int = 30,
) -> dict[str, Any]:
    """Query Groq LLM (Llama 3.3 70B) to select start_sec and end_sec based on user prompt."""
    from groq import Groq

    client = Groq(api_key=api_key)

    system_prompt = (
        "You are an expert viral video editor, dubbing producer, and social media creator.\n"
        "Your job is to analyze a timestamped video transcript and select the SINGLE BEST contiguous time window\n"
        "that satisfies the user's prompt (e.g. funny scene, action, dramatic dialogue, hook).\n"
        "Rules:\n"
        "1. Identify start_sec and end_sec in float seconds matching transcript timestamps.\n"
        f"2. The duration (end_sec - start_sec) should be ideally around {target_duration_sec} seconds (between 10s and 60s).\n"
        "3. Select complete natural sentences so cuts sound smooth and not truncated.\n"
        "4. Output MUST be ONLY valid JSON matching this exact structure without markdown backticks:\n"
        "{\n"
        '  "start_sec": <float>,\n'
        '  "end_sec": <float>,\n'
        '  "title": "<short clip title in Turkish>",\n'
        '  "reasoning": "<explanation in Turkish why this scene was selected>",\n'
        '  "hook_sentence": "<key line in Turkish>"\n'
        "}"
    )

    user_content = (
        f"User Edit Request / Prompt: {user_prompt}\n"
        f"Target Clip Duration: ~{target_duration_sec} seconds\n\n"
        f"Timestamped Video Transcript:\n{transcript_text[:12000]}"
    )

    models_to_try = [
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-20b",
        "groq/compound",
    ]

    for model in models_to_try:
        try:
            resp = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                model=model,
                temperature=0.2,
                max_tokens=500,
            )
            raw = (resp.choices[0].message.content or "").strip()
            # Clean JSON codeblock wrappers if present
            raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"```$", "", raw, flags=re.MULTILINE).strip()

            data = json.loads(raw)
            start_sec = float(data.get("start_sec", 0))
            end_sec = float(data.get("end_sec", start_sec + target_duration_sec))
            if end_sec > start_sec and (end_sec - start_sec) >= 5:
                return {
                    "start_sec": max(0.0, start_sec),
                    "end_sec": end_sec,
                    "title": data.get("title", "AI Clip"),
                    "reasoning": data.get("reasoning", "İstemle eşleşen en uygun sahne seçildi."),
                    "hook_sentence": data.get("hook_sentence", ""),
                }
        except Exception:
            continue

    # Fallback if API or JSON parsing fails
    return {
        "start_sec": 0.0,
        "end_sec": float(target_duration_sec),
        "title": "Varsayılan Klip",
        "reasoning": "Varsayılan başlangıç aralığı kullanıldı.",
        "hook_sentence": "",
    }


def translate_segments_to_turkish_with_groq(
    api_key: str,
    segments: list[SubtitleSegment],
) -> list[SubtitleSegment]:
    """Translate subtitle segments into natural conversational Turkish dubbing lines using Groq LLM."""
    if not segments or not api_key:
        return segments

    from groq import Groq

    client = Groq(api_key=api_key)
    input_items = [{"id": idx, "text": seg.text.strip()} for idx, seg in enumerate(segments)]
    system_prompt = (
        "You are an expert Turkish animation dubbing translator for GCK Studio (Gecekondu Dublaj).\n"
        "Translate the given dialogue lines into natural, conversational, punchy Turkish (Metal Family / Animation Dubbing style).\n"
        "Rules:\n"
        "1. Make it sound natural, emotional, and colloquial Turkish as spoken in Turkish dubbing.\n"
        "2. Keep it concise, expressive, and matched to character emotion.\n"
        "3. NEVER output sound effect descriptions, laughter words (e.g. 'kahkaha', 'gülüşme', 'hahaha', 'ahahah'), or screaming tags. If a line is only laughter or screaming, return empty string \"\" for that id.\n"
        "4. Output MUST be ONLY a valid JSON array in this exact format without markdown:\n"
        "[\n"
        '  {"id": 0, "turkish_text": "..."},\n'
        '  {"id": 1, "turkish_text": "..."}\n'
        "]"
    )

    models_to_try = [
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-20b",
        "groq/compound",
    ]

    from videcook.services.groq_transcription import clean_non_speech_text

    for model in models_to_try:
        try:
            resp = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(input_items, ensure_ascii=False)},
                ],
                model=model,
                temperature=0.3,
                max_tokens=2000,
            )
            raw = (resp.choices[0].message.content or "").strip()
            raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"```$", "", raw, flags=re.MULTILINE).strip()

            data = json.loads(raw)
            trans_map = {item["id"]: item["turkish_text"] for item in data if "id" in item and "turkish_text" in item}

            translated_segments: list[SubtitleSegment] = []
            for idx, seg in enumerate(segments):
                raw_tr = trans_map.get(idx, seg.text)
                cleaned_tr = clean_non_speech_text(raw_tr)
                if cleaned_tr and len(cleaned_tr) >= 2:
                    translated_segments.append(SubtitleSegment(start=seg.start, end=seg.end, text=cleaned_tr))
            return translated_segments
        except Exception:
            continue

    return [s for s in segments if clean_non_speech_text(s.text)]


def align_translation_to_audio_segments(
    api_key: str,
    audio_segments: list[SubtitleSegment],
    translation_segments: list[SubtitleSegment],
    start_sec: float,
    end_sec: float,
) -> list[SubtitleSegment]:
    """Map human Turkish dubbing script lines to the exact millisecond audio speech timestamps for the cut scene."""
    audio_clip = [s for s in audio_segments if s.end >= start_sec - 0.2 and s.start <= end_sec + 0.2]
    trans_clip = [s for s in translation_segments if s.end >= start_sec - 8.0 and s.start <= end_sec + 8.0]

    if not audio_clip or not trans_clip or not api_key:
        return [s for s in translation_segments if s.end >= start_sec + 0.4 and s.start <= end_sec]

    from groq import Groq
    from videcook.services.groq_transcription import clean_non_speech_text

    client = Groq(api_key=api_key)

    audio_items = [{"id": i, "start": round(s.start, 2), "end": round(s.end, 2), "audio_speech": s.text.strip()} for i, s in enumerate(audio_clip)]
    trans_items = [{"id": j, "start": round(t.start, 2), "turkish_line": t.text.strip()} for j, t in enumerate(trans_clip)]

    system_prompt = (
        "You are an expert audio-to-subtitle synchronizer for Turkish animation dubbing.\n"
        "Given:\n"
        "1. Audio speech segments with EXACT millisecond audio timestamps from the video:\n"
        f"{json.dumps(audio_items, ensure_ascii=False)}\n"
        "2. Authentic human Turkish dubbing script lines:\n"
        f"{json.dumps(trans_items, ensure_ascii=False)}\n\n"
        "Task:\n"
        "Match each audio speech segment (by id 0, 1, 2...) to its corresponding Turkish dubbing dialogue line.\n"
        "Rules:\n"
        "- If an audio segment is laughter, screaming, or non-verbal, set 'turkish_text' to empty string \"\".\n"
        "- The dialogue must match the character action and timeline.\n"
        "- Return ONLY a valid JSON array in this exact format:\n"
        "[\n"
        '  {"id": 0, "turkish_text": "..."},\n'
        '  {"id": 1, "turkish_text": "..."}\n'
        "]"
    )

    models_to_try = [
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-20b",
    ]

    for model in models_to_try:
        try:
            resp = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Match the audio segments to the corresponding Turkish dubbing lines."},
                ],
                model=model,
                temperature=0.1,
                max_tokens=2000,
            )
            raw = (resp.choices[0].message.content or "").strip()
            raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"```$", "", raw, flags=re.MULTILINE).strip()

            data = json.loads(raw)
            matched_map = {item["id"]: item["turkish_text"] for item in data if "id" in item and "turkish_text" in item}

            aligned_segments: list[SubtitleSegment] = []
            for i, a_seg in enumerate(audio_clip):
                tr_txt = matched_map.get(i, "").strip()
                cleaned = clean_non_speech_text(tr_txt)
                if cleaned and len(cleaned) >= 2:
                    aligned_segments.append(SubtitleSegment(start=a_seg.start, end=a_seg.end, text=cleaned))

            if aligned_segments:
                return aligned_segments
        except Exception:
            continue

    return [s for s in translation_segments if s.end >= start_sec + 0.4 and s.start <= end_sec]


def format_text_into_balanced_lines(text: str, max_line_words: int = 3) -> str:
    """Format short sentence into 1 or 2 balanced lines matching Gecekondu / GCK Studio reels."""
    clean = text.replace("\n", " ").strip()
    words = clean.split()
    if len(words) <= max_line_words:
        return clean
    mid = (len(words) + 1) // 2
    return " ".join(words[:mid]) + "\\N" + " ".join(words[mid:])


def split_segment_into_short_phrases(
    segment: SubtitleSegment,
    max_words_per_phrase: int = 4,
) -> list[SubtitleSegment]:
    """Break long multi-sentence or paragraph segments into short punchy subtitle lines with proportional word-weighted timestamps."""
    from videcook.services.groq_transcription import clean_non_speech_text
    raw_text = clean_non_speech_text(segment.text.strip())
    if not raw_text or len(raw_text) < 2:
        return []

    # Split by sentence ending punctuation and commas
    raw_parts = re.split(r'(?<=[.!?])\s+', raw_text)
    phrases: list[str] = []

    for part in raw_parts:
        part = clean_non_speech_text(part.strip())
        if not part or len(part) < 2:
            continue
        words = part.split()
        if len(words) <= max_words_per_phrase:
            phrases.append(part)
        else:
            # Chunk long sentences into 3-4 words per line
            for i in range(0, len(words), max_words_per_phrase):
                chunk = " ".join(words[i:i + max_words_per_phrase])
                if chunk and len(chunk) >= 2:
                    phrases.append(chunk)

    if not phrases:
        return []

    duration = max(0.6, segment.end - segment.start)
    total_words = max(1, sum(len(p.split()) for p in phrases))

    result: list[SubtitleSegment] = []
    cur_start = segment.start
    for phr in phrases:
        p_words = max(1, len(phr.split()))
        p_dur = duration * (p_words / total_words)
        p_end = cur_start + p_dur
        result.append(SubtitleSegment(start=cur_start, end=p_end, text=phr))
        cur_start = p_end

    return result


def generate_ass_subtitles(
    segments: list[SubtitleSegment],
    start_sec: float,
    end_sec: float,
    style: str = "Metal Family",
    ass_path: Path | None = None,
    is_blurred_bg: bool = False,
    aspect_ratio_str: str = "9:16",
) -> bool:
    """Generate styled ASS subtitles centered and timed relative to the video clip with uniform large sizing across all aspect ratios."""
    if not ass_path:
        return False

    clip_segments: list[SubtitleSegment] = []
    for seg in segments:
        # Ignore previous-scene tail segments that ended right as cut started
        if seg.end < start_sec + 0.4:
            continue
        if seg.start > end_sec:
            continue

        # Subdivide long sentences into short punchy phrases (2-4 words per subtitle card)
        sub_phrases = split_segment_into_short_phrases(seg)
        for sub_p in sub_phrases:
            if sub_p.end < start_sec + 0.3 or sub_p.start > end_sec:
                continue

            rel_start = max(0.0, sub_p.start - start_sec)
            rel_end = min(end_sec - start_sec, sub_p.end - start_sec)

            if rel_end > rel_start + 0.25 and sub_p.text.strip():
                clip_segments.append(SubtitleSegment(start=rel_start, end=rel_end, text=sub_p.text.strip()))

    if not clip_segments:
        return False

    # Sort segments and ensure no overlapping collisions
    clip_segments.sort(key=lambda s: s.start)
    for i in range(len(clip_segments) - 1):
        if clip_segments[i].end > clip_segments[i + 1].start:
            clip_segments[i].end = max(clip_segments[i].start + 0.3, clip_segments[i + 1].start - 0.05)

    is_metal_family = "Metal Family" in style or "Metal" in style or "Gecekondu" in style
    is_capcut = "CapCut" in style or "Vurgulu" in style

    # Calculate exact canvas resolution (PlayResX, PlayResY) & MarginV for the selected aspect ratio
    if "1:1" in aspect_ratio_str or "Kare" in aspect_ratio_str:
        play_res_x = 1080
        play_res_y = 1080
        margin_v = 120
    elif "16:9" in aspect_ratio_str or "Yatay" in aspect_ratio_str:
        play_res_x = 1920
        play_res_y = 1080
        margin_v = 90
    elif "4:5" in aspect_ratio_str:
        play_res_x = 1080
        play_res_y = 1350
        margin_v = 160
    else:
        # 9:16 Dikey / 9:16 Bulanık Arka Plan
        play_res_x = 1080
        play_res_y = 1920
        margin_v = 580 if is_blurred_bg else 240

    header = (
        "[Script Info]\n"
        "Title: Videcook AI Edit Subtitles\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "YCbCr Matrix: None\n"
        f"PlayResX: {play_res_x}\n"
        f"PlayResY: {play_res_y}\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
    )

    if is_metal_family:
        # Gecekondu / Metal Family style: Extra Large Bold White with 7px Black Outline (Exact GCK Studio style)
        styles = (
            f"Style: Default,Arial,92,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
            f"-1,0,0,0,100,100,0,0,1,7,2.5,2,40,40,{margin_v},1\n\n"
        )
    elif is_capcut:
        # CapCut style: Extra Large Bold Yellow with 6px Black Outline
        styles = (
            f"Style: Default,Arial,86,&H0000FFFF,&H000000FF,&H00000000,&H80000000,"
            f"-1,0,0,0,100,100,0,0,1,6,2,2,40,40,{margin_v},1\n\n"
        )
    else:
        # Classic style: Large Bold White with Black Outline
        styles = (
            f"Style: Default,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
            f"-1,0,0,0,100,100,0,0,1,5,2,2,30,30,{margin_v},1\n\n"
        )

    events = "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    dialogue_lines: list[str] = []

    for seg in clip_segments:
        m_start, s_start = divmod(seg.start, 60)
        h_start, m_start = divmod(m_start, 60)
        m_end, s_end = divmod(seg.end, 60)
        h_end, m_end = divmod(m_end, 60)

        t_start = f"{int(h_start):01d}:{int(m_start):02d}:{s_start:05.2f}"
        t_end = f"{int(h_end):01d}:{int(m_end):02d}:{s_end:05.2f}"

        formatted_text = format_text_into_balanced_lines(seg.text, max_line_words=3)
        if is_metal_family:
            formatted_text = f"{{\\b1\\c&H00FFFFFF&\\3c&H00000000&}}{formatted_text}"
        elif is_capcut:
            formatted_text = f"{{\\b1\\c&H0000FFFF&\\3c&H00000000&}}{formatted_text}"

        dialogue_lines.append(f"Dialogue: 0,{t_start},{t_end},Default,,0,0,0,,{formatted_text}")

    content = header + styles + events + "\n".join(dialogue_lines) + "\n"
    ass_path.write_text(content, encoding="utf-8")
    return True


def build_edit_ffmpeg_command(
    video_path: Path,
    output_path: Path,
    start_sec: float,
    end_sec: float,
    aspect_ratio_str: str,
    ass_subtitle_path: Path | None,
    ffmpeg_path: Path,
    bg_music_path: Path | None = None,
) -> list[str]:
    """Build FFmpeg command line for trimming, cropping aspect ratio, burning ASS subtitles, and optional background music mixing."""
    from videcook.core.bg_music import build_edit_ffmpeg_command_with_bg_music

    return build_edit_ffmpeg_command_with_bg_music(
        video_path=video_path,
        output_path=output_path,
        start_sec=start_sec,
        end_sec=end_sec,
        aspect_ratio_str=aspect_ratio_str,
        ass_subtitle_path=ass_subtitle_path,
        bg_music_path=bg_music_path,
        ffmpeg_path=ffmpeg_path,
    )

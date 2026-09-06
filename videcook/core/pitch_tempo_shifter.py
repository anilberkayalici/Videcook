"""Core audio engine for Pitch (Transpose) and Tempo (Time-Stretching) manipulation.

Leverages FFmpeg with the native librubberband audio DSP filter to deliver
high-fidelity pitch shifting and time stretching with formant and transient preservation.
"""

from __future__ import annotations

import ctypes
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import List, Optional, Tuple

import numpy as np

from videcook.core.audio_analyzer import CAMELOT_MAP, PITCH_CLASSES, load_audio_pcm
from videcook.services.binary_locator import get_ffmpeg_path

ENHARMONIC_MAP = {
    "Db": "C#",
    "Eb": "D#",
    "Gb": "F#",
    "Ab": "G#",
    "Bb": "A#",
}


def transpose_musical_key(root: str, mode: str, semitones: int) -> Tuple[str, str, str]:
    """Transposes a musical root and mode by a given number of semitones.

    Returns:
        (new_root, new_mode, new_camelot_code)
        e.g. ("C", "Minor", +2) -> ("D", "Minor", "7A")
    """
    clean_root = root.strip().capitalize()
    clean_root = ENHARMONIC_MAP.get(clean_root, clean_root)
    if clean_root not in PITCH_CLASSES:
        clean_root = "C"

    idx = PITCH_CLASSES.index(clean_root)
    new_idx = (idx + semitones) % 12
    new_root = PITCH_CLASSES[new_idx]
    new_mode = "Major" if mode.capitalize().startswith("Maj") else "Minor"
    new_camelot = CAMELOT_MAP.get((new_root, new_mode), "8B")
    return new_root, new_mode, new_camelot


def calculate_harmonic_match(
    src_root: str,
    src_mode: str,
    ref_root: str,
    ref_mode: str,
) -> Tuple[int, str]:
    """Calculates the musically optimal semitone shift to harmonically match a source audio

    to a reference track based on the Camelot Wheel and Harmonic Mixing theory.

    Returns:
        (optimal_semitones, match_description)
        e.g. (+4, "Relatif Majör (C Majör - Camelot 8B / Tam Uyum)")
    """
    clean_src = ENHARMONIC_MAP.get(src_root.strip().capitalize(), src_root.strip().capitalize())
    clean_ref = ENHARMONIC_MAP.get(ref_root.strip().capitalize(), ref_root.strip().capitalize())

    if clean_src not in PITCH_CLASSES:
        clean_src = "C"
    if clean_ref not in PITCH_CLASSES:
        clean_ref = "C"

    src_idx = PITCH_CLASSES.index(clean_src)
    ref_idx = PITCH_CLASSES.index(clean_ref)

    src_is_maj = src_mode.capitalize().startswith("Maj")
    ref_is_maj = ref_mode.capitalize().startswith("Maj")

    if src_is_maj == ref_is_maj:
        # Same mode: directly match the root key with shortest chromatic distance (-6 to +6)
        diff = (ref_idx - src_idx) % 12
        if diff > 6:
            diff -= 12
        mode_str = "Majör" if ref_is_maj else "Minör"
        camelot = CAMELOT_MAP.get((clean_ref, "Major" if ref_is_maj else "Minor"), "")
        cam_str = f" ({camelot})" if camelot else ""
        return diff, f"Birebir Ton ({clean_ref} {mode_str}{cam_str})"

    # Different mode: match using Relative Major / Relative Minor (Zero harmonic dissonance)
    if not ref_is_maj:
        # Reference is Minor, Source is Major: Relative Major of a Minor is +3 semitones
        target_idx = (ref_idx + 3) % 12
        target_root = PITCH_CLASSES[target_idx]
        diff = (target_idx - src_idx) % 12
        if diff > 6:
            diff -= 12
        camelot = CAMELOT_MAP.get((target_root, "Major"), "")
        cam_str = f" ({camelot})" if camelot else ""
        return diff, f"Relatif Majör ({target_root} Majör{cam_str} — Camelot Uyumlu)"
    else:
        # Reference is Major, Source is Minor: Relative Minor of a Major is -3 semitones
        target_idx = (ref_idx - 3) % 12
        target_root = PITCH_CLASSES[target_idx]
        diff = (target_idx - src_idx) % 12
        if diff > 6:
            diff -= 12
        camelot = CAMELOT_MAP.get((target_root, "Minor"), "")
        cam_str = f" ({camelot})" if camelot else ""
        return diff, f"Relatif Minör ({target_root} Minör{cam_str} — Camelot Uyumlu)"


def calculate_optimal_bpm_match(src_bpm: float, ref_bpm: float) -> Tuple[float, str]:
    """Calculates the musically optimal matching BPM considering half-time, normal, and double-time.

    Prevents chipmunk/turbo speeds (e.g. 73.6 BPM vs 171 BPM matches to 85.5 BPM half-time).

    Returns:
        (best_target_bpm, match_description)
    """
    candidates = [
        (ref_bpm * 0.5, "Yarım Zaman (Half-Time)"),
        (ref_bpm * 1.0, "Birebir Tempo (1x)"),
        (ref_bpm * 2.0, "Çift Zaman (Double-Time)"),
    ]
    # Filter candidates that stay within reasonable music range (40 - 260 BPM)
    valid_candidates = [c for c in candidates if 40.0 <= c[0] <= 260.0] or candidates
    # Pick the candidate that minimizes speed ratio distance from 1.0x
    best_bpm, best_desc = min(valid_candidates, key=lambda c: abs((c[0] / max(1.0, src_bpm)) - 1.0))
    ratio = best_bpm / max(1.0, src_bpm)
    pct = (ratio - 1.0) * 100.0
    sign = "+" if pct > 0 else ""
    return best_bpm, f"{best_desc} ➔ {best_bpm:.1f} BPM ({sign}{pct:.1f}%)"


def render_pitch_tempo_audio(
    input_file: Path,
    output_file: Path,
    semitones: float = 0.0,
    tempo_ratio: float = 1.0,
    preserve_formant: bool = True,
    duration_limit: Optional[float] = None,
    start_offset: float = 0.0,
    ffmpeg_path: Optional[Path] = None,
) -> Path:
    """Renders an audio file with pitch and tempo transformations using librubberband.

    Includes studio brickwall limiter protection to guarantee zero clipping or distortion.

    Args:
        input_file: Source audio path.
        output_file: Destination output path.
        semitones: Pitch shift in semitones (e.g. -12.0 to +12.0).
        tempo_ratio: Speed/tempo multiplier (e.g. 1.129 for +12.9%, 0.5 for half tempo).
        preserve_formant: Whether to keep human vocal naturalness intact.
        duration_limit: Optional snippet duration limit in seconds.
        start_offset: Optional start offset in seconds.
        ffmpeg_path: Optional explicit path to FFmpeg binary.

    Returns:
        Path to rendered output file.
    """
    if not input_file.is_file():
        raise FileNotFoundError(f"Input audio file not found: {input_file}")

    ff = ffmpeg_path or get_ffmpeg_path()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Calculate ratios
    pitch_scale = 2.0 ** (float(semitones) / 12.0)
    tempo_scale = max(0.1, min(10.0, float(tempo_ratio)))

    is_passthrough = (abs(semitones) < 0.001 and abs(tempo_ratio - 1.0) < 0.001)

    cmd = [str(ff), "-y"]

    if start_offset > 0.0:
        cmd.extend(["-ss", f"{start_offset:.3f}"])

    cmd.extend(["-i", str(input_file)])

    if duration_limit is not None and duration_limit > 0.0:
        cmd.extend(["-t", f"{duration_limit:.3f}"])

    if not is_passthrough:
        formant_opt = ":formant=preserved" if preserve_formant else ":formant=shifted"
        # High quality rubberband with studio-grade lookahead limiter to prevent clipping/distortion
        rb_filter = (
            f"rubberband=pitch={pitch_scale:.6f}:tempo={tempo_scale:.6f}"
            f":pitchq=quality:transients=crisp{formant_opt}"
            f",alimiter=limit=0.98:attack=5:release=50:asc=true"
        )
        cmd.extend(["-filter:a", rb_filter])

    # If destination is WAV, specify high quality PCM codec
    if output_file.suffix.lower() == ".wav":
        cmd.extend(["-c:a", "pcm_s16le"])
    elif output_file.suffix.lower() == ".mp3":
        cmd.extend(["-c:a", "libmp3lame", "-b:a", "320k"])

    cmd.append(str(output_file))

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg pitch/tempo render failed: {proc.stderr[:400]}")

    return output_file


def generate_preview_snippet(
    input_file: Path,
    semitones: float = 0.0,
    tempo_ratio: float = 1.0,
    preserve_formant: bool = True,
    duration_seconds: float = 6.0,
    start_offset: float = 0.0,
) -> Path:
    """Generates a fast temporary WAV snippet for live playback preview."""
    temp_dir = Path(tempfile.gettempdir())
    temp_preview = temp_dir / f"videcook_preview_{os.getpid()}_{int(time.time() * 1000) % 1000000}.wav"
    return render_pitch_tempo_audio(
        input_file=input_file,
        output_file=temp_preview,
        semitones=semitones,
        tempo_ratio=tempo_ratio,
        preserve_formant=preserve_formant,
        duration_limit=duration_seconds,
        start_offset=start_offset,
    )


def extract_waveform_peaks(file_path: Path, num_bars: int = 160) -> List[float]:
    """Fast extraction of normalized amplitude peaks across an audio file for waveform display.

    Downsamples audio to 8000Hz mono and computes peak amplitude for each bucket.
    Returns a list of float values in [0.08, 1.0].
    """
    if not file_path.is_file():
        return [0.15] * num_bars

    try:
        # Load up to 10 minutes at 8kHz (low memory, very fast ~0.08s)
        y = load_audio_pcm(file_path, sample_rate=8000, max_duration_sec=600.0)
        if y.size == 0:
            return [0.15] * num_bars

        # Divide into num_bars chunks
        chunk_size = max(1, len(y) // num_bars)
        peaks: List[float] = []

        for i in range(num_bars):
            start = i * chunk_size
            end = min(len(y), start + chunk_size)
            if start >= len(y):
                peaks.append(0.08)
                continue

            chunk = y[start:end]
            if len(chunk) > 0:
                val = float(np.max(np.abs(chunk)))
            else:
                val = 0.08
            peaks.append(val)

        # Normalize peaks
        max_p = max(peaks) if peaks else 1.0
        if max_p > 0.001:
            norm_peaks = [max(0.08, min(1.0, p / max_p)) for p in peaks]
        else:
            norm_peaks = [0.15] * num_bars

        return norm_peaks
    except Exception:
        # Fallback gentle curve
        return [0.15 + 0.3 * abs(math.sin(i * 0.1)) for i in range(num_bars)]


import threading


class MCIAudioPlayer:
    """Windows MCI-based audio player with sub-second seeking and position tracking."""

    def __init__(self, alias: Optional[str] = None) -> None:
        self.alias = alias or f"vc_player_{os.getpid()}_{int(time.time() * 1000) % 10000}"
        self._is_open = False
        self._is_playing = False
        self._current_file: Optional[Path] = None
        self._lock = threading.RLock()

    def _send(self, command: str) -> Tuple[int, str]:
        if os.name != "nt":
            return 0, ""
        try:
            buf = ctypes.create_unicode_buffer(256)
            res = ctypes.windll.winmm.mciSendStringW(command, buf, 256, 0)
            return res, buf.value
        except Exception:
            return -1, ""

    def is_playing(self) -> bool:
        if not self._is_open:
            return False
        res, val = self._send(f"status {self.alias} mode")
        return res == 0 and "playing" in val.lower()

    def get_position_ms(self) -> int:
        """Returns current playback position in milliseconds."""
        if not self._is_open:
            return 0
        res, val = self._send(f"status {self.alias} position")
        if res == 0 and val.isdigit():
            return int(val)
        return 0

    def play_wav(self, wav_path: Path, from_ms: int = 0) -> bool:
        """Loads and plays a WAV file starting at `from_ms`."""
        with self._lock:
            self.stop()
            if not wav_path.is_file():
                return False

            self._current_file = wav_path
            self._send(f"close {self.alias}")
            res, _ = self._send(f'open "{wav_path}" type waveaudio alias {self.alias}')
            if res == 0:
                self._is_open = True
                self._send(f"set {self.alias} time format milliseconds")
                play_res, _ = self._send(f"play {self.alias} from {from_ms}")
                self._is_playing = (play_res == 0)
                return self._is_playing
            return False

    def pause(self) -> None:
        with self._lock:
            if self._is_open:
                self._send(f"pause {self.alias}")
                self._is_playing = False

    def resume(self) -> None:
        with self._lock:
            if self._is_open:
                self._send(f"resume {self.alias}")
                self._is_playing = True

    def stop(self) -> None:
        with self._lock:
            if self._is_open:
                self._send(f"stop {self.alias}")
                self._send(f"close {self.alias}")
                self._is_open = False
                self._is_playing = False

    def cleanup(self) -> None:
        self.stop()
        if self._current_file and self._current_file.is_file():
            try:
                self._current_file.unlink(missing_ok=True)
            except Exception:
                pass
            self._current_file = None


class AudioPreviewPlayer:
    """Fallback asynchronous audio player."""

    def __init__(self) -> None:
        self._player = MCIAudioPlayer()

    @property
    def is_playing(self) -> bool:
        return self._player.is_playing()

    def play_wav(self, wav_path: Path, from_ms: int = 0) -> None:
        self._player.play_wav(wav_path, from_ms=from_ms)

    def stop(self) -> None:
        self._player.stop()

    def cleanup(self) -> None:
        self._player.cleanup()

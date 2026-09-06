"""Audio analysis core module for BPM (tempo) and Musical Key (scale) detection.

Uses FFmpeg for ultra-fast PCM audio decoding and NumPy for digital signal processing
(Spectral Flux + Autocorrelation for tempo, Chromagram + Krumhansl-Schmuckler for key).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
import numpy as np

from videcook.services.binary_locator import get_ffmpeg_path

# Standard 12 chromatic pitch classes
PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Krumhansl-Schmuckler key profiles for tonal hierarchy
KRUMHANSL_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KRUMHANSL_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

# Camelot Wheel mapping for DJ & harmonic mixing
CAMELOT_MAP = {
    ("C", "Major"): "8B", ("A", "Minor"): "8A",
    ("G", "Major"): "9B", ("E", "Minor"): "9A",
    ("D", "Major"): "10B", ("B", "Minor"): "10A",
    ("A", "Major"): "11B", ("F#", "Minor"): "11A",
    ("E", "Major"): "12B", ("C#", "Minor"): "12A",
    ("B", "Major"): "1B", ("G#", "Minor"): "1A",
    ("F#", "Major"): "2B", ("D#", "Minor"): "2A",
    ("C#", "Major"): "3B", ("A#", "Minor"): "3A",
    ("G#", "Major"): "4B", ("F", "Minor"): "4A",
    ("D#", "Major"): "5B", ("C", "Minor"): "5A",
    ("A#", "Major"): "6B", ("G", "Minor"): "6A",
    ("F", "Major"): "7B", ("D", "Minor"): "7A",
}


@dataclass
class AudioAnalysisResult:
    """Dataclass holding extracted musical and technical parameters."""
    file_path: Path
    bpm: float
    bpm_half: float
    bpm_double: float
    key_root: str
    key_mode: str
    camelot_code: str
    sample_rate: int
    channels: int
    duration_sec: float
    format_name: str
    bitrate_kbps: int

    @property
    def key_display(self) -> str:
        return f"{self.key_root} {self.key_mode}"

    @property
    def summary_tag(self) -> str:
        cam = f" ({self.camelot_code})" if self.camelot_code else ""
        return f"{round(self.bpm)} BPM - {self.key_display}{cam}"


def probe_audio_metadata(file_path: Path) -> dict:
    """Probe technical audio parameters via FFprobe/FFmpeg."""
    ffmpeg = get_ffmpeg_path()
    ffprobe = ffmpeg.parent / ("ffprobe.exe" if ffmpeg.name.endswith(".exe") else "ffprobe")
    if not ffprobe.is_file():
        ffprobe = ffmpeg

    cmd = [
        str(ffprobe),
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(file_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(proc.stdout)
        fmt = data.get("format", {})
        streams = data.get("streams", [])
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

        sr = int(a_stream.get("sample_rate", 44100))
        ch = int(a_stream.get("channels", 2))
        dur = float(fmt.get("duration", 0.0))
        br = int(int(fmt.get("bit_rate", 0)) / 1000)
        ext = file_path.suffix.lstrip(".").upper()

        return {
            "sample_rate": sr,
            "channels": ch,
            "duration_sec": dur,
            "format_name": ext or "AUDIO",
            "bitrate_kbps": br,
        }
    except Exception:
        return {
            "sample_rate": 44100,
            "channels": 2,
            "duration_sec": 0.0,
            "format_name": file_path.suffix.lstrip(".").upper() or "AUDIO",
            "bitrate_kbps": 0,
        }


def load_audio_pcm(file_path: Path, sample_rate: int = 22050, max_duration_sec: float = 90.0) -> np.ndarray:
    """Decode mono 32-bit float PCM audio samples using FFmpeg."""
    ffmpeg = get_ffmpeg_path()
    cmd = [
        str(ffmpeg),
        "-i", str(file_path),
        "-t", str(max_duration_sec),
        "-ac", "1",
        "-ar", str(sample_rate),
        "-f", "f32le",
        "-vn",
        "-loglevel", "error",
        "-",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return np.frombuffer(proc.stdout, dtype=np.float32)


def detect_bpm(y: np.ndarray, sr: int = 22050) -> float:
    """Detect tempo (BPM) from audio onset envelope autocorrelation."""
    if len(y) < sr * 2:
        return 120.0

    hop_length = 512
    n_fft = 1024

    # Generate Hanning windowed frames
    n_frames = (len(y) - n_fft) // hop_length
    if n_frames < 20:
        return 120.0

    frames = np.array([y[i * hop_length: i * hop_length + n_fft] * np.hanning(n_fft) for i in range(n_frames)])
    stft = np.abs(np.fft.rfft(frames, axis=1))

    # Spectral flux (half-wave rectified difference between consecutive frames)
    diff = np.diff(stft, axis=0)
    onset_env = np.sum(np.maximum(0, diff), axis=1)

    if len(onset_env) < 50:
        return 120.0

    # Normalization
    onset_env = onset_env - np.mean(onset_env)
    std = np.std(onset_env)
    if std > 0:
        onset_env /= std

    # Autocorrelation
    corr = np.correlate(onset_env, onset_env, mode="full")
    corr = corr[len(corr) // 2:]

    frame_rate = sr / hop_length
    # Range of human tempos: 65 to 195 BPM
    min_bpm, max_bpm = 65, 195
    min_lag = int(frame_rate * 60 / max_bpm)
    max_lag = int(frame_rate * 60 / min_bpm)

    if max_lag >= len(corr):
        max_lag = len(corr) - 1

    if min_lag >= max_lag:
        return 120.0

    search_region = corr[min_lag:max_lag]
    best_offset = int(np.argmax(search_region))
    best_lag = min_lag + best_offset

    # Parabolic peak interpolation for sub-frame accuracy
    if 0 < best_offset < len(search_region) - 1:
        alpha = search_region[best_offset - 1]
        beta = search_region[best_offset]
        gamma = search_region[best_offset + 1]
        denom = alpha - 2 * beta + gamma
        if denom != 0:
            delta = 0.5 * (alpha - gamma) / denom
            best_lag += delta

    bpm = (frame_rate * 60.0) / best_lag
    return round(float(bpm), 1)


def detect_musical_key(y: np.ndarray, sr: int = 22050) -> tuple[str, str, str]:
    """Detect musical key (root, mode, camelot) using chromagram & Krumhansl-Schmuckler profiles."""
    if len(y) < sr * 2:
        return "C", "Major", "8B"

    n_fft = 4096
    hop = 1024
    n_frames = (len(y) - n_fft) // hop
    if n_frames < 10:
        return "C", "Major", "8B"

    frames = np.array([y[i * hop: i * hop + n_fft] * np.hanning(n_fft) for i in range(n_frames)])
    stft = np.abs(np.fft.rfft(frames, axis=1))
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

    chroma = np.zeros(12)
    # Focus on fundamental musical pitch range (65 Hz - 2000 Hz)
    valid = (freqs >= 65) & (freqs <= 2000)
    valid_freqs = freqs[valid]
    semitones = np.round(12 * np.log2(valid_freqs / 440.0) + 69).astype(int) % 12

    mag_sum = np.sum(stft[:, valid], axis=0)
    for semi, mag in zip(semitones, mag_sum):
        chroma[semi] += mag

    c_mean = np.mean(chroma)
    c_std = np.std(chroma)
    if c_std > 0:
        chroma = (chroma - c_mean) / c_std

    best_score = -1e9
    best_root = "C"
    best_mode = "Major"

    for i in range(12):
        # Major correlation
        maj_profile = np.roll(KRUMHANSL_MAJOR, i)
        maj_norm = (maj_profile - np.mean(maj_profile)) / np.std(maj_profile)
        r_maj = float(np.dot(chroma, maj_norm))
        if r_maj > best_score:
            best_score = r_maj
            best_root = PITCH_CLASSES[i]
            best_mode = "Major"

        # Minor correlation
        min_profile = np.roll(KRUMHANSL_MINOR, i)
        min_norm = (min_profile - np.mean(min_profile)) / np.std(min_profile)
        r_min = float(np.dot(chroma, min_norm))
        if r_min > best_score:
            best_score = r_min
            best_root = PITCH_CLASSES[i]
            best_mode = "Minor"

    camelot = CAMELOT_MAP.get((best_root, best_mode), "")
    return best_root, best_mode, camelot


def analyze_audio_file(file_path: Path) -> AudioAnalysisResult:
    """Execute complete technical and musical analysis for a given audio file."""
    if not file_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    meta = probe_audio_metadata(file_path)
    pcm = load_audio_pcm(file_path, sample_rate=22050, max_duration_sec=90.0)

    bpm = detect_bpm(pcm, sr=22050)
    root, mode, camelot = detect_musical_key(pcm, sr=22050)

    return AudioAnalysisResult(
        file_path=file_path,
        bpm=bpm,
        bpm_half=round(bpm / 2.0, 1),
        bpm_double=round(bpm * 2.0, 1),
        key_root=root,
        key_mode=mode,
        camelot_code=camelot,
        sample_rate=meta["sample_rate"],
        channels=meta["channels"],
        duration_sec=meta["duration_sec"],
        format_name=meta["format_name"],
        bitrate_kbps=meta["bitrate_kbps"],
    )

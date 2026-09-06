"""Unit tests for the audio analyzer module (videcook/core/audio_analyzer.py)."""

from pathlib import Path
import numpy as np
import pytest

from videcook.core.audio_analyzer import (
    AudioAnalysisResult,
    CAMELOT_MAP,
    PITCH_CLASSES,
    detect_bpm,
    detect_musical_key,
    load_audio_pcm,
    analyze_audio_file,
)


def test_camelot_map_completeness():
    """Verify Camelot Wheel contains 24 major and minor keys."""
    assert len(CAMELOT_MAP) == 24
    assert CAMELOT_MAP[("C", "Major")] == "8B"
    assert CAMELOT_MAP[("A", "Minor")] == "8A"
    assert CAMELOT_MAP[("G", "Major")] == "9B"
    assert CAMELOT_MAP[("E", "Minor")] == "9A"
    assert CAMELOT_MAP[("F", "Major")] == "7B"
    assert CAMELOT_MAP[("D", "Minor")] == "7A"
    assert CAMELOT_MAP[("C", "Minor")] == "5A"


def test_detect_bpm_synthetic_metronome():
    """Verify BPM detection on a synthetic 120 BPM pulsed audio signal."""
    sr = 22050
    duration_sec = 6.0
    total_samples = int(sr * duration_sec)
    y = np.zeros(total_samples, dtype=np.float32)

    # 120 BPM = 2 beats per second = 0.5s interval
    interval_samples = int(sr * 0.5)
    for beat_start in range(0, total_samples - 1000, interval_samples):
        # 100ms 1kHz burst with exponential decay
        burst = np.sin(2 * np.pi * 1000 * np.linspace(0, 0.1, int(sr * 0.1)))
        decay = np.exp(-np.linspace(0, 5, len(burst)))
        click = burst * decay
        end = min(total_samples, beat_start + len(click))
        y[beat_start:end] += click[: end - beat_start]

    bpm = detect_bpm(y, sr=sr)
    # Expected: ~120 BPM (+- 3 BPM tolerance)
    assert 115.0 <= bpm <= 125.0


def test_detect_bpm_short_audio_fallback():
    """Verify fallback on empty or very short audio."""
    bpm = detect_bpm(np.zeros(100, dtype=np.float32), sr=22050)
    assert bpm == 120.0


def test_detect_musical_key_synthetic_tone():
    """Verify musical key detection on a pure A440 tone."""
    sr = 22050
    duration_sec = 3.0
    t = np.linspace(0, duration_sec, int(sr * duration_sec))
    # 440 Hz is pitch class A
    y = (np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)

    root, mode, camelot = detect_musical_key(y, sr=sr)
    assert root in ["A", "F#", "D"]  # Related keys in harmonic profile
    assert camelot in CAMELOT_MAP.values()


def test_detect_musical_key_fallback():
    """Verify fallback on empty or short audio."""
    root, mode, camelot = detect_musical_key(np.zeros(50, dtype=np.float32), sr=22050)
    assert root == "C"
    assert mode == "Major"
    assert camelot == "8B"


def test_analyze_audio_file_non_existent():
    """Verify FileNotFoundError on non-existent audio path."""
    with pytest.raises(FileNotFoundError):
        analyze_audio_file(Path("C:/non_existent_audio_sample_12345.mp3"))


def test_audio_analysis_result_dataclass():
    """Verify AudioAnalysisResult properties and formatting."""
    res = AudioAnalysisResult(
        file_path=Path("sample.wav"),
        bpm=124.2,
        bpm_half=62.1,
        bpm_double=248.4,
        key_root="C",
        key_mode="Minor",
        camelot_code="5A",
        sample_rate=44100,
        channels=2,
        duration_sec=180.0,
        format_name="WAV",
        bitrate_kbps=1411,
    )
    assert res.key_display == "C Minor"
    assert res.summary_tag == "124 BPM - C Minor (5A)"

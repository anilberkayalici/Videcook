"""Unit tests for Pitch and Tempo Shifter and Realtime Audio Engine."""

from pathlib import Path
import math
import struct
import wave
import numpy as np
import pytest

from videcook.core.pitch_tempo_shifter import (
    AudioPreviewPlayer,
    extract_waveform_peaks,
    render_pitch_tempo_audio,
    transpose_musical_key,
)
from videcook.core.realtime_audio_engine import RealtimeAudioEngine
from videcook.ui.pitch_tempo_dialog import PitchTempoDialog, WaveformWidget


def test_transpose_musical_key_positive():
    """C Minor shifted by +2 semitones should become D Minor (7A)."""
    root, mode, camelot = transpose_musical_key("C", "Minor", 2)
    assert root == "D"
    assert mode == "Minor"
    assert camelot == "7A"


def test_transpose_musical_key_negative():
    """C Minor shifted by -1 semitones should become B Minor (10A)."""
    root, mode, camelot = transpose_musical_key("C", "Minor", -1)
    assert root == "B"
    assert mode == "Minor"
    assert camelot == "10A"


def test_transpose_musical_key_full_octave():
    """Full 12 semitone shift should return the same root and mode."""
    root, mode, camelot = transpose_musical_key("A", "Minor", 12)
    assert root == "A"
    assert mode == "Minor"
    assert camelot == "8A"


def test_transpose_musical_key_enharmonic():
    """Enharmonic flat root should map correctly."""
    root, mode, camelot = transpose_musical_key("Bb", "Major", 2)
    assert root == "C"
    assert mode == "Major"
    assert camelot == "8B"


def test_render_pitch_tempo_audio_non_existent():
    """Non-existent file should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        render_pitch_tempo_audio(
            input_file=Path("C:/non_existent_file_xyz_123.wav"),
            output_file=Path("C:/dummy_out.wav"),
            semitones=2.0,
            tempo_ratio=1.1,
        )


def test_extract_waveform_peaks_fallback():
    """Extracting waveform peaks on non-existent file returns default peaks without crashing."""
    peaks = extract_waveform_peaks(Path("C:/non_existent_audio_xyz.wav"), num_bars=50)
    assert len(peaks) == 50
    assert all(0.0 <= p <= 1.0 for p in peaks)


def test_waveform_widget(qtbot):
    """WaveformWidget should store peaks and emit seek ratio on interaction."""
    widget = WaveformWidget()
    qtbot.addWidget(widget)

    dummy_peaks = [0.1, 0.5, 0.9, 0.3, 0.7]
    widget.peaks = dummy_peaks
    assert len(widget.peaks) == 5

    widget.progress = 0.45
    assert widget.progress == 0.45


def test_realtime_audio_engine_lifecycle(tmp_path):
    """RealtimeAudioEngine should load audio, extract peaks, seek, and set pitch safely."""
    dummy_wav = tmp_path / "engine_tone.wav"
    with wave.open(str(dummy_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        frames = bytearray()
        for i in range(44100):  # 1 second
            amp = int(25000 * math.sin(2 * math.pi * 440 * i / 44100))
            frames.extend(struct.pack("<h", amp))
        wf.writeframes(frames)

    engine = RealtimeAudioEngine(sample_rate=44100)
    loaded = engine.load_file(dummy_wav)
    assert loaded is True
    assert engine.duration_seconds > 0.9

    peaks = engine.get_waveform_peaks(20)
    assert len(peaks) == 20
    assert max(peaks) > 0.5

    # Test seek
    engine.seek(0.5)
    assert abs(engine.current_time_seconds - 0.5) < 0.05

    # Test pitch & tempo set
    engine.set_pitch(3.0)
    engine.set_tempo_ratio(1.2)
    assert engine.is_playing is False

    engine.close()


def test_pitch_tempo_dialog_instantiation(qtbot, tmp_path):
    """PitchTempoDialog should instantiate with controls, waveform, and default values."""
    dummy_wav = tmp_path / "sample.wav"

    with wave.open(str(dummy_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(b"\x00\x00" * 22050)  # 1 second of silence

    dialog = PitchTempoDialog(file_path=dummy_wav)
    qtbot.addWidget(dialog)

    assert dialog._pitch_slider is not None
    assert dialog._pitch_slider.value() == 0
    assert dialog._bpm_spin is not None
    assert dialog._play_btn is not None
    assert dialog._time_lbl is not None
    assert dialog._waveform is not None
    assert dialog._save_btn is not None

    # Test shifting slider to +3
    dialog._pitch_slider.setValue(3)
    assert dialog._semitones == 3
    assert "+3" in dialog._pitch_value_lbl.text()

    # Test volume slider
    assert dialog._vol_slider is not None
    dialog._vol_slider.setValue(60)
    assert abs(dialog._engine.volume - 0.6) < 0.01
    assert dialog._vol_lbl.text() == "%60"

    # Test seeking on waveform updates engine
    dialog._on_waveform_seek_requested(0.5)
    assert abs(dialog._engine.current_time_seconds - (dialog._total_duration_sec * 0.5)) < 0.1

    # Test reference matching flow
    dialog._ref_file = Path("C:/dummy_beat.wav")
    dialog._ref_bpm = 140.0
    dialog._ref_root = "A"
    dialog._ref_mode = "Minor"
    dialog._ref_camelot = "8A"
    dialog._on_apply_match_clicked()

    assert dialog._bpm_spin.value() == 140.0
    assert dialog._is_matched is True
    assert "Eşlendi" in dialog._live_status_lbl.text()

    dialog.close()


def test_calculate_harmonic_match():
    """Harmonic matching should return musically correct semitone shifts according to Camelot rules."""
    from videcook.core.pitch_tempo_shifter import calculate_harmonic_match

    # Same mode: C Major -> G Major (+7 or -5)
    semi, desc = calculate_harmonic_match("C", "Major", "G", "Major")
    assert semi == -5  # shortest chromatic shift
    assert "Birebir Ton" in desc

    # Minor reference, Major sample: A Minor ref, F Major sample
    # A Minor's relative Major is C Major (+3 from A).
    # F to C is -5 semitones.
    semi, desc = calculate_harmonic_match("F", "Major", "A", "Minor")
    assert semi == -5
    assert "Relatif Majör" in desc

    # Major reference, Minor sample: C Major ref, A Minor sample
    # C Major's relative Minor is A Minor.
    # A to A is 0 semitones!
    semi, desc = calculate_harmonic_match("A", "Minor", "C", "Major")
    assert semi == 0
    assert "Relatif Minör" in desc


def test_calculate_optimal_bpm_match():
    """BPM matching should be aware of half-time and double-time to avoid chipmunk speeds."""
    from videcook.core.pitch_tempo_shifter import calculate_optimal_bpm_match

    # Trap/HipHop: 73.6 vs 171.0 should match to 85.5 (half-time), NOT 171.0 (2.32x turbo)
    bpm, desc = calculate_optimal_bpm_match(73.6, 171.0)
    assert abs(bpm - 85.5) < 0.1
    assert "Half-Time" in desc

    # Fast track vs slow ref: 140.0 vs 72.0 should match to 144.0 (double-time)
    bpm, desc = calculate_optimal_bpm_match(140.0, 72.0)
    assert abs(bpm - 144.0) < 0.1
    assert "Double-Time" in desc

    # Similar tempos: 120.0 vs 126.0 should match directly (1x)
    bpm, desc = calculate_optimal_bpm_match(120.0, 126.0)
    assert abs(bpm - 126.0) < 0.1
    assert "1x" in desc

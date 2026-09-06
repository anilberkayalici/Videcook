"""Pitch & Tempo Shifter Dialog with Real-Time Audio Streaming (Spotify Engine).

Provides a professional FL Studio / REAPER style interactive waveform,
real-time scrubbing, seamless seek-to-position, and instant live pitch/tempo changes
using Spotify's Pedalboard DSP engine and SoundDevice.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import List, Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from videcook.core.audio_analyzer import AudioAnalysisResult, analyze_audio_file
from videcook.core.pitch_tempo_shifter import (
    calculate_harmonic_match,
    calculate_optimal_bpm_match,
    render_pitch_tempo_audio,
    transpose_musical_key,
)
from videcook.core.realtime_audio_engine import RealtimeAudioEngine


class WaveformWidget(QWidget):
    """Interactive studio waveform display widget with clickable scrubbing and glowing playhead."""

    seek_requested = Signal(float)  # emitted with ratio 0.0 -> 1.0

    def __init__(self, parent: Optional[QWidget] = None, color_scheme: str = "purple") -> None:
        super().__init__(parent)
        self.color_scheme = color_scheme
        self._peaks: List[float] = [0.15] * 130
        self._progress: float = 0.0  # 0.0 to 1.0
        self._is_dragging: bool = False

        self.setFixedHeight(64 if color_scheme == "emerald" else 72)
        self.setMinimumWidth(420)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def peaks(self) -> List[float]:
        return self._peaks

    @peaks.setter
    def peaks(self, values: List[float]) -> None:
        self._peaks = values if values else [0.15] * 130
        self.update()

    @property
    def progress(self) -> float:
        return self._progress

    @progress.setter
    def progress(self, val: float) -> None:
        self._progress = max(0.0, min(1.0, float(val)))
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._handle_mouse(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_dragging:
            self._handle_mouse(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False

    def _handle_mouse(self, event: QMouseEvent) -> None:
        w = max(1.0, float(self.width()))
        x = min(w, max(0.0, event.position().x()))
        ratio = x / w
        self._progress = ratio
        self.update()
        self.seek_requested.emit(ratio)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())

        is_em = (self.color_scheme == "emerald")

        # Background rounded card
        bg_rect = QRectF(0, 0, w, h)
        if is_em:
            painter.setPen(QPen(QColor("#065F46"), 1))
            painter.setBrush(QColor("#061A13"))
        else:
            painter.setPen(QPen(QColor("#2B1E45"), 1))
            painter.setBrush(QColor("#110C1D"))
        painter.drawRoundedRect(bg_rect, 8, 8)

        num_bars = len(self._peaks)
        if num_bars == 0:
            return

        cy = h / 2.0
        bar_spacing = w / num_bars
        bar_width = max(2.2, bar_spacing - 1.4)
        playhead_x = self._progress * w

        for i, peak in enumerate(self._peaks):
            bx = i * bar_spacing + (bar_spacing - bar_width) / 2.0
            bh = max(4.0, (h - 16.0) * peak)
            by = cy - (bh / 2.0)
            bar_rect = QRectF(bx, by, bar_width, bh)

            if bx <= playhead_x:
                # Played: Glowing gradient
                grad = QLinearGradient(bx, by, bx, by + bh)
                if is_em:
                    grad.setColorAt(0.0, QColor("#34D399"))
                    grad.setColorAt(0.5, QColor("#10B981"))
                    grad.setColorAt(1.0, QColor("#059669"))
                else:
                    grad.setColorAt(0.0, QColor("#38BDF8"))
                    grad.setColorAt(0.5, QColor("#8B5CF6"))
                    grad.setColorAt(1.0, QColor("#C084FC"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(grad)
            else:
                # Unplayed: Clean slate
                painter.setPen(Qt.PenStyle.NoPen)
                if is_em:
                    painter.setBrush(QColor(16, 75, 52, 190))
                else:
                    painter.setBrush(QColor(65, 48, 92, 200))

            painter.drawRoundedRect(bar_rect, 1.2, 1.2)

        # Playhead Needle (crisp vertical line)
        needle_color = QColor("#34D399") if is_em else QColor("#38BDF8")
        needle_pen = QPen(needle_color, 2.0)
        painter.setPen(needle_pen)
        painter.drawLine(QPointF(playhead_x, 4), QPointF(playhead_x, h - 4))

        # Playhead glowing cap
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QPointF(playhead_x, 6), 3.5, 3.5)


class RenderFullWorker(QThread):
    """Background worker for rendering full processed audio to disk using rubberband."""

    finished_render = Signal(bool, str, str)

    def __init__(
        self,
        input_file: Path,
        output_file: Path,
        semitones: float,
        tempo_ratio: float,
        preserve_formant: bool,
    ) -> None:
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.semitones = semitones
        self.tempo_ratio = tempo_ratio
        self.preserve_formant = preserve_formant

    def run(self) -> None:
        try:
            render_pitch_tempo_audio(
                input_file=self.input_file,
                output_file=self.output_file,
                semitones=self.semitones,
                tempo_ratio=self.tempo_ratio,
                preserve_formant=self.preserve_formant,
            )
            self.finished_render.emit(True, str(self.output_file), "")
        except Exception as e:
            self.finished_render.emit(False, "", str(e))


class PitchTempoDialog(QDialog):
    """Interactive Studio Dialog for adjusting Pitch & Tempo with a Live Waveform Player."""

    def __init__(
        self,
        file_path: Path,
        analysis_result: Optional[AudioAnalysisResult] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.file_path = file_path
        self._analysis = analysis_result

        # Real-time Spotify/SoundDevice engines (Main track + Reference track)
        self._engine = RealtimeAudioEngine(sample_rate=44100)
        self._ref_engine = RealtimeAudioEngine(sample_rate=44100)
        self._render_worker: Optional[RenderFullWorker] = None
        self._last_rendered_path: Optional[Path] = None

        # Audio parameters
        self._semitones: int = 0
        self._original_bpm: float = 120.0
        self._original_key_root: str = "C"
        self._original_key_mode: str = "Minor"
        self._original_camelot: str = "5A"
        self._total_duration_sec: float = 120.0

        # Reference Track (Smart Match) state
        self._ref_file: Optional[Path] = None
        self._ref_bpm: float = 120.0
        self._ref_root: str = "C"
        self._ref_mode: str = "Minor"
        self._ref_camelot: str = "5A"
        self._ref_total_duration_sec: float = 120.0
        self._is_matched: bool = False

        # UI poll timer (40ms = 25 FPS smooth playback tracking)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(40)
        self._poll_timer.timeout.connect(self._on_poll_tick)
        self._poll_timer.start()

        self.setWindowTitle("VideCook — Ton (Pitch) & BPM Değiştirici")
        self.setMinimumWidth(800)
        self.resize(880, 680)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F0B18;
                color: #F8FAFC;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel {
                color: #F1F5F9;
            }
        """)

        self._init_ui()
        self._load_initial_data()

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(8)
        root_layout.setContentsMargins(18, 14, 18, 14)

        # 1. FIXED TOP HEADER
        header_layout = QHBoxLayout()
        icon_label = QLabel("🎛️")
        icon_label.setStyleSheet("font-size: 26px;")
        header_layout.addWidget(icon_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        main_title = QLabel("Ton (Pitch) & BPM Ayarlayıcı")
        main_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #F3E8FF;")
        title_col.addWidget(main_title)

        self._file_name_lbl = QLabel(self.file_path.name)
        self._file_name_lbl.setStyleSheet("font-size: 12px; color: #A78BFA; font-weight: 600;")
        title_col.addWidget(self._file_name_lbl)
        header_layout.addLayout(title_col, stretch=1)

        # Reference Beat Button (Smart Match)
        self._ref_btn = QPushButton("🎯 Referans Beat Seç")
        self._ref_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ref_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(139, 92, 246, 0.16);
                border: 1px solid rgba(167, 139, 250, 0.45);
                border-radius: 6px;
                color: #E9D5FF;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: rgba(139, 92, 246, 0.32);
                color: #FFFFFF;
                border-color: #C084FC;
            }
        """)
        self._ref_btn.clicked.connect(self._on_choose_ref_file)
        header_layout.addWidget(self._ref_btn)

        change_file_btn = QPushButton("📁 Başka Dosya")
        change_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_file_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: #CBD5E1;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                color: #FFFFFF;
            }
        """)
        change_file_btn.clicked.connect(self._on_choose_other_file)
        header_layout.addWidget(change_file_btn)
        root_layout.addLayout(header_layout)

        # 2. SCROLLABLE MIDDLE SECTION
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #0F0B18;
                width: 7px;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #3B2D54;
                min-height: 25px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6D28D9;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(scroll_widget)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(0, 4, 6, 4)

        # Original Audio Stats Card
        orig_card = QFrame()
        orig_card.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 6px 10px;
            }
        """)
        orig_card_layout = QHBoxLayout(orig_card)
        self._orig_stats_lbl = QLabel("Orijinal Değerler Hesaplanıyor...")
        self._orig_stats_lbl.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 500;")
        orig_card_layout.addWidget(self._orig_stats_lbl)
        content_layout.addWidget(orig_card)

        # Reference Track Card (Smart Match Badge & Full Interactive Player)
        self._ref_card = QFrame()
        self._ref_card.setStyleSheet("""
            QFrame#RefCard {
                background-color: #071912;
                border: 1px solid #065F46;
                border-radius: 10px;
                padding: 10px 14px;
            }
        """)
        self._ref_card.setObjectName("RefCard")
        ref_card_layout = QVBoxLayout(self._ref_card)
        ref_card_layout.setContentsMargins(10, 8, 10, 8)
        ref_card_layout.setSpacing(6)

        # Header: Info badge + Action Buttons
        ref_header = QHBoxLayout()
        self._ref_stats_lbl = QLabel("🎯 Referans Beat:")
        self._ref_stats_lbl.setStyleSheet("font-size: 12px; color: #E9D5FF; font-weight: 600;")
        ref_header.addWidget(self._ref_stats_lbl, stretch=1)

        self._match_btn = QPushButton("✨ Otomatik Eşle (Match)")
        self._match_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._match_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B5CF6;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                font-size: 11px;
                padding: 5px 14px;
            }
            QPushButton:hover {
                background-color: #7C3AED;
            }
        """)
        self._match_btn.clicked.connect(self._on_apply_match_clicked)
        ref_header.addWidget(self._match_btn)

        self._remove_ref_btn = QPushButton("✕")
        self._remove_ref_btn.setFixedSize(22, 22)
        self._remove_ref_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remove_ref_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #CBD5E1;
                border-radius: 11px;
                font-weight: 700;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.25);
                color: #F87171;
            }
        """)
        self._remove_ref_btn.clicked.connect(self._on_remove_ref_clicked)
        ref_header.addWidget(self._remove_ref_btn)
        ref_card_layout.addLayout(ref_header)

        # Player Bar: Play/Pause, Time, Volume, Hint
        ref_player_bar = QHBoxLayout()
        self._ref_play_btn = QPushButton("▶️ Referansı Çal")
        self._ref_play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ref_play_btn.setStyleSheet(self._ref_play_btn_style(is_playing=False))
        self._ref_play_btn.clicked.connect(self._toggle_ref_playback)
        ref_player_bar.addWidget(self._ref_play_btn)

        self._ref_time_lbl = QLabel("00:00 / 00:00")
        self._ref_time_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #6EE7B7; margin-left: 6px; margin-right: 8px;")
        ref_player_bar.addWidget(self._ref_time_lbl)

        self._ref_vol_icon = QLabel("🔊")
        self._ref_vol_icon.setStyleSheet("font-size: 12px; color: #6EE7B7;")
        ref_player_bar.addWidget(self._ref_vol_icon)

        self._ref_vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._ref_vol_slider.setRange(0, 100)
        self._ref_vol_slider.setValue(80)
        self._ref_vol_slider.setFixedWidth(80)
        self._ref_vol_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ref_vol_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #064E3B;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #10B981;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 6px;
                background: #34D399;
            }
        """)
        self._ref_vol_slider.valueChanged.connect(self._on_ref_volume_changed)
        ref_player_bar.addWidget(self._ref_vol_slider)

        self._ref_vol_lbl = QLabel("%80")
        self._ref_vol_lbl.setStyleSheet("font-size: 11px; color: #A7F3D0; font-weight: 600; min-width: 32px;")
        ref_player_bar.addWidget(self._ref_vol_lbl)

        ref_player_bar.addSpacing(10)
        self._ref_status_hint = QLabel("🎯 Dalgaya tıkla ➔ referansın istediğin yerine atla")
        self._ref_status_hint.setStyleSheet("font-size: 11px; color: #6EE7B7; font-style: italic;")
        ref_player_bar.addWidget(self._ref_status_hint, stretch=1)
        ref_card_layout.addLayout(ref_player_bar)

        # Waveform Widget (Interactive seeking on click)
        self._ref_waveform = WaveformWidget(color_scheme="emerald")
        self._ref_waveform.seek_requested.connect(self._on_ref_waveform_seek_requested)
        ref_card_layout.addWidget(self._ref_waveform)

        self._ref_card.setVisible(False)
        content_layout.addWidget(self._ref_card)

        # SECTION 1: PITCH / TRANSPOSE
        pitch_box = QFrame()
        pitch_box.setStyleSheet("""
            QFrame {
                background-color: #171127;
                border: 1px solid #2D224B;
                border-radius: 10px;
                padding: 10px 14px;
            }
        """)
        pitch_layout = QVBoxLayout(pitch_box)
        pitch_layout.setSpacing(8)

        pitch_header = QHBoxLayout()
        pitch_title = QLabel("🎹 Ton (Pitch) / Transpoze")
        pitch_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #E9D5FF;")
        pitch_header.addWidget(pitch_title)

        self._pitch_value_lbl = QLabel("0 Yarı Ton (Orijinal)")
        self._pitch_value_lbl.setStyleSheet(
            "font-weight: 700; font-size: 13px; color: #38BDF8;"
        )
        pitch_header.addWidget(self._pitch_value_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        pitch_layout.addLayout(pitch_header)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(8)

        btn_minus = QPushButton("-1")
        btn_minus.setFixedSize(36, 30)
        btn_minus.setStyleSheet(self._btn_style_secondary())
        btn_minus.clicked.connect(lambda: self._set_semitones(self._semitones - 1))
        slider_row.addWidget(btn_minus)

        self._pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self._pitch_slider.setRange(-12, 12)
        self._pitch_slider.setValue(0)
        self._pitch_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._pitch_slider.setTickInterval(1)
        self._pitch_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #2D224B;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #8B5CF6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #C4B5FD;
                border: 1px solid #7C3AED;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
        """)
        self._pitch_slider.valueChanged.connect(self._set_semitones)
        slider_row.addWidget(self._pitch_slider, stretch=1)

        btn_plus = QPushButton("+1")
        btn_plus.setFixedSize(36, 30)
        btn_plus.setStyleSheet(self._btn_style_secondary())
        btn_plus.clicked.connect(lambda: self._set_semitones(self._semitones + 1))
        slider_row.addWidget(btn_plus)

        btn_reset_pitch = QPushButton("Sıfırla")
        btn_reset_pitch.setFixedHeight(30)
        btn_reset_pitch.setStyleSheet(self._btn_style_secondary())
        btn_reset_pitch.clicked.connect(lambda: self._set_semitones(0))
        slider_row.addWidget(btn_reset_pitch)
        pitch_layout.addLayout(slider_row)

        sub_pitch_row = QHBoxLayout()
        self._target_key_lbl = QLabel("➔ Hedef Ton: C Minor (5A)")
        self._target_key_lbl.setStyleSheet(
            "font-weight: 700; font-size: 13px; color: #4ADE80; background: rgba(74, 222, 128, 0.08); padding: 3px 8px; border-radius: 4px;"
        )
        sub_pitch_row.addWidget(self._target_key_lbl)

        self._formant_cb = QCheckBox("Vokal Doğallığını Koru (Formant)")
        self._formant_cb.setChecked(True)
        self._formant_cb.setStyleSheet("""
            QCheckBox {
                color: #CBD5E1;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 1px solid #64748B;
            }
            QCheckBox::indicator:checked {
                background-color: #8B5CF6;
                border-color: #A78BFA;
            }
        """)
        sub_pitch_row.addWidget(self._formant_cb, alignment=Qt.AlignmentFlag.AlignRight)
        pitch_layout.addLayout(sub_pitch_row)

        # SECTION 2: TEMPO / BPM
        tempo_box = QFrame()
        tempo_box.setStyleSheet("""
            QFrame {
                background-color: #171127;
                border: 1px solid #2D224B;
                border-radius: 10px;
                padding: 10px 14px;
            }
        """)
        tempo_layout = QVBoxLayout(tempo_box)
        tempo_layout.setSpacing(8)

        tempo_header = QHBoxLayout()
        tempo_title = QLabel("⚡ Hız & Tempo (BPM)")
        tempo_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #E9D5FF;")
        tempo_header.addWidget(tempo_title)

        self._speed_percent_lbl = QLabel("Hız Farkı: %0.0 (1.0x)")
        self._speed_percent_lbl.setStyleSheet(
            "font-weight: 700; font-size: 13px; color: #F59E0B;"
        )
        tempo_header.addWidget(self._speed_percent_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        tempo_layout.addLayout(tempo_header)

        bpm_row = QHBoxLayout()
        bpm_row.setSpacing(8)

        bpm_label = QLabel("Hedef BPM:")
        bpm_label.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 600;")
        bpm_row.addWidget(bpm_label)

        self._bpm_spin = QDoubleSpinBox()
        self._bpm_spin.setRange(20.0, 350.0)
        self._bpm_spin.setDecimals(1)
        self._bpm_spin.setValue(self._original_bpm)
        self._bpm_spin.setSingleStep(1.0)
        self._bpm_spin.setFixedHeight(32)
        self._bpm_spin.setMinimumWidth(95)
        self._bpm_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #0F0B18;
                color: #F8FAFC;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 4px 8px;
                font-weight: 700;
                font-size: 13px;
            }
            QDoubleSpinBox:focus {
                border: 1px solid #8B5CF6;
            }
        """)
        self._bpm_spin.valueChanged.connect(self._on_bpm_spin_changed)
        bpm_row.addWidget(self._bpm_spin)

        btn_half = QPushButton("½ Yarım (x0.5)")
        btn_half.setFixedHeight(32)
        btn_half.setStyleSheet(self._btn_style_secondary())
        btn_half.clicked.connect(lambda: self._bpm_spin.setValue(self._original_bpm * 0.5))
        bpm_row.addWidget(btn_half)

        btn_double = QPushButton("2x Çift (x2.0)")
        btn_double.setFixedHeight(32)
        btn_double.setStyleSheet(self._btn_style_secondary())
        btn_double.clicked.connect(lambda: self._bpm_spin.setValue(self._original_bpm * 2.0))
        bpm_row.addWidget(btn_double)

        btn_reset_bpm = QPushButton("1x Orijinal")
        btn_reset_bpm.setFixedHeight(32)
        btn_reset_bpm.setStyleSheet(self._btn_style_secondary())
        btn_reset_bpm.clicked.connect(lambda: self._bpm_spin.setValue(self._original_bpm))
        bpm_row.addWidget(btn_reset_bpm)
        tempo_layout.addLayout(bpm_row)

        # Side-by-Side Dual Studio Controls (Pitch + Tempo)
        controls_row = QHBoxLayout()
        controls_row.setSpacing(10)
        controls_row.addWidget(pitch_box, stretch=1)
        controls_row.addWidget(tempo_box, stretch=1)
        content_layout.addLayout(controls_row)

        # SECTION 3: INTERACTIVE WAVEFORM & REAL-TIME AUDIO PLAYER
        player_box = QFrame()
        player_box.setStyleSheet("""
            QFrame {
                background-color: #171127;
                border: 1px solid #38295C;
                border-radius: 10px;
                padding: 10px 14px;
            }
        """)
        player_layout = QVBoxLayout(player_box)
        player_layout.setSpacing(8)

        player_top = QHBoxLayout()

        self._play_btn = QPushButton("▶️ Oynat")
        self._play_btn.setFixedHeight(34)
        self._play_btn.setMinimumWidth(100)
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._play_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                font-size: 13px;
                padding: 4px 14px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        self._play_btn.clicked.connect(self._toggle_playback)
        player_top.addWidget(self._play_btn)

        self._time_lbl = QLabel("00:00 / 00:00")
        self._time_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 700; color: #38BDF8; margin-left: 8px;"
        )
        player_top.addWidget(self._time_lbl)

        # Volume slider control
        vol_box = QHBoxLayout()
        vol_box.setSpacing(5)
        vol_box.setContentsMargins(12, 0, 0, 0)

        self._vol_icon = QLabel("🔊")
        self._vol_icon.setStyleSheet("font-size: 13px;")
        vol_box.addWidget(self._vol_icon)

        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(80)
        self._vol_slider.setFixedWidth(80)
        self._vol_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self._vol_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #2D224B;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #38BDF8;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 1px solid #0284C7;
                width: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 6px;
            }
        """)
        self._vol_slider.valueChanged.connect(self._on_volume_changed)
        vol_box.addWidget(self._vol_slider)

        self._vol_lbl = QLabel("%80")
        self._vol_lbl.setStyleSheet("font-size: 11px; color: #94A3B8; font-weight: 600; min-width: 28px;")
        vol_box.addWidget(self._vol_lbl)

        player_top.addLayout(vol_box)

        self._live_status_lbl = QLabel("Dalgaya tıkla ➔ istediğin yere atla")
        self._live_status_lbl.setStyleSheet("font-size: 11px; color: #94A3B8; font-style: italic;")
        player_top.addWidget(self._live_status_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        player_layout.addLayout(player_top)

        # Custom Waveform Widget
        self._waveform = WaveformWidget()
        self._waveform.seek_requested.connect(self._on_waveform_seek_requested)
        player_layout.addWidget(self._waveform)

        content_layout.addWidget(player_box)

        scroll_area.setWidget(scroll_widget)
        root_layout.addWidget(scroll_area, stretch=1)

        # Progress bar for saving
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1E1B2E;
                border-radius: 2px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #8B5CF6;
                border-radius: 2px;
            }
        """)
        self._progress_bar.setVisible(False)
        root_layout.addWidget(self._progress_bar)

        # Bottom Action Buttons (PINNED TO BOTTOM - ALWAYS VISIBLE)
        bottom_actions = QHBoxLayout()
        bottom_actions.setSpacing(10)

        self._save_btn = QPushButton("💾 Yeni Haliyle Kaydet")
        self._save_btn.setFixedHeight(42)
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setStyleSheet("""
            QPushButton {
                background-color: #7C3AED;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                padding: 6px 20px;
            }
            QPushButton:hover {
                background-color: #6D28D9;
            }
            QPushButton:disabled {
                background-color: #4C1D95;
                color: #A78BFA;
            }
        """)
        self._save_btn.clicked.connect(self._on_save_clicked)
        bottom_actions.addWidget(self._save_btn, stretch=1)

        self._reveal_btn = QPushButton("📂 Klasörde Göster")
        self._reveal_btn.setFixedHeight(42)
        self._reveal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reveal_btn.setStyleSheet(self._btn_style_secondary())
        self._reveal_btn.setVisible(False)
        self._reveal_btn.clicked.connect(self._on_reveal_clicked)
        bottom_actions.addWidget(self._reveal_btn)

        root_layout.addLayout(bottom_actions)

    def _btn_style_secondary(self) -> str:
        return """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                color: #CBD5E1;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                color: #FFFFFF;
            }
        """

    def _load_initial_data(self) -> None:
        if self._analysis:
            self._apply_analysis_result(self._analysis)
        else:
            try:
                res = analyze_audio_file(self.file_path)
                self._apply_analysis_result(res)
            except Exception:
                self._orig_stats_lbl.setText("Orijinal: 120.0 BPM — C Minor (5A)")
                self._original_bpm = 120.0
                self._original_key_root = "C"
                self._original_key_mode = "Minor"
                self._original_camelot = "5A"
                self._total_duration_sec = 120.0
                self._bpm_spin.setValue(120.0)
                self._update_readouts()

        # Load audio into Realtime RAM engine
        self._engine.load_file(self.file_path)
        self._total_duration_sec = max(1.0, self._engine.duration_seconds)

        # Extract authentic waveform peaks in 5ms from RAM
        peaks = self._engine.get_waveform_peaks(num_bars=130)
        self._waveform.peaks = peaks
        self._waveform.progress = 0.0
        self._update_time_label()

    def _apply_analysis_result(self, res: AudioAnalysisResult) -> None:
        self._analysis = res
        self._original_bpm = res.bpm
        self._original_key_root = res.key_root
        self._original_key_mode = res.key_mode
        self._original_camelot = res.camelot_code
        self._total_duration_sec = max(1.0, res.duration_sec)

        self._orig_stats_lbl.setText(
            f"Orijinal Parça: ⚡ {res.bpm:.1f} BPM  |  🎹 {res.key_display}  |  🎛️ Camelot: {res.camelot_code}  |  ⏳ {int(res.duration_sec)} sn"
        )
        self._bpm_spin.setValue(self._original_bpm)
        self._update_readouts()

    def _set_semitones(self, value: int) -> None:
        self._semitones = max(-12, min(12, int(value)))
        if self._pitch_slider.value() != self._semitones:
            self._pitch_slider.blockSignals(True)
            self._pitch_slider.setValue(self._semitones)
            self._pitch_slider.blockSignals(False)
        self._update_readouts()

        # Instant live pitch update in Spotify engine (0ms latency!)
        self._engine.set_pitch(float(self._semitones))
        if self._engine.is_playing:
            self._live_status_lbl.setText(f"🎵 Canlı Ton: {self._target_key_lbl.text().split('➔')[-1].strip()}")

    def _on_bpm_spin_changed(self, value: float) -> None:
        self._update_readouts()
        ratio = value / max(1.0, self._original_bpm)
        # Instant live tempo update in Spotify engine (0ms latency!)
        self._engine.set_tempo_ratio(ratio)
        if self._engine.is_playing:
            self._live_status_lbl.setText(f"⚡ Canlı Hız: {ratio:.2f}x")

    def _update_readouts(self) -> None:
        sign = "+" if self._semitones > 0 else ""
        if self._semitones == 0:
            self._pitch_value_lbl.setText("0 Yarı Ton (Orijinal)")
        else:
            self._pitch_value_lbl.setText(f"{sign}{self._semitones} Yarı Ton")

        new_root, new_mode, new_camelot = transpose_musical_key(
            self._original_key_root,
            self._original_key_mode,
            self._semitones,
        )
        self._target_key_lbl.setText(f"➔ Hedef Ton: {new_root} {new_mode} ({new_camelot})")

        target_bpm = self._bpm_spin.value()
        ratio = target_bpm / max(1.0, self._original_bpm)
        pct_diff = (ratio - 1.0) * 100.0
        pct_sign = "+" if pct_diff > 0 else ""
        self._speed_percent_lbl.setText(f"Hız Çarpanı: {ratio:.2f}x ({pct_sign}{pct_diff:.1f}%)")

    def _update_time_label(self) -> None:
        def fmt(s: float) -> str:
            m = int(s) // 60
            sec = int(s) % 60
            return f"{m:02d}:{sec:02d}"

        cur_sec = self._engine.current_time_seconds
        cur = fmt(cur_sec)
        tot = fmt(self._total_duration_sec)
        self._time_lbl.setText(f"{cur} / {tot}")

    # ------------------------------------------------------------------
    # Live Waveform & Playback Controls
    # ------------------------------------------------------------------

    def _on_waveform_seek_requested(self, ratio: float) -> None:
        """Called when user clicks anywhere on the waveform -> 0ms instant jump!"""
        seek_sec = ratio * self._total_duration_sec
        self._engine.seek(seek_sec)
        self._update_time_label()

        if self._engine.is_playing:
            self._live_status_lbl.setText(f"➔ {int(seek_sec)} sn")
        else:
            self._live_status_lbl.setText(f"Konum: {int(seek_sec)} sn (Oynat'a bas)")

    def _toggle_playback(self) -> None:
        if self._engine.is_playing:
            self._pause_playback()
        else:
            self._start_playback()

    def _start_playback(self) -> None:
        # Pause reference playback if active
        if self._ref_engine.is_playing:
            self._ref_engine.pause()
            self._ref_play_btn.setText("▶️ Referansı Çal")
            self._ref_play_btn.setStyleSheet(self._ref_play_btn_style(is_playing=False))

        # Apply current pitch and tempo settings before starting
        target_bpm = self._bpm_spin.value()
        ratio = target_bpm / max(1.0, self._original_bpm)
        self._engine.set_pitch(float(self._semitones))
        self._engine.set_tempo_ratio(ratio)

        self._engine.play()

        self._play_btn.setText("⏸️ Duraklat")
        self._play_btn.setStyleSheet("""
            QPushButton {
                background-color: #F59E0B;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                font-size: 13px;
                padding: 4px 14px;
            }
            QPushButton:hover {
                background-color: #D97706;
            }
        """)
        self._live_status_lbl.setText("🎵 Canlı Çalınıyor")

    def _pause_playback(self) -> None:
        self._engine.pause()
        cur_sec = int(self._engine.current_time_seconds)

        self._play_btn.setText("▶️ Oynat")
        self._play_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                font-size: 13px;
                padding: 4px 14px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        self._live_status_lbl.setText(f"Duraklatıldı ({cur_sec} sn)")

    def _on_poll_tick(self) -> None:
        """Runs every 40ms to track playback progress smoothly."""
        # Poll reference playback progress
        if self._ref_engine.is_playing:
            ref_cur = self._ref_engine.current_time_seconds
            ref_tot = max(1.0, self._ref_total_duration_sec)
            self._ref_waveform.progress = ref_cur / ref_tot
            c_int = int(ref_cur)
            t_int = int(ref_tot)
            self._ref_time_lbl.setText(f"{c_int//60:02d}:{c_int%60:02d} / {t_int//60:02d}:{t_int%60:02d}")
            if ref_cur >= ref_tot and ref_tot > 0:
                self._ref_engine.pause()
                self._ref_play_btn.setText("▶️ Referansı Çal")
                self._ref_play_btn.setStyleSheet(self._ref_play_btn_style(is_playing=False))

        # Poll main playback progress
        if not self._engine.is_playing:
            if self._play_btn.text() != "▶️ Oynat" and not self._engine.is_playing:
                self._pause_playback()
            return

        cur_sec = self._engine.current_time_seconds
        tot_sec = max(1.0, self._total_duration_sec)

        self._waveform.progress = cur_sec / tot_sec
        self._update_time_label()

    def _on_volume_changed(self, val: int) -> None:
        vol = max(0.0, min(1.0, val / 100.0))
        self._engine.set_volume(vol)
        self._vol_lbl.setText(f"%{val}")
        if val == 0:
            self._vol_icon.setText("🔇")
        elif val < 45:
            self._vol_icon.setText("🔉")
        else:
            self._vol_icon.setText("🔊")

    def _on_ref_volume_changed(self, val: int) -> None:
        vol = max(0.0, min(1.0, val / 100.0))
        self._ref_engine.set_volume(vol)
        self._ref_vol_lbl.setText(f"%{val}")
        if val == 0:
            self._ref_vol_icon.setText("🔇")
        elif val < 45:
            self._ref_vol_icon.setText("🔉")
        else:
            self._ref_vol_icon.setText("🔊")

    def _on_ref_waveform_seek_requested(self, ratio: float) -> None:
        seek_sec = ratio * self._ref_total_duration_sec
        self._ref_engine.seek(seek_sec)
        tot = int(self._ref_total_duration_sec)
        cur = int(seek_sec)
        self._ref_time_lbl.setText(f"{cur//60:02d}:{cur%60:02d} / {tot//60:02d}:{tot%60:02d}")
        self._ref_waveform.progress = ratio
        if self._ref_engine.is_playing:
            self._live_status_lbl.setText(f"🎯 Referans Konumu: {int(seek_sec)} sn")
        else:
            self._live_status_lbl.setText(f"🎯 Referans Konumu: {int(seek_sec)} sn (Referansı Çal'a bas)")

    def _ref_play_btn_style(self, is_playing: bool = False) -> str:
        if is_playing:
            return """
                QPushButton {
                    background-color: #D97706;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    font-weight: 700;
                    font-size: 11px;
                    padding: 5px 12px;
                }
                QPushButton:hover {
                    background-color: #B45309;
                }
            """
        return """
            QPushButton {
                background-color: #059669;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                font-size: 11px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """

    def _toggle_ref_playback(self) -> None:
        """Toggles playback of the reference track with mutual exclusion against main track."""
        if not self._ref_file:
            return

        if self._engine.is_playing:
            self._pause_playback()

        if self._ref_engine.is_playing:
            self._ref_engine.pause()
            self._ref_play_btn.setText("▶️ Referansı Çal")
            self._ref_play_btn.setStyleSheet(self._ref_play_btn_style(is_playing=False))
            self._live_status_lbl.setText("Referans beat duraklatıldı")
        else:
            self._ref_engine.play()
            self._ref_play_btn.setText("⏸️ Durdur")
            self._ref_play_btn.setStyleSheet(self._ref_play_btn_style(is_playing=True))
            self._live_status_lbl.setText("🎵 Referans beat dinleniyor (Orijinal)")

    def _on_choose_ref_file(self) -> None:
        ref_file_str, _ = QFileDialog.getOpenFileName(
            self,
            "Referans Beat / Parça Seç (Uydurmak İstediğin Proje)",
            str(self.file_path.parent),
            "Ses Dosyaları (*.wav *.mp3 *.flac *.opus *.m4a *.aac *.ogg);;Tüm Dosyalar (*.*)",
        )
        if not ref_file_str:
            return

        ref_path = Path(ref_file_str)
        self._live_status_lbl.setText("⏳ Referans beat analiz ediliyor...")

        try:
            res = analyze_audio_file(ref_path)
            self._ref_file = ref_path
            self._ref_bpm = res.bpm
            self._ref_root = res.key_root
            self._ref_mode = res.key_mode
            self._ref_camelot = res.camelot_code

            # Load into reference audio engine & extract peaks for interactive waveform
            self._ref_engine.load_file(ref_path)
            self._ref_total_duration_sec = max(1.0, self._ref_engine.duration_seconds)
            peaks = self._ref_engine.get_waveform_peaks(130)
            self._ref_waveform.peaks = peaks
            self._ref_waveform.progress = 0.0

            ref_tot = int(self._ref_total_duration_sec)
            self._ref_time_lbl.setText(f"00:00 / {ref_tot//60:02d}:{ref_tot%60:02d}")
            self._ref_play_btn.setText("▶️ Referansı Çal")
            self._ref_play_btn.setStyleSheet(self._ref_play_btn_style(is_playing=False))

            # Smart harmonic key & half/double-time BPM match calculation
            opt_semi, key_desc = calculate_harmonic_match(
                self._original_key_root,
                self._original_key_mode,
                self._ref_root,
                self._ref_mode,
            )
            best_bpm, bpm_desc = calculate_optimal_bpm_match(self._original_bpm, self._ref_bpm)

            sign = "+" if opt_semi > 0 else ""
            semi_str = f"{sign}{opt_semi}" if opt_semi != 0 else "0"

            self._ref_stats_lbl.setText(
                f"🎯 Referans: <b>{ref_path.name[:24]}</b>  |  ⚡ {res.bpm:.1f} BPM  |  🎹 {res.key_display} ({res.camelot_code})<br>"
                f"<span style='color: #34D399; font-size: 11px;'>➔ Akıllı Uyum: <b>{semi_str} Yarı Ton</b> ({key_desc})  |  ⚡ <b>{bpm_desc}</b></span>"
            )
            self._ref_card.setVisible(True)
            self._live_status_lbl.setText("🎯 Referans beat hazır! Dalga boyuna tıklayıp dinleyebilir veya eşleyebilirsin.")
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Referans dosya analiz edilemedi:\n{e}")
            self._live_status_lbl.setText("❌ Referans analiz hatası")

    def _on_apply_match_clicked(self) -> None:
        if not self._ref_file:
            return

        opt_semi, key_desc = calculate_harmonic_match(
            self._original_key_root,
            self._original_key_mode,
            self._ref_root,
            self._ref_mode,
        )
        best_bpm, bpm_desc = calculate_optimal_bpm_match(self._original_bpm, self._ref_bpm)

        # Apply optimal pitch shift
        self._set_semitones(opt_semi)

        # Apply musically optimal BPM (half-time / double-time aware)
        self._bpm_spin.setValue(best_bpm)

        self._is_matched = True
        sign = "+" if opt_semi > 0 else ""
        semi_str = f"{sign}{opt_semi}" if opt_semi != 0 else "0"
        bpm_short = bpm_desc.split("➔")[0].strip()
        self._live_status_lbl.setText(f"✨ Akıllı Eşlendi: {semi_str} Yarı Ton ({key_desc}) & {best_bpm:.1f} BPM ({bpm_short})")

    def _on_remove_ref_clicked(self) -> None:
        self._ref_engine.pause()
        self._ref_file = None
        self._is_matched = False
        self._ref_card.setVisible(False)
        self._live_status_lbl.setText("Referans beat kaldırıldı")

    # ------------------------------------------------------------------
    # Save & Export
    # ------------------------------------------------------------------

    def _on_save_clicked(self) -> None:
        self._pause_playback()

        target_bpm = self._bpm_spin.value()
        new_root, new_mode, _ = transpose_musical_key(
            self._original_key_root,
            self._original_key_mode,
            self._semitones,
        )

        stem = self.file_path.stem
        if self._is_matched and self._ref_file:
            ref_name_clean = self._ref_file.stem[:18].strip()
            tag = f"[{int(round(target_bpm))} BPM - {new_root} {new_mode} - Matched to {ref_name_clean}]"
        else:
            tag = f"[{int(round(target_bpm))} BPM - {new_root} {new_mode}]"

        default_out_name = f"{stem} {tag}{self.file_path.suffix}"
        default_dir = self.file_path.parent

        save_path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Yeni Parçayı Kaydet",
            str(default_dir / default_out_name),
            "Ses Dosyaları (*.wav *.mp3);;WAV Ses (*.wav);;MP3 Ses (*.mp3)",
        )
        if not save_path_str:
            return

        out_path = Path(save_path_str)
        self._live_status_lbl.setText("⏳ Yeni ton ve tempoda stüdyo kalitesinde işleniyor...")
        self._progress_bar.setVisible(True)
        self._save_btn.setEnabled(False)

        tempo_ratio = target_bpm / max(1.0, self._original_bpm)
        preserve_formant = self._formant_cb.isChecked()

        self._render_worker = RenderFullWorker(
            input_file=self.file_path,
            output_file=out_path,
            semitones=self._semitones,
            tempo_ratio=tempo_ratio,
            preserve_formant=preserve_formant,
        )
        self._render_worker.finished_render.connect(self._on_render_finished)
        self._render_worker.start()

    def _on_render_finished(self, success: bool, out_path_str: str, err: str) -> None:
        self._progress_bar.setVisible(False)
        self._save_btn.setEnabled(True)

        if success and out_path_str:
            self._last_rendered_path = Path(out_path_str)
            self._live_status_lbl.setText(f"✨ Stüdyo Kalitesinde Kaydedildi: {self._last_rendered_path.name}")
            self._reveal_btn.setVisible(True)
        else:
            self._live_status_lbl.setText("❌ Hata oluştu.")
            QMessageBox.warning(self, "Hata", f"Ses işlenirken hata oluştu:\n{err}")

    def _on_reveal_clicked(self) -> None:
        if not self._last_rendered_path or not self._last_rendered_path.is_file():
            return
        if os.name == "nt":
            subprocess.Popen(f'explorer /select,"{os.path.normpath(str(self._last_rendered_path))}"')
        else:
            subprocess.Popen(["xdg-open", str(self._last_rendered_path.parent)])

    def _on_choose_other_file(self) -> None:
        self._pause_playback()
        new_file_str, _ = QFileDialog.getOpenFileName(
            self,
            "Ses Dosyası Seç",
            str(self.file_path.parent),
            "Ses Dosyaları (*.wav *.mp3 *.flac *.opus *.m4a *.aac *.ogg);;Tüm Dosyalar (*.*)",
        )
        if not new_file_str:
            return

        self.file_path = Path(new_file_str)
        self._file_name_lbl.setText(self.file_path.name)
        self._analysis = None
        self._semitones = 0
        self._pitch_slider.setValue(0)
        self._reveal_btn.setVisible(False)
        self._ref_file = None
        self._is_matched = False
        self._ref_card.setVisible(False)
        self._load_initial_data()

    def closeEvent(self, event) -> None:
        self._pause_playback()
        self._poll_timer.stop()
        self._ref_engine.close()
        self._engine.close()
        super().closeEvent(event)

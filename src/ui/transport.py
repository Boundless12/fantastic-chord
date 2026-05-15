"""TransportWidget: Playback transport controls."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSpinBox, QWidget


class TransportWidget(QWidget):
    """Transport bar with play/stop/record, BPM, and position display."""

    bpm_changed = Signal(float)
    play_clicked = Signal()
    stop_clicked = Signal()
    record_clicked = Signal()

    _is_playing: bool
    _is_recording: bool

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_playing = False
        self._is_recording = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self._play_btn = QPushButton("▶")
        self._play_btn.setFixedSize(40, 32)
        self._play_btn.setCheckable(True)
        self._play_btn.clicked.connect(self._on_play)

        self._stop_btn = QPushButton("■")
        self._stop_btn.setFixedSize(40, 32)
        self._stop_btn.clicked.connect(self._on_stop)

        self._record_btn = QPushButton("●")
        self._record_btn.setFixedSize(40, 32)
        self._record_btn.setCheckable(True)
        self._record_btn.clicked.connect(self._on_record)

        layout.addWidget(self._play_btn)
        layout.addWidget(self._stop_btn)
        layout.addWidget(self._record_btn)

        layout.addSpacing(16)

        bpm_label = QLabel("BPM")
        layout.addWidget(bpm_label)

        self._bpm_spin = QSpinBox()
        self._bpm_spin.setRange(40, 300)
        self._bpm_spin.setValue(120)
        self._bpm_spin.setFixedWidth(70)
        self._bpm_spin.valueChanged.connect(lambda v: self.bpm_changed.emit(float(v)))
        layout.addWidget(self._bpm_spin)

        layout.addSpacing(16)

        self._position_label = QLabel("Bar 1.1")
        self._position_label.setStyleSheet("color: #8888a0; font-size: 14px;")
        layout.addWidget(self._position_label)

        layout.addStretch()

    def _on_play(self) -> None:
        self._is_playing = not self._is_playing
        self._play_btn.setText("⏸" if self._is_playing else "▶")
        self.play_clicked.emit()

    def _on_stop(self) -> None:
        self._is_playing = False
        self._is_recording = False
        self._play_btn.setText("▶")
        self._play_btn.setChecked(False)
        self._record_btn.setChecked(False)
        self.stop_clicked.emit()

    def _on_record(self) -> None:
        self._is_recording = not self._is_recording
        self.record_clicked.emit()

    def update_position(self, bar: int, beat: int) -> None:
        self._position_label.setText(f"Bar {bar}.{beat}")

    @property
    def bpm(self) -> float:
        return float(self._bpm_spin.value())

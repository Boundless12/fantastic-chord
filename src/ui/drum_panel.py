"""DrumPanel: Main drum panel with pads, step sequencer, kit selection, and pattern presets."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..audio.drum_kit import DRUM_KIT_PRESETS
from ..audio.engine import AudioEngine
from ..chord.drum_patterns import DrumPatternParser
from ..sequencer.drum_pattern import DRUM_LABELS, DRUM_TYPES
from ..sequencer.transport import Transport
from .drum_pad_widget import DrumPadWidget
from .step_sequencer_widget import StepSequencerWidget


class DrumPanel(QWidget):
    """Drum panel combining pads, step sequencer, kit selector, and pattern presets."""

    _engine: AudioEngine | None
    _transport: Transport | None
    _poll_timer: QTimer
    _pads: dict[str, DrumPadWidget]
    _sequencer: StepSequencerWidget
    _kit_combo: QComboBox
    _label_combos: dict[str, QComboBox]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = None
        self._transport = None
        self._pads = {}
        self._label_combos = {}

        self._setup_ui()
        self._setup_poll_timer()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Kit selector
        kit_layout = QHBoxLayout()
        kit_label = QLabel("Kit:")
        kit_label.setStyleSheet("background: transparent;")
        kit_layout.addWidget(kit_label)

        self._kit_combo = QComboBox()
        self._kit_combo.addItems(sorted(DRUM_KIT_PRESETS.keys()))
        self._kit_combo.currentTextChanged.connect(self._on_kit_changed)
        kit_layout.addWidget(self._kit_combo, 1)

        apply_style_btn = QPushButton("Apply Style")
        apply_style_btn.clicked.connect(self._on_apply_style)
        kit_layout.addWidget(apply_style_btn)

        layout.addLayout(kit_layout)

        # Drum pads in 2 rows × 5 columns
        pads_group = QGroupBox("Pads")
        pads_layout = QVBoxLayout(pads_group)

        pad_rows = [DRUM_TYPES[:5], DRUM_TYPES[5:]]
        for row_types in pad_rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            for drum_type in row_types:
                pad = DrumPadWidget(drum_type)
                pad.drum_triggered.connect(self._on_pad_hit)
                row_layout.addWidget(pad)
                self._pads[drum_type] = pad
            pads_layout.addLayout(row_layout)

        layout.addWidget(pads_group)

        # Step sequencer
        seq_group = QGroupBox("Pattern Sequencer")
        seq_layout = QVBoxLayout(seq_group)
        self._sequencer = StepSequencerWidget()
        self._sequencer.pattern_changed.connect(self._on_pattern_changed)
        seq_layout.addWidget(self._sequencer)
        layout.addWidget(seq_group, 1)

        # Pattern label selectors per drum type
        labels_group = QGroupBox("Quick Patterns")
        labels_outer = QVBoxLayout(labels_group)

        available_labels = DrumPatternParser.get_available_labels()
        for row_types in pad_rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            for drum_type in row_types:
                inner = QVBoxLayout()
                inner.setSpacing(1)
                lbl = QLabel(DRUM_LABELS.get(drum_type, drum_type))
                lbl.setStyleSheet("font-size: 9px; color: #8888a0; background: transparent;")
                inner.addWidget(lbl)

                combo = QComboBox()
                combo.addItem("—")
                combo.addItems(available_labels)
                combo.currentTextChanged.connect(lambda text, dt=drum_type: self._on_label_changed(dt, text))
                inner.addWidget(combo)
                row_layout.addLayout(inner)
                self._label_combos[drum_type] = combo
            labels_outer.addLayout(row_layout)

        layout.addWidget(labels_group)

    def _setup_poll_timer(self) -> None:
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(50)
        self._poll_timer.timeout.connect(self._poll_playhead)

    def _poll_playhead(self) -> None:
        if self._transport is None:
            return
        if not self._transport.is_playing:
            self._sequencer.set_current_step(-1)
            return
        steps = 16
        step_dur_beats = 4.0 / steps
        step = int(self._transport.position_beats / step_dur_beats) % steps
        self._sequencer.set_current_step(step)

    def set_engine(self, engine: AudioEngine) -> None:
        self._engine = engine
        self._transport = engine.transport

        # Load default kit
        kit_name = self._kit_combo.currentText()
        if kit_name:
            engine.load_drum_kit(kit_name)

        # Sync initial pattern
        pattern = self._sequencer.get_pattern()
        engine.set_drum_pattern(pattern)

    # -- Slots --

    def _on_kit_changed(self, kit_name: str) -> None:
        if self._engine is not None:
            self._engine.load_drum_kit(kit_name)

    def _on_pad_hit(self, drum_type: str) -> None:
        if self._engine is not None:
            self._engine.trigger_drum(drum_type, 100)

    def _on_pattern_changed(self) -> None:
        if self._engine is not None:
            pattern = self._sequencer.get_pattern()
            self._engine.set_drum_pattern(pattern)

    def _on_apply_style(self) -> None:
        """Apply label selections from quick-pattern combos to the sequencer grid."""
        from ..chord.styles import DrumPatternRef

        ref = DrumPatternRef(
            kick=self._label_combos["kick"].currentText() if self._label_combos["kick"].currentText() != "—" else "",
            snare=self._label_combos["snare"].currentText() if self._label_combos["snare"].currentText() != "—" else "",
            hh_closed=(
                self._label_combos["hh_closed"].currentText()
                if self._label_combos["hh_closed"].currentText() != "—"
                else ""
            ),
            hh_open=(
                self._label_combos["hh_open"].currentText()
                if self._label_combos["hh_open"].currentText() != "—"
                else ""
            ),
            clap=self._label_combos["clap"].currentText() if self._label_combos["clap"].currentText() != "—" else "",
            crash=self._label_combos["crash"].currentText() if self._label_combos["crash"].currentText() != "—" else "",
        )
        pattern = DrumPatternParser.parse(ref)
        self._sequencer.set_pattern(pattern)
        self._on_pattern_changed()

    def _on_label_changed(self, drum_type: str, text: str) -> None:
        """Apply a single label to the corresponding drum row immediately."""
        if text == "—":
            return
        steps = DrumPatternParser.label_steps(text)
        current = self._sequencer.get_pattern()
        parts = current.get_parts()
        step_list = parts.get(drum_type, [])
        for i in range(len(step_list)):
            step_list[i].active = i in steps
        self._sequencer.set_pattern(current)
        self._on_pattern_changed()

    # -- Public API --

    def start_polling(self) -> None:
        self._poll_timer.start()

    def stop_polling(self) -> None:
        self._poll_timer.stop()
        self._sequencer.set_current_step(-1)

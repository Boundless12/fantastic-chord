"""EffectsPanel: Global effects mixer panel with knobs and bypass toggles."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from ..audio.engine import AudioEngine
from .knob_widget import KnobWidget


class EffectsPanel(QWidget):
    """Global effects mixer with per-effect parameter knobs and bypass toggles."""

    _engine: AudioEngine | None
    _knobs: dict[str, KnobWidget]
    _bypasses: dict[str, QCheckBox]
    _pre_bypass_wet: dict[str, float]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = None
        self._knobs = {}
        self._bypasses = {}
        self._pre_bypass_wet = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # -- Reverb --
        reverb_group = QGroupBox("Reverb")
        rev_layout = QVBoxLayout(reverb_group)
        rev_knobs = QHBoxLayout()

        self._add_knob(rev_knobs, "reverb_room_size", "Room", 0.5)
        self._add_knob(rev_knobs, "reverb_damping", "Damp", 0.5)
        self._add_knob(rev_knobs, "reverb_wet", "Wet", 0.3)

        rev_layout.addLayout(rev_knobs)
        self._add_bypass(rev_layout, "reverb")
        layout.addWidget(reverb_group)

        # -- Delay --
        delay_group = QGroupBox("Delay")
        del_layout = QVBoxLayout(delay_group)
        del_knobs = QHBoxLayout()

        self._add_knob(del_knobs, "delay_time", "Time", 0.25)
        self._add_knob(del_knobs, "delay_feedback", "Fdbk", 0.4)
        self._add_knob(del_knobs, "delay_wet", "Wet", 0.3)

        del_layout.addLayout(del_knobs)
        self._add_bypass(del_layout, "delay")
        layout.addWidget(delay_group)

        # -- Chorus --
        chorus_group = QGroupBox("Chorus")
        cho_layout = QVBoxLayout(chorus_group)
        cho_knobs = QHBoxLayout()

        self._add_knob(cho_knobs, "chorus_rate", "Rate", 0.3)
        self._add_knob(cho_knobs, "chorus_depth", "Depth", 0.3)
        self._add_knob(cho_knobs, "chorus_wet", "Wet", 0.5)

        cho_layout.addLayout(cho_knobs)
        self._add_bypass(cho_layout, "chorus")
        layout.addWidget(chorus_group)

        # -- Distortion --
        dist_group = QGroupBox("Distortion")
        dist_layout = QVBoxLayout(dist_group)
        dist_knobs = QHBoxLayout()

        self._add_knob(dist_knobs, "distortion_drive", "Drive", 0.0)

        dist_layout.addLayout(dist_knobs)
        self._add_bypass(dist_layout, "distortion")
        layout.addWidget(dist_group)

        # -- Master Volume --
        master_group = QGroupBox("Master")
        master_layout = QHBoxLayout(master_group)
        self._master_knob = KnobWidget("Volume", 0.8, "percent")
        self._master_knob.value_changed.connect(lambda v: self._on_knob_changed("volume", v))
        self._knobs["volume"] = self._master_knob
        master_layout.addWidget(self._master_knob)
        master_layout.addStretch()
        layout.addWidget(master_group)

        layout.addStretch()

    def _add_knob(self, layout: QHBoxLayout, param: str, label: str, default: float) -> None:
        knob = KnobWidget(label, default, "percent")
        knob.value_changed.connect(lambda v, p=param: self._on_knob_changed(p, v))
        layout.addWidget(knob)
        self._knobs[param] = knob

    def _add_bypass(self, layout: QVBoxLayout, effect: str) -> None:
        cb = QCheckBox("Bypass")
        cb.toggled.connect(lambda checked, e=effect: self._on_bypass_toggled(e, checked))
        self._bypasses[effect] = cb
        layout.addWidget(cb)

    def set_engine(self, engine: AudioEngine) -> None:
        self._engine = engine

    # -- Slots --

    def _on_knob_changed(self, param: str, value: float) -> None:
        if self._engine is None:
            return
        self._engine.set_master_param(param, value)

    def _on_bypass_toggled(self, effect: str, checked: bool) -> None:
        if self._engine is None:
            return
        wet_key = f"{effect}_wet"
        if checked:
            knob = self._knobs.get(wet_key)
            if knob is not None:
                self._pre_bypass_wet[effect] = knob.value()
                self._engine.set_master_param(wet_key, 0.0)
        else:
            prev = self._pre_bypass_wet.pop(effect, 0.3)
            self._engine.set_master_param(wet_key, prev)
            knob = self._knobs.get(wet_key)
            if knob is not None:
                knob.set_value(prev, emit=False)

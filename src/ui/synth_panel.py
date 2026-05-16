"""SynthPanel: Full synthesizer control panel with knob matrix, presets, and MIDI CC Learn."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..audio.engine import AudioEngine
from ..audio.patch import Patch, PatchLibrary
from .knob_widget import KnobWidget
from .theme import COLOR_SURFACE, FONT_SIZE_SM


def _hz_to_knob(hz: float, max_hz: float = 20000.0) -> float:
    """Convert Hz to 0-1 knob value using log mapping."""
    import math

    if hz <= 20.0:
        return 0.0
    return max(0.0, min(1.0, math.log(hz / 20.0) / math.log(max_hz / 20.0)))


class SynthPanel(QWidget):
    """Synthesizer control panel — knob matrix, preset browser, MIDI CC Learn."""

    param_changed = Signal(str, float)
    patch_loaded = Signal(str)
    cc_learn_started = Signal()
    cc_learn_finished = Signal(int, str)

    _engine: AudioEngine | None
    _patch_library: PatchLibrary
    _knobs: dict[str, KnobWidget]
    _cc_mappings: dict[int, str]
    _learn_target: KnobWidget | None
    _preview_btn: QPushButton
    _preset_combo: QComboBox

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = None
        self._patch_library = PatchLibrary()
        self._knobs = {}
        self._cc_mappings = {}
        self._learn_target = None

        self._setup_ui()
        self._load_presets()

    def set_engine(self, engine: AudioEngine) -> None:
        self._engine = engine

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Preset browser row
        layout.addLayout(self._make_preset_row())

        # Scrollable knob sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {COLOR_SURFACE}; }}")

        sections = QWidget()
        sections_layout = QVBoxLayout(sections)
        sections_layout.setContentsMargins(0, 0, 0, 0)
        sections_layout.setSpacing(8)

        sections_layout.addWidget(self._make_osc1_section())
        sections_layout.addWidget(self._make_osc2_section())
        sections_layout.addWidget(self._make_mixer_section())
        sections_layout.addWidget(self._make_filter_section())
        sections_layout.addWidget(self._make_amp_env_section())
        sections_layout.addWidget(self._make_filter_env_section())
        sections_layout.addWidget(self._make_lfo1_section())
        sections_layout.addWidget(self._make_lfo2_section())
        sections_layout.addWidget(self._make_effects_section())
        sections_layout.addWidget(self._make_portamento_section())
        sections_layout.addWidget(self._make_unison_section())
        sections_layout.addStretch()

        scroll.setWidget(sections)
        layout.addWidget(scroll)

    def _make_preset_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)

        label = QLabel("Preset:")
        label.setStyleSheet(f"color: #e0e0e0; font-size: {FONT_SIZE_SM}pt;")
        row.addWidget(label)

        self._preset_combo = QComboBox()
        self._preset_combo.setMinimumWidth(140)
        self._preset_combo.setStyleSheet(
            f"QComboBox {{ background: #2a2a3c; color: #e0e0e0; border: 1px solid #444477;"
            f" padding: 2px 6px; border-radius: 3px; font-size: {FONT_SIZE_SM}pt; }}"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background: #2a2a3c; color: #e0e0e0; selection-background-color: #7c3aed; }"
        )
        row.addWidget(self._preset_combo)

        load_btn = QPushButton("Load")
        load_btn.setFixedSize(50, 24)
        load_btn.clicked.connect(self._on_load_preset)
        row.addWidget(load_btn)

        save_btn = QPushButton("Save")
        save_btn.setFixedSize(50, 24)
        save_btn.clicked.connect(self._on_save_preset)
        row.addWidget(save_btn)

        init_btn = QPushButton("Init")
        init_btn.setFixedSize(40, 24)
        init_btn.clicked.connect(self._on_init_patch)
        row.addWidget(init_btn)

        self._preview_btn = QPushButton("Preview")
        self._preview_btn.setFixedSize(60, 24)
        self._preview_btn.setToolTip("Play a test note (C4)")
        self._preview_btn.clicked.connect(self._on_preview)
        row.addWidget(self._preview_btn)

        row.addStretch()
        return row

    # ---- Section builders ----

    def _make_osc_section(self, prefix: str, title: str) -> QGroupBox:
        group = QGroupBox(title)
        group.setStyleSheet(self._group_style())
        grid = QGridLayout(group)
        grid.setSpacing(4)

        wf_map = ["sine", "saw", "square", "tri", "noise"]
        oct_range = (-3, 3)

        self._add_knob(grid, 0, 0, f"{prefix}.waveform_int", "Wave", display_map=wf_map, default=1, row_name="osc")
        self._add_knob(grid, 0, 1, f"{prefix}.octave", "Oct", default=3, step=1, vrange=oct_range, row_name="osc")
        self._add_knob(grid, 0, 2, f"{prefix}.semitones", "Semi", fmt="semitones", default=0.5, row_name="osc")
        self._add_knob(grid, 0, 3, f"{prefix}.detune_cents", "Detune", fmt="cents", default=0.5, row_name="osc")
        self._add_knob(grid, 1, 0, f"{prefix}.pulse_width", "PulseW", default=0.5, row_name="osc")
        self._add_knob(grid, 1, 1, f"{prefix}.phase", "Phase", default=0.0, row_name="osc")
        self._add_knob(grid, 1, 2, f"{prefix}.fm_amount", "FM Amt", default=0.0, row_name="osc")
        # Serum controls: wavetable position + warp
        self._add_knob(grid, 2, 0, f"{prefix}.wt_position", "WT Pos", default=0.0, row_name="wavetable")
        warp_opts = ["none", "bend_p", "bend_n", "mirror", "fold", "pwm", "crush"]
        self._add_knob(
            grid,
            2,
            1,
            f"{prefix}.warp_mode_int",
            "Warp",
            display_map=warp_opts,
            default=0,
            step=0.1667,
            row_name="wavetable",
        )
        self._add_knob(grid, 2, 2, f"{prefix}.warp_amount", "WarpAmt", default=0.0, row_name="wavetable")
        return group

    def _make_osc1_section(self) -> QGroupBox:
        return self._make_osc_section("osc1", "Oscillator 1")

    def _make_osc2_section(self) -> QGroupBox:
        return self._make_osc_section("osc2", "Oscillator 2")

    def _make_mixer_section(self) -> QGroupBox:
        group = QGroupBox("Mixer")
        group.setStyleSheet(self._group_style())
        grid = QGridLayout(group)
        grid.setSpacing(4)
        self._add_knob(grid, 0, 0, "mixer.osc1_level", "OSC1", default=1.0)
        self._add_knob(grid, 0, 1, "mixer.osc2_level", "OSC2", default=0.0)
        self._add_knob(grid, 0, 2, "mixer.noise_level", "Noise", default=0.0)
        self._add_knob(grid, 0, 3, "mixer.sub_osc_level", "Sub", default=0.0)
        self._add_knob(grid, 0, 4, "mixer.ring_mod", "RingM", default=0.0)
        return group

    def _make_filter_section(self) -> QGroupBox:
        group = QGroupBox("Filter")
        group.setStyleSheet(self._group_style())
        grid = QGridLayout(group)
        grid.setSpacing(4)
        ft_map = ["LP", "HP", "BP", "Notch"]
        self._add_knob(grid, 0, 0, "filter.filter_type_int", "Type", display_map=ft_map, default=0, step=0.333)
        self._add_knob(grid, 0, 1, "filter.cutoff", "Cutoff", fmt="hz", default=0.9)
        self._add_knob(grid, 0, 2, "filter.resonance", "Res", default=0.0)
        self._add_knob(grid, 0, 3, "filter.key_track", "KeyTrk", default=0.0)
        self._add_knob(grid, 1, 0, "filter.env_amount", "EnvAmt", default=0.0)
        self._add_knob(grid, 1, 1, "filter.drive", "Drive", default=0.0)
        self._add_knob(grid, 1, 2, "filter.cutoff_link", "Link", default=1.0)
        self._add_knob(grid, 1, 3, "filter.slope_int", "Slope", display_map=["12dB", "24dB"], default=1, step=1)
        return group

    def _make_amp_env_section(self) -> QGroupBox:
        group = QGroupBox("Amp Envelope")
        group.setStyleSheet(self._group_style())
        grid = QGridLayout(group)
        grid.setSpacing(4)
        self._add_knob(grid, 0, 0, "amp_env.attack", "Attack", fmt="ms", default=0.0)
        self._add_knob(grid, 0, 1, "amp_env.decay", "Decay", fmt="ms", default=0.2 / 2.0)
        self._add_knob(grid, 0, 2, "amp_env.sustain", "Sustain", default=0.8)
        self._add_knob(grid, 0, 3, "amp_env.release", "Release", fmt="ms", default=0.3 / 2.0)
        self._add_knob(grid, 0, 4, "amp_env.velocity_to_amp", "VelAmt", default=0.5)
        return group

    def _make_filter_env_section(self) -> QGroupBox:
        group = QGroupBox("Filter Envelope")
        group.setStyleSheet(self._group_style())
        grid = QGridLayout(group)
        grid.setSpacing(4)
        self._add_knob(grid, 0, 0, "filter_env.attack", "Attack", fmt="ms", default=0.0)
        self._add_knob(grid, 0, 1, "filter_env.decay", "Decay", fmt="ms", default=0.3 / 2.0)
        self._add_knob(grid, 0, 2, "filter_env.sustain", "Sustain", default=0.0)
        self._add_knob(grid, 0, 3, "filter_env.release", "Release", fmt="ms", default=0.3 / 2.0)
        self._add_knob(grid, 1, 0, "filter_env.amount", "Amount", default=0.0)
        self._add_knob(grid, 1, 1, "filter_env.velocity_to_env", "VelAmt", default=0.0)
        return group

    def _make_lfo_section(self, prefix: str, title: str) -> QGroupBox:
        group = QGroupBox(title)
        group.setStyleSheet(self._group_style())
        grid = QGridLayout(group)
        grid.setSpacing(4)
        wf_map = ["sine", "tri", "sq", "saw↑", "saw↓", "S&H", "rand"]
        tgt_map = ["none", "pitch", "mix", "cutoff", "res", "amp", "pan"]
        self._add_knob(grid, 0, 0, f"{prefix}.waveform_int", "Wave", display_map=wf_map, default=0, step=0.166)
        self._add_knob(grid, 0, 1, f"{prefix}.rate", "Rate", fmt="hz", default=0.05)
        self._add_knob(grid, 0, 2, f"{prefix}.depth", "Depth", default=0.0)
        self._add_knob(grid, 0, 3, f"{prefix}.target_int", "Target", display_map=tgt_map, default=0, step=0.166)
        self._add_knob(grid, 1, 0, f"{prefix}.phase", "Phase", default=0.0)
        self._add_knob(grid, 1, 1, f"{prefix}.fade_in", "FadeIn", fmt="ms", default=0.0)
        self._add_knob(grid, 1, 2, f"{prefix}.key_sync", "KeySyn", display_map=["Off", "On"], default=1, step=1)
        self._add_knob(grid, 1, 3, f"{prefix}.one_shot", "1-Shot", display_map=["Off", "On"], default=0, step=1)
        return group

    def _make_lfo1_section(self) -> QGroupBox:
        return self._make_lfo_section("lfo1", "LFO 1")

    def _make_lfo2_section(self) -> QGroupBox:
        return self._make_lfo_section("lfo2", "LFO 2")

    def _make_effects_section(self) -> QGroupBox:
        group = QGroupBox("Effects")
        group.setStyleSheet(self._group_style())
        grid = QGridLayout(group)
        grid.setSpacing(4)
        self._add_knob(grid, 0, 0, "effects.reverb_send", "Reverb", default=0.0)
        self._add_knob(grid, 0, 1, "effects.delay_send", "Delay", default=0.0)
        self._add_knob(grid, 0, 2, "effects.chorus_send", "Chorus", default=0.0)
        self._add_knob(grid, 0, 3, "effects.distortion_drive", "Drive", default=0.0)
        return group

    def _make_unison_section(self) -> QGroupBox:
        group = QGroupBox("Unison")
        group.setStyleSheet(self._group_style())
        grid = QGridLayout(group)
        grid.setSpacing(4)
        self._add_knob(grid, 0, 0, "unison.voices", "Voices", default=1, step=1, vrange=(1, 7), fmt="int")
        self._add_knob(grid, 0, 1, "unison.detune", "Detune", default=0.1)
        self._add_knob(grid, 0, 2, "unison.spread", "Spread", default=0.3)
        return group

    def _make_portamento_section(self) -> QGroupBox:
        group = QGroupBox("Portamento")
        group.setStyleSheet(self._group_style())
        grid = QGridLayout(group)
        grid.setSpacing(4)
        self._add_knob(grid, 0, 0, "portamento.time", "Time", fmt="ms", default=0.0)
        self._add_knob(
            grid, 0, 1, "portamento.mode_int", "Mode", display_map=["Off", "Always", "Auto"], default=0, step=0.5
        )
        self._add_knob(
            grid, 0, 2, "portamento.polyphony_int", "Voice", display_map=["Poly", "Mono", "Legato"], default=0, step=0.5
        )
        self._add_knob(grid, 0, 3, "portamento.bend_range", "Bend", default=2, step=1, vrange=(2, 24))
        return group

    # ---- Knob factory ----

    def _add_knob(
        self,
        grid: QGridLayout,
        row: int,
        col: int,
        param_path: str,
        label: str,
        *,
        default: float = 0.5,
        fmt: str = "percent",
        bipolar: bool = False,
        step: float = 0.0,
        display_map: list[str] | None = None,
        vrange: tuple[float, float] | None = None,
        row_name: str = "",
    ) -> KnobWidget:
        """Create a KnobWidget, add to grid, register in _knobs dict."""
        knob = KnobWidget(
            display_name=label,
            default_value=default,
            value_format=fmt,
            bipolar=bipolar,
            step=step,
            display_map=display_map,
        )
        if vrange:
            knob.set_range(vrange[0], vrange[1])
        knob.value_changed.connect(lambda v, pp=param_path: self._on_knob_changed(pp, v))
        knob.context_menu_requested.connect(lambda k=knob: self._on_knob_context_menu(k))
        grid.addWidget(knob, row, col)
        self._knobs[param_path] = knob
        return knob

    # ---- Signal handlers ----

    def _on_knob_changed(self, param_path: str, value: float) -> None:
        self.param_changed.emit(param_path, value)
        if self._engine is not None:
            self._engine.set_param(param_path, value)

    def _on_knob_context_menu(self, knob: KnobWidget) -> None:
        menu = QMenu(self)
        learn_action = menu.addAction("Learn CC...")
        if self._learn_target is not None:
            menu.addAction("Cancel Learn")
        action = menu.exec(self.cursor().pos())
        if action == learn_action:
            self._learn_target = knob
            self.cc_learn_started.emit()

    def on_midi_cc(self, cc_number: int, value: int) -> None:
        """Receive MIDI CC message — either learn or apply mapping."""
        if self._learn_target is not None:
            for pp, k in self._knobs.items():
                if k is self._learn_target:
                    self._cc_mappings[cc_number] = pp
                    self._learn_target = None
                    self.cc_learn_finished.emit(cc_number, pp)
                    # Also apply this CC value
                    float_val = value / 127.0
                    k.set_value(float_val)
                    self.param_changed.emit(pp, float_val)
                    return

        if cc_number in self._cc_mappings:
            param_path = self._cc_mappings[cc_number]
            float_val = value / 127.0
            if param_path in self._knobs:
                self._knobs[param_path].set_value(float_val)
                self.param_changed.emit(param_path, float_val)

    # ---- Preset management ----

    def _load_presets(self) -> None:
        preset_dir = str(Path(__file__).parent.parent.parent / "resources" / "presets")
        self._patch_library.load_all(preset_dir)
        self._refresh_combo()

    def _refresh_combo(self) -> None:
        self._preset_combo.clear()
        names = sorted(self._patch_library.patches.keys())
        for name in names:
            self._preset_combo.addItem(name)

    def _on_load_preset(self) -> None:
        name = self._preset_combo.currentText()
        patch = self._patch_library.get(name)
        if patch is None:
            return
        self._apply_patch_to_knobs(patch)
        if self._engine is not None:
            self._engine.load_patch(patch)
        self.patch_loaded.emit(name)

    def _on_save_preset(self) -> None:
        name = self._preset_combo.currentText()
        if not name:
            return
        patch = self._build_patch_from_knobs()
        patch.name = name
        preset_dir = str(Path(__file__).parent.parent.parent / "resources" / "presets")
        self._patch_library.save(patch, preset_dir)
        self._refresh_combo()

    def _on_init_patch(self) -> None:
        default_patch = Patch()
        self._apply_patch_to_knobs(default_patch)

    def _on_preview(self) -> None:
        if self._engine is None:
            return
        import time as _time
        from threading import Thread

        def _play() -> None:
            self._engine.note_on(60, 80)  # type: ignore[union-attr]
            _time.sleep(0.4)
            self._engine.note_off(60)  # type: ignore[union-attr]

        Thread(target=_play, daemon=True).start()

    def _apply_patch_to_knobs(self, patch: Patch) -> None:
        """Update all knobs to reflect a loaded patch."""
        mapping: dict[str, float] = {
            # OSC1
            "osc1.waveform_int": (
                float(["sine", "saw", "square", "triangle", "noise"].index(patch.osc1.waveform)) / 4.0
                if patch.osc1.waveform in ["sine", "saw", "square", "triangle", "noise"]
                else 0.25
            ),
            "osc1.octave": float(patch.osc1.octave),
            "osc1.semitones": patch.osc1.semitones / 48.0 + 0.5,
            "osc1.detune_cents": patch.osc1.detune_cents / 100.0 + 0.5,
            "osc1.pulse_width": patch.osc1.pulse_width,
            "osc1.phase": patch.osc1.phase,
            "osc1.fm_amount": patch.osc1.fm_amount,
            # OSC2
            "osc2.waveform_int": (
                float(["sine", "saw", "square", "triangle", "noise"].index(patch.osc2.waveform)) / 4.0
                if patch.osc2.waveform in ["sine", "saw", "square", "triangle", "noise"]
                else 0.25
            ),
            "osc2.octave": float(patch.osc2.octave),
            "osc2.semitones": patch.osc2.semitones / 48.0 + 0.5,
            "osc2.detune_cents": patch.osc2.detune_cents / 100.0 + 0.5,
            "osc2.pulse_width": patch.osc2.pulse_width,
            "osc2.phase": patch.osc2.phase,
            "osc2.fm_amount": patch.osc2.fm_amount,
            # Mixer
            "mixer.osc1_level": patch.mixer.osc1_level,
            "mixer.osc2_level": patch.mixer.osc2_level,
            "mixer.noise_level": patch.mixer.noise_level,
            "mixer.sub_osc_level": patch.mixer.sub_osc_level,
            "mixer.ring_mod": patch.mixer.ring_mod,
            # Filter
            "filter.filter_type_int": float(
                ["lowpass", "highpass", "bandpass", "notch"].index(patch.filter.filter_type)
            )
            / 3.0,
            "filter.cutoff": _hz_to_knob(patch.filter.cutoff),
            "filter.resonance": patch.filter.resonance,
            "filter.key_track": patch.filter.key_track,
            "filter.env_amount": patch.filter.env_amount,
            "filter.drive": patch.filter.drive,
            "filter.cutoff_link": patch.filter.cutoff_link,
            "filter.slope_int": 0.0 if patch.filter.slope == "12db" else 1.0,
            # Amp env
            "amp_env.attack": patch.amp_env.attack / 2.0,
            "amp_env.decay": patch.amp_env.decay / 2.0,
            "amp_env.sustain": patch.amp_env.sustain,
            "amp_env.release": patch.amp_env.release / 2.0,
            "amp_env.velocity_to_amp": patch.amp_env.velocity_to_amp,
            # Filter env
            "filter_env.attack": patch.filter_env.attack / 2.0,
            "filter_env.decay": patch.filter_env.decay / 2.0,
            "filter_env.sustain": patch.filter_env.sustain,
            "filter_env.release": patch.filter_env.release / 2.0,
            "filter_env.amount": patch.filter.env_amount,
            "filter_env.velocity_to_env": patch.filter_env.velocity_to_env,
            # LFO1
            "lfo1.waveform_int": (
                float(
                    ["sine", "triangle", "square", "saw_up", "saw_down", "sample_hold", "random"].index(
                        patch.lfo1.waveform
                    )
                )
                / 6.0
                if patch.lfo1.waveform in ["sine", "triangle", "square", "saw_up", "saw_down", "sample_hold", "random"]
                else 0.0
            ),
            "lfo1.rate": _hz_to_knob(patch.lfo1.rate, max_hz=50.0),
            "lfo1.depth": patch.lfo1.depth,
            "lfo1.target_int": float(
                ["none", "osc_pitch", "mix", "filter_cutoff", "filter_res", "amp", "pan"].index(patch.lfo1.target)
            )
            / 6.0,
            "lfo1.phase": patch.lfo1.phase,
            "lfo1.fade_in": patch.lfo1.fade_in / 2.0,
            "lfo1.key_sync": 1.0 if patch.lfo1.key_sync else 0.0,
            "lfo1.one_shot": 1.0 if patch.lfo1.one_shot else 0.0,
            # LFO2
            "lfo2.waveform_int": (
                float(
                    ["sine", "triangle", "square", "saw_up", "saw_down", "sample_hold", "random"].index(
                        patch.lfo2.waveform
                    )
                )
                / 6.0
                if patch.lfo2.waveform in ["sine", "triangle", "square", "saw_up", "saw_down", "sample_hold", "random"]
                else 0.0
            ),
            "lfo2.rate": _hz_to_knob(patch.lfo2.rate, max_hz=50.0),
            "lfo2.depth": patch.lfo2.depth,
            "lfo2.target_int": float(
                ["none", "osc_pitch", "mix", "filter_cutoff", "filter_res", "amp", "pan"].index(patch.lfo2.target)
            )
            / 6.0,
            "lfo2.phase": patch.lfo2.phase,
            "lfo2.fade_in": patch.lfo2.fade_in / 2.0,
            "lfo2.key_sync": 1.0 if patch.lfo2.key_sync else 0.0,
            "lfo2.one_shot": 1.0 if patch.lfo2.one_shot else 0.0,
            # Effects
            "effects.reverb_send": patch.effects.reverb_send,
            "effects.delay_send": patch.effects.delay_send,
            "effects.chorus_send": patch.effects.chorus_send,
            "effects.distortion_drive": patch.effects.distortion_drive,
            # Portamento
            "portamento.time": patch.portamento.time / 2.0,
            "portamento.mode_int": (
                float(["off", "always", "auto"].index(patch.portamento.mode)) / 2.0
                if patch.portamento.mode in ["off", "always", "auto"]
                else 0.0
            ),
            "portamento.polyphony_int": (
                float(["poly", "mono", "legato"].index(patch.portamento.polyphony)) / 2.0
                if patch.portamento.polyphony in ["poly", "mono", "legato"]
                else 0.0
            ),
            "portamento.bend_range": float(patch.portamento.bend_range),
        }

        for param_path, value in mapping.items():
            if param_path in self._knobs:
                self._knobs[param_path].set_value(value, emit=False)

    def _build_patch_from_knobs(self) -> Patch:
        """Build a Patch from current knob values."""
        patch = Patch()

        wf_osc = ["sine", "saw", "square", "triangle", "noise"]
        wf_lfo = ["sine", "triangle", "square", "saw_up", "saw_down", "sample_hold", "random"]
        ft_map = ["lowpass", "highpass", "bandpass", "notch"]
        tgt_map = ["none", "osc_pitch", "mix", "filter_cutoff", "filter_res", "amp", "pan"]
        mode_map = ["off", "always", "auto"]
        voice_map = ["poly", "mono", "legato"]

        def _map_int(path: str, n: int) -> int:
            v = self._knob_val(path, 0.0)
            return max(0, min(n, int(v * n + 0.5)))

        # OSC1
        patch.osc1.waveform = wf_osc[_map_int("osc1.waveform_int", 4)]
        patch.osc1.octave = int(self._knob_val("osc1.octave", 0))
        patch.osc1.semitones = int((self._knob_val("osc1.semitones", 0.5) - 0.5) * 48)
        patch.osc1.detune_cents = (self._knob_val("osc1.detune_cents", 0.5) - 0.5) * 100
        patch.osc1.pulse_width = self._knob_val("osc1.pulse_width", 0.5)
        patch.osc1.phase = self._knob_val("osc1.phase", 0.0)
        patch.osc1.fm_amount = self._knob_val("osc1.fm_amount", 0.0)

        # OSC2
        patch.osc2.waveform = wf_osc[_map_int("osc2.waveform_int", 4)]
        patch.osc2.octave = int(self._knob_val("osc2.octave", 0))
        patch.osc2.semitones = int((self._knob_val("osc2.semitones", 0.5) - 0.5) * 48)
        patch.osc2.detune_cents = (self._knob_val("osc2.detune_cents", 0.5) - 0.5) * 100
        patch.osc2.pulse_width = self._knob_val("osc2.pulse_width", 0.5)
        patch.osc2.phase = self._knob_val("osc2.phase", 0.0)
        patch.osc2.fm_amount = self._knob_val("osc2.fm_amount", 0.0)

        # Mixer
        patch.mixer.osc1_level = self._knob_val("mixer.osc1_level", 1.0)
        patch.mixer.osc2_level = self._knob_val("mixer.osc2_level", 0.0)
        patch.mixer.noise_level = self._knob_val("mixer.noise_level", 0.0)
        patch.mixer.sub_osc_level = self._knob_val("mixer.sub_osc_level", 0.0)
        patch.mixer.ring_mod = self._knob_val("mixer.ring_mod", 0.0)

        # Filter
        patch.filter.filter_type = ft_map[_map_int("filter.filter_type_int", 3)]
        patch.filter.cutoff = 20.0 * (20000.0 / 20.0) ** max(0.0, min(1.0, self._knob_val("filter.cutoff", 0.9)))
        patch.filter.resonance = self._knob_val("filter.resonance", 0.0)
        patch.filter.key_track = self._knob_val("filter.key_track", 0.0)
        patch.filter.env_amount = self._knob_val("filter.env_amount", 0.0)
        patch.filter.drive = self._knob_val("filter.drive", 0.0)
        patch.filter.cutoff_link = self._knob_val("filter.cutoff_link", 1.0)
        patch.filter.slope = "24db" if self._knob_val("filter.slope_int", 1.0) > 0.5 else "12db"

        # Amp Env
        patch.amp_env.attack = self._knob_val("amp_env.attack", 0.0) * 2.0
        patch.amp_env.decay = self._knob_val("amp_env.decay", 0.1) * 2.0
        patch.amp_env.sustain = self._knob_val("amp_env.sustain", 0.8)
        patch.amp_env.release = self._knob_val("amp_env.release", 0.15) * 2.0
        patch.amp_env.velocity_to_amp = self._knob_val("amp_env.velocity_to_amp", 0.5)

        # Filter Env
        patch.filter_env.attack = self._knob_val("filter_env.attack", 0.0) * 2.0
        patch.filter_env.decay = self._knob_val("filter_env.decay", 0.15) * 2.0
        patch.filter_env.sustain = self._knob_val("filter_env.sustain", 0.0)
        patch.filter_env.release = self._knob_val("filter_env.release", 0.15) * 2.0
        patch.filter.env_amount = self._knob_val("filter_env.amount", 0.0)
        patch.filter_env.velocity_to_env = self._knob_val("filter_env.velocity_to_env", 0.0)

        # LFO1
        patch.lfo1.waveform = wf_lfo[_map_int("lfo1.waveform_int", 6)]
        patch.lfo1.rate = 0.01 + self._knob_val("lfo1.rate", 0.05) * 49.99
        patch.lfo1.depth = self._knob_val("lfo1.depth", 0.0)
        patch.lfo1.target = tgt_map[_map_int("lfo1.target_int", 6)]
        patch.lfo1.phase = self._knob_val("lfo1.phase", 0.0)
        patch.lfo1.fade_in = self._knob_val("lfo1.fade_in", 0.0) * 2.0
        patch.lfo1.key_sync = self._knob_val("lfo1.key_sync", 1.0) > 0.5
        patch.lfo1.one_shot = self._knob_val("lfo1.one_shot", 0.0) > 0.5

        # LFO2
        patch.lfo2.waveform = wf_lfo[_map_int("lfo2.waveform_int", 6)]
        patch.lfo2.rate = 0.01 + self._knob_val("lfo2.rate", 0.05) * 49.99
        patch.lfo2.depth = self._knob_val("lfo2.depth", 0.0)
        patch.lfo2.target = tgt_map[_map_int("lfo2.target_int", 6)]
        patch.lfo2.phase = self._knob_val("lfo2.phase", 0.0)
        patch.lfo2.fade_in = self._knob_val("lfo2.fade_in", 0.0) * 2.0
        patch.lfo2.key_sync = self._knob_val("lfo2.key_sync", 1.0) > 0.5
        patch.lfo2.one_shot = self._knob_val("lfo2.one_shot", 0.0) > 0.5

        # Effects
        patch.effects.reverb_send = self._knob_val("effects.reverb_send", 0.0)
        patch.effects.delay_send = self._knob_val("effects.delay_send", 0.0)
        patch.effects.chorus_send = self._knob_val("effects.chorus_send", 0.0)
        patch.effects.distortion_drive = self._knob_val("effects.distortion_drive", 0.0)

        # Portamento
        patch.portamento.time = self._knob_val("portamento.time", 0.0) * 2.0
        patch.portamento.mode = mode_map[_map_int("portamento.mode_int", 2)]
        patch.portamento.polyphony = voice_map[_map_int("portamento.polyphony_int", 2)]
        patch.portamento.bend_range = int(self._knob_val("portamento.bend_range", 2))

        return patch

    # ---- Helpers ----

    def _knob_val(self, param_path: str, fallback: float = 0.5) -> float:
        k = self._knobs.get(param_path)
        return float(k.value()) if k is not None else fallback

    def _group_style(self) -> str:
        return (
            "QGroupBox {"
            "  border: 1px solid #444477;"
            "  border-radius: 4px;"
            "  margin-top: 8px;"
            "  padding-top: 12px;"
            "  font-size: 10pt;"
            "  color: #c0c0d0;"
            "}"
            "QGroupBox::title {"
            "  subcontrol-origin: margin;"
            "  left: 10px;"
            "  padding: 0 4px;"
            "}"
        )

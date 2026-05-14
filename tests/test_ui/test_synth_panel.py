"""Tests for SynthPanel construction and functionality."""

import pytest
from PySide6.QtWidgets import QApplication

from src.audio.patch import Patch
from src.ui.synth_panel import SynthPanel


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def panel(qapp: QApplication) -> SynthPanel:
    return SynthPanel()


def test_panel_constructs(panel: SynthPanel) -> None:
    """SynthPanel should construct without errors."""
    assert panel is not None
    assert panel._preset_combo is not None


def test_knobs_registered(panel: SynthPanel) -> None:
    """All expected param paths should have corresponding knobs."""
    expected_prefixes = [
        "osc1.waveform_int",
        "osc1.octave",
        "osc1.semitones",
        "osc2.waveform_int",
        "osc2.detune_cents",
        "mixer.osc1_level",
        "mixer.osc2_level",
        "mixer.noise_level",
        "filter.cutoff",
        "filter.resonance",
        "filter.filter_type_int",
        "filter.env_amount",
        "amp_env.attack",
        "amp_env.decay",
        "amp_env.sustain",
        "amp_env.release",
        "filter_env.attack",
        "filter_env.decay",
        "filter_env.sustain",
        "filter_env.release",
        "filter_env.amount",
        "lfo1.rate",
        "lfo1.depth",
        "lfo1.waveform_int",
        "lfo1.target_int",
        "lfo2.rate",
        "lfo2.depth",
        "lfo2.waveform_int",
        "lfo2.target_int",
        "effects.reverb_send",
        "effects.delay_send",
        "effects.chorus_send",
        "effects.distortion_drive",
        "portamento.time",
    ]

    for prefix in expected_prefixes:
        assert prefix in panel._knobs, f"Missing knob: {prefix}"

    # Count should be ~50 knobs
    assert len(panel._knobs) >= 40, f"Expected >= 40 knobs, got {len(panel._knobs)}"


def test_param_changed_signal(panel: SynthPanel) -> None:
    """Changing a knob value should emit param_changed."""
    signals: list[tuple[str, float]] = []
    panel.param_changed.connect(lambda p, v: signals.append((p, v)))

    knob = panel._knobs.get("filter.cutoff")
    assert knob is not None
    knob.set_value(0.5)

    assert len(signals) >= 1
    assert signals[-1][0] == "filter.cutoff"


def test_midi_cc_learn(panel: SynthPanel) -> None:
    """MIDI CC Learn should map CC to param path."""
    knob = panel._knobs.get("filter.resonance")
    assert knob is not None

    # Simulate Learn CC flow
    panel._learn_target = knob
    panel.on_midi_cc(14, 64)

    # Should map CC 14 to filter.resonance
    assert 14 in panel._cc_mappings
    assert panel._cc_mappings[14] == "filter.resonance"
    assert panel._learn_target is None


def test_midi_cc_apply_mapping(panel: SynthPanel) -> None:
    """Receiving a mapped CC should update the corresponding knob."""
    signals: list[tuple[str, float]] = []
    panel.param_changed.connect(lambda p, v: signals.append((p, v)))

    # Set up a mapping
    panel._cc_mappings[20] = "amp_env.sustain"
    panel.on_midi_cc(20, 100)

    assert len(signals) >= 1
    assert signals[-1][0] == "amp_env.sustain"
    # 100/127 ≈ 0.787
    assert 0.7 < signals[-1][1] < 0.85


def test_preset_combo_populated(panel: SynthPanel) -> None:
    """Preset combo should show factory presets."""
    count = panel._preset_combo.count()
    assert count >= 12, f"Expected >= 12 presets, got {count}"


def test_init_patch_resets_knobs(panel: SynthPanel) -> None:
    """Init should reset knobs to Patch defaults."""
    # First change some knobs
    panel._knobs["amp_env.sustain"].set_value(0.3, emit=False)
    panel._knobs["filter.cutoff"].set_value(0.2, emit=False)

    # Init
    panel._on_init_patch()

    # Sustain should be ~0.8 (default)
    assert abs(panel._knobs["amp_env.sustain"].value() - 0.8) < 0.01


def test_build_patch_from_knobs(panel: SynthPanel) -> None:
    """_build_patch_from_knobs should produce a valid Patch."""
    patch = panel._build_patch_from_knobs()
    assert isinstance(patch, Patch)
    assert patch.name == "Init Patch"
    assert patch.osc1.waveform in ("sine", "saw", "square", "triangle", "noise")
    assert 0.0 <= patch.mixer.osc1_level <= 1.0
    assert 20.0 <= patch.filter.cutoff <= 20000.0


def test_apply_patch_to_knobs(panel: SynthPanel) -> None:
    """_apply_patch_to_knobs should set knobs to match a Patch."""
    patch = Patch()
    patch.amp_env.sustain = 0.6
    patch.filter.cutoff = 3000.0
    patch.effects.reverb_send = 0.4

    panel._apply_patch_to_knobs(patch)

    # Sustain knob should be ~0.6
    assert abs(panel._knobs["amp_env.sustain"].value() - 0.6) < 0.02
    assert abs(panel._knobs["effects.reverb_send"].value() - 0.4) < 0.02

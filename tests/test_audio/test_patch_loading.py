"""Tests for Patch serialization, PatchLibrary, and AudioEngine load_patch."""

import os
from pathlib import Path

from src.audio.engine import AudioEngine
from src.audio.patch import Patch, PatchLibrary
from src.audio.synth_voice import SynthVoice


def test_patch_roundtrip_json(tmp_path: Path) -> None:
    """Patch to_json / from_json preserves all major parameters."""
    original = Patch(name="Test Patch", category="lead")
    original.osc1.waveform = "square"
    original.osc1.octave = 1
    original.osc2.waveform = "triangle"
    original.osc2.detune_cents = 12.0
    original.mixer.osc1_level = 0.8
    original.mixer.osc2_level = 0.5
    original.filter.cutoff = 5000.0
    original.filter.resonance = 0.3
    original.filter.env_amount = 0.4
    original.amp_env.attack = 0.05
    original.amp_env.sustain = 0.7
    original.amp_env.release = 0.5
    original.filter.env_amount = 0.3
    original.lfo1.rate = 2.0
    original.lfo1.depth = 0.2
    original.lfo1.target = "osc_pitch"
    original.effects.reverb_send = 0.3
    original.effects.distortion_drive = 0.15

    path = os.path.join(str(tmp_path), "test.json")
    original.to_json(path)

    loaded = Patch.from_json(path)
    assert loaded.name == "Test Patch"
    assert loaded.osc1.waveform == "square"
    assert loaded.osc1.octave == 1
    assert loaded.osc2.waveform == "triangle"
    assert loaded.osc2.detune_cents == 12.0
    assert loaded.mixer.osc1_level == 0.8
    assert loaded.mixer.osc2_level == 0.5
    assert loaded.filter.cutoff == 5000.0
    assert loaded.filter.resonance == 0.3
    assert loaded.filter.env_amount == 0.3
    assert loaded.amp_env.attack == 0.05
    assert loaded.amp_env.sustain == 0.7
    assert loaded.amp_env.release == 0.5
    assert loaded.filter.env_amount == 0.3
    assert loaded.lfo1.rate == 2.0
    assert loaded.lfo1.depth == 0.2
    assert loaded.lfo1.target == "osc_pitch"
    assert loaded.effects.reverb_send == 0.3
    assert loaded.effects.distortion_drive == 0.15


def test_patch_library_discovers_presets() -> None:
    """PatchLibrary should discover all 12 factory presets."""
    lib = PatchLibrary()
    preset_dir = str(Path(__file__).parent.parent.parent / "resources" / "presets")
    lib.load_all(preset_dir)

    assert len(lib.patches) >= 12
    names = sorted(lib.patches.keys())
    assert "Classic Saw Lead" in names
    assert "Deep Reese" in names
    assert "Lush Strings" in names
    assert "FM Pluck" in names


def test_patch_library_get_by_category() -> None:
    lib = PatchLibrary()
    preset_dir = str(Path(__file__).parent.parent.parent / "resources" / "presets")
    lib.load_all(preset_dir)

    leads = lib.get_by_category("lead")
    assert len(leads) >= 2
    lead_names = [p.name for p in leads]
    assert "Classic Saw Lead" in lead_names

    basses = lib.get_by_category("bass")
    assert len(basses) >= 2

    categories = lib.list_categories()
    assert "lead" in categories
    assert "bass" in categories
    assert "pad" in categories
    assert "pluck" in categories
    assert "keys" in categories
    assert "fx" in categories


def test_every_factory_preset_loads_as_valid_patch() -> None:
    """Every factory preset JSON should parse without error."""
    lib = PatchLibrary()
    preset_dir = str(Path(__file__).parent.parent.parent / "resources" / "presets")
    lib.load_all(preset_dir)

    for name, patch in lib.patches.items():
        assert patch.name == name
        assert patch.osc1.waveform in ("sine", "saw", "square", "triangle", "noise")
        assert 0.0 <= patch.mixer.osc1_level <= 1.0
        assert 20.0 <= patch.filter.cutoff <= 20000.0
        assert 0.001 <= patch.amp_env.attack <= 5.0


def test_synth_voice_load_patch_sets_params() -> None:
    """load_patch on a voice should transfer key parameters."""
    patch = Patch(name="Test", category="lead")
    patch.osc1.waveform = "square"
    patch.mixer.osc1_level = 0.7
    patch.mixer.osc2_level = 0.3
    patch.filter.cutoff = 4000.0
    patch.amp_env.sustain = 0.5
    patch.effects.reverb_send = 0.4
    patch.lfo1.rate = 3.0
    patch.lfo1.key_sync = False

    voice = SynthVoice(44100)
    voice.load_patch(patch)

    assert voice.osc1.waveform == "square"
    assert voice.osc1_level == 0.7
    assert voice.osc2_level == 0.3
    assert voice.filter.cutoff == 4000.0
    assert voice.amp_env.sustain == 0.5
    assert voice.reverb_send == 0.4
    assert voice.lfo1.rate == 3.0
    assert voice.lfo1.key_sync is False


def test_audio_engine_load_patch_dispatches() -> None:
    """AudioEngine.load_patch should queue and dispatch to voices."""
    engine = AudioEngine()
    patch = Patch(name="Engine Test", category="test")
    patch.osc1.waveform = "triangle"
    patch.filter.cutoff = 2000.0

    engine.load_patch(patch)

    # Manually drain one callback cycle to process the queue
    engine._dispatch(("patch_load",))

    # All voices should have the patch loaded
    for voice in engine.voices:
        assert voice.osc1.waveform == "triangle"
        assert voice.filter.cutoff == 2000.0

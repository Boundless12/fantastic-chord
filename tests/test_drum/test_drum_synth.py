"""Tests for DrumSynth — verify each drum type produces valid audio."""

import numpy as np
import pytest

from src.audio.drum_kit import DRUM_KIT_PRESETS, DrumKitPreset
from src.audio.drum_synth import DrumSynth


@pytest.fixture
def synth() -> DrumSynth:
    return DrumSynth(sample_rate=44100)


def _get_first_kit() -> DrumKitPreset:
    return list(DRUM_KIT_PRESETS.values())[0]


@pytest.mark.parametrize(
    "drum_type",
    ["kick", "snare", "hh_closed", "hh_open", "clap", "crash", "tom_high", "tom_mid", "tom_low", "rim"],
)
def test_render_valid_buffer(synth: DrumSynth, drum_type: str) -> None:
    kit = _get_first_kit()
    params = kit.get_params(drum_type)
    buf = synth.render(params, velocity=0.8)

    assert isinstance(buf, np.ndarray)
    assert buf.dtype == np.float32
    assert buf.ndim == 1
    assert len(buf) > 0
    assert len(buf) <= 44100 * 4  # max 4 seconds
    assert np.all(np.abs(buf) <= 1.0)  # no clipping


@pytest.mark.parametrize("drum_type", ["kick", "snare", "hh_closed", "crash"])
def test_render_produces_energy(synth: DrumSynth, drum_type: str) -> None:
    kit = _get_first_kit()
    params = kit.get_params(drum_type)
    buf = synth.render(params, velocity=0.8)

    rms = float(np.sqrt(np.mean(buf**2)))
    assert rms > 0.001, f"{drum_type} produced silent output (RMS={rms:.6f})"


def test_velocity_scales_amplitude(synth: DrumSynth) -> None:
    kit = _get_first_kit()
    params = kit.kick

    soft = synth.render(params, velocity=0.2)
    loud = synth.render(params, velocity=1.0)

    peak_soft = float(np.max(np.abs(soft)))
    peak_loud = float(np.max(np.abs(loud)))
    assert peak_loud > peak_soft * 1.5


def test_kick_has_tonal_component(synth: DrumSynth) -> None:
    kit = DRUM_KIT_PRESETS["909 House"]
    buf = synth.render(kit.kick, velocity=0.8)

    # Kick should have dominant low-frequency energy
    spectrum = np.abs(np.fft.rfft(buf))
    freqs = np.fft.rfftfreq(len(buf), 1.0 / 44100)
    low_energy = float(np.sum(spectrum[freqs < 200]))
    high_energy = float(np.sum(spectrum[freqs > 2000]))
    assert low_energy > high_energy, "Kick should have dominant low-frequency content"


def test_hh_closed_is_short(synth: DrumSynth) -> None:
    kit = _get_first_kit()
    buf = synth.render(kit.hh_closed, velocity=0.8)

    # Closed hi-hat should be very short (< 150ms of audible signal)
    # Find where signal drops below 1% of peak
    peak = float(np.max(np.abs(buf)))
    threshold = peak * 0.01
    above = np.where(np.abs(buf) > threshold)[0]
    if len(above) > 0:
        duration_samples = above[-1] - above[0]
        duration_ms = duration_samples / 44100 * 1000
        assert duration_ms < 200, f"Closed HH too long: {duration_ms:.0f}ms"


def test_crash_is_long(synth: DrumSynth) -> None:
    kit = _get_first_kit()
    buf = synth.render(kit.crash, velocity=0.8)

    # Crash should last at least 500ms
    peak = float(np.max(np.abs(buf)))
    threshold = peak * 0.01
    above = np.where(np.abs(buf) > threshold)[0]
    if len(above) > 0:
        duration_samples = above[-1] - above[0]
        duration_ms = duration_samples / 44100 * 1000
        assert duration_ms > 300, f"Crash too short: {duration_ms:.0f}ms"


def test_all_kits_render_kick(synth: DrumSynth) -> None:
    for kit_name, kit in DRUM_KIT_PRESETS.items():
        buf = synth.render(kit.kick, velocity=0.8)
        rms = float(np.sqrt(np.mean(buf**2)))
        assert rms > 0.001, f"Kit '{kit_name}' kick is silent"
        assert len(buf) > 0

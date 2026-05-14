"""Tests for SynthVoice.apply_param — verify all routes work without error."""

import pytest

from src.audio.synth_voice import SynthVoice


@pytest.fixture
def voice() -> SynthVoice:
    v = SynthVoice(sample_rate=44100)
    v.note_on(60, 100)
    return v


# All param_paths that should be routable
ROUTABLE_PARAMS = [
    # OSC1
    ("osc1.waveform_int", 1.0),
    ("osc1.octave", 3.0),
    ("osc1.semitones", 0.5),
    ("osc1.detune_cents", 0.5),
    ("osc1.pulse_width", 0.5),
    ("osc1.phase", 0.0),
    # OSC2
    ("osc2.waveform_int", 2.0),
    ("osc2.octave", 3.0),
    ("osc2.semitones", 0.5),
    ("osc2.detune_cents", 0.5),
    ("osc2.pulse_width", 0.3),
    ("osc2.phase", 1.0),
    # Mixer
    ("mixer.osc1_level", 0.8),
    ("mixer.osc2_level", 0.5),
    ("mixer.noise_level", 0.3),
    # Filter
    ("filter.cutoff", 5000.0),
    ("filter.resonance", 0.4),
    ("filter.filter_type_int", 2.0),
    ("filter.env_amount", 0.5),
    ("filter.key_track", 0.3),
    # Amp Env
    ("amp_env.attack", 0.05),
    ("amp_env.decay", 0.3),
    ("amp_env.sustain", 0.7),
    ("amp_env.release", 0.4),
    # Filter Env
    ("filter_env.attack", 0.05),
    ("filter_env.decay", 0.3),
    ("filter_env.sustain", 0.5),
    ("filter_env.release", 0.4),
    ("filter_env.amount", 0.3),
    # LFO1
    ("lfo1.rate", 2.0),
    ("lfo1.depth", 0.5),
    ("lfo1.waveform_int", 1.0),
    ("lfo1.target_int", 2.0),
    ("lfo1.key_sync", 1.0),
    ("lfo1.one_shot", 0.0),
    ("lfo1.fade_in", 0.5),
    # LFO2
    ("lfo2.rate", 3.0),
    ("lfo2.depth", 0.3),
    ("lfo2.waveform_int", 3.0),
    ("lfo2.target_int", 1.0),
    ("lfo2.key_sync", 0.0),
    ("lfo2.one_shot", 1.0),
    ("lfo2.fade_in", 0.2),
    # Effects
    ("effects.reverb_send", 0.3),
    ("effects.delay_send", 0.2),
    ("effects.chorus_send", 0.1),
    ("effects.distortion_drive", 0.4),
    # Portamento
    ("portamento.time", 0.1),
]


@pytest.mark.parametrize("param_path, value", ROUTABLE_PARAMS)
def test_apply_param_no_error(voice: SynthVoice, param_path: str, value: float) -> None:
    """Every routable param_path should not raise an exception."""
    voice.apply_param(param_path, value)


def test_osc1_waveform_changes(voice: SynthVoice) -> None:
    voice.apply_param("osc1.waveform_int", 0.0)  # sine
    assert voice.osc1.waveform == "sine"
    voice.apply_param("osc1.waveform_int", 3.0)  # triangle
    assert voice.osc1.waveform == "triangle"


def test_osc2_detune_applied(voice: SynthVoice) -> None:
    voice.apply_param("osc2.detune_cents", 0.55)  # +5 cents from 0.5 center
    assert voice._osc2_detune_cents == 0.55


def test_mixer_levels_stored(voice: SynthVoice) -> None:
    voice.apply_param("mixer.osc1_level", 0.8)
    assert voice.osc1_level == 0.8
    voice.apply_param("mixer.osc2_level", 0.3)
    assert voice.osc2_level == 0.3
    voice.apply_param("mixer.noise_level", 0.5)
    assert voice.noise_level == 0.5


def test_filter_type_changes(voice: SynthVoice) -> None:
    voice.apply_param("filter.filter_type_int", 1.0)  # highpass
    assert voice.filter.filter_type == "highpass"
    voice.apply_param("filter.filter_type_int", 2.0)  # bandpass
    assert voice.filter.filter_type == "bandpass"


def test_cutoff_applied(voice: SynthVoice) -> None:
    voice.apply_param("filter.cutoff", 3000.0)
    assert voice.filter.cutoff == 3000.0


def test_lfo_waveform_and_target(voice: SynthVoice) -> None:
    voice.apply_param("lfo1.waveform_int", 2.0)  # square
    assert voice.lfo1.waveform == "square"
    voice.apply_param("lfo1.target_int", 1.0)  # osc_pitch
    assert voice.lfo1.target == "osc_pitch"


def test_lfo_key_sync_one_shot(voice: SynthVoice) -> None:
    voice.apply_param("lfo1.key_sync", 0.0)
    assert voice.lfo1.key_sync is False
    voice.apply_param("lfo1.one_shot", 1.0)
    assert voice.lfo1.one_shot is True


def test_effects_sends(voice: SynthVoice) -> None:
    voice.apply_param("effects.reverb_send", 0.5)
    assert voice.reverb_send == 0.5
    voice.apply_param("effects.delay_send", 0.3)
    assert voice.delay_send == 0.3

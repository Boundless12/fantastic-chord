"""Tests for DrumVoice — verify buffer playback and voice lifecycle."""

import numpy as np
import pytest

from src.audio.drum_voice import DrumVoice


@pytest.fixture
def voice() -> DrumVoice:
    return DrumVoice(sample_rate=44100)


def make_test_buffer(samples: int = 1000) -> np.ndarray:
    """Create a simple test buffer: 1kHz sine * exponential decay."""
    t = np.arange(samples, dtype=np.float32) / 44100
    env = np.exp(-t * 5.0).astype(np.float32)
    return (np.sin(2 * np.pi * 1000 * t) * env).astype(np.float32)


def test_initial_state(voice: DrumVoice) -> None:
    assert not voice.active
    assert voice.is_finished()


def test_trigger_activates(voice: DrumVoice) -> None:
    buf = make_test_buffer(1000)
    voice.trigger(buf, pan=0.0)
    assert voice.active
    assert not voice.is_finished()


def test_render_block_returns_audio(voice: DrumVoice) -> None:
    buf = make_test_buffer(1000)
    voice.trigger(buf, pan=0.0)

    block = voice.render_block(512)
    assert block.shape == (512,)
    assert block.dtype == np.float32
    assert np.any(block != 0.0)  # contains signal


def test_render_matches_buffer(voice: DrumVoice) -> None:
    """Verify that rendered blocks concatenate to match the original buffer."""
    buf = make_test_buffer(500)
    voice.trigger(buf, pan=0.0)

    rendered: list[np.ndarray] = []
    while voice.active:
        rendered.append(voice.render_block(128))

    result = np.concatenate(rendered)
    assert len(result) >= len(buf)
    np.testing.assert_array_almost_equal(result[: len(buf)], buf[: len(buf)], decimal=5)


def test_finishes_after_buffer(voice: DrumVoice) -> None:
    buf = make_test_buffer(1000)
    voice.trigger(buf, pan=0.0)

    total_rendered = 0
    while voice.active:
        block = voice.render_block(256)
        total_rendered += len(block)

    assert voice.is_finished()
    assert total_rendered >= len(buf)


def test_reset_clears_state(voice: DrumVoice) -> None:
    buf = make_test_buffer(1000)
    voice.trigger(buf, pan=0.0)
    assert voice.active

    voice.reset()
    assert not voice.active
    assert voice.is_finished()


def test_render_when_inactive_returns_zeros(voice: DrumVoice) -> None:
    block = voice.render_block(256)
    assert np.all(block == 0.0)


def test_retrigger_replaces_buffer(voice: DrumVoice) -> None:
    buf1 = make_test_buffer(500)
    buf2 = make_test_buffer(300)  # shorter

    voice.trigger(buf1, pan=0.0)
    voice.render_block(128)  # consume some
    voice.trigger(buf2, pan=0.0)  # retrigger with shorter buffer

    assert voice.active
    rendered: list[np.ndarray] = []
    while voice.active:
        rendered.append(voice.render_block(128))

    result = np.concatenate(rendered)
    # Should match buf2 (the retriggered buffer), not buf1
    np.testing.assert_array_almost_equal(result[: len(buf2)], buf2[: len(buf2)], decimal=5)


def test_pan_stereo_split(voice: DrumVoice) -> None:
    buf = make_test_buffer(500)

    # Full right
    voice.trigger(buf, pan=1.0)
    assert voice.pan_left < voice.pan_right

    # Full left
    voice.trigger(buf, pan=-1.0)
    assert voice.pan_left > voice.pan_right

    # Center
    voice.trigger(buf, pan=0.0)
    assert abs(voice.pan_left - voice.pan_right) < 0.01


def test_pan_bounds(voice: DrumVoice) -> None:
    buf = make_test_buffer(100)
    # Should not crash with extreme pan values
    voice.trigger(buf, pan=5.0)
    assert 0.0 <= voice.pan_left <= 1.0
    assert 0.0 <= voice.pan_right <= 1.0

    voice.trigger(buf, pan=-5.0)
    assert 0.0 <= voice.pan_left <= 1.0
    assert 0.0 <= voice.pan_right <= 1.0

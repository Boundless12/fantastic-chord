"""Tests for AudioEngine offline rendering."""

import numpy as np
import pytest

from src.audio.constants import CHANNELS, SAMPLE_RATE
from src.audio.engine import AudioEngine
from src.audio.patch import Patch


class TestEngine:
    @pytest.fixture
    def engine(self) -> AudioEngine:
        eng = AudioEngine()
        # Load a patch so voices have sound
        eng._current_patch = Patch()
        for voice in eng.voices:
            voice.load_patch(eng._current_patch)
        return eng

    def test_render_offline_returns_stereo_buffer(self, engine: AudioEngine) -> None:
        buffer, sr = engine.render_offline(duration_beats=4.0, bpm=120.0)
        assert sr == SAMPLE_RATE
        assert buffer.ndim == 2
        assert buffer.shape[1] == CHANNELS
        assert buffer.shape[0] > 0
        assert buffer.dtype == np.float32

    def test_render_offline_respects_bpm(self, engine: AudioEngine) -> None:
        buffer_fast, _ = engine.render_offline(duration_beats=4.0, bpm=200.0)
        buffer_slow, _ = engine.render_offline(duration_beats=4.0, bpm=60.0)
        # Faster BPM = shorter duration = fewer frames
        assert buffer_fast.shape[0] < buffer_slow.shape[0]

    def test_render_offline_restores_transport(self, engine: AudioEngine) -> None:
        engine.transport.position_beats = 10.0
        engine.transport.is_playing = True
        engine.transport.set_bpm(140.0)

        engine.render_offline(duration_beats=2.0, bpm=100.0)

        assert engine.transport.is_playing is True
        assert engine.transport.bpm == 140.0
        assert engine.transport.position_beats == 10.0

    def test_render_offline_stems_returns_three_keys(self, engine: AudioEngine) -> None:
        stems = engine.render_offline_stems(duration_beats=1.0, bpm=120.0)
        assert set(stems.keys()) == {"synth", "drums", "master"}
        for buffer, sr in stems.values():
            assert sr == SAMPLE_RATE
            assert buffer.ndim == 2
            assert buffer.shape[1] == CHANNELS

    def test_render_offline_produces_audio(self, engine: AudioEngine) -> None:
        # Trigger a note so there's something to render
        engine.note_on(60, 100)
        import time

        time.sleep(0.05)  # Let the command dispatch
        buffer, _ = engine.render_offline(duration_beats=1.0, bpm=120.0)
        # Should have some non-zero samples
        assert np.max(np.abs(buffer)) > 0
        engine.note_off(60)

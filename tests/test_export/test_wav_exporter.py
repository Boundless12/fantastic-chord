"""Tests for WavExporter."""

import os
import tempfile
from unittest.mock import MagicMock

import numpy as np

from src.audio.constants import SAMPLE_RATE
from src.export.wav_exporter import WavExporter


class TestWavExporter:
    def test_export_writes_file(self) -> None:
        engine = MagicMock()
        buffer = np.zeros((44100, 2), dtype=np.float32)
        engine.render_offline.return_value = (buffer, SAMPLE_RATE)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name

        try:
            success = WavExporter.export(engine, tmp_path, duration_beats=4.0, bpm=120.0)
            assert success
            assert os.path.getsize(tmp_path) > 0
        finally:
            os.unlink(tmp_path)

    def test_export_failure_returns_false(self) -> None:
        engine = MagicMock()
        engine.render_offline.side_effect = RuntimeError("Boom")
        success = WavExporter.export(engine, "/nonexistent/path.wav")
        assert not success

    def test_export_stems_writes_three_files(self) -> None:
        engine = MagicMock()
        buffer = np.zeros((22050, 2), dtype=np.float32)
        engine.render_offline_stems.return_value = {
            "synth": (buffer, SAMPLE_RATE),
            "drums": (buffer, SAMPLE_RATE),
            "master": (buffer, SAMPLE_RATE),
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            success = WavExporter.export_stems(engine, tmp_dir, duration_beats=4.0, bpm=120.0)
            assert success
            for name in ("synth", "drums", "master"):
                path = os.path.join(tmp_dir, f"{name}.wav")
                assert os.path.isfile(path)
                assert os.path.getsize(path) > 0

    def test_export_stems_failure_returns_false(self) -> None:
        engine = MagicMock()
        engine.render_offline_stems.side_effect = RuntimeError("Boom")
        with tempfile.TemporaryDirectory() as tmp_dir:
            success = WavExporter.export_stems(engine, tmp_dir)
            assert not success

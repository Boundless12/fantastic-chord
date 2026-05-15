"""Tests for MidiExporter."""

import os
import tempfile

from src.export.midi_exporter import MidiExporter
from src.sequencer.drum_pattern import DrumPattern
from src.sequencer.pattern import Note, Pattern


class TestMidiExporter:
    def test_export_piano_roll_writes_file(self) -> None:
        pattern = Pattern(
            notes=[
                Note(pitch=60, velocity=100, start_time=0.0, duration=1.0),
                Note(pitch=64, velocity=90, start_time=1.0, duration=1.0),
            ],
            length_beats=4.0,
        )

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            tmp_path = f.name

        try:
            success = MidiExporter.export_piano_roll(pattern, bpm=120.0, filepath=tmp_path)
            assert success
            assert os.path.getsize(tmp_path) > 0
        finally:
            os.unlink(tmp_path)

    def test_export_drum_pattern_writes_file(self) -> None:
        pattern = DrumPattern.empty()
        pattern.kick[0].active = True
        pattern.kick[8].active = True
        pattern.snare[4].active = True
        pattern.snare[12].active = True
        pattern.hh_closed[0].active = True
        pattern.hh_closed[2].active = True

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            tmp_path = f.name

        try:
            success = MidiExporter.export_drum_pattern(pattern, bpm=120.0, filepath=tmp_path)
            assert success
            assert os.path.getsize(tmp_path) > 0
        finally:
            os.unlink(tmp_path)

    def test_export_project_writes_file(self) -> None:
        pr_pattern = Pattern(
            notes=[Note(pitch=60, velocity=100, start_time=0.0, duration=1.0)],
            length_beats=4.0,
        )
        drum_pattern = DrumPattern.empty()
        drum_pattern.kick[0].active = True

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            tmp_path = f.name

        try:
            success = MidiExporter.export_project(pr_pattern, drum_pattern, bpm=120.0, filepath=tmp_path)
            assert success
            assert os.path.getsize(tmp_path) > 0
        finally:
            os.unlink(tmp_path)

    def test_export_failure_returns_false(self) -> None:
        pattern = Pattern(notes=[], length_beats=4.0)
        success = MidiExporter.export_piano_roll(pattern, bpm=120.0, filepath="/nonexistent/path.mid")
        assert not success

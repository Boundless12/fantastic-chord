"""Tests for MidiFileIO read/write."""

import os
import tempfile

from src.midi.file_io import MidiFileData, MidiFileIO, MidiNote, MidiTrackData


class TestMidiFileIO:
    def test_roundtrip_single_track(self) -> None:
        notes = [
            MidiNote(pitch=60, velocity=100, start_time=0.0, duration=1.0),
            MidiNote(pitch=64, velocity=90, start_time=1.0, duration=1.0),
            MidiNote(pitch=67, velocity=80, start_time=2.0, duration=2.0),
        ]
        track = MidiTrackData(name="Test", notes=notes, channel=0)
        data = MidiFileData(tracks=[track], bpm=120)

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            tmp_path = f.name

        try:
            MidiFileIO.save(data, tmp_path)
            loaded = MidiFileIO.load(tmp_path)

            assert loaded.bpm == 120
            assert len(loaded.tracks) >= 1
            loaded_track = loaded.tracks[0]
            assert len(loaded_track.notes) == 3
            assert loaded_track.notes[0].pitch == 60
        finally:
            os.unlink(tmp_path)

    def test_roundtrip_drum_track(self) -> None:
        notes = [
            MidiNote(pitch=36, velocity=100, start_time=0.0, duration=0.5),
            MidiNote(pitch=36, velocity=100, start_time=1.0, duration=0.5),
        ]
        track = MidiTrackData(name="Drums", notes=notes, channel=9)
        data = MidiFileData(tracks=[track], bpm=140)

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            tmp_path = f.name

        try:
            MidiFileIO.save(data, tmp_path)
            loaded = MidiFileIO.load(tmp_path)

            assert len(loaded.tracks) >= 1
            assert len(loaded.tracks[0].notes) == 2
        finally:
            os.unlink(tmp_path)

    def test_multi_track_roundtrip(self) -> None:
        track1 = MidiTrackData(
            name="Melody",
            notes=[MidiNote(pitch=72, velocity=100, start_time=0.0, duration=1.0)],
            channel=0,
        )
        track2 = MidiTrackData(
            name="Bass",
            notes=[MidiNote(pitch=36, velocity=80, start_time=0.0, duration=2.0)],
            channel=1,
        )
        data = MidiFileData(tracks=[track1, track2], bpm=128)

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            tmp_path = f.name

        try:
            MidiFileIO.save(data, tmp_path)
            loaded = MidiFileIO.load(tmp_path)
            assert len(loaded.tracks) >= 2
        finally:
            os.unlink(tmp_path)

    def test_empty_file_returns_empty_tracks(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            tmp_path = f.name

        try:
            # Write minimal MIDI
            from mido import MidiFile, MidiTrack

            mid = MidiFile()
            mid.tracks.append(MidiTrack())
            mid.save(tmp_path)

            loaded = MidiFileIO.load(tmp_path)
            assert loaded.tracks is not None
        finally:
            os.unlink(tmp_path)

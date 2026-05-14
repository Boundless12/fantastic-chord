"""MidiFileIO: MIDI file read/write via mido."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import mido

logger = logging.getLogger(__name__)


@dataclass
class MidiNote:
    """A single note in a MIDI file track."""

    pitch: int
    velocity: int
    start_time: float
    duration: float


@dataclass
class MidiTrackData:
    """Raw track data read from / to be written to a MIDI file."""

    name: str
    notes: list[MidiNote] = field(default_factory=list)
    channel: int = 0
    program: int = 0
    control_changes: list[tuple[float, int, int]] = field(default_factory=list)
    pitch_bends: list[tuple[float, int]] = field(default_factory=list)

    def add_note(self, pitch: int, velocity: int, start: float, duration: float) -> None:
        self.notes.append(MidiNote(pitch, velocity, start, duration))


@dataclass
class MidiFileData:
    """Complete MIDI file data."""

    tracks: list[MidiTrackData] = field(default_factory=list)
    bpm: float = 120.0
    time_signature: tuple[int, int] = (4, 4)
    ticks_per_beat: int = 480


class MidiFileIO:
    """MIDI file read/write using mido."""

    @staticmethod
    def load(path: str) -> MidiFileData:
        """Parse a .mid file into MidiFileData."""
        mid = mido.MidiFile(path)
        result = MidiFileData(ticks_per_beat=mid.ticks_per_beat)

        tempo = 500000
        time_sig = (4, 4)

        for i, track in enumerate(mid.tracks):
            track_data = MidiTrackData(name=f"Track {i + 1}", channel=i)
            abs_time = 0
            active_notes: dict[int, tuple[float, int]] = {}

            for msg in track:
                abs_time += msg.time

                if msg.type == "set_tempo":
                    tempo = msg.tempo
                elif msg.type == "time_signature":
                    time_sig = (msg.numerator, msg.denominator)
                elif msg.type == "program_change":
                    track_data.program = msg.program
                    track_data.channel = msg.channel
                elif msg.type == "control_change":
                    track_data.control_changes.append((abs_time, msg.control, msg.value))
                elif msg.type == "pitchwheel":
                    track_data.pitch_bends.append((abs_time, msg.pitch))

                elif msg.type == "note_on" and msg.velocity > 0:
                    active_notes[msg.note] = (abs_time, msg.velocity)

                elif (
                    msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0)
                ) and msg.note in active_notes:
                    start_t, vel = active_notes.pop(msg.note)
                    duration = abs_time - start_t
                    track_data.add_note(msg.note, vel, start_t, duration)

            result.tracks.append(track_data)

        result.bpm = 60000000 / tempo
        result.time_signature = time_sig
        logger.info(f"Loaded MIDI file: {path} ({len(result.tracks)} tracks, {result.bpm:.1f} BPM)")
        return result

    @staticmethod
    def save(data: MidiFileData, path: str) -> None:
        """Write MidiFileData to a standard MIDI file."""
        mid = mido.MidiFile(ticks_per_beat=data.ticks_per_beat)

        tempo = mido.bpm2tempo(data.bpm)

        for track_idx, track_data in enumerate(data.tracks):
            mido_track = mido.MidiTrack()

            if track_idx == 0:
                mido_track.append(mido.MetaMessage("set_tempo", tempo=tempo))
                mido_track.append(
                    mido.MetaMessage(
                        "time_signature", numerator=data.time_signature[0], denominator=data.time_signature[1]
                    )
                )
                mido_track.append(mido.MetaMessage("track_name", name=track_data.name))

            # Sort all events by time
            events: list[tuple[float, str, Any]] = []

            for note in track_data.notes:
                events.append((note.start_time, "note_on", note))
                events.append((note.start_time + note.duration, "note_off", note))

            for cc_time, controller, value in track_data.control_changes:
                events.append((cc_time, "cc", (controller, value)))

            for pb_time, value in track_data.pitch_bends:
                events.append((pb_time, "pb", value))

            events.sort(key=lambda e: e[0])

            prev_time: float = 0.0
            for evt_time, evt_type, evt_data in events:
                delta = int((evt_time - prev_time) * data.ticks_per_beat)
                prev_time = evt_time

                if evt_type == "note_on":
                    note_data: MidiNote = evt_data
                    mido_track.append(
                        mido.Message(
                            "note_on", note=note_data.pitch, velocity=note_data.velocity, time=delta, channel=track_idx
                        )
                    )
                elif evt_type == "note_off":
                    note_data = evt_data
                    mido_track.append(
                        mido.Message("note_off", note=note_data.pitch, velocity=0, time=delta, channel=track_idx)
                    )
                elif evt_type == "cc":
                    ctrl, val = evt_data
                    mido_track.append(
                        mido.Message("control_change", control=ctrl, value=val, time=delta, channel=track_idx)
                    )
                elif evt_type == "pb":
                    mido_track.append(mido.Message("pitchwheel", pitch=evt_data, time=delta, channel=track_idx))

            mid.tracks.append(mido_track)

        mid.save(path)
        logger.info(f"Saved MIDI file: {path} ({len(data.tracks)} tracks, {data.bpm:.1f} BPM)")

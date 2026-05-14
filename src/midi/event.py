"""MIDI event dataclasses for real-time and file-based MIDI messaging."""

from dataclasses import dataclass
from enum import IntEnum, auto


class MidiEventType(IntEnum):
    NOTE_ON = auto()
    NOTE_OFF = auto()
    CONTROL_CHANGE = auto()
    PITCH_BEND = auto()
    PROGRAM_CHANGE = auto()
    AFTERTOUCH = auto()
    CHANNEL_PRESSURE = auto()


@dataclass
class MidiEvent:
    """Base MIDI event."""

    channel: int = 0
    timestamp: float = 0.0
    event_type: MidiEventType = MidiEventType.NOTE_ON


@dataclass
class NoteOnEvent(MidiEvent):
    note: int = 60
    velocity: int = 100
    event_type: MidiEventType = MidiEventType.NOTE_ON


@dataclass
class NoteOffEvent(MidiEvent):
    note: int = 60
    velocity: int = 64
    event_type: MidiEventType = MidiEventType.NOTE_OFF


@dataclass
class ControlChangeEvent(MidiEvent):
    controller: int = 0
    value: int = 0
    event_type: MidiEventType = MidiEventType.CONTROL_CHANGE


@dataclass
class PitchBendEvent(MidiEvent):
    value: int = 0
    event_type: MidiEventType = MidiEventType.PITCH_BEND


@dataclass
class ProgramChangeEvent(MidiEvent):
    program: int = 0
    event_type: MidiEventType = MidiEventType.PROGRAM_CHANGE


class MidiParser:
    """Parse raw MIDI bytes into MidiEvent objects."""

    @staticmethod
    def parse(status_byte: int, data1: int, data2: int = 0, timestamp: float = 0.0) -> MidiEvent | None:
        """Parse a 2-3 byte MIDI message into a MidiEvent."""
        msg_type = status_byte & 0xF0
        channel = status_byte & 0x0F

        if msg_type == 0x80:
            return NoteOffEvent(channel=channel, note=data1, velocity=data2, timestamp=timestamp)
        elif msg_type == 0x90:
            if data2 == 0:
                return NoteOffEvent(channel=channel, note=data1, velocity=0, timestamp=timestamp)
            return NoteOnEvent(channel=channel, note=data1, velocity=data2, timestamp=timestamp)
        elif msg_type == 0xB0:
            return ControlChangeEvent(channel=channel, controller=data1, value=data2, timestamp=timestamp)
        elif msg_type == 0xE0:
            bend_value = (data2 << 7) | data1
            return PitchBendEvent(channel=channel, value=bend_value - 8192, timestamp=timestamp)
        elif msg_type == 0xC0:
            return ProgramChangeEvent(channel=channel, program=data1, timestamp=timestamp)
        return None

    @staticmethod
    def to_midi_bytes(event: MidiEvent) -> tuple[int, int, int]:
        """Convert a MidiEvent back to raw MIDI bytes (status, data1, data2)."""
        if isinstance(event, NoteOnEvent):
            return (0x90 | event.channel, event.note, event.velocity)
        elif isinstance(event, NoteOffEvent):
            return (0x80 | event.channel, event.note, event.velocity)
        elif isinstance(event, ControlChangeEvent):
            return (0xB0 | event.channel, event.controller, event.value)
        elif isinstance(event, PitchBendEvent):
            val = event.value + 8192
            return (0xE0 | event.channel, val & 0x7F, (val >> 7) & 0x7F)
        elif isinstance(event, ProgramChangeEvent):
            return (0xC0 | event.channel, event.program, 0)
        return (0, 0, 0)

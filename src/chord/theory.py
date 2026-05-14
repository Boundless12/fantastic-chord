"""Music theory utilities wrapping music21 for scale and chord operations."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import music21 as m21

logger = logging.getLogger(__name__)

m21.environment.UserSettings()["autoDownload"] = "deny"  # type: ignore[no-untyped-call]

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SCALE_PATTERNS: dict[str, tuple[int, ...]] = {
    "major": (2, 2, 1, 2, 2, 2, 1),
    "natural_minor": (2, 1, 2, 2, 1, 2, 2),
    "harmonic_minor": (2, 1, 2, 2, 1, 3, 1),
    "melodic_minor": (2, 1, 2, 2, 2, 2, 1),
    "dorian": (2, 1, 2, 2, 2, 1, 2),
    "phrygian": (1, 2, 2, 2, 1, 2, 2),
    "lydian": (2, 2, 2, 1, 2, 2, 1),
    "mixolydian": (2, 2, 1, 2, 2, 1, 2),
    "locrian": (1, 2, 2, 1, 2, 2, 2),
}

CHORD_QUALITIES: dict[str, tuple[int, ...]] = {
    "maj": (0, 4, 7),
    "min": (0, 3, 7),
    "dim": (0, 3, 6),
    "aug": (0, 4, 8),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
    "maj7": (0, 4, 7, 11),
    "min7": (0, 3, 7, 10),
    "dom7": (0, 4, 7, 10),
    "dim7": (0, 3, 6, 9),
    "m7b5": (0, 3, 6, 10),
    "maj9": (0, 4, 7, 11, 2),
    "min9": (0, 3, 7, 10, 2),
    "dom9": (0, 4, 7, 10, 2),
    "maj7#11": (0, 4, 7, 11, 6),
    "add9": (0, 4, 7, 2),
    "min11": (0, 3, 7, 10, 5),
    "7sus4": (0, 5, 7, 10),
    "maj7sus2": (0, 2, 7, 11),
}

DIATONIC_MAJOR: list[str] = ["maj", "min", "min", "maj", "maj", "min", "dim"]
DIATONIC_MINOR: list[str] = ["min", "dim", "maj", "min", "min", "maj", "maj"]
DIATONIC_MAJOR_7TH: list[str] = ["maj7", "min7", "min7", "maj7", "dom7", "min7", "m7b5"]
DIATONIC_MINOR_7TH: list[str] = ["min7", "m7b5", "maj7", "min7", "min7", "maj7", "dom7"]


@dataclass
class ScaleData:
    """A musical scale."""

    root: int
    scale_type: str
    notes: list[int] = field(default_factory=list)


@dataclass
class ChordData:
    """A chord built from a root and quality."""

    root: int
    quality: str
    notes: list[int] = field(default_factory=list)
    duration: float = 1.0


@dataclass
class ProgressionData:
    """A complete chord progression."""

    chords: list[ChordData] = field(default_factory=list)
    key: str = "C"
    scale_type: str = "major"
    style: str = ""
    bpm: float = 120.0
    time_signature: tuple[int, int] = (4, 4)


class ChordTheory:
    """Music theory utilities."""

    @staticmethod
    def note_name_to_midi(name: str) -> int:
        """Convert a pitch name like 'C4' or 'C#' to MIDI number."""
        pitch = m21.pitch.Pitch(name)
        return int(pitch.midi)

    @staticmethod
    def midi_to_note_name(midi_note: int) -> str:
        """Convert MIDI number to pitch name with octave."""
        pitch = m21.pitch.Pitch()
        pitch.midi = midi_note
        return str(pitch)

    @staticmethod
    def root_to_midi(key: str, octave: int = 4) -> int:
        """Convert a key name like 'C', 'Eb' to MIDI number."""
        idx = NOTE_NAMES.index(key) if key in NOTE_NAMES else 0
        return idx + octave * 12

    @staticmethod
    def get_scale(root: str, scale_type: str = "major") -> ScaleData:
        """Return a scale as MIDI notes starting from the root at octave 4."""
        pattern = SCALE_PATTERNS.get(scale_type, SCALE_PATTERNS["major"])
        root_midi = ChordTheory.root_to_midi(root)
        notes: list[int] = [root_midi]
        current = root_midi
        for step in pattern[:-1]:
            current += step
            notes.append(current)
        return ScaleData(root=root_midi, scale_type=scale_type, notes=notes)

    @staticmethod
    def get_chord_tones(root: int, quality: str) -> list[int]:
        """Return MIDI notes for a chord given its root and quality."""
        intervals = CHORD_QUALITIES.get(quality, CHORD_QUALITIES["maj"])
        return [root + i for i in intervals]

    @staticmethod
    def diatonic_chords(key: str, scale_type: str = "major") -> dict[int, list[int]]:
        """Return all diatonic triads mapped by scale degree (1-7)."""
        scale = ChordTheory.get_scale(key, scale_type)
        diatonic = DIATONIC_MAJOR if scale_type in ("major", "lydian", "mixolydian") else DIATONIC_MINOR

        result: dict[int, list[int]] = {}
        for i, note in enumerate(scale.notes):
            degree = i + 1
            quality = diatonic[i]
            result[degree] = ChordTheory.get_chord_tones(note, quality)
        return result

    @staticmethod
    def chord_to_symbol(root: int, quality: str) -> str:
        """Convert a root + quality to a chord symbol like 'Cm7'."""
        pitch_class = root % 12
        note_name = NOTE_NAMES[pitch_class]
        quality_map: dict[str, str] = {
            "maj": "",
            "min": "m",
            "dim": "dim",
            "aug": "aug",
            "sus2": "sus2",
            "sus4": "sus4",
            "maj7": "maj7",
            "min7": "m7",
            "dom7": "7",
            "dim7": "dim7",
            "m7b5": "m7b5",
            "maj9": "maj9",
            "min9": "m9",
            "dom9": "9",
            "maj7#11": "maj7#11",
            "add9": "add9",
            "min11": "m11",
            "7sus4": "7sus4",
            "maj7sus2": "maj7sus2",
        }
        suffix = quality_map.get(quality, "")
        return f"{note_name}{suffix}"

    @staticmethod
    def progression_to_symbols(progression: ProgressionData) -> list[str]:
        """Convert all chords in a progression to chord symbols."""
        return [ChordTheory.chord_to_symbol(c.root, c.quality) for c in progression.chords]

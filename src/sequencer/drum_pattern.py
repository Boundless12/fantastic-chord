"""Drum pattern data model with step-sequencer grid and GM drum map."""

from __future__ import annotations

from dataclasses import dataclass, field

from .pattern import Note, Pattern

# General MIDI drum note map
GM_KICK = 36
GM_SNARE = 38
GM_CLAP = 39
GM_HH_CLOSED = 42
GM_HH_OPEN = 46
GM_TOM_LOW = 45
GM_TOM_MID = 47
GM_TOM_HIGH = 50
GM_RIMSHOT = 37
GM_CRASH = 49

GM_DRUM_MAP: dict[str, int] = {
    "kick": GM_KICK,
    "snare": GM_SNARE,
    "hh_closed": GM_HH_CLOSED,
    "hh_open": GM_HH_OPEN,
    "clap": GM_CLAP,
    "crash": GM_CRASH,
    "tom_high": GM_TOM_HIGH,
    "tom_mid": GM_TOM_MID,
    "tom_low": GM_TOM_LOW,
    "rim": GM_RIMSHOT,
}

GM_DRUM_REVERSE: dict[int, str] = {v: k for k, v in GM_DRUM_MAP.items()}

DRUM_TYPES: list[str] = [
    "kick",
    "snare",
    "hh_closed",
    "hh_open",
    "clap",
    "crash",
    "tom_high",
    "tom_mid",
    "tom_low",
    "rim",
]

DRUM_COLORS: dict[str, str] = {
    "kick": "#ff6b6b",
    "snare": "#4d96ff",
    "hh_closed": "#ffd93d",
    "hh_open": "#ff922b",
    "clap": "#6bcb77",
    "crash": "#4ecdc4",
    "tom_high": "#845ef7",
    "tom_mid": "#f06595",
    "tom_low": "#cc5de8",
    "rim": "#94d82d",
}

DRUM_LABELS: dict[str, str] = {
    "kick": "Kick",
    "snare": "Snare",
    "hh_closed": "HH C",
    "hh_open": "HH O",
    "clap": "Clap",
    "crash": "Crash",
    "tom_high": "T H",
    "tom_mid": "T M",
    "tom_low": "T L",
    "rim": "Rim",
}


@dataclass
class DrumStep:
    """A single step in a drum pattern grid."""

    active: bool = False
    velocity: float = 1.0
    micro_offset: float = 0.0
    flam: bool = False


@dataclass
class DrumPattern:
    """16-step drum pattern grid — one pattern per bar (4/4, 16th notes)."""

    name: str = "Drum Pattern"
    steps: int = 16

    kick: list[DrumStep] = field(default_factory=lambda: [DrumStep() for _ in range(16)])
    snare: list[DrumStep] = field(default_factory=lambda: [DrumStep() for _ in range(16)])
    hh_closed: list[DrumStep] = field(default_factory=lambda: [DrumStep() for _ in range(16)])
    hh_open: list[DrumStep] = field(default_factory=lambda: [DrumStep() for _ in range(16)])
    clap: list[DrumStep] = field(default_factory=lambda: [DrumStep() for _ in range(16)])
    crash: list[DrumStep] = field(default_factory=lambda: [DrumStep() for _ in range(16)])
    tom_high: list[DrumStep] = field(default_factory=lambda: [DrumStep() for _ in range(16)])
    tom_mid: list[DrumStep] = field(default_factory=lambda: [DrumStep() for _ in range(16)])
    tom_low: list[DrumStep] = field(default_factory=lambda: [DrumStep() for _ in range(16)])
    rim: list[DrumStep] = field(default_factory=lambda: [DrumStep() for _ in range(16)])

    def get_parts(self) -> dict[str, list[DrumStep]]:
        """Return mapping of drum type name to its step list."""
        return {
            "kick": self.kick,
            "snare": self.snare,
            "hh_closed": self.hh_closed,
            "hh_open": self.hh_open,
            "clap": self.clap,
            "crash": self.crash,
            "tom_high": self.tom_high,
            "tom_mid": self.tom_mid,
            "tom_low": self.tom_low,
            "rim": self.rim,
        }

    def to_pattern(self, bpm: float) -> Pattern:
        """Convert drum grid to a Pattern of Note events for sequencer compatibility."""
        step_duration = 60.0 / bpm / 4.0  # 16th note duration in seconds
        notes: list[Note] = []

        parts = self.get_parts()
        for drum_type, steps in parts.items():
            pitch = GM_DRUM_MAP.get(drum_type, 0)
            for i, step in enumerate(steps):
                if step.active:
                    start_time = i * step_duration
                    notes.append(
                        Note(
                            pitch=pitch,
                            velocity=int(step.velocity * 127),
                            start_time=start_time,
                            duration=step_duration * 0.8,
                        )
                    )

        pattern = Pattern(name=self.name, notes=notes, length_beats=4.0)
        return pattern

    @classmethod
    def from_pattern(cls, pattern: Pattern, bpm: float = 120.0) -> DrumPattern:
        """Restore a DrumPattern from a Pattern, best-effort.

        Args:
            pattern: Source pattern with note events in seconds.
            bpm: Tempo used to convert seconds back to beat-position steps.
        """
        drum = cls(name=pattern.name)
        step_duration_seconds = 60.0 / bpm / 4.0  # 16th note in seconds

        for note in pattern.notes:
            drum_type = GM_DRUM_REVERSE.get(note.pitch)
            if drum_type is None:
                continue
            step_idx = int(note.start_time / step_duration_seconds)
            if 0 <= step_idx < drum.steps:
                parts = drum.get_parts()
                step_list = parts[drum_type]
                step_list[step_idx].active = True
                step_list[step_idx].velocity = note.velocity / 127.0

        return drum

    @classmethod
    def empty(cls, name: str = "Empty", steps: int = 16) -> DrumPattern:
        """Create an empty drum pattern."""
        return cls(name=name, steps=steps)

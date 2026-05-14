"""Pattern and Note dataclasses for the sequencer."""

from dataclasses import dataclass, field


@dataclass
class Note:
    """A single note event in the piano roll."""

    pitch: int
    velocity: int
    start_time: float
    duration: float
    muted: bool = False

    def end_time(self) -> float:
        return self.start_time + self.duration


@dataclass
class Pattern:
    """A container of Note events — one musical phrase."""

    name: str = "Pattern"
    notes: list[Note] = field(default_factory=list)
    length_beats: float = 16.0


@dataclass
class Chord:
    """A chord as a collection of simultaneous notes."""

    root: int
    quality: str
    notes: list[int] = field(default_factory=list)
    duration: float = 1.0

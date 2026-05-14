"""Track dataclass for the sequencer."""

from dataclasses import dataclass, field

from .pattern import Pattern


@dataclass
class Track:
    """A track containing patterns, assigned to one instrument."""

    name: str = "Track"
    instrument_name: str = "Synth"
    patterns: list[Pattern] = field(default_factory=list)
    channel: int = 0
    color: str = "#4ecdc4"
    volume: float = 1.0
    pan: float = 0.0
    mute: bool = False
    solo: bool = False

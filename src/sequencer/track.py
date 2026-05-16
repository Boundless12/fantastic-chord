"""Track dataclass for the sequencer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from .pattern import Pattern


class InstrumentType(Enum):
    """Type of instrument assigned to a track."""

    SYNTH = auto()
    DRUMS = auto()


@dataclass
class Track:
    """A track containing patterns, assigned to one instrument."""

    name: str = "Track"
    instrument_type: InstrumentType = InstrumentType.SYNTH
    patterns: list[Pattern] = field(default_factory=list)
    channel: int = 0
    color: str = "#4ecdc4"
    volume: float = 1.0
    pan: float = 0.0
    mute: bool = False
    solo: bool = False

    @property
    def instrument_name(self) -> str:
        return self.instrument_type.name.title()

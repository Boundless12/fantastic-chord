"""Clip dataclass for arrangement timeline."""

from dataclasses import dataclass

from .pattern import Pattern


@dataclass
class Clip:
    """A placement of a pattern on the arrangement timeline."""

    pattern: Pattern
    track_index: int
    start_beat: float
    length_beats: float
    loop: bool = False
    muted: bool = False

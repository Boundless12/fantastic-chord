"""PianoRollSequencer: Transport-synced note sequencer for piano roll patterns."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .pattern import Note, Pattern
from .transport import Transport

if TYPE_CHECKING:
    from ..audio.engine import AudioEngine


class PianoRollSequencer:
    """Scans a Pattern's notes and triggers synth voices in sync with transport.

    Called once per audio callback block. Detects note-on and note-off
    edges from transport position and triggers voice allocation directly.
    """

    pattern: Pattern | None
    _transport: Transport
    _last_position_beats: float
    _active_notes: dict[int, float]  # pitch -> end_time (beats)
    _enabled: bool

    def __init__(self, transport: Transport) -> None:
        self._transport = transport
        self.pattern = None
        self._last_position_beats = 0.0
        self._active_notes = {}
        self._enabled = True

    def set_pattern(self, pattern: Pattern) -> None:
        self.pattern = pattern

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self._active_notes.clear()

    def process(self, engine: AudioEngine) -> None:
        """Scan pattern notes and trigger note-on/note-off for edge transitions.

        Called from the audio callback thread.
        """
        if not self._enabled or self.pattern is None:
            return

        current_pos = self._transport.position_beats
        last_pos = self._last_position_beats

        notes = self.pattern.notes
        pattern_length = self.pattern.length_beats

        # Detect wrap-around
        if current_pos < last_pos:
            # Handle crossing the loop boundary
            self._scan_interval(last_pos, pattern_length, engine, notes)
            self._scan_interval(0.0, current_pos, engine, notes)
        else:
            self._scan_interval(last_pos, current_pos, engine, notes)

        self._last_position_beats = current_pos

    def _scan_interval(self, start_beats: float, end_beats: float, engine: AudioEngine, notes: list[Note]) -> None:
        """Scan for note edges in the interval [start_beats, end_beats)."""
        for note in notes:
            n_start = note.start_time
            n_end = note.end_time()
            pitch = note.pitch

            # Note-on: note starts in this interval
            if start_beats <= n_start < end_beats and pitch not in self._active_notes:
                engine._note_on_direct(pitch, note.velocity)
                self._active_notes[pitch] = n_end

            # Note-off: note ends in this interval
            if start_beats <= n_end < end_beats and pitch in self._active_notes:
                engine._note_off_direct(pitch)
                del self._active_notes[pitch]

    def reset(self) -> None:
        self._last_position_beats = 0.0
        self._active_notes.clear()

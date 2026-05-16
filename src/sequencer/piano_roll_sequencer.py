"""PianoRollSequencer: Transport-synced note sequencer for piano roll patterns."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .pattern import Note, Pattern
from .transport import Transport

if TYPE_CHECKING:
    from ..audio.engine import AudioEngine


class PianoRollSequencer:
    """Scans multiple track patterns and triggers synth voices in sync with transport.

    Called once per audio callback block. Detects note-on and note-off
    edges from transport position and triggers voice allocation directly.
    Supports multiple tracks via a dict of track_index -> Pattern.
    """

    patterns: dict[int, Pattern]
    _transport: Transport
    _last_position_beats: float
    _active_notes: dict[tuple[int, int], float]  # (track_index, pitch) -> end_time (beats)
    _enabled: bool

    def __init__(self, transport: Transport) -> None:
        self._transport = transport
        self.patterns = {}
        self._last_position_beats = 0.0
        self._active_notes = {}
        self._enabled = True

    def set_pattern(self, track_index: int, pattern: Pattern) -> None:
        self.patterns[track_index] = pattern

    def remove_track(self, track_index: int) -> None:
        self.patterns.pop(track_index, None)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self._active_notes.clear()

    def process(self, engine: AudioEngine) -> None:
        """Scan all track patterns and trigger note-on/note-off for edge transitions.

        Called from the audio callback thread.
        """
        if not self._enabled or not self.patterns:
            return

        current_pos = self._transport.position_beats
        last_pos = self._last_position_beats

        for track_index, pattern in self.patterns.items():
            notes = pattern.notes
            pattern_length = pattern.length_beats

            if current_pos < last_pos:
                self._scan_interval(last_pos, pattern_length, engine, notes, track_index)
                self._scan_interval(0.0, current_pos, engine, notes, track_index)
            else:
                self._scan_interval(last_pos, current_pos, engine, notes, track_index)

        self._last_position_beats = current_pos

    def _scan_interval(
        self, start_beats: float, end_beats: float, engine: AudioEngine, notes: list[Note], track_index: int
    ) -> None:
        """Scan for note edges in the interval [start_beats, end_beats)."""
        for note in notes:
            n_start = note.start_time
            n_end = note.end_time()
            pitch = note.pitch
            key = (track_index, pitch)

            if start_beats <= n_start < end_beats and key not in self._active_notes:
                engine._note_on_direct(pitch, note.velocity, track_index)
                self._active_notes[key] = n_end

            if start_beats <= n_end < end_beats and key in self._active_notes:
                engine._note_off_direct(pitch, track_index)
                del self._active_notes[key]

    def reset(self) -> None:
        self._last_position_beats = 0.0
        self._active_notes.clear()

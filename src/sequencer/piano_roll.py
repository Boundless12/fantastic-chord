"""PianoRollModel: Data model for the piano roll editor with undo/redo support."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QObject, Signal

from .pattern import Note, Pattern
from .track import Track
from .transport import Transport

logger = logging.getLogger(__name__)

TRACK_COLORS: list[str] = ["#4ecdc4", "#ff6b6b", "#ffd93d", "#6bcb77", "#4d96ff", "#ff922b", "#845ef7", "#f06595"]


@dataclass
class PianoRollAction:
    """A single undoable action."""

    description: str
    track_index: int = 0
    undo_data: dict[str, Any] = field(default_factory=dict)
    redo_data: dict[str, Any] = field(default_factory=dict)


class PianoRollModel(QObject):
    """The data model backing the piano roll editor."""

    active_track_changed = Signal(int)

    tracks: list[Track]
    transport: Transport
    grid: float
    _undo_stack: list[PianoRollAction]
    _redo_stack: list[PianoRollAction]
    _max_undo: int
    _active_track_index: int

    def __init__(self, transport: Transport) -> None:
        super().__init__()
        self.tracks = [Track(name="Track 1", color=TRACK_COLORS[0])]
        self.transport = transport
        self.grid = 0.25
        self._undo_stack = []
        self._redo_stack = []
        self._max_undo = 200
        self._active_track_index = 0

    def add_track(self, track: Track | None = None) -> Track:
        if track is None:
            idx = len(self.tracks)
            track = Track(
                name=f"Track {idx + 1}",
                color=TRACK_COLORS[idx % len(TRACK_COLORS)],
            )
        self.tracks.append(track)
        return track

    def remove_track(self, index: int) -> None:
        if 0 <= index < len(self.tracks) and len(self.tracks) > 1:
            del self.tracks[index]
            if self._active_track_index >= len(self.tracks):
                self._active_track_index = len(self.tracks) - 1

    @property
    def active_track_index(self) -> int:
        return self._active_track_index

    def set_active_track(self, index: int) -> None:
        if 0 <= index < len(self.tracks) and index != self._active_track_index:
            self._active_track_index = index
            self.active_track_changed.emit(index)

    @property
    def current_track(self) -> Track:
        return self.tracks[self._active_track_index]

    @property
    def current_pattern(self) -> Pattern:
        track = self.current_track
        if not track.patterns:
            track.patterns.append(Pattern(length_beats=16.0))
        return track.patterns[0]

    def insert_note(self, pitch: int, start: float, duration: float, velocity: int = 100) -> Note:
        note = Note(pitch=pitch, velocity=velocity, start_time=start, duration=duration)
        self.current_pattern.notes.append(note)
        self._push_undo(
            PianoRollAction(
                description="Insert note",
                track_index=self._active_track_index,
                undo_data={"action": "delete_note", "index": len(self.current_pattern.notes) - 1},
                redo_data={"action": "insert_note", "note": note},
            )
        )
        return note

    def delete_note(self, index: int) -> Note | None:
        pattern = self.current_pattern
        if 0 <= index < len(pattern.notes):
            removed = pattern.notes.pop(index)
            self._push_undo(
                PianoRollAction(
                    track_index=self._active_track_index,
                    description="Delete note",
                    undo_data={"action": "insert_note", "note": removed, "index": index},
                    redo_data={"action": "delete_note", "index": index},
                )
            )
            return removed
        return None

    def delete_notes_in_range(self, pitch_min: int, pitch_max: int, beat_start: float, beat_end: float) -> int:
        pattern = self.current_pattern
        to_remove: list[int] = []
        for i, note in enumerate(pattern.notes):
            if pitch_min <= note.pitch <= pitch_max and note.start_time < beat_end and note.end_time() > beat_start:
                to_remove.append(i)
        removed_notes: list[Note] = []
        for i in reversed(to_remove):
            removed_notes.append(pattern.notes.pop(i))
        if removed_notes:
            self._push_undo(
                PianoRollAction(
                    track_index=self._active_track_index,
                    description="Delete notes in range",
                    undo_data={"action": "insert_notes", "notes": removed_notes},
                    redo_data={
                        "action": "delete_range",
                        "pitch_min": pitch_min,
                        "pitch_max": pitch_max,
                        "start": beat_start,
                        "end": beat_end,
                    },
                )
            )
        return len(removed_notes)

    def move_note(self, index: int, new_start: float, new_pitch: int) -> bool:
        pattern = self.current_pattern
        if 0 <= index < len(pattern.notes):
            note = pattern.notes[index]
            old_start = note.start_time
            old_pitch = note.pitch
            note.start_time = max(0.0, new_start)
            note.pitch = max(0, min(127, new_pitch))
            self._push_undo(
                PianoRollAction(
                    track_index=self._active_track_index,
                    description="Move note",
                    undo_data={"action": "move_note", "index": index, "start": old_start, "pitch": old_pitch},
                    redo_data={"action": "move_note", "index": index, "start": new_start, "pitch": new_pitch},
                )
            )
            return True
        return False

    def resize_note(self, index: int, new_duration: float) -> bool:
        pattern = self.current_pattern
        if 0 <= index < len(pattern.notes):
            note = pattern.notes[index]
            old_duration = note.duration
            note.duration = max(0.0625, new_duration)
            self._push_undo(
                PianoRollAction(
                    track_index=self._active_track_index,
                    description="Resize note",
                    undo_data={"action": "resize_note", "index": index, "duration": old_duration},
                    redo_data={"action": "resize_note", "index": index, "duration": new_duration},
                )
            )
            return True
        return False

    def set_grid(self, grid: float) -> None:
        self.grid = max(0.0625, grid)

    def quantize(self, grid: float | None = None) -> int:
        g = grid if grid is not None else self.grid
        pattern = self.current_pattern
        old_starts: list[tuple[int, float]] = []
        for i, note in enumerate(pattern.notes):
            old_starts.append((i, note.start_time))
            note.start_time = round(note.start_time / g) * g
            note.duration = round(note.duration / g) * max(g, g)
        self._push_undo(
            PianoRollAction(
                track_index=self._active_track_index,
                description="Quantize",
                undo_data={"action": "restore_starts", "starts": old_starts},
                redo_data={"action": "quantize", "grid": g},
            )
        )
        return len(pattern.notes)

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        action = self._undo_stack.pop()
        self._apply_undo(action)
        self._redo_stack.append(action)
        logger.debug(f"Undo: {action.description}")
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        action = self._redo_stack.pop()
        self._apply_redo(action)
        self._undo_stack.append(action)
        logger.debug(f"Redo: {action.description}")
        return True

    def _push_undo(self, action: PianoRollAction) -> None:
        self._undo_stack.append(action)
        self._redo_stack.clear()
        while len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)

    def _apply_undo(self, action: PianoRollAction) -> None:
        self._active_track_index = action.track_index
        data = action.undo_data
        act = data.get("action", "")
        pattern = self.current_pattern
        if act == "delete_note" and "index" in data:
            idx: int = data["index"]
            if 0 <= idx < len(pattern.notes):
                pattern.notes.pop(idx)
        elif act == "insert_note" and "note" in data:
            note_data: Note = data["note"]
            idx = data.get("index", len(pattern.notes))
            pattern.notes.insert(min(idx, len(pattern.notes)), note_data)
        elif act == "insert_notes" and "notes" in data:
            for note_data in data["notes"]:
                pattern.notes.append(note_data)
        elif act == "move_note":
            idx = data["index"]
            if 0 <= idx < len(pattern.notes):
                pattern.notes[idx].start_time = data["start"]
                pattern.notes[idx].pitch = data["pitch"]
        elif act == "resize_note":
            idx = data["index"]
            if 0 <= idx < len(pattern.notes):
                pattern.notes[idx].duration = data["duration"]
        elif act == "restore_starts" and "starts" in data:
            for idx, start in data["starts"]:
                if 0 <= idx < len(pattern.notes):
                    pattern.notes[idx].start_time = start

    def _apply_redo(self, action: PianoRollAction) -> None:
        self._active_track_index = action.track_index
        data = action.redo_data
        act = data.get("action", "")
        pattern = self.current_pattern
        if act == "delete_note" and "index" in data:
            idx: int = data["index"]
            if 0 <= idx < len(pattern.notes):
                pattern.notes.pop(idx)
        elif act == "insert_note" and "note" in data:
            note_data: Note = data["note"]
            idx = data.get("index", len(pattern.notes))
            pattern.notes.insert(min(idx, len(pattern.notes)), note_data)
        elif act == "delete_range":
            self.delete_notes_in_range(data["pitch_min"], data["pitch_max"], data["start"], data["end"])
        elif act == "move_note":
            idx = data["index"]
            if 0 <= idx < len(pattern.notes):
                pattern.notes[idx].start_time = data["start"]
                pattern.notes[idx].pitch = data["pitch"]
        elif act == "resize_note":
            idx = data["index"]
            if 0 <= idx < len(pattern.notes):
                pattern.notes[idx].duration = data["duration"]
        elif act == "quantize":
            self.quantize(data.get("grid"))

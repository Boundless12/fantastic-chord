"""KeyboardWidget: Virtual piano keyboard with click-to-play and MIDI visualization."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from .theme import COLOR_ACTIVE_KEY, COLOR_BLACK_KEY, COLOR_WHITE_KEY

WHITE_KEY_PATTERN = [0, 2, 4, 5, 7, 9, 11]
BLACK_KEY_PATTERN = [1, 3, None, 6, 8, 10, None]
BLACK_KEY_OFFSET = [-0.35, 0.35, 0, -0.35, 0.35, -0.35, 0]


class KeyboardWidget(QWidget):
    """Virtual piano keyboard with 37 keys (C3-C6)."""

    note_on = Signal(int, int)
    note_off = Signal(int)

    NUM_KEYS: int = 37
    START_NOTE: int = 48

    _active_notes: set[int]
    _white_key_width: float
    _black_key_width: float
    _white_key_height: float
    _black_key_height: float

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active_notes = set()
        self.setMinimumHeight(120)
        self.setMinimumWidth(600)
        self.setMouseTracking(True)

    def highlight_note(self, note: int) -> None:
        self._active_notes.add(note)
        self.update()

    def unhighlight_note(self, note: int) -> None:
        self._active_notes.discard(note)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        w = self.width()
        h = self.height()
        num_white = sum(1 for i in range(self.NUM_KEYS) if self.START_NOTE + i not in BLACK_KEY_PATTERN)

        self._white_key_width = w / max(num_white, 1)
        self._white_key_height = h
        self._black_key_width = self._white_key_width * 0.6
        self._black_key_height = h * 0.6

        # Draw white keys
        white_idx = 0
        white_key_map: dict[int, float] = {}
        for i in range(self.NUM_KEYS):
            note = self.START_NOTE + i
            pitch = note % 12
            if pitch in WHITE_KEY_PATTERN:
                x = white_idx * self._white_key_width
                white_key_map[i] = x
                is_active = note in self._active_notes
                color = QColor(COLOR_ACTIVE_KEY) if is_active else QColor(COLOR_WHITE_KEY)
                painter.fillRect(
                    int(x) + 1,
                    0,
                    int(self._white_key_width) - 2,
                    int(h) - 1,
                    color,
                )
                painter.setPen(QColor("#cccccc"))
                painter.drawRect(int(x), 0, int(self._white_key_width), int(h) - 1)
                white_idx += 1

        # Draw black keys
        white_idx = 0
        for i in range(self.NUM_KEYS):
            note = self.START_NOTE + i
            pitch = note % 12
            if pitch in WHITE_KEY_PATTERN:
                white_idx += 1
            elif pitch in BLACK_KEY_PATTERN:
                wp_idx = BLACK_KEY_PATTERN.index(pitch)
                offset_ratio = BLACK_KEY_OFFSET[wp_idx]
                x = (white_idx - 0.5) * self._white_key_width + offset_ratio * self._white_key_width * 0.5
                is_active = note in self._active_notes
                color = QColor(COLOR_ACTIVE_KEY) if is_active else QColor(COLOR_BLACK_KEY)
                painter.fillRect(
                    int(x),
                    0,
                    int(self._black_key_width),
                    int(self._black_key_height),
                    color,
                )
                painter.setPen(QColor("#111111"))
                painter.drawRect(int(x), 0, int(self._black_key_width), int(self._black_key_height))

    def _get_note_at(self, x: float, y: float) -> int:
        w = self.width()
        num_white = sum(1 for i in range(self.NUM_KEYS) if self.START_NOTE + i not in BLACK_KEY_PATTERN)
        wkw = w / max(num_white, 1)
        bkw = wkw * 0.6
        bkh = self.height() * 0.6

        white_idx = 0
        for i in range(self.NUM_KEYS):
            note = self.START_NOTE + i
            pitch = note % 12
            if pitch in BLACK_KEY_PATTERN:
                wp_idx = BLACK_KEY_PATTERN.index(pitch)
                offset_ratio = BLACK_KEY_OFFSET[wp_idx]
                bx = (white_idx - 0.5) * wkw + offset_ratio * wkw * 0.5
                if bx <= x <= bx + bkw and y <= bkh:
                    return note
            if pitch in WHITE_KEY_PATTERN:
                white_idx += 1

        white_idx = 0
        for i in range(self.NUM_KEYS):
            note = self.START_NOTE + i
            pitch = note % 12
            if pitch in WHITE_KEY_PATTERN:
                wx = white_idx * wkw
                if wx <= x <= wx + wkw:
                    return note
                white_idx += 1
        return -1

    def mousePressEvent(self, event: QMouseEvent) -> None:
        note = self._get_note_at(event.position().x(), event.position().y())
        if note >= 0:
            self.highlight_note(note)
            self.note_on.emit(note, 100)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            note = self._get_note_at(event.position().x(), event.position().y())
            if note >= 0 and note not in self._active_notes:
                self.highlight_note(note)
                self.note_on.emit(note, 100)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        for note in list(self._active_notes):
            self.unhighlight_note(note)
            self.note_off.emit(note)

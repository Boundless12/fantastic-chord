"""PianoRollWidget: QGraphicsView-based piano roll editor."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QWidget,
)

from ..sequencer.pattern import Note
from ..sequencer.piano_roll import PianoRollModel
from .theme import COLOR_GRID, COLOR_GRID_STRONG, COLOR_SURFACE, COLOR_TEXT_DIM, TRACK_COLORS

NOTE_MIN = 0
NOTE_MAX = 127
DEFAULT_NOTE_DURATION = 0.5


class NoteGraphicsItem(QGraphicsRectItem):
    """A single note rectangle on the piano roll."""

    note_index: int
    note: Note
    track_color: QColor

    def __init__(self, note: Note, index: int, color: QColor) -> None:
        super().__init__()
        self.note = note
        self.note_index = index
        self.track_color = color
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)

    def paint(self, painter: QPainter, option: object, widget: object | None = None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self.track_color.darker(120), 1))
        if self.isSelected():
            painter.setBrush(QBrush(self.track_color.lighter(150)))
        else:
            painter.setBrush(QBrush(self.track_color))
        painter.drawRoundedRect(self.rect(), 2, 2)


class PianoRollWidget(QGraphicsView):
    """Piano roll editor using QGraphicsView/QGraphicsScene."""

    note_selected = Signal(int)
    note_changed = Signal()

    _model: PianoRollModel
    _scene: QGraphicsScene
    _pixels_per_beat: float
    _note_height: float
    _key_width: float
    _track_color: QColor
    _dragging: bool
    _drag_mode: str
    _drag_note_index: int
    _drag_start_pos: tuple[float, float]
    _resize_right_edge: bool

    def __init__(self, model: PianoRollModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self._pixels_per_beat = 40.0
        self._note_height = 12.0
        self._key_width = 50.0
        self._track_color = QColor(TRACK_COLORS[0])
        self._dragging = False
        self._drag_mode = ""
        self._drag_note_index = -1
        self._drag_start_pos = (0.0, 0.0)
        self._resize_right_edge = True

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._setup_scene()

    def _setup_scene(self) -> None:
        self._scene.setBackgroundBrush(QBrush(QColor(COLOR_SURFACE)))
        total_beats = 32.0
        total_pitch_height = (NOTE_MAX - NOTE_MIN + 1) * self._note_height
        scene_width = self._key_width + total_beats * self._pixels_per_beat
        self._scene.setSceneRect(0, 0, scene_width, total_pitch_height)

    def _beat_to_x(self, beat: float) -> float:
        return self._key_width + beat * self._pixels_per_beat

    def _pitch_to_y(self, pitch: int) -> float:
        return (NOTE_MAX - pitch) * self._note_height

    def _x_to_beat(self, x: float) -> float:
        return max(0.0, (x - self._key_width) / self._pixels_per_beat)

    def _y_to_pitch(self, y: float) -> int:
        return max(NOTE_MIN, min(NOTE_MAX, NOTE_MAX - int(y / self._note_height)))

    def drawBackground(self, painter: QPainter, rect: QRectF | QRect) -> None:
        """Draw grid lines and piano key labels."""
        painter.fillRect(rect, QColor(COLOR_SURFACE))

        # Piano key background
        key_rect = QRectF(0, rect.top(), self._key_width, rect.height())
        painter.fillRect(key_rect, QColor("#252538"))

        # Horizontal pitch lines and key labels
        for pitch in range(NOTE_MIN, NOTE_MAX + 1):
            y = self._pitch_to_y(pitch)
            if y + self._note_height < rect.top() or y > rect.bottom():
                continue

            is_black = pitch % 12 in (1, 3, 6, 8, 10)
            if is_black:
                painter.fillRect(QRectF(0, y, self._key_width, self._note_height), QColor("#2a2a3c"))
            else:
                painter.fillRect(QRectF(0, y, self._key_width, self._note_height), QColor("#2e2e40"))

            # Grid line
            pen = QPen(QColor(COLOR_GRID), 1, Qt.PenStyle.DotLine)
            if pitch % 12 == 0:
                pen = QPen(QColor(COLOR_GRID_STRONG), 1)
            painter.setPen(pen)
            painter.drawLine(QPointF(self._key_width, y), QPointF(rect.right(), y))

            # Note name on C notes
            if pitch % 12 == 0:
                octave = pitch // 12 - 1
                name = f"C{octave}"
                painter.setPen(QColor(COLOR_TEXT_DIM))
                painter.drawText(
                    QRectF(2, y, self._key_width - 4, self._note_height), Qt.AlignmentFlag.AlignVCenter, name
                )

        # Vertical beat lines
        total_beats = 32.0
        for beat in range(int(total_beats * 4) + 1):
            b = beat / 4.0
            x = self._beat_to_x(b)
            if x < rect.left() or x > rect.right():
                continue
            if beat % 16 == 0:
                pen = QPen(QColor(COLOR_GRID_STRONG), 1)
            elif beat % 4 == 0:
                pen = QPen(QColor(COLOR_GRID), 1)
            else:
                pen = QPen(QColor("#2a2a3a"), 1, Qt.PenStyle.DotLine)
            painter.setPen(pen)
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))

    def refresh_notes(self) -> None:
        """Redraw all note rectangles from the model."""
        for item in self._scene.items():
            if isinstance(item, NoteGraphicsItem):
                self._scene.removeItem(item)

        pattern = self._model.current_pattern
        for i, note in enumerate(pattern.notes):
            if note.pitch < NOTE_MIN or note.pitch > NOTE_MAX:
                continue
            x = self._beat_to_x(note.start_time)
            y = self._pitch_to_y(note.pitch)
            w = note.duration * self._pixels_per_beat
            h = self._note_height

            item = NoteGraphicsItem(note, i, self._track_color)
            item.setRect(QRectF(x, y, max(w, 4), h))
            item.setZValue(10)
            self._scene.addItem(item)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        scene_pos = self.mapToScene(event.pos())
        x, y = scene_pos.x(), scene_pos.y()

        beat = self._x_to_beat(x)
        pitch = self._y_to_pitch(y)

        # Check if clicking on a note's right edge for resize
        items = self._scene.items(scene_pos)
        note_item = None
        for item in items:
            if isinstance(item, NoteGraphicsItem):
                note_item = item
                break

        if note_item and event.button() == Qt.MouseButton.LeftButton:
            rect = note_item.rect()
            right_edge_x = rect.right()
            if abs(x - right_edge_x) < 6:
                self._drag_mode = "resize"
                self._drag_note_index = note_item.note_index
                self._drag_start_pos = (x, y)
                self._resize_right_edge = True
                self.setCursor(Qt.CursorShape.SizeHorCursor)
                return

            self._drag_mode = "move"
            self._drag_note_index = note_item.note_index
            self._drag_start_pos = (beat, pitch)
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            return

        if event.button() == Qt.MouseButton.RightButton and note_item:
            idx = note_item.note_index
            self._model.delete_note(idx)
            self.refresh_notes()
            self.note_changed.emit()
            return

        if event.button() == Qt.MouseButton.LeftButton and not note_item:
            quantized_beat = round(beat / self._model.grid) * self._model.grid
            self._model.insert_note(pitch, quantized_beat, DEFAULT_NOTE_DURATION)
            self.refresh_notes()
            self.note_changed.emit()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        scene_pos = self.mapToScene(event.pos())
        x, y = scene_pos.x(), scene_pos.y()

        if self._drag_mode == "move":
            beat = self._x_to_beat(x)
            pitch = self._y_to_pitch(y)
            quantized_beat = round(beat / self._model.grid) * self._model.grid
            self._model.move_note(self._drag_note_index, quantized_beat, pitch)
            self.refresh_notes()
            self.note_changed.emit()
            return

        if self._drag_mode == "resize":
            beat = self._x_to_beat(x)
            note = self._model.current_pattern.notes[self._drag_note_index]
            new_duration = max(0.0625, beat - note.start_time)
            quantized = round(new_duration / self._model.grid) * self._model.grid
            self._model.resize_note(self._drag_note_index, max(0.0625, quantized))
            self.refresh_notes()
            self.note_changed.emit()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = False
        self._drag_mode = ""
        self._drag_note_index = -1
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            selected = self._scene.selectedItems()
            for item in selected:
                if isinstance(item, NoteGraphicsItem):
                    self._model.delete_note(item.note_index)
            self.refresh_notes()
            self.note_changed.emit()
            return

        if event.key() == Qt.Key.Key_Z and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self._model.undo():
                self.refresh_notes()
                self.note_changed.emit()
            return

        if event.key() == Qt.Key.Key_Y and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self._model.redo():
                self.refresh_notes()
                self.note_changed.emit()
            return

        super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()

        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.1 if delta > 0 else 0.9
            self._pixels_per_beat = max(10.0, min(200.0, self._pixels_per_beat * factor))
            self._update_scene_rect()
            self.refresh_notes()
        else:
            super().wheelEvent(event)

    def _update_scene_rect(self) -> None:
        total_beats = 32.0
        total_height = (NOTE_MAX - NOTE_MIN + 1) * self._note_height
        self._scene.setSceneRect(0, 0, self._key_width + total_beats * self._pixels_per_beat, total_height)

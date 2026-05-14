"""KnobWidget: Custom rotary knob control with drag-to-rotate interaction."""

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import QWidget

from .theme import COLOR_KNOB_ARC, COLOR_KNOB_TRACK, COLOR_TEXT, COLOR_TEXT_DIM, FONT_SIZE_SM


class KnobWidget(QWidget):
    """Circular rotary knob styled like a hardware synth.

    Interaction:
      - Vertical drag: change value
      - Scroll wheel: change value
      - Ctrl+scroll: fine adjust
      - Shift+drag: fine adjust
      - Double-click: reset to default
      - Right-click: context menu (CC learn)
    """

    value_changed = Signal(float)
    context_menu_requested = Signal()

    _value: float
    _default_value: float
    _min: float
    _max: float
    _display_name: str
    _value_format: str
    _bipolar: bool
    _step: float
    _dragging: bool
    _drag_start_y: float
    _drag_start_value: float
    _display_map: list[str] | None

    def __init__(
        self,
        display_name: str = "",
        default_value: float = 0.5,
        value_format: str = "percent",
        bipolar: bool = False,
        step: float = 0.0,
        parent: QWidget | None = None,
        display_map: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._value = default_value
        self._default_value = default_value
        self._min = -1.0 if bipolar else 0.0
        self._max = 1.0
        self._display_name = display_name
        self._value_format = value_format
        self._bipolar = bipolar
        self._step = step
        self._dragging = False
        self._drag_start_y = 0
        self._drag_start_value = default_value
        self._display_map = display_map
        self.setFixedSize(56, 72)
        self.setMouseTracking(True)

    def value(self) -> float:
        return self._value

    def set_value(self, v: float, emit: bool = True) -> None:
        if self._step > 0.0:
            v = round(v / self._step) * self._step
        self._value = max(self._min, min(self._max, v))
        self.update()
        if emit:
            self.value_changed.emit(self._value)

    def set_default(self, v: float) -> None:
        self._default_value = v

    def set_range(self, min_val: float, max_val: float) -> None:
        self._min = min_val
        self._max = max_val
        self._value = max(min_val, min(max_val, self._value))
        self.update()

    def _format_value(self) -> str:
        if self._display_map is not None:
            n = len(self._display_map)
            idx = max(
                0,
                min(
                    n - 1,
                    (
                        int(self._value * (n - 1) + 0.5)
                        if self._bipolar is False and self._min >= 0.0
                        else int((self._value - self._min) / (self._max - self._min) * (n - 1) + 0.5)
                    ),
                ),
            )
            return self._display_map[idx]

        if self._value_format == "percent":
            return f"{int(self._value * 100)}"
        elif self._value_format == "hz":
            v = 20.0 * (1000.0**self._value)
            if v >= 1000:
                return f"{v / 1000:.1f}k"
            return f"{v:.0f}"
        elif self._value_format == "ms":
            v = 1.0 + self._value * 999.0
            if v >= 1000:
                return f"{v / 1000:.1f}s"
            return f"{v:.0f}ms"
        elif self._value_format == "db":
            v = self._value * 24.0 - 12.0
            return f"{v:.1f}"
        elif self._value_format == "semitones":
            v = (self._value - 0.5) * 48.0
            return f"{v:+.0f}"
        elif self._value_format == "cents":
            return f"{self._value * 100 - 50:.0f}c"
        elif self._value_format == "ratio":
            return f"{self._value:.2f}"
        elif self._value_format == "int":
            return f"{int(self._value)}"
        return f"{self._value:.2f}"

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        cx, cy = w / 2, 28
        radius = 20

        track_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        pen = QPen(QColor(COLOR_KNOB_TRACK), 3)
        painter.setPen(pen)
        painter.drawArc(track_rect, 135 * 16, 270 * 16)

        if self._bipolar:
            span = int(270 * (self._value - self._min) / (self._max - self._min))
        else:
            span = int(270 * self._value)
        pen = QPen(QColor(COLOR_KNOB_ARC), 3)
        painter.setPen(pen)
        painter.drawArc(track_rect, 135 * 16, -span * 16)

        painter.setPen(QColor(COLOR_TEXT))
        font = painter.font()
        font.setPointSize(FONT_SIZE_SM - 2)
        painter.setFont(font)
        painter.drawText(QRectF(cx - 18, cy - 8, 36, 16), Qt.AlignmentFlag.AlignCenter, self._format_value())

        painter.setPen(QColor(COLOR_TEXT_DIM))
        font = painter.font()
        font.setPointSize(FONT_SIZE_SM - 4)
        painter.setFont(font)
        painter.drawText(QRectF(0, 52, w, 14), Qt.AlignmentFlag.AlignCenter, self._display_name)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self.context_menu_requested.emit()
        elif event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_y = event.globalPosition().y()
            self._drag_start_value = self._value
            self.setCursor(Qt.CursorShape.SizeVerCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            delta = self._drag_start_y - event.globalPosition().y()
            sensitivity = 0.005
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                sensitivity *= 0.1
            new_value = self._drag_start_value + delta * sensitivity
            self.set_value(new_value)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_value(self._default_value)

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y() / 120.0
        step = self._step if self._step > 0.0 else 0.01
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            step *= 0.1
        self.set_value(self._value + delta * step)

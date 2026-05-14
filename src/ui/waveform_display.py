"""WaveformDisplay: Real-time oscilloscope visualization."""

from collections import deque

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPaintEvent
from PySide6.QtWidgets import QWidget

from .theme import COLOR_ACCENT, COLOR_SURFACE_LIGHT


class WaveformDisplay(QWidget):
    """Real-time oscilloscope display of audio output waveform."""

    _buffer: deque[float]
    _timer: QTimer
    _max_samples: int

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._max_samples = 512
        self._buffer = deque([0.0] * self._max_samples, maxlen=self._max_samples)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(33)
        self.setMinimumHeight(80)

    def push_samples(self, data: "list[float] | None" = None) -> None:
        if data is None:
            data = [0.0] * 32
        for sample in data:
            self._buffer.append(sample)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(COLOR_SURFACE_LIGHT))

        w = self.width()
        h = self.height()
        mid = h // 2
        amp = h // 2 - 4

        if len(self._buffer) < 2:
            return

        path = QPainterPath()
        buf_list = list(self._buffer)
        step = max(len(buf_list) / w, 1.0)

        path.moveTo(0, mid)
        for i in range(w):
            idx = int(i * step)
            if idx < len(buf_list):
                y = mid - buf_list[idx] * amp
                path.lineTo(i, y)

        painter.setPen(QColor(COLOR_ACCENT))
        painter.drawPath(path)

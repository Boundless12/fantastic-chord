"""DrumVoice: A renderable drum sound voice for the audio callback.
from __future__ import annotations


Holds a pre-rendered mono buffer and reads from it during callback rendering.
Trigger and render_block are called on the same audio callback thread,
so no locking is needed.
"""

import numpy as np
import numpy.typing as npt

from .constants import SAMPLE_RATE

MAX_DRUM_DURATION = 4.0


class DrumVoice:
    """A single drum voice that plays back a pre-rendered buffer."""

    active: bool
    pan_left: float
    pan_right: float
    _buffer: npt.NDArray[np.float32]
    _position: int
    _length: int

    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        max_samples = int(sample_rate * MAX_DRUM_DURATION)
        self._buffer = np.zeros(max_samples, dtype=np.float32)
        self._position = 0
        self._length = 0
        self.active = False
        self.pan_left = 0.707
        self.pan_right = 0.707

    def trigger(self, buffer: npt.NDArray[np.float32], pan: float = 0.0) -> None:
        """Load a pre-rendered buffer and start playback.

        Args:
            buffer: Mono float32 drum sound buffer.
            pan: Stereo pan position -1.0 (left) to 1.0 (right).
        """
        length = min(len(buffer), len(self._buffer))
        self._buffer[:length] = buffer[:length]
        self._length = length
        self._position = 0
        self.active = True

        # Equal-power pan law
        pan_norm = max(-1.0, min(1.0, pan))
        angle = (pan_norm + 1.0) * np.pi / 4.0
        self.pan_left = float(np.cos(angle))
        self.pan_right = float(np.sin(angle))

    def render_block(self, frames: int) -> npt.NDArray[np.float32]:
        """Render one block of mono audio from the stored buffer.

        Returns shape (frames,) float32. Returns zeros if not active.
        Must be called from the audio callback thread only.
        """
        if not self.active:
            return np.zeros(frames, dtype=np.float32)

        remaining = self._length - self._position
        to_read = min(frames, remaining)

        out = np.zeros(frames, dtype=np.float32)
        out[:to_read] = self._buffer[self._position : self._position + to_read]
        self._position += to_read

        if self._position >= self._length:
            self.active = False

        return out

    def is_finished(self) -> bool:
        return not self.active

    def reset(self) -> None:
        self.active = False
        self._position = 0

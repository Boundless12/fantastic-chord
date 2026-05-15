"""Biquad filter implementation using RBJ Audio EQ Cookbook formulas.
from __future__ import annotations


Direct Form I topology with coefficients recomputed on parameter change.
"""

import numpy as np
import numpy.typing as npt

from .constants import PI_2


class BiquadFilter:
    """Biquadratic filter with selectable type and dynamic coefficient updates.

    Supported types: lowpass, highpass, bandpass, notch, peaking, lowshelf, highshelf.
    """

    filter_type: str
    cutoff: float
    resonance: float
    env_amount: float
    sample_rate: int

    _b0: float
    _b1: float
    _b2: float
    _a1: float
    _a2: float

    _x1: float
    _x2: float
    _y1: float
    _y2: float

    def __init__(
        self, sample_rate: int, filter_type: str = "lowpass", cutoff: float = 20000.0, resonance: float = 0.0
    ) -> None:
        self.sample_rate = sample_rate
        self.filter_type = filter_type
        self.cutoff = cutoff
        self.resonance = resonance
        self.env_amount = 0.0
        self._b0 = 1.0
        self._b1 = 0.0
        self._b2 = 0.0
        self._a1 = 0.0
        self._a2 = 0.0
        self._x1 = 0.0
        self._x2 = 0.0
        self._y1 = 0.0
        self._y2 = 0.0
        self.recompute_coeffs()

    def set_type(self, name: str) -> None:
        self.filter_type = name
        self.recompute_coeffs()

    def set_cutoff(self, hz: float) -> None:
        self.cutoff = max(20.0, min(20000.0, hz))
        self.recompute_coeffs()

    def set_resonance(self, q: float) -> None:
        self.resonance = max(0.0, min(1.0, q))
        self.recompute_coeffs()

    def recompute_coeffs(self) -> None:
        """Recompute biquad coefficients using RBJ cookbook formulas."""
        w0 = PI_2 * self.cutoff / self.sample_rate
        cos_w0 = np.cos(w0)
        sin_w0 = np.sin(w0)

        q = 0.5 + self.resonance * 9.5
        alpha = sin_w0 / (2.0 * q)
        a0_inv: float

        ftype = self.filter_type

        if ftype == "lowpass":
            b0 = (1.0 - cos_w0) / 2.0
            b1 = 1.0 - cos_w0
            b2 = (1.0 - cos_w0) / 2.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cos_w0
            a2 = 1.0 - alpha
        elif ftype == "highpass":
            b0 = (1.0 + cos_w0) / 2.0
            b1 = -(1.0 + cos_w0)
            b2 = (1.0 + cos_w0) / 2.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cos_w0
            a2 = 1.0 - alpha
        elif ftype == "bandpass":
            b0 = sin_w0 / 2.0
            b1 = 0.0
            b2 = -sin_w0 / 2.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cos_w0
            a2 = 1.0 - alpha
        elif ftype == "notch":
            b0 = 1.0
            b1 = -2.0 * cos_w0
            b2 = 1.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cos_w0
            a2 = 1.0 - alpha
        elif ftype == "peaking":
            a = sin_w0 / (2.0 * max(q, 0.01))
            b0 = 1.0 + alpha * (1.0 + self.resonance)
            b1 = -2.0 * cos_w0
            b2 = 1.0 - alpha * (1.0 + self.resonance)
            a0 = 1.0 + alpha / (1.0 + self.resonance)
            a1 = -2.0 * cos_w0
            a2 = 1.0 - alpha / (1.0 + self.resonance)
        elif ftype == "lowshelf":
            a = 10.0 ** (self.resonance * 12.0 / 40.0)
            b0 = a * ((a + 1.0) - (a - 1.0) * cos_w0 + 2.0 * np.sqrt(a) * alpha)
            b1 = 2.0 * a * ((a - 1.0) - (a + 1.0) * cos_w0)
            b2 = a * ((a + 1.0) - (a - 1.0) * cos_w0 - 2.0 * np.sqrt(a) * alpha)
            a0 = (a + 1.0) + (a - 1.0) * cos_w0 + 2.0 * np.sqrt(a) * alpha
            a1 = -2.0 * ((a - 1.0) + (a + 1.0) * cos_w0)
            a2 = (a + 1.0) + (a - 1.0) * cos_w0 - 2.0 * np.sqrt(a) * alpha
        elif ftype == "highshelf":
            a = 10.0 ** (self.resonance * 12.0 / 40.0)
            b0 = a * ((a + 1.0) + (a - 1.0) * cos_w0 + 2.0 * np.sqrt(a) * alpha)
            b1 = -2.0 * a * ((a - 1.0) + (a + 1.0) * cos_w0)
            b2 = a * ((a + 1.0) + (a - 1.0) * cos_w0 - 2.0 * np.sqrt(a) * alpha)
            a0 = (a + 1.0) - (a - 1.0) * cos_w0 + 2.0 * np.sqrt(a) * alpha
            a1 = 2.0 * ((a - 1.0) - (a + 1.0) * cos_w0)
            a2 = (a + 1.0) - (a - 1.0) * cos_w0 - 2.0 * np.sqrt(a) * alpha
        else:
            b0, b1, b2, a0, a1, a2 = 1.0, 0.0, 0.0, 1.0, 0.0, 0.0

        a0_inv = 1.0 / a0
        self._b0 = b0 * a0_inv
        self._b1 = b1 * a0_inv
        self._b2 = b2 * a0_inv
        self._a1 = a1 * a0_inv
        self._a2 = a2 * a0_inv

    def reset(self) -> None:
        self._x1 = 0.0
        self._x2 = 0.0
        self._y1 = 0.0
        self._y2 = 0.0

    def process_sample(self, x: float) -> float:
        y = self._b0 * x + self._b1 * self._x1 + self._b2 * self._x2 - self._a1 * self._y1 - self._a2 * self._y2
        self._x2 = self._x1
        self._x1 = x
        self._y2 = self._y1
        self._y1 = y
        return y

    def process(self, x: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        """Process an audio block. Returns same-shape float32 array."""
        out = np.empty_like(x)
        for i in range(len(x)):
            out[i] = self.process_sample(float(x[i]))
        return out


class StateVariableFilter(BiquadFilter):
    """State-variable filter with smoother cutoff modulation.

    Uses Chamberlin topology for better behavior under rapid parameter changes.
    """

    _low: float
    _band: float
    _high: float

    def __init__(
        self, sample_rate: int, filter_type: str = "lowpass", cutoff: float = 20000.0, resonance: float = 0.0
    ) -> None:
        super().__init__(sample_rate, filter_type, cutoff, resonance)
        self._low = 0.0
        self._band = 0.0
        self._high = 0.0

    def reset(self) -> None:
        super().reset()
        self._low = 0.0
        self._band = 0.0
        self._high = 0.0

    def recompute_coeffs(self) -> None:
        w0 = PI_2 * self.cutoff / self.sample_rate
        self._f = 2.0 * np.sin(w0 / 2.0)
        self._q = 0.5 + self.resonance * 9.5

    def process_sample(self, x: float) -> float:
        q_inv = 1.0 / self._q
        f = min(self._f, 2.0)
        self._high = x - self._low - q_inv * self._band
        self._band += f * self._high
        self._low += f * self._band

        if self.filter_type == "lowpass":
            return self._low
        elif self.filter_type == "highpass":
            return self._high
        elif self.filter_type == "bandpass":
            return self._band
        elif self.filter_type == "notch":
            return self._high + self._low
        else:
            return self._low

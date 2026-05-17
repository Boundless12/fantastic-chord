"""Compressor: Simple RMS compressor with threshold, ratio, attack, and release."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


class Compressor:
    """RMS-based stereo compressor with soft knee."""

    threshold: float
    ratio: float
    attack: float
    release: float
    makeup_gain: float

    _sample_rate: int
    _env: float
    _attack_coeff: float
    _release_coeff: float

    def __init__(
        self,
        sample_rate: int = 44100,
        threshold: float = 0.5,
        ratio: float = 2.0,
        attack: float = 0.01,
        release: float = 0.1,
        makeup_gain: float = 0.0,
    ) -> None:
        self._sample_rate = sample_rate
        self.threshold = threshold
        self.ratio = ratio
        self.attack = attack
        self.release = release
        self.makeup_gain = makeup_gain
        self._env = 0.0
        self._attack_coeff = np.exp(-1.0 / max(attack * sample_rate, 1))
        self._release_coeff = np.exp(-1.0 / max(release * sample_rate, 1))

    def _update_coeffs(self) -> None:
        self._attack_coeff = np.exp(-1.0 / max(self.attack * self._sample_rate, 1))
        self._release_coeff = np.exp(-1.0 / max(self.release * self._sample_rate, 1))

    def process(self, x: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        """Apply compression to stereo audio. Returns same-shape array."""
        if x.ndim == 1:
            x = np.column_stack([x, x])

        rms = np.sqrt(np.mean(x**2, axis=-1) + 1e-9)
        peak = float(np.max(rms))

        # Envelope follower (attack/release)
        target = peak
        if target > self._env:
            self._env = self._env * self._attack_coeff + target * (1.0 - self._attack_coeff)
        else:
            self._env = self._env * self._release_coeff + target * (1.0 - self._release_coeff)

        if self._env > self.threshold:
            # Soft knee: smooth transition into compression
            over = self._env - self.threshold
            gain_reduction = over * (1.0 - 1.0 / self.ratio) / (self._env + 1e-9)
            gain = 1.0 - gain_reduction
        else:
            gain = 1.0

        return np.asarray(x * gain * (1.0 + self.makeup_gain), dtype=np.float32)


class EQ:
    """3-band parametric equalizer using BiquadFilter stages (stereo-safe)."""

    low_gain: float
    mid_gain: float
    high_gain: float
    mid_freq: float
    mid_q: float
    _enabled: bool

    _sample_rate: int
    _dirty: bool

    def __init__(self, sample_rate: int = 44100) -> None:
        self._sample_rate = sample_rate
        self.low_gain = 0.0
        self.mid_gain = 0.0
        self.high_gain = 0.0
        self.mid_freq = 1000.0
        self.mid_q = 0.7
        self._enabled = True
        self._dirty = True

        from .filter import BiquadFilter

        self._low_L = BiquadFilter(sample_rate, "lowshelf", 200.0, 0.0)
        self._low_R = BiquadFilter(sample_rate, "lowshelf", 200.0, 0.0)
        self._mid_L = BiquadFilter(sample_rate, "peaking", self.mid_freq, self.mid_q)
        self._mid_R = BiquadFilter(sample_rate, "peaking", self.mid_freq, self.mid_q)
        self._high_L = BiquadFilter(sample_rate, "highshelf", 8000.0, 0.0)
        self._high_R = BiquadFilter(sample_rate, "highshelf", 8000.0, 0.0)

    def set_params(self, low: float | None = None, mid: float | None = None, high: float | None = None) -> None:
        if low is not None and low != self.low_gain:
            self.low_gain = low
            self._dirty = True
        if mid is not None and mid != self.mid_gain:
            self.mid_gain = mid
            self._dirty = True
        if high is not None and high != self.high_gain:
            self.high_gain = high
            self._dirty = True

    def _update_filters(self) -> None:
        if not self._dirty:
            return
        self._dirty = False
        from .filter import BiquadFilter

        for ch_filt in (self._low_L, self._low_R):
            if isinstance(ch_filt, BiquadFilter):
                ch_filt.cutoff = 200.0
                ch_filt.resonance = max(0.0, min(1.0, (self.low_gain + 15.0) / 30.0))
                ch_filt.recompute_coeffs()

        for ch_filt in (self._mid_L, self._mid_R):
            if isinstance(ch_filt, BiquadFilter):
                ch_filt.cutoff = self.mid_freq
                ch_filt.resonance = max(0.0, min(1.0, abs(self.mid_gain) / 15.0))
                ch_filt.recompute_coeffs()

        for ch_filt in (self._high_L, self._high_R):
            if isinstance(ch_filt, BiquadFilter):
                ch_filt.cutoff = 8000.0
                ch_filt.resonance = max(0.0, min(1.0, (self.high_gain + 15.0) / 30.0))
                ch_filt.recompute_coeffs()

    def process(self, x: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        if not self._enabled:
            return x
        if self.low_gain == 0.0 and self.mid_gain == 0.0 and self.high_gain == 0.0:
            return x

        self._update_filters()
        from .filter import BiquadFilter

        if x.ndim == 2:
            left = x[:, 0].copy()
            right = x[:, 1].copy()
            for flt_l, flt_r in ((self._low_L, self._low_R), (self._mid_L, self._mid_R), (self._high_L, self._high_R)):
                if isinstance(flt_l, BiquadFilter):
                    left = flt_l.process(left)
                    right = flt_r.process(right)
            return np.column_stack([left, right])
        else:
            out = x
            for flt in (self._low_L, self._mid_L, self._high_L):
                if isinstance(flt, BiquadFilter):
                    out = flt.process(out)
            return out

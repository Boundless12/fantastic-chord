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
    """3-band parametric equalizer using BiquadFilter stages."""

    low_gain: float
    mid_gain: float
    high_gain: float
    mid_freq: float
    mid_q: float
    _enabled: bool

    _sample_rate: int
    _low_shelf: object  # BiquadFilter
    _mid_peak: object  # BiquadFilter
    _high_shelf: object  # BiquadFilter

    def __init__(self, sample_rate: int = 44100) -> None:
        self._sample_rate = sample_rate
        self.low_gain = 0.0
        self.mid_gain = 0.0
        self.high_gain = 0.0
        self.mid_freq = 1000.0
        self.mid_q = 0.7
        self._enabled = True

        from .filter import BiquadFilter

        self._low_shelf = BiquadFilter(sample_rate, "lowshelf", 200.0, 0.0)
        self._mid_peak = BiquadFilter(sample_rate, "peaking", self.mid_freq, self.mid_q)
        self._high_shelf = BiquadFilter(sample_rate, "highshelf", 8000.0, 0.0)

    def _update_filters(self) -> None:
        from .filter import BiquadFilter

        low = self._low_shelf
        if isinstance(low, BiquadFilter):
            low.cutoff = 200.0
            low.resonance = max(0.0, min(1.0, (self.low_gain + 15.0) / 30.0))
            low.recompute_coeffs()

        mid = self._mid_peak
        if isinstance(mid, BiquadFilter):
            mid.cutoff = self.mid_freq
            mid.resonance = max(0.0, min(1.0, abs(self.mid_gain) / 15.0))
            mid.recompute_coeffs()

        high = self._high_shelf
        if isinstance(high, BiquadFilter):
            high.cutoff = 8000.0
            high.resonance = max(0.0, min(1.0, (self.high_gain + 15.0) / 30.0))
            high.recompute_coeffs()

    def process(self, x: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        if not self._enabled:
            return x
        self._update_filters()
        out = x
        for filt in (self._low_shelf, self._mid_peak, self._high_shelf):
            from .filter import BiquadFilter

            if isinstance(filt, BiquadFilter):
                out = filt.process(out)
        return out

"""Oscillator types for the synthesizer engine.
from __future__ import annotations


All oscillators generate mono float32 numpy arrays in range [-1.0, 1.0].
"""

import numpy as np
import numpy.typing as npt

from .constants import PI_2


class Oscillator:
    """Base oscillator with phase accumulator and frequency control."""

    phase: float
    frequency: float
    sample_rate: int
    waveform: str

    def __init__(self, sample_rate: int, waveform: str = "sine") -> None:
        self.phase = 0.0
        self.frequency = 440.0
        self.sample_rate = sample_rate
        self.waveform = waveform

    def set_frequency(self, hz: float) -> None:
        self.frequency = max(0.0, hz)

    def set_waveform(self, name: str) -> None:
        self.waveform = name

    def reset_phase(self) -> None:
        self.phase = 0.0

    def _advance_phase(self, frames: int, fm_input: npt.NDArray[np.float32] | None = None) -> npt.NDArray[np.float32]:
        """Compute phase array for one block. Returns shape (frames,) float32 in range [0, 2π)."""
        phase_increment = PI_2 * self.frequency / self.sample_rate
        phase_start = self.phase
        phase_end = phase_start + phase_increment * frames

        if fm_input is not None:
            phase_end = phase_start + phase_increment * np.sum(1.0 + fm_input)

        phases = np.linspace(phase_start, np.float32(phase_end), frames, endpoint=False, dtype=np.float32)
        self.phase = float(phase_end % PI_2)
        return np.asarray(phases, dtype=np.float32)

    def generate(self, frames: int, fm_input: npt.NDArray[np.float32] | None = None) -> npt.NDArray[np.float32]:
        phases = self._advance_phase(frames, fm_input)
        if self.waveform == "sine":
            return np.asarray(np.sin(phases), dtype=np.float32)
        elif self.waveform == "saw":
            result = 2.0 * (phases / PI_2 - np.floor(0.5 + phases / PI_2))
            return np.asarray(result, dtype=np.float32)
        elif self.waveform == "square":
            return np.asarray(np.where(np.sin(phases) >= 0.0, np.float32(1.0), np.float32(-1.0)), dtype=np.float32)
        elif self.waveform == "triangle":
            result = 2.0 * np.abs(2.0 * (phases / PI_2 - np.floor(0.5 + phases / PI_2))) - 1.0
            return np.asarray(result, dtype=np.float32)
        elif self.waveform == "noise":
            return np.asarray(np.random.uniform(-1.0, 1.0, frames), dtype=np.float32)
        else:
            return np.asarray(np.sin(phases), dtype=np.float32)


class SineOscillator(Oscillator):
    def __init__(self, sample_rate: int) -> None:
        super().__init__(sample_rate, "sine")


class SawOscillator(Oscillator):
    def __init__(self, sample_rate: int) -> None:
        super().__init__(sample_rate, "saw")


class SquareOscillator(Oscillator):
    def __init__(self, sample_rate: int, pulse_width: float = 0.5) -> None:
        super().__init__(sample_rate, "square")
        self.pulse_width = pulse_width

    def generate(self, frames: int, fm_input: npt.NDArray[np.float32] | None = None) -> npt.NDArray[np.float32]:
        phases = self._advance_phase(frames, fm_input)
        return np.where((phases % PI_2) < PI_2 * self.pulse_width, np.float32(1.0), np.float32(-1.0))


class TriangleOscillator(Oscillator):
    def __init__(self, sample_rate: int) -> None:
        super().__init__(sample_rate, "triangle")


class NoiseOscillator(Oscillator):
    def __init__(self, sample_rate: int) -> None:
        super().__init__(sample_rate, "noise")

    def generate(self, frames: int, fm_input: npt.NDArray[np.float32] | None = None) -> npt.NDArray[np.float32]:
        return np.random.uniform(-1.0, 1.0, frames).astype(np.float32)


class WavetableOscillator(Oscillator):
    """Oscillator that reads from a pre-loaded wavetable with linear interpolation."""

    wavetable: npt.NDArray[np.float32]
    table_size: int

    def __init__(self, sample_rate: int, wavetable: npt.NDArray[np.float32]) -> None:
        super().__init__(sample_rate, "wavetable")
        self.wavetable = wavetable.astype(np.float32)
        self.table_size = len(wavetable)

    def generate(self, frames: int, fm_input: npt.NDArray[np.float32] | None = None) -> npt.NDArray[np.float32]:
        phases = self._advance_phase(frames, fm_input)
        indices = (phases / PI_2) * self.table_size
        idx_floor = np.floor(indices).astype(np.int32) % self.table_size
        idx_ceil = (idx_floor + 1) % self.table_size
        frac = (indices - np.floor(indices)).astype(np.float32)
        result = self.wavetable[idx_floor] * (1.0 - frac) + self.wavetable[idx_ceil] * frac
        return np.asarray(result, dtype=np.float32)


class FMOscillator:
    """Two-operator FM oscillator: carrier modulated by a modulator."""

    carrier: Oscillator
    modulator: Oscillator
    modulation_index: float
    modulator_ratio: float

    def __init__(self, sample_rate: int, modulation_index: float = 1.0, modulator_ratio: float = 1.0) -> None:
        self.carrier = SineOscillator(sample_rate)
        self.modulator = SineOscillator(sample_rate)
        self.modulation_index = modulation_index
        self.modulator_ratio = modulator_ratio

    def set_frequency(self, hz: float) -> None:
        self.carrier.frequency = max(0.0, hz)
        self.modulator.frequency = max(0.0, hz * self.modulator_ratio)

    def generate(self, frames: int) -> npt.NDArray[np.float32]:
        mod_out = self.modulator.generate(frames)
        fm_input = mod_out * self.modulation_index
        return self.carrier.generate(frames, fm_input)

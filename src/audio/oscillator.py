"""Oscillator types for the synthesizer engine.


All oscillators generate mono float32 numpy arrays in range [-1.0, 1.0].
"""

from __future__ import annotations

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
    """Serum-style multi-table wavetable oscillator with position crossfade and warp modes."""

    tables: list[npt.NDArray[np.float32]]
    table_size: int
    wavetable_position: float
    warp_mode: str
    warp_amount: float

    def __init__(self, sample_rate: int, tables: list[npt.NDArray[np.float32]]) -> None:
        super().__init__(sample_rate, "wavetable")
        self.tables = [t.astype(np.float32) for t in tables]
        self.table_size = len(tables[0]) if tables else 2048
        self.wavetable_position = 0.0
        self.warp_mode = "none"
        self.warp_amount = 0.0

    def set_position(self, pos: float) -> None:
        self.wavetable_position = max(0.0, min(1.0, pos))

    def set_warp(self, mode: str, amount: float) -> None:
        self.warp_mode = mode
        self.warp_amount = max(0.0, min(1.0, amount))

    def _read_tables(self, phases: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        num_tables = len(self.tables)
        if num_tables == 0:
            return np.sin(phases).astype(np.float32)
        if num_tables == 1:
            indices = (phases / PI_2) * self.table_size
            idx_floor = np.floor(indices).astype(np.int32) % self.table_size
            idx_ceil = (idx_floor + 1) % self.table_size
            frac = (indices - np.floor(indices)).astype(np.float32)
            return np.asarray(
                self.tables[0][idx_floor] * (1.0 - frac) + self.tables[0][idx_ceil] * frac, dtype=np.float32
            )

        float_idx = self.wavetable_position * (num_tables - 1)
        idx_a = int(float_idx)
        idx_b = min(idx_a + 1, num_tables - 1)
        mix = float_idx - idx_a

        indices = (phases / PI_2) * self.table_size
        idx_floor = np.floor(indices).astype(np.int32) % self.table_size
        idx_ceil = (idx_floor + 1) % self.table_size
        frac = (indices - np.floor(indices)).astype(np.float32)

        tbl_a = self.tables[idx_a]
        tbl_b = self.tables[idx_b]
        samples_a = tbl_a[idx_floor] * (1.0 - frac) + tbl_a[idx_ceil] * frac
        samples_b = tbl_b[idx_floor] * (1.0 - frac) + tbl_b[idx_ceil] * frac
        return np.asarray(samples_a * (1.0 - mix) + samples_b * mix, dtype=np.float32)

    def _apply_warp(self, samples: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        if self.warp_mode == "none" or self.warp_amount <= 0.001:
            return samples
        amt = self.warp_amount
        if self.warp_mode == "bend_p":
            gain = 1.0 + amt * 8.0
            return np.asarray(np.tanh(samples * gain) / max(np.tanh(np.float32(gain)), 0.1), dtype=np.float32)
        elif self.warp_mode == "bend_n":
            gain = 1.0 + amt * 8.0
            neg = np.where(samples < 0, np.tanh(samples * gain), samples)
            return np.asarray(neg / max(np.tanh(np.float32(gain)), 0.1), dtype=np.float32)
        elif self.warp_mode == "mirror":
            threshold = 1.0 - amt * 0.9
            return np.where(samples > threshold, 2.0 * threshold - samples, samples)
        elif self.warp_mode == "fold":
            gain = 1.0 + amt * 4.0
            folded = np.abs(samples * gain + (1.0 - amt)) % (4.0 * amt + 0.1) - 2.0 * amt
            return np.asarray(np.clip(folded, -1.0, 1.0), dtype=np.float32)
        elif self.warp_mode == "pwm":
            duty = 0.1 + amt * 0.8
            return np.where(samples > (duty * 2.0 - 1.0), np.float32(1.0), np.float32(-1.0))
        elif self.warp_mode == "crush":
            steps = max(2, int(16 - amt * 14))
            return np.asarray(np.round(samples * steps) / steps, dtype=np.float32)
        return samples

    def generate(self, frames: int, fm_input: npt.NDArray[np.float32] | None = None) -> npt.NDArray[np.float32]:
        phases = self._advance_phase(frames, fm_input)
        samples = self._read_tables(phases)
        return self._apply_warp(samples)


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

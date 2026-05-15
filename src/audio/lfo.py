"""LFO - Low Frequency Oscillator for parameter modulation."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


class LFO:
    """Low-frequency oscillator for parameter modulation.

    Targets: osc_pitch, osc_mix, filter_cutoff, filter_resonance, amp_level, pan, osc1_pw, osc2_pw.
    """

    waveform: str
    rate: float
    depth: float
    phase: float
    fade_in: float
    target: str
    key_sync: bool
    one_shot: bool
    rate_sync: bool
    rate_sync_subdiv: str

    _sample_rate: int
    _age_samples: int
    _fade_samples: int

    def __init__(self, sample_rate: int) -> None:
        self._sample_rate = sample_rate
        self.waveform = "sine"
        self.rate = 1.0
        self.depth = 0.0
        self.phase = 0.0
        self.fade_in = 0.0
        self.target = "none"
        self.key_sync = True
        self.one_shot = False
        self.rate_sync = False
        self.rate_sync_subdiv = "1/4"
        self._age_samples = 0
        self._fade_samples = 0

    def reset(self) -> None:
        self.phase = 0.0
        self._age_samples = 0

    def set_rate(self, hz: float) -> None:
        self.rate = max(0.01, min(50.0, hz))

    def set_rate_sync(self, bpm: float, subdivision: str) -> None:
        beats_per_cycle: dict[str, float] = {
            "1/16": 0.25,
            "1/8": 0.5,
            "1/4": 1.0,
            "1/2": 2.0,
            "1": 4.0,
            "2": 8.0,
            "4": 16.0,
        }
        beat_duration = 60.0 / bpm
        cycle_beats = beats_per_cycle.get(subdivision, 1.0)
        self.rate = 1.0 / (beat_duration * cycle_beats)
        self.rate_sync_subdiv = subdivision

    def process(self, frames: int) -> npt.NDArray[np.float32]:
        out = np.zeros(frames, dtype=np.float32)

        if self.depth <= 0.0:
            return out

        phase_increment = 2.0 * np.pi * self.rate / self._sample_rate
        fade_gain = 1.0
        if self.fade_in > 0.0:
            fade_samples = int(self.fade_in * self._sample_rate)
            fade_gain = min(1.0, self._age_samples / max(1, fade_samples))

        for i in range(frames):
            if self.waveform == "sine":
                val = np.sin(self.phase)
            elif self.waveform == "triangle":
                val = (
                    2.0 * np.abs(2.0 * (self.phase / (2.0 * np.pi) - np.floor(0.5 + self.phase / (2.0 * np.pi)))) - 1.0
                )
            elif self.waveform == "square":
                val = 1.0 if np.sin(self.phase) >= 0.0 else -1.0
            elif self.waveform == "saw_up":
                val = 2.0 * (self.phase / (2.0 * np.pi) - np.floor(0.5 + self.phase / (2.0 * np.pi)))
            elif self.waveform == "saw_down":
                val = 1.0 - 2.0 * (self.phase / (2.0 * np.pi) - np.floor(self.phase / (2.0 * np.pi)))
            elif self.waveform == "sample_hold":
                if i == 0 or (self.phase + phase_increment) % (2.0 * np.pi) < self.phase % (2.0 * np.pi):
                    self._held = np.random.uniform(-1.0, 1.0)
                val = getattr(self, "_held", 0.0)
            elif self.waveform == "random":
                val = np.random.uniform(-1.0, 1.0)
            else:
                val = 0.0

            out[i] = np.float32(val * self.depth * fade_gain)
            self.phase += phase_increment
            if self.phase >= 2.0 * np.pi:
                self.phase -= 2.0 * np.pi
                if self.one_shot:
                    self.depth = 0.0
                    break

            self._age_samples += 1

        return np.asarray(out, dtype=np.float32)

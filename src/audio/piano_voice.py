"""PianoVoice: Clean additive-synthesis piano voice.

Uses 8 pure harmonic partials with gentle attack, natural decay,
and velocity-sensitive brightness for a warm, musical tone.
"""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt

from .constants import SAMPLE_RATE
from .oscillator import Oscillator


class PianoVoice:
    """Clean additive-synthesis piano with warm, musical tone."""

    NUM_PARTIALS: int = 8
    # Relative amplitudes for each harmonic (fundamental through 8th)
    _BASE_AMPS = np.array(
        [0.35, 0.26, 0.18, 0.11, 0.06, 0.03, 0.015, 0.008], dtype=np.float32
    )
    # Decay times in seconds — longer for lower partials
    _DECAY_TIMES = np.array(
        [2.5, 1.8, 1.2, 0.8, 0.5, 0.3, 0.18, 0.10], dtype=np.float32
    )
    ATTACK_TIME: float = 0.004  # 4ms soft attack to avoid clicks
    RELEASE_TIME: float = 0.20
    STEREO_WIDTH: float = 0.35

    active: bool
    note: int
    velocity: float
    pan_left: float
    pan_right: float

    _sample_rate: int
    _partial_oscs: list[Oscillator]
    _partial_amps: npt.NDArray[np.float32]
    _decay_factors: npt.NDArray[np.float32]
    _release_factor: float
    _attack_len: int
    _releasing: bool
    _sample_count: int

    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        self._sample_rate = sample_rate
        self._partial_oscs = [Oscillator(sample_rate, "sine") for _ in range(self.NUM_PARTIALS)]
        self._partial_amps = np.zeros(self.NUM_PARTIALS, dtype=np.float32)
        self._decay_factors = np.zeros(self.NUM_PARTIALS, dtype=np.float32)
        self._release_factor = math.exp(-1.0 / (self.RELEASE_TIME * sample_rate))
        self._attack_len = int(self.ATTACK_TIME * sample_rate)
        self._releasing = False
        self._sample_count = 0
        self.active = False
        self.note = 60
        self.velocity = 1.0
        self.pan_left = 0.707
        self.pan_right = 0.707

    def note_on(self, note: int, velocity: int) -> None:
        self.note = note
        self.velocity = max(0.1, min(1.0, velocity / 127.0))
        self.active = True
        self._releasing = False
        self._sample_count = 0

        f0 = 440.0 * math.pow(2.0, (note - 69) / 12.0)
        vel_norm = self.velocity

        for n in range(self.NUM_PARTIALS):
            k = n + 1
            # Pure harmonic series for clean, consonant chords
            freq = k * f0
            self._partial_oscs[n].set_frequency(float(freq))
            self._partial_oscs[n].reset_phase()

            # Velocity shapes brightness: softer = darker, harder = brighter
            vel_exp = 0.5 + 0.5 * k / self.NUM_PARTIALS
            amp = float(self._BASE_AMPS[n]) * (vel_norm ** vel_exp)
            self._partial_amps[n] = np.float32(amp)

            # Louder velocity = slightly longer sustain
            decay_time = float(self._DECAY_TIMES[n]) * (0.7 + 0.3 * vel_norm)
            self._decay_factors[n] = np.float32(math.exp(-1.0 / (decay_time * self._sample_rate)))

        # Stereo pan based on note position
        note_pos = (note - 60) / 48.0
        pan = note_pos * self.STEREO_WIDTH
        pan = max(-0.9, min(0.9, pan))
        self.pan_left = float(np.float32(math.sqrt(0.5 * (1.0 - pan))))
        self.pan_right = float(np.float32(math.sqrt(0.5 * (1.0 + pan))))

    def note_off(self) -> None:
        self._releasing = True

    def is_finished(self) -> bool:
        return not self.active

    def render_block(self, frames: int) -> npt.NDArray[np.float32]:
        if not self.active:
            return np.zeros(frames, dtype=np.float32)

        output = np.zeros(frames, dtype=np.float32)
        t = np.arange(frames, dtype=np.float32)

        # Soft attack envelope (linear ramp from 0 to 1 over ATTACK_TIME)
        attack_env = np.ones(frames, dtype=np.float32)
        start = self._sample_count
        if start < self._attack_len:
            attack_end = min(self._attack_len - start, frames)
            attack_env[:attack_end] = np.linspace(0.0, 1.0, attack_end, dtype=np.float32)

        for n in range(self.NUM_PARTIALS):
            amp = float(self._partial_amps[n])
            if amp < 1e-8:
                continue

            samples = self._partial_oscs[n].generate(frames)

            if self._releasing:
                env = amp * np.power(np.float32(self._release_factor), t)
            else:
                env = amp * np.power(np.float32(float(self._decay_factors[n])), t)

            env *= attack_env
            output += samples * env.astype(np.float32)

            # Update amplitude for next block
            if self._releasing:
                self._partial_amps[n] = np.float32(amp * (self._release_factor ** frames))
            else:
                self._partial_amps[n] = np.float32(amp * (float(self._decay_factors[n]) ** frames))

        self._sample_count += frames

        if float(np.max(self._partial_amps)) < 1e-8:
            self.active = False

        return output

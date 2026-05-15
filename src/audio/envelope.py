"""ADSR and DAHDSR envelope generators.
from __future__ import annotations


State machines that produce per-sample envelope amplitude values.
"""

from enum import Enum, auto

import numpy as np
import numpy.typing as npt


class EnvState(Enum):
    IDLE = auto()
    DELAY = auto()
    ATTACK = auto()
    HOLD = auto()
    DECAY = auto()
    SUSTAIN = auto()
    RELEASE = auto()


class ADSR:
    """Standard four-stage ADSR envelope with sample-accurate timing.

    Parameters:
        attack:  Rise time in seconds (0 to peak amplitude).
        decay:   Fall time in seconds (peak to sustain level).
        sustain: Sustain amplitude level (0.0 to 1.0).
        release: Fall time in seconds after note-off (sustain to 0).
    """

    attack: float
    decay: float
    sustain: float
    release: float

    _state: EnvState
    _value: float
    _sample_rate: int
    _sample_counter: int

    def __init__(
        self, sample_rate: int, attack: float = 0.01, decay: float = 0.2, sustain: float = 0.8, release: float = 0.3
    ) -> None:
        self._sample_rate = sample_rate
        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.release = release
        self._state = EnvState.IDLE
        self._value = 0.0
        self._sample_counter = 0

    def set_attack(self, seconds: float) -> None:
        self.attack = max(0.001, seconds)

    def set_decay(self, seconds: float) -> None:
        self.decay = max(0.001, seconds)

    def set_sustain(self, level: float) -> None:
        self.sustain = max(0.0, min(1.0, level))

    def set_release(self, seconds: float) -> None:
        self.release = max(0.001, seconds)

    def note_on(self) -> None:
        self._state = EnvState.ATTACK
        self._sample_counter = 0

    def note_off(self) -> None:
        self._state = EnvState.RELEASE
        self._sample_counter = 0

    def is_idle(self) -> bool:
        return self._state == EnvState.IDLE

    def is_finished(self) -> bool:
        return self._state == EnvState.IDLE and self._value <= 0.001

    def _attack_samples(self) -> int:
        return max(1, int(self.attack * self._sample_rate))

    def _decay_samples(self) -> int:
        return max(1, int(self.decay * self._sample_rate))

    def _release_samples(self) -> int:
        return max(1, int(self.release * self._sample_rate))

    def process(self) -> float:
        """Advance one sample and return current amplitude value."""
        if self._state == EnvState.IDLE:
            self._value = 0.0
        elif self._state == EnvState.ATTACK:
            self._sample_counter += 1
            total = self._attack_samples()
            if self._sample_counter >= total:
                self._state = EnvState.DECAY
                self._sample_counter = 0
                self._value = 1.0
            else:
                self._value = self._sample_counter / total
        elif self._state == EnvState.DECAY:
            self._sample_counter += 1
            total = self._decay_samples()
            if self._sample_counter >= total:
                self._state = EnvState.SUSTAIN
                self._value = self.sustain
            else:
                self._value = 1.0 - (1.0 - self.sustain) * (self._sample_counter / total)
        elif self._state == EnvState.SUSTAIN:
            self._value = self.sustain
        elif self._state == EnvState.RELEASE:
            self._sample_counter += 1
            total = self._release_samples()
            if self._sample_counter >= total:
                self._state = EnvState.IDLE
                self._value = 0.0
            else:
                self._value = self.sustain * (1.0 - self._sample_counter / total)
        return self._value

    def render_block(self, frames: int) -> npt.NDArray[np.float32]:
        out = np.empty(frames, dtype=np.float32)
        for i in range(frames):
            out[i] = self.process()
        return out


class DAHDSR(ADSR):
    """Six-stage envelope with Delay and Hold stages before Attack/Decay.

    Extra parameters:
        delay: Wait time before attack starts (seconds).
        hold:  Hold time at peak amplitude before decay (seconds).
    """

    delay: float
    hold: float

    def __init__(
        self,
        sample_rate: int,
        delay: float = 0.0,
        attack: float = 0.01,
        hold: float = 0.0,
        decay: float = 0.2,
        sustain: float = 0.8,
        release: float = 0.3,
    ) -> None:
        super().__init__(sample_rate, attack, decay, sustain, release)
        self.delay = delay
        self.hold = hold

    def note_on(self) -> None:
        if self.delay > 0.0:
            self._state = EnvState.DELAY
        else:
            self._state = EnvState.ATTACK
        self._sample_counter = 0

    def _delay_samples(self) -> int:
        return max(1, int(self.delay * self._sample_rate))

    def _hold_samples(self) -> int:
        return max(1, int(self.hold * self._sample_rate))

    def process(self) -> float:
        if self._state == EnvState.DELAY:
            self._sample_counter += 1
            self._value = 0.0
            if self._sample_counter >= self._delay_samples():
                self._state = EnvState.ATTACK
                self._sample_counter = 0
        elif self._state == EnvState.ATTACK:
            self._sample_counter += 1
            total = self._attack_samples()
            if self._sample_counter >= total:
                if self.hold > 0.0:
                    self._state = EnvState.HOLD
                    self._sample_counter = 0
                else:
                    self._state = EnvState.DECAY
                    self._sample_counter = 0
                self._value = 1.0
            else:
                self._value = self._sample_counter / total
        elif self._state == EnvState.HOLD:
            self._sample_counter += 1
            self._value = 1.0
            if self._sample_counter >= self._hold_samples():
                self._state = EnvState.DECAY
                self._sample_counter = 0
        else:
            return super().process()
        return self._value

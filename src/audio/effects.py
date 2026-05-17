"""Audio effects: Reverb, Delay, Chorus, Distortion, BitCrusher."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from .constants import SAMPLE_RATE


class Reverb:
    """Schroeder-Moorer reverb: 4 comb filters in parallel + 2 all-pass filters in series."""

    _comb_delays: tuple[int, int, int, int]
    _comb_buffers: list[npt.NDArray[np.float32]]
    _comb_positions: list[int]
    _ap_delays: tuple[int, int]
    _ap_buffers: list[npt.NDArray[np.float32]]
    _ap_positions: list[int]
    room_size: float
    damping: float
    wet_dry: float

    def __init__(self, room_size: float = 0.5, damping: float = 0.5, wet_dry: float = 0.12) -> None:
        self.room_size = room_size
        self.damping = damping
        self.wet_dry = wet_dry
        self._comb_delays = (1557, 1617, 1491, 1422)
        self._ap_delays = (225, 556)
        self._comb_buffers = [np.zeros(d, dtype=np.float32) for d in self._comb_delays]
        self._comb_positions = [0, 0, 0, 0]
        self._ap_buffers = [np.zeros(d, dtype=np.float32) for d in self._ap_delays]
        self._ap_positions = [0, 0]

    def process(self, x: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        if x.ndim == 1:
            x = np.column_stack([x, x])
        frames = x.shape[0]
        out = np.zeros((frames, 2), dtype=np.float32)
        idx = np.arange(frames, dtype=np.int32)

        for ch in range(2):
            ch_in = x[:, ch]
            comb_sum = np.zeros(frames, dtype=np.float32)
            for i in range(4):
                buf = self._comb_buffers[i]
                dlen = self._comb_delays[i]
                pos = self._comb_positions[i]
                rpos = (idx + pos) % dlen
                delayed = buf[rpos].copy()
                buf[rpos] = np.asarray(ch_in + self.room_size * 0.8 * delayed, dtype=np.float32)
                comb_sum += delayed
                self._comb_positions[i] = (pos + frames) % dlen

            ap_in = comb_sum * (1.0 - self.damping * 0.5) + ch_in * self.damping * 0.5
            for i in range(2):
                buf = self._ap_buffers[i]
                dlen = self._ap_delays[i]
                pos = self._ap_positions[i]
                rpos = (idx + pos) % dlen
                delayed = buf[rpos].copy()
                buf[rpos] = np.asarray(ap_in + delayed * 0.5, dtype=np.float32)
                ap_in = delayed - ap_in * 0.5
                self._ap_positions[i] = (pos + frames) % dlen
            out[:, ch] = ap_in

        return (1.0 - self.wet_dry) * x + self.wet_dry * out


class Delay:
    """Stereo ping-pong delay with feedback."""

    _buffer_left: npt.NDArray[np.float32]
    _buffer_right: npt.NDArray[np.float32]
    _pos_left: int
    _pos_right: int
    time_left: float
    time_right: float
    feedback: float
    wet_dry: float

    def __init__(
        self, time_left: float = 0.25, time_right: float = 0.375, feedback: float = 0.2, wet_dry: float = 0.12
    ) -> None:
        self.time_left = time_left
        self.time_right = time_right
        self.feedback = feedback
        self.wet_dry = wet_dry
        max_delay = int(SAMPLE_RATE * 2.0)
        self._buffer_left = np.zeros(max_delay, dtype=np.float32)
        self._buffer_right = np.zeros(max_delay, dtype=np.float32)
        self._pos_left = 0
        self._pos_right = 0
        self._delay_len_left = int(SAMPLE_RATE * time_left)
        self._delay_len_right = int(SAMPLE_RATE * time_right)

    def process(self, x: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        if x.ndim == 1:
            x = np.column_stack([x, x])
        frames = x.shape[0]
        buf_size = len(self._buffer_left)

        ridx_left = (np.arange(frames, dtype=np.int32) + self._pos_left - self._delay_len_left) % buf_size
        ridx_right = (np.arange(frames, dtype=np.int32) + self._pos_right - self._delay_len_right) % buf_size
        widx_left = (np.arange(frames, dtype=np.int32) + self._pos_left) % buf_size
        widx_right = (np.arange(frames, dtype=np.int32) + self._pos_right) % buf_size

        dl_left = self._buffer_left[ridx_left]
        dl_right = self._buffer_right[ridx_right]

        self._buffer_left[widx_left] = np.asarray(x[:, 0] + dl_right * self.feedback, dtype=np.float32)
        self._buffer_right[widx_right] = np.asarray(x[:, 1] + dl_left * self.feedback, dtype=np.float32)

        self._pos_left = (self._pos_left + frames) % buf_size
        self._pos_right = (self._pos_right + frames) % buf_size

        out = np.zeros((frames, 2), dtype=np.float32)
        out[:, 0] = (1.0 - self.wet_dry) * x[:, 0] + self.wet_dry * dl_left
        out[:, 1] = (1.0 - self.wet_dry) * x[:, 1] + self.wet_dry * dl_right
        return out


class Chorus:
    """Single modulated delay line with LFO."""

    rate: float
    depth: float
    wet_dry: float
    _buffer: npt.NDArray[np.float32]
    _lfo_phase: float
    _pos: int

    def __init__(self, rate: float = 0.5, depth: float = 0.01, wet_dry: float = 0.2) -> None:
        self.rate = rate
        self.depth = depth
        self.wet_dry = wet_dry
        self._buffer = np.zeros(int(SAMPLE_RATE * 0.05), dtype=np.float32)
        self._lfo_phase = 0.0
        self._pos = 0

    def process(self, x: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        if x.ndim == 1:
            x = np.column_stack([x, x])
        frames = x.shape[0]
        buf_size = len(self._buffer)

        lfo_center = np.sin(self._lfo_phase + np.pi * self.rate * frames / SAMPLE_RATE, dtype=np.float32)
        delay_samples = int(self.depth * SAMPLE_RATE * (1.0 + float(lfo_center)))
        delay_samples = max(1, min(delay_samples, buf_size - 1))

        idx = np.arange(frames, dtype=np.int32)
        widx = (idx + self._pos) % buf_size
        ridx = (widx - delay_samples) % buf_size

        delayed = self._buffer[ridx].copy()
        self._buffer[widx] = x[:, 1]

        out = np.zeros((frames, 2), dtype=np.float32)
        out[:, 0] = (1.0 - self.wet_dry) * x[:, 0] + self.wet_dry * delayed
        out[:, 1] = (1.0 - self.wet_dry) * x[:, 1] + self.wet_dry * delayed

        self._pos = (self._pos + frames) % buf_size
        self._lfo_phase += 2.0 * np.pi * self.rate * frames / SAMPLE_RATE
        if self._lfo_phase >= 2.0 * np.pi:
            self._lfo_phase -= 2.0 * np.pi

        return out


class Distortion:
    """Soft-clipping distortion via tanh with drive and tone controls."""

    drive: float
    tone: float

    def __init__(self, drive: float = 0.0, tone: float = 0.5) -> None:
        self.drive = drive
        self.tone = tone

    def process(self, x: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        gain = 1.0 + self.drive * 20.0
        result = np.tanh(x * gain)
        return np.asarray(result, dtype=np.float32)


class BitCrusher:
    """Sample rate reduction + bit depth reduction."""

    bit_depth: float
    rate_reduction: float

    _sample_counter: int
    _last_sample: npt.NDArray[np.float32]

    def __init__(self, bit_depth: float = 8.0, rate_reduction: float = 1.0) -> None:
        self.bit_depth = bit_depth
        self.rate_reduction = rate_reduction

    def process(self, x: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        if x.ndim == 1:
            x = np.column_stack([x, x])
        levels = np.float32(2.0**self.bit_depth)
        hold_samples = max(1, int(self.rate_reduction))

        # Bit crush: quantize
        crushed = np.round(x * levels) / levels

        # Sample-and-hold: take every hold_samples-th sample, then repeat
        n_frames = x.shape[0]
        sample_indices = np.arange(n_frames) // hold_samples * hold_samples
        np.clip(sample_indices, 0, n_frames - 1, out=sample_indices)
        out = crushed[sample_indices]

        return np.asarray(out, dtype=np.float32)

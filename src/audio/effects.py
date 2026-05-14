"""Audio effects: Reverb, Delay, Chorus, Distortion, BitCrusher."""

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

    def __init__(self, room_size: float = 0.5, damping: float = 0.5, wet_dry: float = 0.3) -> None:
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

        for ch in range(2):
            ch_in = x[:, ch]
            comb_sum = np.zeros(frames, dtype=np.float32)
            for i in range(4):
                buf = self._comb_buffers[i]
                pos = self._comb_positions[i]
                delay_len = self._comb_delays[i]
                for n in range(frames):
                    delayed = buf[pos]
                    buf[pos] = ch_in[n] + self.room_size * 0.8 * delayed
                    comb_sum[n] += delayed
                    pos = (pos + 1) % delay_len
                self._comb_positions[i] = pos

            ap_in = comb_sum * (1.0 - self.damping * 0.5) + ch_in * self.damping * 0.5
            for i in range(2):
                buf = self._ap_buffers[i]
                pos = self._ap_positions[i]
                delay_len = self._ap_delays[i]
                for n in range(frames):
                    delayed = buf[pos]
                    buf[pos] = ap_in[n] + delayed * 0.5
                    ap_in[n] = delayed - ap_in[n] * 0.5
                    pos = (pos + 1) % delay_len
                self._ap_positions[i] = pos
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
        self, time_left: float = 0.25, time_right: float = 0.375, feedback: float = 0.4, wet_dry: float = 0.3
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
        out = np.zeros((frames, 2), dtype=np.float32)
        buf_size = len(self._buffer_left)

        for n in range(frames):
            dl_left = self._buffer_left[(self._pos_left - self._delay_len_left) % buf_size]
            dl_right = self._buffer_right[(self._pos_right - self._delay_len_right) % buf_size]

            self._buffer_left[self._pos_left] = x[n, 0] + dl_right * self.feedback
            self._buffer_right[self._pos_right] = x[n, 1] + dl_left * self.feedback
            self._pos_left = (self._pos_left + 1) % buf_size
            self._pos_right = (self._pos_right + 1) % buf_size

            out[n, 0] = (1.0 - self.wet_dry) * x[n, 0] + self.wet_dry * dl_left
            out[n, 1] = (1.0 - self.wet_dry) * x[n, 1] + self.wet_dry * dl_right

        return out


class Chorus:
    """Single modulated delay line with LFO."""

    rate: float
    depth: float
    wet_dry: float
    _buffer: npt.NDArray[np.float32]
    _lfo_phase: float
    _pos: int

    def __init__(self, rate: float = 0.5, depth: float = 0.01, wet_dry: float = 0.5) -> None:
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
        out = np.zeros((frames, 2), dtype=np.float32)
        buf_size = len(self._buffer)

        for n in range(frames):
            lfo = np.sin(self._lfo_phase, dtype=np.float32)
            delay_samples = int(self.depth * SAMPLE_RATE * (1.0 + lfo))
            delay_samples = max(1, min(delay_samples, buf_size - 1))

            for ch in range(2):
                read_pos = (self._pos - delay_samples) % buf_size
                delayed = self._buffer[read_pos]
                self._buffer[self._pos] = x[n, ch]
                out[n, ch] = (1.0 - self.wet_dry) * x[n, ch] + self.wet_dry * delayed

            self._pos = (self._pos + 1) % buf_size
            self._lfo_phase += 2.0 * np.pi * self.rate / SAMPLE_RATE
            if self._lfo_phase >= 2.0 * np.pi:
                self._lfo_phase -= 2.0 * np.pi

        return out


class Distortion:
    """Soft-clipping distortion via tanh with drive and tone controls."""

    drive: float
    tone: float

    def __init__(self, drive: float = 0.5, tone: float = 0.5) -> None:
        self.drive = drive
        self.tone = tone

    def process(self, x: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        gain = 1.0 + self.drive * 20.0
        result = np.tanh(x * gain, dtype=np.float32)
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
        self._sample_counter = 0
        self._last_sample = np.zeros(2, dtype=np.float32)

    def process(self, x: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        if x.ndim == 1:
            x = np.column_stack([x, x])
        out = np.zeros_like(x)
        hold_samples = max(1, int(self.rate_reduction))

        for n in range(x.shape[0]):
            if self._sample_counter % hold_samples == 0:
                levels = 2.0**self.bit_depth
                self._last_sample = np.round(x[n] * levels) / levels
            out[n] = self._last_sample
            self._sample_counter += 1

        return np.asarray(out, dtype=np.float32)

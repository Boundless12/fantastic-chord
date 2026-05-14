"""Mixer and MixerChannel for audio mixing and effects routing."""

import numpy as np
import numpy.typing as npt

from .constants import CHANNELS


class MixerChannel:
    """Single mixer channel strip with volume, pan, mute, solo, and effects sends."""

    volume: float
    pan: float
    mute: bool
    solo: bool
    meter_level: float
    reverb_send: float
    delay_send: float
    chorus_send: float

    def __init__(self, volume: float = 0.8, pan: float = 0.0) -> None:
        self.volume = volume
        self.pan = pan
        self.mute = False
        self.solo = False
        self.meter_level = 0.0
        self.reverb_send = 0.0
        self.delay_send = 0.0
        self.chorus_send = 0.0

    def apply(self, block: npt.NDArray[np.float32], stereo_out: npt.NDArray[np.float32]) -> None:
        """Mix mono block into stereo output with pan and volume."""
        if self.mute:
            return
        vol = self.volume
        pan_left = np.float32(np.cos((self.pan + 1.0) * np.pi / 4.0))
        pan_right = np.float32(np.sin((self.pan + 1.0) * np.pi / 4.0))
        if block.ndim == 1:
            stereo_out[:, 0] += block * vol * pan_left
            stereo_out[:, 1] += block * vol * pan_right
        else:
            stereo_out[:, 0] += block[:, 0] * vol
            stereo_out[:, 1] += block[:, 1] * vol


class Mixer:
    """Stereo mix bus with channel strips and master controls."""

    channels: dict[int, MixerChannel]
    master_volume: float
    master_mute: bool
    _fx_bus_reverb: npt.NDArray[np.float32] | None
    _fx_bus_delay: npt.NDArray[np.float32] | None
    _fx_bus_chorus: npt.NDArray[np.float32] | None

    def __init__(self, num_channels: int = 16) -> None:
        self.channels = {i: MixerChannel() for i in range(num_channels)}
        self.master_volume = 1.0
        self.master_mute = False
        self._fx_bus_reverb = None
        self._fx_bus_delay = None
        self._fx_bus_chorus = None

    def get_channel(self, idx: int) -> MixerChannel:
        return self.channels[idx]

    def mix_stereo(self, blocks: dict[int, npt.NDArray[np.float32]], frames: int) -> npt.NDArray[np.float32]:
        """Mix multiple mono blocks into a stereo output buffer."""
        out = np.zeros((frames, CHANNELS), dtype=np.float32)
        if self.master_mute:
            return out

        for ch_idx, block in blocks.items():
            if ch_idx in self.channels:
                self.channels[ch_idx].apply(block, out)

        out *= self.master_volume
        return np.asarray(np.clip(out, -1.0, 1.0), dtype=np.float32)

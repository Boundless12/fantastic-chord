"""AudioEngine: Real-time audio engine with sounddevice callback.

Manages the synth voice pool, processes commands from the GUI thread,
and renders audio in a high-priority callback thread.
"""

from __future__ import annotations

import contextlib
import logging
import queue
import threading
from typing import Any

import numpy as np
import numpy.typing as npt
import sounddevice as sd

from .constants import BLOCK_SIZE, CHANNELS, MAX_SYNTH_VOICES, SAMPLE_RATE
from .effects import Chorus, Delay, Distortion, Reverb
from .patch import Patch
from .synth_voice import SynthVoice

logger = logging.getLogger(__name__)

VoiceCommand = tuple[str, ...]


class AudioEngine:
    """Real-time audio synthesis engine running on a sounddevice callback thread."""

    sample_rate: int
    block_size: int
    voices: list[SynthVoice]
    master_volume: float
    is_running: bool

    command_queue: queue.Queue[VoiceCommand]
    meter_queue: queue.Queue[tuple[float, float]]

    _output_stream: sd.OutputStream | None
    _stream_thread: threading.Thread | None
    _note_to_voice: dict[int, int]
    _voice_ages: list[int]

    # Master effects
    reverb: Reverb
    delay: Delay
    chorus: Chorus
    distortion: Distortion

    def __init__(self, sample_rate: int = SAMPLE_RATE, block_size: int = BLOCK_SIZE) -> None:
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.master_volume = 0.8
        self.is_running = False

        self.voices = [SynthVoice(sample_rate) for _ in range(MAX_SYNTH_VOICES)]
        self.command_queue = queue.Queue()
        self.meter_queue = queue.Queue()
        self._output_stream = None
        self._stream_thread = None
        self._note_to_voice = {}
        self._voice_ages = [0] * MAX_SYNTH_VOICES

        self.reverb = Reverb()
        self.delay = Delay()
        self.chorus = Chorus()
        self.distortion = Distortion()

    @staticmethod
    def list_devices() -> list[dict[str, Any]]:
        devices = sd.query_devices()
        result: list[dict[str, Any]] = []
        for i, dev in enumerate(devices):
            result.append({"index": i, "name": dev["name"], "channels": dev["max_output_channels"]})
        return result

    def start(self, device_name: str | None = None) -> None:
        if self.is_running:
            return

        try:
            device: int | str | None = None
            if device_name:
                devices = sd.query_devices()
                for i, dev in enumerate(devices):
                    if dev["name"] == device_name:
                        device = i
                        break

            self._output_stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                device=device,
                channels=CHANNELS,
                callback=self._audio_callback,
                dtype=np.float32,
            )
            self._output_stream.start()
            self.is_running = True
            logger.info(f"Audio engine started: {self.sample_rate}Hz, block={self.block_size}")
        except Exception as e:
            logger.error(f"Failed to start audio engine: {e}")
            raise

    def stop(self) -> None:
        if not self.is_running:
            return
        self.is_running = False
        if self._output_stream:
            self._output_stream.stop()
            self._output_stream.close()
            self._output_stream = None
        logger.info("Audio engine stopped")

    def note_on(self, note: int, velocity: int) -> None:
        self.command_queue.put(("note_on", str(note), str(velocity)))

    def note_off(self, note: int) -> None:
        self.command_queue.put(("note_off", str(note)))

    def set_param(self, param_path: str, value: float) -> None:
        self.command_queue.put(("param", param_path, str(value)))

    def load_patch(self, patch: Patch) -> None:
        self.command_queue.put(("patch_load", patch.name))

    def all_notes_off(self) -> None:
        self.command_queue.put(("all_notes_off",))

    def panic(self) -> None:
        self.command_queue.put(("panic",))

    def _allocate_voice(self, note: int) -> int | None:
        """Find a free voice or steal the oldest one."""
        # First: look for a free, finished voice
        for i, voice in enumerate(self.voices):
            if not voice.active and voice.is_finished():
                if note in self._note_to_voice:
                    del self._note_to_voice[note]
                self._note_to_voice[note] = i
                self._voice_ages[i] = 0
                return i

        # Second: steal the oldest active voice
        oldest_idx = 0
        oldest_age = -1
        for i, voice in enumerate(self.voices):
            if voice.active and self._voice_ages[i] > oldest_age:
                oldest_age = self._voice_ages[i]
                oldest_idx = i

        # Remove old note mapping
        for n, v in list(self._note_to_voice.items()):
            if v == oldest_idx:
                del self._note_to_voice[n]
                break

        self._note_to_voice[note] = oldest_idx
        self._voice_ages[oldest_idx] = 0
        return oldest_idx

    def _dispatch(self, cmd: VoiceCommand) -> None:
        cmd_type = cmd[0]

        if cmd_type == "note_on":
            note = int(cmd[1])
            velocity = int(cmd[2])
            # If note already playing, retrigger it
            if note in self._note_to_voice:
                existing = self._note_to_voice[note]
                self.voices[existing].note_off()
            v_idx = self._allocate_voice(note)
            if v_idx is not None:
                self.voices[v_idx].note_on(note, velocity)

        elif cmd_type == "note_off":
            note = int(cmd[1])
            if note in self._note_to_voice:
                v_idx = self._note_to_voice[note]
                self.voices[v_idx].note_off()
                del self._note_to_voice[note]

        elif cmd_type == "param":
            param_path = cmd[1]
            value = float(cmd[2])
            for voice in self.voices:
                voice.apply_param(param_path, value)

        elif cmd_type == "all_notes_off":
            for voice in self.voices:
                if voice.active:
                    voice.note_off()
            self._note_to_voice.clear()

        elif cmd_type == "panic":
            for voice in self.voices:
                voice.active = False
            self._note_to_voice.clear()

    def _audio_callback(self, outdata: npt.NDArray[np.float32], frames: int, time_info: Any, status: int) -> None:
        """Audio callback executed on sounddevice's high-priority thread.

        Must not allocate memory, hold locks, or create Python objects
        beyond simple tuples and floats.
        """
        # Drain command queue (non-blocking)
        while True:
            try:
                cmd = self.command_queue.get_nowait()
                self._dispatch(cmd)
            except queue.Empty:
                break

        # Render active voices
        mixed = np.zeros((frames, CHANNELS), dtype=np.float32)
        for i, voice in enumerate(self.voices):
            if voice.active:
                block = voice.render_block(frames)
                mixed[:, 0] += block * voice.pan_left
                mixed[:, 1] += block * voice.pan_right
                self._voice_ages[i] += 1
                if voice.is_finished():
                    voice.active = False

        # Master effects
        mixed = self.reverb.process(mixed)
        mixed = self.delay.process(mixed)
        mixed = self.chorus.process(mixed)
        mixed = self.distortion.process(mixed)

        # Master volume
        mixed *= self.master_volume

        # Compute peak levels
        peak_left = float(np.max(np.abs(mixed[:, 0])))
        peak_right = float(np.max(np.abs(mixed[:, 1])))
        with contextlib.suppress(queue.Full):
            self.meter_queue.put_nowait((peak_left, peak_right))

        outdata[:] = np.clip(mixed, -1.0, 1.0)

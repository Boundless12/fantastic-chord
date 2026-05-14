"""AudioEngine: Real-time audio engine with sounddevice callback.

Manages the synth voice pool and drum voice pool, processes commands
from the GUI thread, and renders audio in a high-priority callback thread.
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

from ..sequencer.drum_pattern import DrumPattern
from ..sequencer.drum_sequencer import DrumSequencer, TriggerEvent
from ..sequencer.transport import Transport
from .constants import BLOCK_SIZE, CHANNELS, MAX_DRUM_VOICES, MAX_SYNTH_VOICES, SAMPLE_RATE
from .drum_kit import DRUM_KIT_PRESETS, DrumKitPreset
from .drum_synth import DrumSynth
from .drum_voice import DrumVoice
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

    # Drum engine
    drum_voices: list[DrumVoice]
    drum_synth: DrumSynth
    drum_sequencer: DrumSequencer
    current_drum_kit: DrumKitPreset | None
    transport: Transport

    command_queue: queue.Queue[VoiceCommand]
    meter_queue: queue.Queue[tuple[float, float]]

    _output_stream: sd.OutputStream | None
    _stream_thread: threading.Thread | None
    _note_to_voice: dict[int, int]
    _voice_ages: list[int]
    _drum_voice_ages: list[int]

    # Master effects
    reverb: Reverb
    delay: Delay
    chorus: Chorus
    distortion: Distortion

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        block_size: int = BLOCK_SIZE,
        transport: Transport | None = None,
    ) -> None:
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

        # Drum engine init
        self.drum_voices = [DrumVoice(sample_rate) for _ in range(MAX_DRUM_VOICES)]
        self.drum_synth = DrumSynth(sample_rate)
        self.drum_sequencer = DrumSequencer(transport or Transport())
        self.current_drum_kit = DRUM_KIT_PRESETS.get("909 House")
        self.transport = self.drum_sequencer._transport
        self._drum_voice_ages = [0] * MAX_DRUM_VOICES

        self._current_patch: Patch | None = None

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

    # -- Synth voice commands --

    def note_on(self, note: int, velocity: int) -> None:
        self.command_queue.put(("note_on", str(note), str(velocity)))

    def note_off(self, note: int) -> None:
        self.command_queue.put(("note_off", str(note)))

    def set_param(self, param_path: str, value: float) -> None:
        self.command_queue.put(("param", param_path, str(value)))

    def load_patch(self, patch: Patch) -> None:
        self._current_patch = patch
        self.command_queue.put(("patch_load",))

    def all_notes_off(self) -> None:
        self.command_queue.put(("all_notes_off",))

    def panic(self) -> None:
        self.command_queue.put(("panic",))

    # -- Drum commands --

    def trigger_drum(self, drum_type: str, velocity: int, pan: float = 0.0) -> None:
        self.command_queue.put(("drum_trigger", drum_type, str(velocity), str(pan)))

    def load_drum_kit(self, kit_name: str) -> None:
        self.command_queue.put(("drum_load_kit", kit_name))

    def set_drum_pattern(self, pattern: DrumPattern) -> None:
        self.command_queue.put(("drum_set_pattern",))

    def _set_drum_pattern_direct(self, pattern: DrumPattern) -> None:
        """Directly set the pattern reference (called from dispatch)."""
        self.drum_sequencer.set_pattern(pattern)

    # -- Voice allocation --

    def _allocate_voice(self, note: int) -> int | None:
        """Find a free synth voice or steal the oldest one."""
        for i, voice in enumerate(self.voices):
            if not voice.active and voice.is_finished():
                if note in self._note_to_voice:
                    del self._note_to_voice[note]
                self._note_to_voice[note] = i
                self._voice_ages[i] = 0
                return i

        oldest_idx = 0
        oldest_age = -1
        for i, voice in enumerate(self.voices):
            if voice.active and self._voice_ages[i] > oldest_age:
                oldest_age = self._voice_ages[i]
                oldest_idx = i

        for n, v in list(self._note_to_voice.items()):
            if v == oldest_idx:
                del self._note_to_voice[n]
                break

        self._note_to_voice[note] = oldest_idx
        self._voice_ages[oldest_idx] = 0
        return oldest_idx

    def _allocate_drum_voice(self) -> int:
        """Find a free drum voice or steal the oldest one."""
        for i, voice in enumerate(self.drum_voices):
            if not voice.active:
                self._drum_voice_ages[i] = 0
                return i

        oldest_idx = 0
        oldest_age = -1
        for i in range(len(self.drum_voices)):
            if self._drum_voice_ages[i] > oldest_age:
                oldest_age = self._drum_voice_ages[i]
                oldest_idx = i

        self._drum_voice_ages[oldest_idx] = 0
        return oldest_idx

    # -- Command dispatch --

    def _dispatch(self, cmd: VoiceCommand) -> None:
        cmd_type = cmd[0]

        if cmd_type == "note_on":
            note = int(cmd[1])
            velocity = int(cmd[2])
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
            for dv in self.drum_voices:
                dv.reset()

        elif cmd_type == "panic":
            for voice in self.voices:
                voice.active = False
            self._note_to_voice.clear()
            for dv in self.drum_voices:
                dv.reset()

        elif cmd_type == "patch_load":
            if self._current_patch is not None:
                for voice in self.voices:
                    voice.load_patch(self._current_patch)

        elif cmd_type == "drum_trigger":
            drum_type = cmd[1]
            velocity = int(cmd[2])
            pan = float(cmd[3])
            kit = self.current_drum_kit
            if kit is not None:
                params = kit.get_params(drum_type)
                buffer = self.drum_synth.render(params, velocity / 127.0)
                v_idx = self._allocate_drum_voice()
                self.drum_voices[v_idx].trigger(buffer, pan)

        elif cmd_type == "drum_load_kit":
            kit_name = cmd[1]
            kit = DRUM_KIT_PRESETS.get(kit_name)
            if kit is not None:
                self.current_drum_kit = kit
                logger.info(f"Drum kit loaded: {kit_name}")
            else:
                logger.warning(f"Drum kit not found: {kit_name}")

        elif cmd_type == "drum_set_pattern":
            # Pattern is set externally via _set_drum_pattern_direct before enqueue
            pass

    def _trigger_drum_from_event(self, event: TriggerEvent) -> None:
        """Trigger a drum sound directly from a TriggerEvent (called in callback)."""
        kit = self.current_drum_kit
        if kit is not None:
            params = kit.get_params(event.drum_type)
            buffer = self.drum_synth.render(params, event.velocity)
            v_idx = self._allocate_drum_voice()
            self.drum_voices[v_idx].trigger(buffer, event.pan)

    # -- Audio callback --

    def _audio_callback(self, outdata: npt.NDArray[np.float32], frames: int, time_info: Any, status: int) -> None:
        """Audio callback executed on sounddevice's high-priority thread."""
        # Drain command queue (non-blocking)
        while True:
            try:
                cmd = self.command_queue.get_nowait()
                self._dispatch(cmd)
            except queue.Empty:
                break

        # Advance transport (audio clock source)
        if self.transport.is_playing:
            self.transport.advance(frames, self.sample_rate)

        # Process drum sequencer
        triggers = self.drum_sequencer.process()
        for event in triggers:
            self._trigger_drum_from_event(event)

        # Render active synth voices
        mixed = np.zeros((frames, CHANNELS), dtype=np.float32)
        for i, voice in enumerate(self.voices):
            if voice.active:
                block = voice.render_block(frames)
                mixed[:, 0] += block * voice.pan_left
                mixed[:, 1] += block * voice.pan_right
                self._voice_ages[i] += 1
                if voice.is_finished():
                    voice.active = False

        # Render active drum voices
        for i, dv in enumerate(self.drum_voices):
            if dv.active:
                block = dv.render_block(frames)
                mixed[:, 0] += block * dv.pan_left
                mixed[:, 1] += block * dv.pan_right
                self._drum_voice_ages[i] += 1
                if dv.is_finished():
                    dv.active = False

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

"""SynthVoice: Complete monophonic synthesizer voice signal chain.

Osc1+Osc2 → Mixer → Filter → Amp(ADSR) → Pan → Voice Output
With LFO modulation and effects sends.
"""

import numpy as np
import numpy.typing as npt

from .constants import SAMPLE_RATE
from .envelope import ADSR
from .filter import BiquadFilter
from .lfo import LFO
from .oscillator import NoiseOscillator, Oscillator
from .patch import Patch


class SynthVoice:
    """A single monophonic synthesizer voice with 2 oscillators, filter, and envelopes."""

    note: int
    velocity: float
    active: bool
    pan_left: float
    pan_right: float
    _sample_rate: int

    osc1: Oscillator
    osc2: Oscillator
    noise_osc: NoiseOscillator
    filter: BiquadFilter
    amp_env: ADSR
    filter_env: ADSR
    lfo1: LFO
    lfo2: LFO

    # Per-voice effects send levels
    reverb_send: float
    delay_send: float
    chorus_send: float
    distortion_drive: float

    # Portamento
    _target_frequency: float
    _current_frequency: float
    _portamento_time: float

    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        self._sample_rate = sample_rate
        self.note = 0
        self.velocity = 0.0
        self.active = False
        self.pan_left = 0.707
        self.pan_right = 0.707

        self.osc1 = Oscillator(sample_rate, "saw")
        self.osc2 = Oscillator(sample_rate, "sine")
        self.noise_osc = NoiseOscillator(sample_rate)
        self.filter = BiquadFilter(sample_rate)
        self.amp_env = ADSR(sample_rate)
        self.filter_env = ADSR(sample_rate)
        self.lfo1 = LFO(sample_rate)
        self.lfo2 = LFO(sample_rate)

        self.reverb_send = 0.0
        self.delay_send = 0.0
        self.chorus_send = 0.0
        self.distortion_drive = 0.0

        self._target_frequency = 440.0
        self._current_frequency = 440.0
        self._portamento_time = 0.0

    @staticmethod
    def _midi_to_freq(note: int) -> float:
        return float(440.0 * (2.0 ** ((note - 69) / 12.0)))

    def note_on(self, note: int, velocity: int) -> None:
        self.note = note
        self.velocity = velocity / 127.0
        self.active = True
        freq = self._midi_to_freq(note)

        if self._portamento_time > 0.0 and self._current_frequency > 0.0:
            self._target_frequency = freq
        else:
            self._current_frequency = freq
            self._target_frequency = freq

        self.osc1.set_frequency(self._current_frequency)
        self.osc2.set_frequency(self._current_frequency)
        if self.lfo1.key_sync:
            self.lfo1.reset()
        if self.lfo2.key_sync:
            self.lfo2.reset()
        self.amp_env.note_on()
        self.filter_env.note_on()

    def note_off(self) -> None:
        self.amp_env.note_off()
        self.filter_env.note_off()

    def is_finished(self) -> bool:
        return self.amp_env.is_finished()

    def load_patch(self, patch: Patch) -> None:
        self.osc1.waveform = patch.osc1.waveform
        self.osc2.waveform = patch.osc2.waveform
        self.filter.filter_type = patch.filter.filter_type
        self.filter.set_cutoff(patch.filter.cutoff)
        self.filter.set_resonance(patch.filter.resonance)
        self.amp_env.set_attack(patch.amp_env.attack)
        self.amp_env.set_decay(patch.amp_env.decay)
        self.amp_env.set_sustain(patch.amp_env.sustain)
        self.amp_env.set_release(patch.amp_env.release)
        self.filter_env.set_attack(patch.filter_env.attack)
        self.filter_env.set_decay(patch.filter_env.decay)
        self.filter_env.set_sustain(patch.filter_env.sustain)
        self.filter_env.set_release(patch.filter_env.release)
        self.reverb_send = patch.effects.reverb_send
        self.delay_send = patch.effects.delay_send
        self.chorus_send = patch.effects.chorus_send
        self.distortion_drive = patch.effects.distortion_drive
        self.lfo1.waveform = patch.lfo1.waveform
        self.lfo1.depth = patch.lfo1.depth
        self.lfo1.set_rate(patch.lfo1.rate)
        self.lfo1.target = patch.lfo1.target
        self.lfo2.waveform = patch.lfo2.waveform
        self.lfo2.depth = patch.lfo2.depth
        self.lfo2.set_rate(patch.lfo2.rate)
        self.lfo2.target = patch.lfo2.target

    def apply_param(self, param_path: str, value: float) -> None:
        """Apply a parameter change from the audio thread."""
        parts = param_path.split(".")
        if parts[0] == "osc1" and len(parts) == 2:
            if parts[1] == "waveform_int":
                waveforms = ["sine", "saw", "square", "triangle", "noise"]
                idx = min(max(int(value), 0), len(waveforms) - 1)
                self.osc1.waveform = waveforms[idx]
            elif parts[1] == "octave":
                self.osc1.set_frequency(self._target_frequency * (2.0 ** int(value - 3)))
        elif parts[0] == "osc2" and len(parts) == 2:
            if parts[1] == "waveform_int":
                waveforms = ["sine", "saw", "square", "triangle", "noise"]
                idx = min(max(int(value), 0), len(waveforms) - 1)
                self.osc2.waveform = waveforms[idx]
            elif parts[1] == "detune_cents":
                detune_hz = self._target_frequency * (2.0 ** (value / 1200.0)) - self._target_frequency
                self.osc2.set_frequency(self._target_frequency + detune_hz)
        elif parts[0] == "filter" and len(parts) == 2:
            if parts[1] == "cutoff":
                self.filter.set_cutoff(value)
            elif parts[1] == "resonance":
                self.filter.set_resonance(value)
            elif parts[1] == "filter_type_int":
                types = ["lowpass", "highpass", "bandpass", "notch"]
                idx = min(max(int(value), 0), len(types) - 1)
                self.filter.set_type(types[idx])
        elif parts[0] == "amp_env" and len(parts) == 2:
            if parts[1] == "attack":
                self.amp_env.set_attack(value)
            elif parts[1] == "decay":
                self.amp_env.set_decay(value)
            elif parts[1] == "sustain":
                self.amp_env.set_sustain(value)
            elif parts[1] == "release":
                self.amp_env.set_release(value)
        elif parts[0] == "filter_env" and len(parts) == 2:
            if parts[1] == "attack":
                self.filter_env.set_attack(value)
            elif parts[1] == "decay":
                self.filter_env.set_decay(value)
            elif parts[1] == "sustain":
                self.filter_env.set_sustain(value)
            elif parts[1] == "release":
                self.filter_env.set_release(value)
            elif parts[1] == "amount":
                self.filter.env_amount = value
        elif parts[0] == "lfo1" and len(parts) == 2:
            if parts[1] == "rate":
                self.lfo1.set_rate(value)
            elif parts[1] == "depth":
                self.lfo1.depth = value
        elif parts[0] == "effects" and len(parts) == 2:
            if parts[1] == "reverb_send":
                self.reverb_send = value
            elif parts[1] == "delay_send":
                self.delay_send = value
            elif parts[1] == "chorus_send":
                self.chorus_send = value
            elif parts[1] == "distortion_drive":
                self.distortion_drive = value
        elif parts[0] == "portamento" and len(parts) == 2 and parts[1] == "time":
            self._portamento_time = max(0.0, value)

    def render_block(self, frames: int) -> npt.NDArray[np.float32]:
        """Render one block of mono audio. Returns shape (frames,) float32."""
        if not self.active:
            return np.zeros(frames, dtype=np.float32)

        # Portamento glide
        if self._portamento_time > 0.0 and abs(self._target_frequency - self._current_frequency) > 0.01:
            glide_samples = int(self._portamento_time * self._sample_rate)
            step = (self._target_frequency - self._current_frequency) / max(glide_samples, 1)
            self._current_frequency += step * frames
            if abs(self._current_frequency - self._target_frequency) < 0.01:
                self._current_frequency = self._target_frequency
            self.osc1.set_frequency(self._current_frequency)
            self.osc2.set_frequency(self._current_frequency)

        # Apply LFO to oscillator pitch
        lfo1_out = self.lfo1.process(frames)
        if self.lfo1.target == "osc_pitch" and self.lfo1.depth > 0.0:
            pitch_mod = lfo1_out * 12.0
            self.osc1.set_frequency(self._current_frequency * (2.0 ** (pitch_mod.mean() / 12.0)))

        self.lfo2.process(frames)  # LFO2 output available for future modulation targets

        # Generate oscillator outputs
        osc1_out = self.osc1.generate(frames) * 0.5
        osc2_out = self.osc2.generate(frames) * 0.5
        noise_out = self.noise_osc.generate(frames) * 0.3
        mixed = osc1_out + osc2_out + noise_out

        # Apply filter envelope modulation
        base_cutoff = self.filter.cutoff
        fe_env = self.filter_env.render_block(frames)
        if self.filter.env_amount != 0.0:
            env_mod = fe_env * self.filter.env_amount * base_cutoff
            self.filter.set_cutoff(max(20.0, min(20000.0, base_cutoff + env_mod.mean())))

        # Apply filter
        filtered = self.filter.process(mixed.astype(np.float32))

        # Restore cutoff
        self.filter.set_cutoff(base_cutoff)

        # Apply amp envelope
        amp_env_out = self.amp_env.render_block(frames)
        output: npt.NDArray[np.float32] = filtered * amp_env_out * self.velocity

        if not self.amp_env.is_idle():
            self.active = self.amp_env.is_idle() is False
        else:
            self.active = False

        return np.asarray(output, dtype=np.float32)

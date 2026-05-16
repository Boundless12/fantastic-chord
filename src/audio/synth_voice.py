"""SynthVoice: Serum-style synthesizer voice with unison, sub osc, and wavetable support.


Osc1+Osc2 → Mixer → Filter → Amp(ADSR) → Pan → Voice Output
With LFO modulation, effects sends, unison stacking, and sub oscillator.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from .constants import SAMPLE_RATE
from .envelope import ADSR
from .filter import BiquadFilter
from .lfo import LFO
from .mod_matrix import ModMatrix
from .oscillator import NoiseOscillator, Oscillator
from .patch import Patch


class SynthVoice:
    """Serum-style synthesizer voice with unison stacking and sub oscillator."""

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

    # Mixer levels
    osc1_level: float
    osc2_level: float
    noise_level: float
    sub_osc_level: float

    # Stored tuning offsets
    _osc1_octave: int
    _osc1_semitones: float
    _osc1_detune_cents: float
    _osc2_octave: int
    _osc2_semitones: float
    _osc2_detune_cents: float
    _key_track: float

    # Unison
    unison_voices: int
    unison_detune: float
    unison_spread: float
    _unison_detunes: list[float]
    _unison_pans: list[tuple[float, float]]

    # Modulation matrix
    mod_matrix: ModMatrix

    # Sub oscillator
    _sub_osc: Oscillator
    _sub_waveform: str
    _sub_octave: int

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

        self.osc1_level = 1.0
        self.osc2_level = 0.0
        self.noise_level = 0.0
        self.sub_osc_level = 0.0

        self._osc1_octave = 0
        self._osc1_semitones = 0.0
        self._osc1_detune_cents = 0.0
        self._osc2_octave = 0
        self._osc2_semitones = 0.0
        self._osc2_detune_cents = 0.0
        self._key_track = 0.0

        self.unison_voices = 1
        self.unison_detune = 0.0
        self.unison_spread = 0.0
        self._unison_detunes = []
        self._unison_pans = []

        self.mod_matrix = ModMatrix(num_slots=16)
        self._sub_osc = Oscillator(sample_rate, "sine")
        self._sub_waveform = "sine"
        self._sub_octave = -1

        self._target_frequency = 440.0
        self._current_frequency = 440.0
        self._portamento_time = 0.0

    @staticmethod
    def _midi_to_freq(note: int) -> float:
        return float(440.0 * (2.0 ** ((note - 69) / 12.0)))

    def _apply_tuning_offsets(self, base_freq: float) -> tuple[float, float]:
        """Apply per-oscillator octave, semitone, and detune offsets to the base frequency."""
        f1 = base_freq * (2.0**self._osc1_octave)
        f1 *= 2.0 ** ((self._osc1_semitones + self._osc1_detune_cents / 100.0) / 12.0)

        f2 = base_freq * (2.0**self._osc2_octave)
        f2 *= 2.0 ** ((self._osc2_semitones + self._osc2_detune_cents / 100.0) / 12.0)

        return f1, f2

    def note_on(self, note: int, velocity: int) -> None:
        self.note = note
        self.velocity = velocity / 127.0
        self.active = True
        base_freq = self._midi_to_freq(note)

        f1, f2 = self._apply_tuning_offsets(base_freq)

        if self._portamento_time > 0.0 and self._current_frequency > 0.0:
            self._target_frequency = f1
        else:
            self._current_frequency = f1
            self._target_frequency = f1
            self.osc1.set_frequency(f1)
            self.osc2.set_frequency(f2)

        # Sub oscillator
        sub_base = base_freq * (2.0**self._sub_octave)
        self._sub_osc.set_frequency(sub_base)
        self._sub_osc.set_waveform(self._sub_waveform)

        # Unison detune calculation (exponential spread)
        uv = max(1, self.unison_voices)
        self._unison_detunes = []
        self._unison_pans = []
        if uv > 1:
            for i in range(uv):
                offset = (i - (uv - 1) / 2.0) / max((uv - 1) / 2.0, 1)
                detune_cents = offset * self.unison_detune * 100.0
                self._unison_detunes.append(detune_cents)
                pan_offset = offset * self.unison_spread
                pan_angle = (pan_offset + 0.5) * np.pi / 2.0
                self._unison_pans.append((float(np.cos(pan_angle)), float(np.sin(pan_angle))))

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
        self._osc1_octave = patch.osc1.octave
        self._osc1_semitones = patch.osc1.semitones
        self._osc1_detune_cents = patch.osc1.detune_cents
        self._osc2_octave = patch.osc2.octave
        self._osc2_semitones = patch.osc2.semitones
        self._osc2_detune_cents = patch.osc2.detune_cents

        self.osc1_level = patch.mixer.osc1_level
        self.osc2_level = patch.mixer.osc2_level
        self.noise_level = patch.mixer.noise_level

        self.filter.filter_type = patch.filter.filter_type
        self.filter.set_cutoff(patch.filter.cutoff)
        self.filter.set_resonance(patch.filter.resonance)
        self.filter.env_amount = patch.filter.env_amount
        self._key_track = patch.filter.key_track

        self.amp_env.set_attack(patch.amp_env.attack)
        self.amp_env.set_decay(patch.amp_env.decay)
        self.amp_env.set_sustain(patch.amp_env.sustain)
        self.amp_env.set_release(patch.amp_env.release)

        self.filter_env.set_attack(patch.filter_env.attack)
        self.filter_env.set_decay(patch.filter_env.decay)
        self.filter_env.set_sustain(patch.filter_env.sustain)
        self.filter_env.set_release(patch.filter_env.release)
        self.filter.env_amount = patch.filter.env_amount

        self.reverb_send = patch.effects.reverb_send
        self.delay_send = patch.effects.delay_send
        self.chorus_send = patch.effects.chorus_send
        self.distortion_drive = patch.effects.distortion_drive

        self.lfo1.waveform = patch.lfo1.waveform
        self.lfo1.depth = patch.lfo1.depth
        self.lfo1.set_rate(patch.lfo1.rate)
        self.lfo1.target = patch.lfo1.target
        self.lfo1.key_sync = patch.lfo1.key_sync
        self.lfo1.one_shot = patch.lfo1.one_shot
        self.lfo1.fade_in = patch.lfo1.fade_in

        self.lfo2.waveform = patch.lfo2.waveform
        self.lfo2.depth = patch.lfo2.depth
        self.lfo2.set_rate(patch.lfo2.rate)
        self.lfo2.target = patch.lfo2.target
        self.lfo2.key_sync = patch.lfo2.key_sync
        self.lfo2.one_shot = patch.lfo2.one_shot
        self.lfo2.fade_in = patch.lfo2.fade_in

        self._portamento_time = max(0.0, patch.portamento.time)
        self.sub_osc_level = getattr(patch, "sub_osc_level", 0.0)
        self._sub_octave = getattr(patch, "sub_octave", -1)
        self.unison_voices = getattr(patch, "unison_voices", 1)
        self.unison_detune = getattr(patch, "unison_detune", 0.0)
        self.unison_spread = getattr(patch, "unison_spread", 0.0)
        mod_data = getattr(patch, "mod_matrix", None)
        if mod_data:
            self.mod_matrix = ModMatrix.from_dict(mod_data)

        # Recompute oscillator frequencies with loaded tuning
        if self.note > 0:
            base_freq = self._midi_to_freq(self.note)
            f1, f2 = self._apply_tuning_offsets(base_freq)
            self.osc1.set_frequency(f1)
            self.osc2.set_frequency(f2)

    def apply_param(self, param_path: str, value: float) -> None:
        """Apply a parameter change from the audio thread."""
        parts = param_path.split(".")
        category = parts[0]

        if category == "osc1" and len(parts) == 2:
            self._apply_osc_param(1, parts[1], value)
        elif category == "osc2" and len(parts) == 2:
            self._apply_osc_param(2, parts[1], value)
        elif category == "mixer" and len(parts) == 2:
            self._apply_mixer_param(parts[1], value)
        elif category == "noise" and len(parts) == 2:
            pass  # Reserved for future
        elif category == "filter" and len(parts) == 2:
            self._apply_filter_param(parts[1], value)
        elif category == "amp_env" and len(parts) == 2:
            self._apply_amp_env_param(parts[1], value)
        elif category == "filter_env" and len(parts) == 2:
            self._apply_filter_env_param(parts[1], value)
        elif category == "lfo1" and len(parts) == 2:
            self._apply_lfo_param(self.lfo1, parts[1], value)
        elif category == "lfo2" and len(parts) == 2:
            self._apply_lfo_param(self.lfo2, parts[1], value)
        elif category == "effects" and len(parts) == 2:
            self._apply_effects_param(parts[1], value)
        elif category == "portamento" and len(parts) == 2 and parts[1] == "time":
            self._portamento_time = max(0.0, value)
        elif category == "unison":
            if len(parts) == 2:
                if parts[1] == "voices":
                    self.unison_voices = max(1, min(7, int(value)))
                elif parts[1] == "detune":
                    self.unison_detune = max(0.0, min(1.0, value))
                elif parts[1] == "spread":
                    self.unison_spread = max(0.0, min(1.0, value))
        elif category == "sub" and len(parts) == 2:
            if parts[1] == "level":
                self.sub_osc_level = max(0.0, min(1.0, value))
            elif parts[1] == "octave":
                self._sub_octave = max(-2, min(1, int(value)))
            elif parts[1] == "waveform":
                self._sub_waveform = str(value) if isinstance(value, str) else "sine"

    def _apply_osc_param(self, osc_num: int, field: str, value: float) -> None:
        osc = self.osc1 if osc_num == 1 else self.osc2
        if field == "waveform_int":
            waveforms = ["sine", "saw", "square", "triangle", "noise"]
            idx = min(max(int(value), 0), len(waveforms) - 1)
            osc.waveform = waveforms[idx]
        elif field == "octave":
            oct_val = int(value) - 3 if value <= 6 else int(value)  # e.g. range -3..+3 sent as float
            if osc_num == 1:
                self._osc1_octave = oct_val
            else:
                self._osc2_octave = oct_val
        elif field == "semitones":
            if osc_num == 1:
                self._osc1_semitones = value
            else:
                self._osc2_semitones = value
        elif field == "detune_cents":
            if osc_num == 1:
                self._osc1_detune_cents = value
            else:
                self._osc2_detune_cents = value
        elif field == "pulse_width":
            if hasattr(osc, "pulse_width"):
                osc.pulse_width = max(0.01, min(0.99, value))
        elif field == "phase":
            osc.phase = value
        elif field == "wt_position":
            if hasattr(osc, "set_position"):
                osc.set_position(max(0.0, min(1.0, value)))
        elif field == "warp_mode_int":
            modes = ["none", "bend_p", "bend_n", "mirror", "fold", "pwm", "crush"]
            idx = min(max(int(value), 0), len(modes) - 1)
            if hasattr(osc, "set_warp"):
                osc.set_warp(modes[idx], getattr(osc, "warp_amount", 0.0))
        elif field == "warp_amount":
            if hasattr(osc, "set_warp"):
                osc.set_warp(getattr(osc, "warp_mode", "none"), max(0.0, min(1.0, value)))

        # Recompute frequency with updated offsets
        if self.note > 0 and field in ("octave", "semitones", "detune_cents"):
            base_freq = self._midi_to_freq(self.note)
            f1, f2 = self._apply_tuning_offsets(base_freq)
            if osc_num == 1:
                self.osc1.set_frequency(f1)
            else:
                self.osc2.set_frequency(f2)

    def _apply_mixer_param(self, field: str, value: float) -> None:
        if field == "osc1_level":
            self.osc1_level = max(0.0, min(1.0, value))
        elif field == "osc2_level":
            self.osc2_level = max(0.0, min(1.0, value))
        elif field == "noise_level":
            self.noise_level = max(0.0, min(1.0, value))
        elif field == "sub_osc_level" or field == "ring_mod":
            pass

    def _apply_filter_param(self, field: str, value: float) -> None:
        if field == "cutoff":
            self.filter.set_cutoff(value)
        elif field == "resonance":
            self.filter.set_resonance(value)
        elif field == "filter_type_int":
            types = ["lowpass", "highpass", "bandpass", "notch"]
            idx = min(max(int(value), 0), len(types) - 1)
            self.filter.set_type(types[idx])
        elif field == "env_amount":
            self.filter.env_amount = max(0.0, min(1.0, value))
        elif field == "key_track":
            self._key_track = max(0.0, min(1.0, value))
        elif field == "drive" or field == "cutoff_link" or field == "slope_int":
            pass

    def _apply_amp_env_param(self, field: str, value: float) -> None:
        if field == "attack":
            self.amp_env.set_attack(value)
        elif field == "decay":
            self.amp_env.set_decay(value)
        elif field == "sustain":
            self.amp_env.set_sustain(value)
        elif field == "release":
            self.amp_env.set_release(value)

    def _apply_filter_env_param(self, field: str, value: float) -> None:
        if field == "attack":
            self.filter_env.set_attack(value)
        elif field == "decay":
            self.filter_env.set_decay(value)
        elif field == "sustain":
            self.filter_env.set_sustain(value)
        elif field == "release":
            self.filter_env.set_release(value)
        elif field == "amount":
            self.filter.env_amount = value

    def _apply_lfo_param(self, lfo: LFO, field: str, value: float) -> None:
        if field == "rate":
            lfo.set_rate(value)
        elif field == "depth":
            lfo.depth = max(0.0, min(1.0, value))
        elif field == "waveform_int":
            waveforms = ["sine", "triangle", "square", "saw_up", "saw_down", "sample_hold", "random"]
            idx = min(max(int(value), 0), len(waveforms) - 1)
            lfo.waveform = waveforms[idx]
        elif field == "target_int":
            targets = ["none", "osc_pitch", "mix", "filter_cutoff", "filter_res", "amp", "pan"]
            idx = min(max(int(value), 0), len(targets) - 1)
            lfo.target = targets[idx]
        elif field == "key_sync":
            lfo.key_sync = value > 0.5
        elif field == "one_shot":
            lfo.one_shot = value > 0.5
        elif field == "fade_in":
            lfo.fade_in = max(0.0, value)
        elif field == "rate_sync":
            lfo.rate_sync = value > 0.5

    def _apply_effects_param(self, field: str, value: float) -> None:
        if field == "reverb_send":
            self.reverb_send = max(0.0, min(1.0, value))
        elif field == "delay_send":
            self.delay_send = max(0.0, min(1.0, value))
        elif field == "chorus_send":
            self.chorus_send = max(0.0, min(1.0, value))
        elif field == "distortion_drive":
            self.distortion_drive = max(0.0, min(1.0, value))

    def render_block(self, frames: int, sub_blocks: int = 16) -> npt.NDArray[np.float32]:
        """Render one block of mono audio with sub-block modulation smoothing."""
        if not self.active:
            return np.zeros(frames, dtype=np.float32)

        # Compute sub-block sizes, distributing remainder
        base_sf = frames // sub_blocks
        remainder = frames % sub_blocks

        # Portamento glide — apply once for the whole block
        if self._portamento_time > 0.0 and abs(self._target_frequency - self._current_frequency) > 0.01:
            glide_samples = int(self._portamento_time * self._sample_rate)
            step = (self._target_frequency - self._current_frequency) / max(glide_samples, 1)
            self._current_frequency += step * frames
            if abs(self._current_frequency - self._target_frequency) < 0.01:
                self._current_frequency = self._target_frequency

        # Pre-compute modulation signals for the full block
        lfo1_out = self.lfo1.process(frames)
        lfo2_out = self.lfo2.process(frames)
        fe_env = self.filter_env.render_block(frames)
        amp_env_out = self.amp_env.render_block(frames)

        # Evaluate modulation matrix
        mod_context: dict[str, float] = {
            "lfo1": float(np.mean(lfo1_out)),
            "lfo2": float(np.mean(lfo2_out)),
            "amp_env": float(np.mean(amp_env_out)),
            "filter_env": float(np.mean(fe_env)),
            "velocity": float(self.velocity),
            "key_track": float(self.note) / 127.0,
            "mod_wheel": 0.0,
            "random": np.random.uniform(-1.0, 1.0),
        }
        mod_values = self.mod_matrix.process(mod_context)

        base_freq = self._current_frequency
        base_cutoff = self.filter.cutoff
        use_lfo_pitch = self.lfo1.target == "osc_pitch" and self.lfo1.depth > 0.0
        use_filter_env = self.filter.env_amount != 0.0

        output_blocks: list[npt.NDArray[np.float32]] = []

        s0 = 0
        actual_blocks = sub_blocks if base_sf > 0 else frames
        for sb in range(actual_blocks):
            sf = base_sf + (1 if sb < remainder else 0) if base_sf > 0 else 1
            if sf == 0:
                sf = base_sf
            s1 = s0 + sf

            # Apply modulation matrix: cutoff offset
            cutoff_mod = mod_values.get("cutoff", 0.0)
            base_cutoff_mod = base_cutoff * (2.0 ** (cutoff_mod * 4.0)) if abs(cutoff_mod) > 0.001 else base_cutoff

            # Apply modulation matrix: volume
            vol_mod = mod_values.get("volume", 0.0)
            vel_mod = float(self.velocity) * max(0.0, min(2.0, 1.0 + vol_mod))

            # Apply sub-block LFO pitch modulation
            if use_lfo_pitch:
                pm = float(np.mean(lfo1_out[s0:s1])) * 12.0
                self.osc1.set_frequency(base_freq * (2.0 ** (pm / 12.0)))
            else:
                self.osc1.set_frequency(base_freq)
            self.osc2.set_frequency(base_freq)

            # Generate oscillator outputs with unison
            uv = max(1, self.unison_voices)
            unison_gain = 1.0 / np.sqrt(uv)
            mixed = np.zeros(sf, dtype=np.float32)

            # Sub oscillator
            if self.sub_osc_level > 0.001:
                sub_out = self._sub_osc.generate(sf) * 0.5 * self.sub_osc_level
                mixed += sub_out

            # Noise (not per-unison-voice)
            if self.noise_level > 0.001:
                mixed += self.noise_osc.generate(sf) * 0.3 * self.noise_level

            # Main oscillators with unison
            for vi in range(uv):
                v_detune = self._unison_detunes[vi] / 100.0 if vi < len(self._unison_detunes) else 0.0
                uf1 = base_freq * (2.0 ** (v_detune / 12.0))
                uf2 = base_freq * (2.0 ** (v_detune / 12.0))
                self.osc1.set_frequency(uf1)
                self.osc2.set_frequency(uf2)
                u_osc1 = self.osc1.generate(sf) * 0.5 * self.osc1_level * unison_gain
                u_osc2 = self.osc2.generate(sf) * 0.5 * self.osc2_level * unison_gain
                mixed += u_osc1 + u_osc2

            # Restore base frequency for next sub-block
            self.osc1.set_frequency(base_freq)
            self.osc2.set_frequency(base_freq)

            # Apply sub-block filter envelope modulation (with mod matrix cutoff)
            if use_filter_env:
                em = float(np.mean(fe_env[s0:s1])) * self.filter.env_amount * base_cutoff_mod
                self.filter.set_cutoff(max(20.0, min(20000.0, base_cutoff_mod + em)))
            else:
                self.filter.set_cutoff(base_cutoff_mod)

            filtered = self.filter.process(mixed.astype(np.float32))

            # Apply amp envelope with mod matrix volume
            output_blocks.append(filtered * amp_env_out[s0:s1] * vel_mod)

            s0 = s1

        # Restore filter cutoff
        self.filter.set_cutoff(base_cutoff)

        if not self.amp_env.is_idle():
            self.active = self.amp_env.is_idle() is False
        else:
            self.active = False

        return np.concatenate(output_blocks).astype(np.float32)

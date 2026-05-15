"""DrumSynth: Algorithmic drum sound synthesis using existing DSP blocks.
from __future__ import annotations


Each drum type has a dedicated synthesis recipe: tuned oscillators with pitch
envelopes, shaped noise, filters, and optional distortion/bit-crushing.
All sounds are synthesized locally — no sample files required.
"""

import numpy as np
import numpy.typing as npt

from .constants import SAMPLE_RATE
from .drum_kit import DrumSoundParams
from .filter import BiquadFilter

PI_2_F = 2.0 * np.pi


class DrumSynth:
    """Synthesizes complete one-shot drum sounds from DrumSoundParams.

    Caches filter objects for reuse across renders. The render() method is called
    at trigger time (in AudioEngine._dispatch), NOT in the hot callback loop,
    so per-sample Python loops and numpy allocations are acceptable here.
    """

    _sample_rate: int

    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        self._sample_rate = sample_rate

    def render(self, params: DrumSoundParams, velocity: float) -> npt.NDArray[np.float32]:
        """Render a complete drum sound into a mono float32 buffer.

        Args:
            params: Synthesis parameters for the drum sound.
            velocity: Velocity 0.0-1.0, scales output amplitude.

        Returns:
            Mono float32 numpy array at the synth's sample rate.
        """
        sr = self._sample_rate

        # Determine buffer length
        max_decay = max(params.amp_decay, params.noise_decay, params.filter_decay)
        total_samples = int(sr * max_decay * 3.5)
        total_samples = max(total_samples, int(sr * 0.01))
        total_samples = min(total_samples, int(sr * 4.0))

        buf = np.zeros(total_samples, dtype=np.float64)

        # --- Tonal oscillator with pitch envelope ---
        if params.tone_level > 0.001:
            self._render_tone(buf, params, sr)

        # --- Noise component ---
        if params.noise_level > 0.001:
            self._render_noise(buf, params, sr)

        # --- Amplitude envelope ---
        self._apply_amp_envelope(buf, params, sr)

        # --- Filter ---
        if params.filter_cutoff < 19900.0:
            self._apply_filter(buf, params, sr)

        # --- Distortion ---
        if params.distortion_drive > 0.001:
            gain = 1.0 + params.distortion_drive * 18.0
            buf = np.tanh(buf * gain) * (1.0 / max(1.0, gain * 0.6))

        # --- Bit crush ---
        if params.bit_crush > 0.001:
            bits = max(1, int(16.0 - params.bit_crush * 14.0))
            levels = float(2**bits)
            buf = np.round(buf * levels) / levels

        # Velocity and safety clamp
        buf *= velocity
        peak = float(np.max(np.abs(buf)))
        if peak > 0.98:
            buf *= 0.98 / peak

        return buf.astype(np.float32)

    def _render_tone(self, buf: npt.NDArray[np.float64], params: DrumSoundParams, sr: int) -> None:
        """Render tonal oscillator with exponential pitch sweep and optional FM."""
        total = len(buf)
        p_start = float(params.pitch_start)
        p_end = float(params.pitch_end)
        p_decay = max(params.pitch_decay, 0.001)
        amp_decay = max(params.amp_decay, 0.01)
        fm_index = float(params.fm_mod_index)
        fm_ratio = float(params.fm_mod_ratio)
        tone_level = float(params.tone_level)
        waveform = params.osc_waveform

        phase = 0.0
        fm_phase = 0.0

        for i in range(total):
            t = i / sr
            if t < amp_decay:
                # Exponential frequency sweep: start → end
                ratio = t / p_decay
                freq = p_start * (p_end / max(p_start, 1e-9)) ** ratio if ratio < 8.0 else p_end
                freq = max(1.0, min(20000.0, freq))
            else:
                freq = p_end

            phase_inc = PI_2_F * freq / sr
            phase += phase_inc
            if phase > PI_2_F:
                phase -= PI_2_F

            if fm_index > 0.0001:
                fm_phase += phase_inc * fm_ratio
                if fm_phase > PI_2_F:
                    fm_phase -= PI_2_F
                sample = np.sin(phase + np.sin(fm_phase) * fm_index)
            else:
                sample = self._waveform_sample(phase, waveform)

            buf[i] += sample * tone_level

    def _render_noise(self, buf: npt.NDArray[np.float64], params: DrumSoundParams, sr: int) -> None:
        """Add shaped white noise."""
        total = len(buf)
        noise = np.random.uniform(-1.0, 1.0, total).astype(np.float64)

        n_decay = max(params.noise_decay, 0.001)
        env = np.exp(-np.arange(total, dtype=np.float64) / (sr * n_decay))
        # Clap-like bursts: 3 rapid noise pulses
        noise_type = params.filter_type if params.tone_level < 0.01 else ""
        if noise_type == "bandpass" and params.noise_level > 0.5 and 1200.0 <= params.filter_cutoff <= 1800.0:
            # Likely a clap — add layered bursts
            burst_env = np.zeros(total, dtype=np.float64)
            burst_times = [0.0, 0.012, 0.025]
            burst_decay = 0.025
            for bt in burst_times:
                start = int(bt * sr)
                if start < total:
                    blen = min(total - start, int(burst_decay * sr * 3))
                    burst_env[start : start + blen] += np.exp(-np.arange(blen, dtype=np.float64) / (sr * burst_decay))
            env = env * burst_env

        buf += noise * env * float(params.noise_level)

    def _apply_amp_envelope(self, buf: npt.NDArray[np.float64], params: DrumSoundParams, sr: int) -> None:
        """Apply attack + exponential decay amplitude envelope."""
        total = len(buf)
        env = np.ones(total, dtype=np.float64)

        attack_samp = max(1, int(params.amp_attack * sr))
        if attack_samp > 1 and attack_samp < total:
            env[:attack_samp] = np.linspace(0.0, 1.0, attack_samp)

        decay_start = attack_samp
        if decay_start < total:
            a_decay = max(params.amp_decay, 0.001)
            decay_len = total - decay_start
            env[decay_start:] = np.exp(-np.arange(decay_len, dtype=np.float64) / (sr * a_decay))

        buf *= env

    def _apply_filter(self, buf: npt.NDArray[np.float64], params: DrumSoundParams, sr: int) -> None:
        """Apply filter with optional envelope sweep."""
        filt = BiquadFilter(sr, params.filter_type, params.filter_cutoff, params.filter_resonance)

        f_env = params.filter_env_amount
        if f_env > 0.001:
            total = len(buf)
            base_cutoff = params.filter_cutoff
            f_decay = max(params.filter_decay, 0.001)
            for i in range(total):
                t = i / sr
                env_mod = np.exp(-t / f_decay) * f_env * base_cutoff
                new_cutoff = max(20.0, min(20000.0, base_cutoff + env_mod))
                filt.set_cutoff(new_cutoff)
                buf[i] = filt.process_sample(float(buf[i]))
        else:
            buf32 = buf.astype(np.float32)
            filtered = filt.process(buf32)
            buf[:] = filtered.astype(np.float64)

    @staticmethod
    def _waveform_sample(phase: float, waveform: str) -> float:
        """Generate a single sample from the given waveform at the current phase."""
        if waveform == "sine" or waveform == "":
            return float(np.sin(phase))
        elif waveform == "triangle":
            val = phase / PI_2_F
            if val > 1.0:
                val -= 1.0
            return float(2.0 * abs(2.0 * val - 1.0) - 1.0)
        elif waveform == "square":
            return 1.0 if np.sin(phase) >= 0.0 else -1.0
        elif waveform == "saw":
            return float(2.0 * (phase / PI_2_F) - 1.0)
        else:
            return float(np.sin(phase))

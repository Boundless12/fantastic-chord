"""Generate 12 factory synthesizer presets."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from audio.patch import Patch

PRESET_DIR = os.path.join(os.path.dirname(__file__), "..", "resources", "presets")


def make_preset(name: str, category: str) -> Patch:
    p = Patch(name=name, category=category)
    return p


def save_all(presets: list[Patch]) -> None:
    for p in presets:
        cat_dir = os.path.join(PRESET_DIR, p.category)
        os.makedirs(cat_dir, exist_ok=True)
        fname = p.name.lower().replace(" ", "_") + ".json"
        p.to_json(os.path.join(cat_dir, fname))
    print(f"Saved {len(presets)} presets to {PRESET_DIR}")


def main() -> None:
    presets: list[Patch] = []

    # 1. Classic Saw Lead
    p = make_preset("Classic Saw Lead", "lead")
    p.osc1.waveform = "saw"
    p.osc2.waveform = "saw"
    p.osc2.detune_cents = 8.0
    p.mixer.osc1_level = 0.85
    p.mixer.osc2_level = 0.55
    p.filter.cutoff = 8000.0
    p.filter.env_amount = 0.25
    p.amp_env.attack = 0.01
    p.amp_env.decay = 0.2
    p.amp_env.sustain = 0.75
    p.amp_env.release = 0.2
    p.filter.env_amount = 0.25
    p.filter_env.decay = 0.3
    p.filter_env.release = 0.3
    p.effects.reverb_send = 0.2
    p.effects.delay_send = 0.15
    p.portamento.time = 0.05
    presets.append(p)

    # 2. Sync Lead
    p = make_preset("Sync Lead", "lead")
    p.osc1.waveform = "saw"
    p.osc2.waveform = "saw"
    p.osc2.detune_cents = 15.0
    p.mixer.osc1_level = 0.8
    p.mixer.osc2_level = 0.6
    p.filter.cutoff = 6000.0
    p.filter.resonance = 0.3
    p.filter.env_amount = 0.4
    p.amp_env.attack = 0.01
    p.amp_env.decay = 0.15
    p.amp_env.sustain = 0.7
    p.amp_env.release = 0.15
    p.filter.env_amount = 0.4
    p.filter_env.decay = 0.25
    p.filter_env.release = 0.25
    p.effects.reverb_send = 0.15
    p.effects.delay_send = 0.2
    p.effects.distortion_drive = 0.1
    p.portamento.time = 0.03
    p.portamento.mode = "always"
    presets.append(p)

    # 3. Deep Reese
    p = make_preset("Deep Reese", "bass")
    p.osc1.waveform = "saw"
    p.osc1.octave = -1
    p.osc2.waveform = "saw"
    p.osc2.octave = -1
    p.osc2.detune_cents = 30.0
    p.mixer.osc1_level = 0.9
    p.mixer.osc2_level = 0.7
    p.filter.cutoff = 800.0
    p.filter.resonance = 0.3
    p.filter.env_amount = 0.3
    p.amp_env.attack = 0.02
    p.amp_env.decay = 0.3
    p.amp_env.sustain = 0.6
    p.amp_env.release = 0.3
    p.filter.env_amount = 0.3
    p.filter_env.decay = 0.4
    p.filter_env.release = 0.4
    p.effects.distortion_drive = 0.15
    presets.append(p)

    # 4. Acid Squelch
    p = make_preset("Acid Squelch", "bass")
    p.osc1.waveform = "square"
    p.osc1.octave = -1
    p.osc2.waveform = "saw"
    p.osc2.octave = -1
    p.osc2.detune_cents = 5.0
    p.mixer.osc1_level = 0.7
    p.mixer.osc2_level = 0.5
    p.filter.cutoff = 1000.0
    p.filter.resonance = 0.7
    p.filter.env_amount = 0.8
    p.amp_env.attack = 0.01
    p.amp_env.decay = 0.25
    p.amp_env.sustain = 0.5
    p.amp_env.release = 0.2
    p.filter.env_amount = 0.8
    p.filter_env.decay = 0.2
    p.filter_env.release = 0.15
    p.effects.distortion_drive = 0.3
    p.portamento.time = 0.04
    p.portamento.mode = "always"
    p.portamento.polyphony = "mono"
    presets.append(p)

    # 5. Lush Strings
    p = make_preset("Lush Strings", "pad")
    p.osc1.waveform = "saw"
    p.osc2.waveform = "saw"
    p.osc2.detune_cents = -7.0
    p.mixer.osc1_level = 0.7
    p.mixer.osc2_level = 0.6
    p.filter.cutoff = 4000.0
    p.filter.resonance = 0.2
    p.filter.env_amount = 0.2
    p.amp_env.attack = 0.8
    p.amp_env.decay = 0.5
    p.amp_env.sustain = 0.7
    p.amp_env.release = 1.5
    p.filter_env.attack = 0.6
    p.filter_env.decay = 0.5
    p.filter_env.sustain = 0.3
    p.filter_env.release = 1.2
    p.filter.env_amount = 0.2
    p.lfo1.waveform = "sine"
    p.lfo1.rate = 0.4
    p.lfo1.depth = 0.15
    p.lfo1.target = "osc_pitch"
    p.effects.reverb_send = 0.5
    p.effects.chorus_send = 0.4
    presets.append(p)

    # 6. Evolving Dream
    p = make_preset("Evolving Dream", "pad")
    p.osc1.waveform = "triangle"
    p.osc2.waveform = "saw"
    p.osc2.detune_cents = 12.0
    p.mixer.osc1_level = 0.6
    p.mixer.osc2_level = 0.5
    p.filter.cutoff = 2000.0
    p.filter.resonance = 0.4
    p.filter.env_amount = 0.5
    p.amp_env.attack = 1.2
    p.amp_env.decay = 0.6
    p.amp_env.sustain = 0.6
    p.amp_env.release = 2.0
    p.filter_env.attack = 1.0
    p.filter_env.decay = 0.8
    p.filter_env.sustain = 0.2
    p.filter_env.release = 1.8
    p.filter.env_amount = 0.5
    p.lfo1.waveform = "triangle"
    p.lfo1.rate = 0.25
    p.lfo1.depth = 0.3
    p.lfo1.target = "filter_cutoff"
    p.effects.reverb_send = 0.6
    p.effects.chorus_send = 0.3
    p.effects.delay_send = 0.2
    presets.append(p)

    # 7. FM Pluck
    p = make_preset("FM Pluck", "pluck")
    p.osc1.waveform = "sine"
    p.osc2.waveform = "sine"
    p.osc2.octave = 1
    p.osc2.fm_amount = 2.5
    p.mixer.osc1_level = 0.5
    p.mixer.osc2_level = 0.6
    p.filter.cutoff = 6000.0
    p.filter.resonance = 0.1
    p.filter.env_amount = 0.3
    p.amp_env.attack = 0.001
    p.amp_env.decay = 0.15
    p.amp_env.sustain = 0.0
    p.amp_env.release = 0.1
    p.filter.env_amount = 0.3
    p.filter_env.attack = 0.001
    p.filter_env.decay = 0.12
    p.filter_env.sustain = 0.0
    p.filter_env.release = 0.08
    p.effects.reverb_send = 0.15
    presets.append(p)

    # 8. Soft Mallet
    p = make_preset("Soft Mallet", "pluck")
    p.osc1.waveform = "triangle"
    p.osc2.waveform = "sine"
    p.osc2.octave = 1
    p.mixer.osc1_level = 0.7
    p.mixer.osc2_level = 0.4
    p.filter.cutoff = 5000.0
    p.filter.env_amount = 0.2
    p.amp_env.attack = 0.002
    p.amp_env.decay = 0.3
    p.amp_env.sustain = 0.0
    p.amp_env.release = 0.2
    p.filter.env_amount = 0.2
    p.filter_env.decay = 0.2
    p.filter_env.release = 0.15
    p.effects.reverb_send = 0.25
    presets.append(p)

    # 9. Warm EP
    p = make_preset("Warm EP", "keys")
    p.osc1.waveform = "triangle"
    p.osc2.waveform = "saw"
    p.osc2.octave = -1
    p.osc2.detune_cents = -5.0
    p.mixer.osc1_level = 0.8
    p.mixer.osc2_level = 0.4
    p.filter.cutoff = 3000.0
    p.filter.resonance = 0.2
    p.amp_env.attack = 0.02
    p.amp_env.decay = 0.4
    p.amp_env.sustain = 0.6
    p.amp_env.release = 0.4
    p.filter_env.attack = 0.02
    p.filter_env.decay = 0.5
    p.filter_env.sustain = 0.4
    p.filter_env.release = 0.3
    p.effects.chorus_send = 0.3
    p.effects.distortion_drive = 0.05
    presets.append(p)

    # 10. Vintage Organ
    p = make_preset("Vintage Organ", "keys")
    p.osc1.waveform = "saw"
    p.osc2.waveform = "square"
    p.osc2.octave = 1
    p.osc2.fm_amount = 1.0
    p.mixer.osc1_level = 0.7
    p.mixer.osc2_level = 0.5
    p.filter.cutoff = 5000.0
    p.filter.resonance = 0.1
    p.amp_env.attack = 0.01
    p.amp_env.decay = 0.1
    p.amp_env.sustain = 1.0
    p.amp_env.release = 0.15
    p.effects.distortion_drive = 0.1
    presets.append(p)

    # 11. Noise Riser
    p = make_preset("Noise Riser", "fx")
    p.osc1.waveform = "saw"
    p.mixer.osc1_level = 0.5
    p.mixer.noise_level = 0.6
    p.filter.cutoff = 200.0
    p.filter.env_amount = 0.9
    p.amp_env.attack = 1.5
    p.amp_env.decay = 0.5
    p.amp_env.sustain = 0.8
    p.amp_env.release = 1.0
    p.filter_env.attack = 1.5
    p.filter_env.decay = 0.5
    p.filter_env.sustain = 0.5
    p.filter_env.release = 0.8
    p.filter.env_amount = 0.9
    p.lfo1.waveform = "saw_up"
    p.lfo1.rate = 0.5
    p.lfo1.depth = 0.6
    p.lfo1.target = "filter_cutoff"
    p.effects.reverb_send = 0.3
    p.effects.delay_send = 0.15
    presets.append(p)

    # 12. Filter Sweep
    p = make_preset("Filter Sweep", "fx")
    p.osc1.waveform = "saw"
    p.osc1.octave = -1
    p.osc2.waveform = "square"
    p.osc2.octave = -2
    p.mixer.osc1_level = 0.7
    p.mixer.osc2_level = 0.4
    p.filter.cutoff = 200.0
    p.filter.resonance = 0.6
    p.filter.env_amount = 0.95
    p.amp_env.attack = 0.02
    p.amp_env.decay = 0.3
    p.amp_env.sustain = 0.7
    p.amp_env.release = 0.5
    p.filter_env.attack = 1.5
    p.filter_env.decay = 1.0
    p.filter_env.sustain = 0.0
    p.filter_env.release = 0.5
    p.filter.env_amount = 0.95
    p.effects.reverb_send = 0.2
    p.effects.distortion_drive = 0.15
    presets.append(p)

    save_all(presets)


if __name__ == "__main__":
    main()

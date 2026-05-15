"""Patch dataclass and PatchLibrary for synthesizer preset management."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class OscParams:
    waveform: str = "saw"
    octave: int = 0
    semitones: int = 0
    detune_cents: float = 0.0
    pulse_width: float = 0.5
    phase: float = 0.0
    wavetable_index: int = 0
    fm_source: str = "none"
    fm_amount: float = 0.0


@dataclass
class MixerParams:
    osc1_level: float = 1.0
    osc2_level: float = 0.0
    noise_level: float = 0.0
    sub_osc_level: float = 0.0
    ring_mod: float = 0.0


@dataclass
class SubOscParams:
    enabled: bool = False
    waveform: str = "square"
    octave: int = -1


@dataclass
class NoiseParams:
    level: float = 0.0
    color: float = 0.5
    stereo_spread: float = 0.0


@dataclass
class FilterParams:
    filter_type: str = "lowpass"
    cutoff: float = 20000.0
    resonance: float = 0.0
    key_track: float = 0.0
    drive: float = 0.0
    env_amount: float = 0.0
    velocity_to_cutoff: float = 0.0
    cutoff_link: float = 1.0
    slope: str = "24db"


@dataclass
class AmpEnvParams:
    attack: float = 0.01
    decay: float = 0.2
    sustain: float = 0.8
    release: float = 0.3
    velocity_to_amp: float = 0.5


@dataclass
class FilterEnvParams:
    attack: float = 0.01
    decay: float = 0.3
    sustain: float = 0.0
    release: float = 0.3
    velocity_to_env: float = 0.0


@dataclass
class LFOParams:
    waveform: str = "sine"
    rate: float = 1.0
    rate_sync: bool = False
    rate_sync_subdiv: str = "1/4"
    depth: float = 0.0
    phase: float = 0.0
    fade_in: float = 0.0
    target: str = "none"
    key_sync: bool = True
    one_shot: bool = False


@dataclass
class EffectsParams:
    reverb_send: float = 0.0
    delay_send: float = 0.0
    chorus_send: float = 0.0
    distortion_drive: float = 0.0


@dataclass
class PortamentoParams:
    time: float = 0.0
    mode: str = "off"
    polyphony: str = "poly"
    bend_range: int = 2
    unison_detune: float = 0.2


@dataclass
class Patch:
    """Complete synthesizer patch serializable to JSON."""

    name: str = "Init Patch"
    category: str = "lead"

    osc1: OscParams = field(default_factory=OscParams)
    osc2: OscParams = field(default_factory=OscParams)
    mixer: MixerParams = field(default_factory=MixerParams)
    sub_osc: SubOscParams = field(default_factory=SubOscParams)
    noise: NoiseParams = field(default_factory=NoiseParams)
    filter: FilterParams = field(default_factory=FilterParams)
    amp_env: AmpEnvParams = field(default_factory=AmpEnvParams)
    filter_env: FilterEnvParams = field(default_factory=FilterEnvParams)
    lfo1: LFOParams = field(default_factory=LFOParams)
    lfo2: LFOParams = field(default_factory=LFOParams)
    effects: EffectsParams = field(default_factory=EffectsParams)
    portamento: PortamentoParams = field(default_factory=PortamentoParams)

    @classmethod
    def from_json(cls, path: str) -> Patch:
        with open(path) as f:
            data = json.load(f)
        return cls(
            name=data["name"],
            category=data.get("category", "lead"),
            osc1=OscParams(**data.get("osc1", {})),
            osc2=OscParams(**data.get("osc2", {})),
            mixer=MixerParams(**data.get("mixer", {})),
            sub_osc=SubOscParams(**data.get("sub_osc", {})),
            noise=NoiseParams(**data.get("noise", {})),
            filter=FilterParams(**data.get("filter", {})),
            amp_env=AmpEnvParams(**data.get("amp_env", {})),
            filter_env=FilterEnvParams(**data.get("filter_env", {})),
            lfo1=LFOParams(**data.get("lfo1", {})),
            lfo2=LFOParams(**data.get("lfo2", {})),
            effects=EffectsParams(**data.get("effects", {})),
            portamento=PortamentoParams(**data.get("portamento", {})),
        )

    def to_json(self, path: str) -> None:
        data: dict[str, Any] = {
            "name": self.name,
            "category": self.category,
            "osc1": self.osc1.__dict__,
            "osc2": self.osc2.__dict__,
            "mixer": self.mixer.__dict__,
            "sub_osc": self.sub_osc.__dict__,
            "noise": self.noise.__dict__,
            "filter": self.filter.__dict__,
            "amp_env": self.amp_env.__dict__,
            "filter_env": self.filter_env.__dict__,
            "lfo1": self.lfo1.__dict__,
            "lfo2": self.lfo2.__dict__,
            "effects": self.effects.__dict__,
            "portamento": self.portamento.__dict__,
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


class PatchLibrary:
    """Manages loading/saving patches from resources/presets/."""

    patches: dict[str, Patch]

    def __init__(self) -> None:
        self.patches = {}

    def load_all(self, base_dir: str | None = None) -> None:
        if base_dir is None:
            base_dir = str(Path(__file__).parent.parent.parent / "resources" / "presets")
        if not os.path.isdir(base_dir):
            return
        for root, _dirs, files in os.walk(base_dir):
            for fname in files:
                if fname.endswith(".json"):
                    path = os.path.join(root, fname)
                    try:
                        patch = Patch.from_json(path)
                        self.patches[patch.name] = patch
                    except Exception:
                        pass

    def get(self, name: str) -> Patch | None:
        return self.patches.get(name)

    def save(self, patch: Patch, base_dir: str | None = None) -> None:
        if base_dir is None:
            base_dir = str(Path(__file__).parent.parent.parent / "resources" / "presets")
        cat_dir = os.path.join(base_dir, patch.category)
        os.makedirs(cat_dir, exist_ok=True)
        path = os.path.join(cat_dir, f"{patch.name.lower().replace(' ', '_')}.json")
        patch.to_json(path)
        self.patches[patch.name] = patch

    def delete(self, name: str) -> None:
        self.patches.pop(name, None)

    def get_by_category(self, category: str) -> list[Patch]:
        return [p for p in self.patches.values() if p.category == category]

    def list_categories(self) -> list[str]:
        return sorted(set(p.category for p in self.patches.values()))

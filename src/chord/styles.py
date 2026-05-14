"""EDM style definitions and StyleManager for loading/saving style JSON files."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ScaleDegreeUsage:
    degree: int = 1
    qualities: list[str] = field(default_factory=list)


@dataclass
class ProgressionTemplate:
    degrees: list[int] = field(default_factory=list)
    weight: int = 5
    name: str = ""


@dataclass
class RhythmPattern:
    name: str = ""
    durations: list[float] = field(default_factory=list)
    accents: list[float] | None = None
    arpeggiate: bool = False


@dataclass
class VoicingRules:
    preferred_inversions: list[str] = field(default_factory=lambda: ["root"])
    voice_range: tuple[int, int] = (48, 84)
    voice_count: int = 4
    spread: str = "close"
    doubling_rules: list[str] = field(default_factory=list)


@dataclass
class FeelParameters:
    swing: float = 0.0
    velocity_variation: float = 0.05
    timing_humanize: float = 0.004


@dataclass
class DrumPatternRef:
    """Reference to a drum pattern configuration for this style."""

    kick: str = ""
    snare: str = ""
    hh_closed: str = ""
    hh_open: str = ""
    clap: str = ""
    crash: str = ""


@dataclass
class StyleDefinition:
    """EDM style definition loaded from JSON."""

    name: str = ""
    description: str = ""
    tempo_range: tuple[int, int] = (120, 130)
    time_signatures: list[str] = field(default_factory=lambda: ["4/4"])
    scale_types: list[str] = field(default_factory=lambda: ["major"])
    scale_degrees: list[ScaleDegreeUsage] = field(default_factory=list)
    common_progressions: list[ProgressionTemplate] = field(default_factory=list)
    rhythm_patterns: list[RhythmPattern] = field(default_factory=list)
    voicing: VoicingRules = field(default_factory=VoicingRules)
    feel: FeelParameters = field(default_factory=FeelParameters)
    drum_patterns: DrumPatternRef = field(default_factory=DrumPatternRef)
    suggested_drum_kit: str = ""


class StyleManager:
    """Loads and manages EDM style definitions from resources/styles/."""

    styles: dict[str, StyleDefinition]

    def __init__(self, styles_dir: str | None = None) -> None:
        self.styles = {}
        if styles_dir is None:
            styles_dir = str(Path(__file__).parent.parent.parent / "resources" / "styles")
        self._styles_dir = styles_dir

    def load_all(self) -> None:
        if not os.path.isdir(self._styles_dir):
            logger.warning(f"Styles directory not found: {self._styles_dir}")
            return

        for fname in sorted(os.listdir(self._styles_dir)):
            if fname.endswith(".json"):
                path = os.path.join(self._styles_dir, fname)
                try:
                    style = self._load_one(path)
                    slug = fname.replace(".json", "")
                    self.styles[slug] = style
                    logger.debug(f"Loaded style: {slug}")
                except Exception as e:
                    logger.warning(f"Failed to load style {fname}: {e}")

    def _load_one(self, path: str) -> StyleDefinition:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        scale_degrees = [ScaleDegreeUsage(**sd) for sd in data.get("scale_degrees", [])]
        progressions = [
            ProgressionTemplate(name=p.get("name", ""), degrees=p["degrees"], weight=p.get("weight", 5))
            for p in data.get("common_progressions", [])
        ]
        rhythms = [RhythmPattern(**r) for r in data.get("rhythm_patterns", [])]

        voicing_data = data.get("voicing", {})
        voicing = VoicingRules(
            preferred_inversions=voicing_data.get("preferred_inversions", ["root"]),
            voice_range=tuple(voicing_data.get("voice_range", [48, 84])),
            voice_count=voicing_data.get("voice_count", 4),
            spread=voicing_data.get("spread", "close"),
            doubling_rules=voicing_data.get("doubling_rules", []),
        )

        feel_data = data.get("feel", {})
        feel = FeelParameters(
            swing=feel_data.get("swing", 0.0),
            velocity_variation=feel_data.get("velocity_variation", 0.05),
            timing_humanize=feel_data.get("timing_humanize", 0.004),
        )

        drum_data = data.get("drum_patterns", {})
        drum_patterns = DrumPatternRef(
            kick=drum_data.get("kick", ""),
            snare=drum_data.get("snare", ""),
            hh_closed=drum_data.get("hh_closed", ""),
            hh_open=drum_data.get("hh_open", ""),
            clap=drum_data.get("clap", ""),
            crash=drum_data.get("crash", ""),
        )

        return StyleDefinition(
            name=data["name"],
            description=data.get("description", ""),
            tempo_range=tuple(data.get("tempo_range", [120, 130])),
            time_signatures=data.get("time_signatures", ["4/4"]),
            scale_types=data.get("scale_types", ["major"]),
            scale_degrees=scale_degrees,
            common_progressions=progressions,
            rhythm_patterns=rhythms,
            voicing=voicing,
            feel=feel,
            drum_patterns=drum_patterns,
            suggested_drum_kit=data.get("suggested_drum_kit", ""),
        )

    def get(self, name: str) -> StyleDefinition | None:
        return self.styles.get(name)

    def list_styles(self) -> list[str]:
        return sorted(self.styles.keys())

    def save_style(self, style: StyleDefinition, slug: str) -> None:
        os.makedirs(self._styles_dir, exist_ok=True)
        path = os.path.join(self._styles_dir, f"{slug}.json")
        data: dict[str, object] = {
            "name": style.name,
            "description": style.description,
            "tempo_range": list(style.tempo_range),
            "time_signatures": style.time_signatures,
            "scale_types": style.scale_types,
            "scale_degrees": [{"degree": sd.degree, "qualities": sd.qualities} for sd in style.scale_degrees],
            "common_progressions": [
                {"name": p.name, "degrees": p.degrees, "weight": p.weight} for p in style.common_progressions
            ],
            "rhythm_patterns": [{k: v for k, v in r.__dict__.items() if v is not None} for r in style.rhythm_patterns],
            "voicing": style.voicing.__dict__,
            "feel": style.feel.__dict__,
            "drum_patterns": style.drum_patterns.__dict__,
            "suggested_drum_kit": style.suggested_drum_kit,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

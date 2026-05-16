"""DrumPatternParser: Converts style DrumPatternRef labels to concrete DrumPattern steps."""

from __future__ import annotations

import random

from ..sequencer.drum_pattern import DRUM_TYPES, DrumPattern
from .styles import DrumPatternRef

# Label → list of active step indices (0-15) for a 16-step grid
LABEL_TO_STEPS: dict[str, list[int]] = {
    "4/4": [0, 4, 8, 12],
    "4/4_rolling": [0, 4, 8, 11, 12],
    "half_time": [0, 8],
    "half_time_3": [8],
    "continuous": [0, 2, 4, 6, 8, 10, 12, 14],
    "offbeat": [4, 12],
    "sparse": [4],
    "fast_8th": [0, 2, 4, 6, 8, 10, 12, 14],
    "swing": [5, 13],
    "fill": [12, 13, 14],
    "2_4": [4, 12],
    "downbeat": [0],
    "build": [4, 8, 10, 12, 13, 14, 15],
}

# Style templates: (kick_template, snare_template, hh_template)
STYLE_TEMPLATES: dict[str, tuple[list[int], list[int], list[int], list[int]]] = {
    "house": ([0, 4, 8, 12], [4, 12], [0, 2, 4, 6, 8, 10, 12, 14], [0, 4, 8, 12]),
    "techno": ([0, 1, 2, 3, 8, 9, 10, 11], [4, 12], [0, 3, 6, 9, 12, 15], [4, 12]),
    "trap": ([0, 6, 8, 14], [4, 12], [0, 2, 4, 6, 8, 10, 12, 14], [0, 4, 8, 12]),
    "dubstep": ([0, 8], [4], [0, 3, 6, 8, 10, 12, 15], []),
    "drum_bass": ([0, 3, 6, 9, 11, 14], [4, 12], [0, 1, 3, 4, 6, 7, 9, 10, 12, 13, 15], [4, 12]),
    "pop": ([0, 4, 8, 12], [4, 12], [0, 2, 4, 6, 8, 10, 12, 14], [4, 12]),
    "lofi": ([0, 5, 8], [4, 12], [0, 3, 6, 9, 12], []),
}


class DrumPatternGenerator:
    """Algorithmic drum pattern generator with style templates and complexity control."""

    @staticmethod
    def generate(style: str = "house", complexity: float = 0.5, steps: int = 16) -> DrumPattern:
        """Generate a complete drum pattern for the given style and complexity.

        Args:
            style: Style name (house, techno, trap, dubstep, drum_bass, pop, lofi).
            complexity: 0.0 (sparse) to 1.0 (dense fills).
            steps: Number of steps (default 16).

        Returns:
            A populated DrumPattern.
        """
        pattern = DrumPattern(name=f"Auto {style.title()}", steps=steps)
        parts = pattern.get_parts()

        kick_tmpl, snare_tmpl, hh_tmpl, clap_tmpl = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES["house"])

        # Kick: increasingly add ghost notes with complexity
        kick_steps = set(kick_tmpl)
        if complexity > 0.5:
            extra_kicks = [s for s in range(steps) if s not in kick_steps and s % 2 == 0]
            kick_steps.update(random.sample(extra_kicks, min(len(extra_kicks), int((complexity - 0.5) * 6))))

        # Snare: add occasional fills
        snare_steps = set(snare_tmpl)
        if complexity > 0.6:
            fill_candidates = [s for s in range(steps) if s not in snare_steps and s >= 12]
            snare_steps.update(random.sample(fill_candidates, min(len(fill_candidates), int((complexity - 0.5) * 3))))

        # Hi-hat: increase density
        hh_steps = set(hh_tmpl)
        if complexity < 0.3:
            hh_steps = {s for s in hh_steps if s % 4 == 0}
        elif complexity > 0.7:
            hh_steps.update(s for s in range(steps) if s % 2 == 1 and random.random() < complexity - 0.4)

        # Clap: layer on snares
        clap_steps = set(clap_tmpl)
        if complexity > 0.5:
            clap_steps.update(snare_steps)

        # Open hi-hat: sparse accents
        hh_open_steps: set[int] = set()
        if complexity > 0.3:
            hh_open_steps.add(random.choice([s for s in range(steps) if s % 2 == 0]))

        # Apply to pattern
        for s in kick_steps:
            if 0 <= s < steps:
                parts["kick"][s].active = True
                parts["kick"][s].velocity = 1.0

        for s in snare_steps:
            if 0 <= s < steps:
                parts["snare"][s].active = True
                parts["snare"][s].velocity = 0.9 if s >= 12 else 1.0

        for s in hh_steps:
            if 0 <= s < steps:
                parts["hh_closed"][s].active = True
                parts["hh_closed"][s].velocity = 0.7

        for s in clap_steps:
            if 0 <= s < steps:
                parts["clap"][s].active = True
                parts["clap"][s].velocity = 0.85

        for s in hh_open_steps:
            if 0 <= s < steps:
                parts["hh_open"][s].active = True
                parts["hh_open"][s].velocity = 0.8

        return pattern

    @staticmethod
    def get_available_styles() -> list[str]:
        return sorted(STYLE_TEMPLATES.keys())


class DrumPatternParser:
    """Parses DrumPatternRef string labels into concrete DrumPattern step grids."""

    @staticmethod
    def parse(drum_ref: DrumPatternRef, bpm: float = 120.0) -> DrumPattern:
        """Convert a style's DrumPatternRef into a playable DrumPattern.

        Args:
            drum_ref: Drum pattern reference from a style definition.
            bpm: Tempo (currently unused, reserved for tempo-dependent patterns).

        Returns:
            A DrumPattern with active steps set according to label mappings.
        """
        pattern = DrumPattern(name="Generated", steps=16)
        labels: dict[str, str] = {
            "kick": drum_ref.kick,
            "snare": drum_ref.snare,
            "hh_closed": drum_ref.hh_closed,
            "hh_open": drum_ref.hh_open,
            "clap": drum_ref.clap,
            "crash": drum_ref.crash,
            "tom_high": "",
            "tom_mid": "",
            "tom_low": "",
            "rim": "",
        }

        parts = pattern.get_parts()
        for drum_type in DRUM_TYPES:
            label = labels.get(drum_type, "")
            if not label:
                continue
            steps = LABEL_TO_STEPS.get(label, [])
            step_list = parts[drum_type]
            for idx in steps:
                if 0 <= idx < pattern.steps:
                    step_list[idx].active = True
                    step_list[idx].velocity = 1.0 if "fill" not in label else 0.85

        return pattern

    @staticmethod
    def get_available_labels() -> list[str]:
        return sorted(LABEL_TO_STEPS.keys())

    @staticmethod
    def label_steps(label: str) -> list[int]:
        return LABEL_TO_STEPS.get(label, [])

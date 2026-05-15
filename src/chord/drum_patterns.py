"""DrumPatternParser: Converts style DrumPatternRef labels to concrete DrumPattern steps."""

from __future__ import annotations

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

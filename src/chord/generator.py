"""ProgressionGenerator: EDM chord progression generation engine."""

from __future__ import annotations

import logging
import random

from .styles import ProgressionTemplate, StyleManager
from .theory import ChordData, ChordTheory, ProgressionData
from .voicing import VoicingEngine

logger = logging.getLogger(__name__)


class ProgressionGenerator:
    """Generates chord progressions based on EDM style rules."""

    style_manager: StyleManager

    def __init__(self, style_manager: StyleManager) -> None:
        self.style_manager = style_manager

    def generate(
        self,
        key: str,
        scale_type: str,
        style: str,
        bars: int = 8,
        complexity: float = 0.5,
        seed: int | None = None,
    ) -> ProgressionData:
        """Generate a complete chord progression.

        Algorithm:
        1. Get the StyleDefinition for the given style.
        2. Compute diatonic chords in the given key.
        3. Weighted-random select a progression template from style.common_progressions.
        4. For each degree: select chord quality → build chord → voice it.
        5. Apply feel parameters (humanize timing and velocity).
        """
        if seed is not None:
            random.seed(seed)

        style_def = self.style_manager.get(style)
        if style_def is None:
            logger.warning(f"Style '{style}' not found, using first available")
            available = self.style_manager.list_styles()
            if not available:
                raise ValueError("No styles loaded")
            style_def = self.style_manager.get(available[0])
            if style_def is None:
                raise ValueError(f"Failed to load style: {available[0]}")

        # Select progression template by weighted random choice
        templates = style_def.common_progressions
        if not templates:
            templates = [self._default_template()]

        weights = [t.weight for t in templates]
        total = sum(weights)
        if total == 0:
            weights = [1] * len(templates)
            total = len(templates)
        r = random.random() * total
        cumulative = 0.0
        selected_template = templates[0]
        for t, w in zip(templates, weights, strict=False):
            cumulative += w
            if r <= cumulative:
                selected_template = t
                break

        # Get scale degrees for key
        scale = ChordTheory.get_scale(key, scale_type)

        # Build chords
        chords: list[ChordData] = []
        prev_voiced: list[int] | None = None

        for degree in selected_template.degrees:
            idx = degree - 1
            if idx < 0 or idx >= len(scale.notes):
                continue

            root_note = scale.notes[idx]
            # Select quality from available qualities for this degree
            sd_use = next((sd for sd in style_def.scale_degrees if sd.degree == degree), None)
            if sd_use and sd_use.qualities:
                qualities = sd_use.qualities
                # complexity > 0.5 favors extended chords
                if complexity > 0.5:
                    extended = [q for q in qualities if len(q) > 3 and q not in ("maj", "min", "dim")]
                    if extended:
                        qualities = extended
                elif complexity < 0.3:
                    basic = [q for q in qualities if q in ("maj", "min", "dim")]
                    if basic:
                        qualities = basic
                quality = random.choice(qualities)
            else:
                quality = "maj"

            chord_tones = ChordTheory.get_chord_tones(root_note, quality)
            voiced = VoicingEngine.voice_chord(chord_tones, style_def.voicing, prev_voiced)
            prev_voiced = voiced

            chord = ChordData(root=root_note, quality=quality, notes=voiced)
            chords.append(chord)

        # Parse beats per bar from time signature string
        ts_str = style_def.time_signatures[0] if style_def.time_signatures else "4/4"
        beats_per_bar = int(ts_str.split("/")[0]) if "/" in ts_str else 4

        # Select rhythm pattern
        patterns = style_def.rhythm_patterns
        if not patterns:
            beats_per_chord = bars / max(len(chords), 1)
            for c in chords:
                c.duration = beats_per_chord
        else:
            pattern = random.choice(patterns)
            total_beats = sum(pattern.durations)
            raw_scale = (bars * beats_per_bar) / max(total_beats, 1)
            scale_factor = min(raw_scale, beats_per_bar * 0.75)
            for i, c in enumerate(chords):
                if i < len(pattern.durations):
                    c.duration = pattern.durations[i] * scale_factor

        # Calculate BPM from style range
        bpm = random.randint(style_def.tempo_range[0], style_def.tempo_range[1])

        return ProgressionData(
            chords=chords,
            key=key,
            scale_type=scale_type,
            style=style,
            bpm=float(bpm),
            time_signature=(4, 4),
        )

    def generate_multiple(
        self,
        key: str,
        scale_type: str,
        style: str,
        count: int = 8,
        bars: int = 8,
        complexity: float = 0.5,
        seed: int | None = None,
    ) -> list[ProgressionData]:
        """Generate multiple progression variants for browsing."""
        results: list[ProgressionData] = []
        base_seed = seed if seed is not None else random.randint(0, 2**31)
        for i in range(count):
            results.append(
                self.generate(
                    key=key, scale_type=scale_type, style=style, bars=bars, complexity=complexity, seed=base_seed + i
                )
            )
        return results

    @staticmethod
    def _default_template() -> ProgressionTemplate:
        return ProgressionTemplate(degrees=[1, 5, 6, 4], weight=5, name="Default")

"""VoicingEngine: chord voicing, inversions, and voice leading."""

from __future__ import annotations

import itertools
import logging

from .styles import VoicingRules

logger = logging.getLogger(__name__)

PENALTY_PARALLEL = 100


class VoicingEngine:
    """Handles chord voicing, inversions, and voice leading between chords."""

    @staticmethod
    def apply_inversion(chord_tones: list[int], inversion: str) -> list[int]:
        """Shift chord to root/first/second/third inversion."""
        if inversion == "root" or len(chord_tones) < 2:
            return sorted(chord_tones)
        if inversion == "first" and len(chord_tones) >= 3:
            return sorted(chord_tones[1:] + [chord_tones[0] + 12])
        if inversion == "second" and len(chord_tones) >= 3:
            return sorted(chord_tones[2:] + [chord_tones[0] + 12, chord_tones[1] + 12])
        if inversion == "third" and len(chord_tones) >= 4:
            return sorted(chord_tones[3:] + [chord_tones[0] + 12, chord_tones[1] + 12, chord_tones[2] + 12])
        return sorted(chord_tones)

    @staticmethod
    def apply_spread(chord_tones: list[int], spread: str) -> list[int]:
        """Apply voicing spread: close, open, drop2, drop3."""
        if spread == "close":
            return sorted(chord_tones)
        if spread == "open":
            voiced = sorted(chord_tones)
            for i in range(1, len(voiced), 2):
                voiced[i] += 12
            return voiced
        if spread == "drop2" and len(chord_tones) >= 4:
            voiced = sorted(chord_tones)
            voiced[1] -= 12
            voiced[2] += 12
            return sorted(voiced)
        if spread == "drop3" and len(chord_tones) >= 4:
            voiced = sorted(chord_tones)
            voiced[0] -= 12
            voiced[2] += 12
            return sorted(voiced)
        return sorted(chord_tones)

    @staticmethod
    def fit_to_range(chord_tones: list[int], voice_range: tuple[int, int]) -> list[int]:
        """Fold chord tones into the given MIDI note range."""
        low, high = voice_range
        result: list[int] = []
        for tone in sorted(chord_tones):
            note = tone % 12
            octave = tone // 12
            midi = note + octave * 12
            while midi < low:
                midi += 12
            while midi > high:
                midi -= 12
            result.append(max(low, min(high, midi)))
        return sorted(result)

    @staticmethod
    def voice_leading(current: list[int], next_chord: list[int]) -> list[int]:
        """Find the voicing of next_chord that minimizes total voice movement from current.

        Each voice in next_chord can be placed at any octave. Returns the best octave
        assignment as a list of MIDI note numbers.
        """
        if not current:
            return sorted(next_chord)

        n_current = len(current)
        n_next = len(next_chord)
        best_voicing: list[int] | None = None
        best_cost = float("inf")

        octave_options = [-12, 0, 12]
        for offsets in itertools.product(octave_options, repeat=n_next):
            candidate = [next_chord[i] + offsets[i] for i in range(n_next)]
            candidate.sort()

            # Match closest voices between current and candidate
            cost = 0.0
            for c in current:
                min_dist = min(abs(c - v) for v in candidate)
                cost += min_dist

            # Penalty for parallel fifths/octaves
            if n_current >= 2 and n_next >= 2:
                cost += VoicingEngine._parallel_penalty(current, candidate)

            if cost < best_cost:
                best_cost = cost
                best_voicing = candidate

        return best_voicing if best_voicing is not None else sorted(next_chord)

    @staticmethod
    def _parallel_penalty(a: list[int], b: list[int]) -> float:
        """Add penalty if there are parallel fifths or octaves between two chords."""
        penalty = 0.0
        for i in range(min(len(a), len(b)) - 1):
            for j in range(i + 1, min(len(a), len(b))):
                interval_a = abs(a[i] - a[j]) % 12
                interval_b = abs(b[i] - b[j]) % 12
                if interval_a == interval_b and interval_a in (0, 7):
                    penalty += PENALTY_PARALLEL
        return penalty

    @staticmethod
    def voice_chord(
        chord_tones: list[int],
        rules: VoicingRules,
        previous_chord: list[int] | None = None,
    ) -> list[int]:
        """Voice a chord according to the given rules.

        Applies inversions, spread, range constraints, and optional voice leading.
        Returns list of MIDI note numbers for the final voicing.
        """
        inversion = rules.preferred_inversions[0] if rules.preferred_inversions else "root"
        voiced = VoicingEngine.apply_inversion(chord_tones, inversion)
        voiced = VoicingEngine.apply_spread(voiced, rules.spread)
        voiced = VoicingEngine.fit_to_range(voiced, rules.voice_range)

        if previous_chord:
            voiced = VoicingEngine.voice_leading(previous_chord, voiced)

        # Ensure correct voice count
        while len(voiced) < rules.voice_count:
            voiced.append(voiced[-1] + 12 if voiced else 60)
        voiced = voiced[: rules.voice_count]

        return sorted(voiced)

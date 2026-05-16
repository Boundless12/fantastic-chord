"""ModMatrix: Serum-style modulation routing system.

Provides a flexible modulation matrix that routes multiple sources
(LFOs, envelopes, velocity, key track, etc.) to multiple destinations
(oscillator parameters, filter, effects, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Valid modulation sources
MOD_SOURCES: list[str] = [
    "lfo1",
    "lfo2",
    "amp_env",
    "filter_env",
    "velocity",
    "key_track",
    "mod_wheel",
    "random",
    "macro1",
    "macro2",
    "macro3",
    "macro4",
    "macro5",
    "macro6",
    "macro7",
    "macro8",
]

# Valid modulation destinations
MOD_DESTINATIONS: list[str] = [
    "osc1_position",
    "osc2_position",
    "osc1_warp",
    "osc2_warp",
    "cutoff",
    "resonance",
    "pan",
    "volume",
    "osc1_level",
    "osc2_level",
    "noise_level",
    "sub_level",
    "lfo1_rate",
    "lfo2_rate",
]


@dataclass
class ModSlot:
    """A single modulation routing: source -> destination * amount."""

    source: str = "lfo1"
    destination: str = "cutoff"
    amount: float = 0.0  # bipolar: -1.0 to 1.0

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "destination": self.destination, "amount": self.amount}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModSlot:
        return cls(
            source=data.get("source", "lfo1"),
            destination=data.get("destination", "cutoff"),
            amount=data.get("amount", 0.0),
        )


class ModMatrix:
    """Evaluates modulation sources and computes per-destination modulation values."""

    slots: list[ModSlot]

    def __init__(self, num_slots: int = 16) -> None:
        self.slots = [ModSlot() for _ in range(num_slots)]

    def set_slot(self, index: int, source: str, destination: str, amount: float) -> None:
        if 0 <= index < len(self.slots):
            self.slots[index] = ModSlot(source=source, destination=destination, amount=amount)

    def get_slot(self, index: int) -> ModSlot | None:
        if 0 <= index < len(self.slots):
            return self.slots[index]
        return None

    def process(self, context: dict[str, float]) -> dict[str, float]:
        """Evaluate all mod slots and return a dict of destination -> total modulation value.

        Args:
            context: Dict with keys matching MOD_SOURCES, each value is a float
                     representing the current modulation source value (typically -1..1).

        Returns:
            Dict mapping destination strings to their total modulation amount (typically -1..1).
        """
        result: dict[str, float] = {}
        for slot in self.slots:
            if abs(slot.amount) < 0.001:
                continue
            src_val = context.get(slot.source, 0.0)
            dest = slot.destination
            result[dest] = result.get(dest, 0.0) + src_val * slot.amount
        return {k: max(-1.0, min(1.0, v)) for k, v in result.items()}

    def clear(self) -> None:
        for slot in self.slots:
            slot.amount = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"slots": [s.to_dict() for s in self.slots]}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ModMatrix:
        matrix = cls()
        if data and "slots" in data:
            for i, slot_data in enumerate(data["slots"]):
                if i < len(matrix.slots):
                    matrix.slots[i] = ModSlot.from_dict(slot_data)
        return matrix

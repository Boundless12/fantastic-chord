"""DrumSequencer: Transport-synced step sequencer for drum patterns."""

from __future__ import annotations

from dataclasses import dataclass

from .drum_pattern import DRUM_TYPES, DrumPattern
from .transport import Transport


@dataclass
class TriggerEvent:
    """A drum hit scheduled at the current block."""

    drum_type: str
    velocity: float
    pan: float = 0.0


class DrumSequencer:
    """Step-sequencer that reads a DrumPattern and emits TriggerEvents.

    Called once per audio callback block. Detects step edge transitions
    from transport position and returns triggers for newly active steps.
    """

    pattern: DrumPattern
    _transport: Transport
    _last_step_index: int
    _step_duration_beats: float

    def __init__(self, transport: Transport) -> None:
        self._transport = transport
        self.pattern = DrumPattern.empty()
        self._last_step_index = -1
        self._step_duration_beats = 4.0 / self.pattern.steps

    def set_pattern(self, pattern: DrumPattern) -> None:
        self.pattern = pattern
        self._step_duration_beats = 4.0 / max(pattern.steps, 1)
        self._last_step_index = -1

    def process(self) -> list[TriggerEvent]:
        """Check transport position and emit triggers for newly entered steps.

        Returns:
            List of TriggerEvent for drum hits starting at this step edge.
            Empty list if transport is not playing or no step transition occurred.
        """
        if not self._transport.is_playing:
            return []

        position_beats = self._transport.position_beats
        steps = self.pattern.steps
        step_dur = self._step_duration_beats

        # Calculate current step index with wraparound
        step_index = int(position_beats / step_dur) % steps

        if step_index == self._last_step_index:
            return []

        self._last_step_index = step_index

        triggers: list[TriggerEvent] = []
        parts = self.pattern.get_parts()

        for drum_type in DRUM_TYPES:
            step_list = parts[drum_type]
            step = step_list[step_index]
            if step.active:
                # Pan: open hi-hat slightly right, crash center, rest center
                pan = 0.0
                if drum_type == "hh_open":
                    pan = 0.25
                elif drum_type == "crash":
                    pan = 0.1

                triggers.append(
                    TriggerEvent(
                        drum_type=drum_type,
                        velocity=step.velocity,
                        pan=pan,
                    )
                )

        return triggers

    def reset(self) -> None:
        self._last_step_index = -1

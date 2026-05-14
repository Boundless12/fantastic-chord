"""Tests for DrumSequencer — step edge detection and trigger generation."""

import pytest

from src.sequencer.drum_pattern import DrumPattern
from src.sequencer.drum_sequencer import DrumSequencer
from src.sequencer.transport import Transport


@pytest.fixture
def transport() -> Transport:
    t = Transport()
    t.bpm = 120.0
    t.is_playing = True
    return t


@pytest.fixture
def sequencer(transport: Transport) -> DrumSequencer:
    return DrumSequencer(transport)


def make_four_on_floor() -> DrumPattern:
    p = DrumPattern(name="4OTF", steps=16)
    p.kick[0].active = True
    p.kick[4].active = True
    p.kick[8].active = True
    p.kick[12].active = True
    return p


def test_no_triggers_when_not_playing(sequencer: DrumSequencer, transport: Transport) -> None:
    sequencer.set_pattern(make_four_on_floor())
    transport.is_playing = False
    triggers = sequencer.process()
    assert len(triggers) == 0


def test_triggers_at_step_boundaries(sequencer: DrumSequencer, transport: Transport) -> None:
    sequencer.set_pattern(make_four_on_floor())
    # In DrumSequencer, process() reads transport.position_beats directly.
    # Set position to trigger step 0.
    transport.position_beats = 0.0
    triggers = sequencer.process()
    assert len(triggers) == 1
    assert triggers[0].drum_type == "kick"
    assert triggers[0].velocity == 1.0


def test_no_duplicate_triggers(sequencer: DrumSequencer, transport: Transport) -> None:
    sequencer.set_pattern(make_four_on_floor())
    transport.position_beats = 0.0
    triggers1 = sequencer.process()
    assert len(triggers1) == 1

    # Same position → no new triggers
    triggers2 = sequencer.process()
    assert len(triggers2) == 0


def test_triggers_on_next_step(sequencer: DrumSequencer, transport: Transport) -> None:
    sequencer.set_pattern(make_four_on_floor())
    # Step 0
    transport.position_beats = 0.0
    sequencer.process()
    # Move to step 4 (beat 2)
    transport.position_beats = 1.0  # step 4 = 4 * 0.25 beats
    triggers = sequencer.process()
    assert len(triggers) == 1
    assert triggers[0].drum_type == "kick"


def test_wraparound(sequencer: DrumSequencer, transport: Transport) -> None:
    sequencer.set_pattern(make_four_on_floor())
    transport.position_beats = 3.75  # step 15
    sequencer.process()
    # Wrap to step 0 (next bar)
    transport.position_beats = 4.0
    triggers = sequencer.process()
    assert len(triggers) == 1
    assert triggers[0].drum_type == "kick"


def test_multiple_triggers_at_same_step(sequencer: DrumSequencer, transport: Transport) -> None:
    p = DrumPattern(name="Multi", steps=16)
    p.kick[0].active = True
    p.snare[0].active = True
    p.hh_closed[0].active = True
    sequencer.set_pattern(p)

    transport.position_beats = 0.0
    triggers = sequencer.process()
    trigger_types = {t.drum_type for t in triggers}
    assert trigger_types == {"kick", "snare", "hh_closed"}


def test_reset(sequencer: DrumSequencer, transport: Transport) -> None:
    sequencer.set_pattern(make_four_on_floor())
    transport.position_beats = 0.0
    sequencer.process()

    sequencer.reset()
    # After reset, same position should trigger again
    triggers = sequencer.process()
    assert len(triggers) == 1


def test_inactive_steps_produce_no_triggers(sequencer: DrumSequencer, transport: Transport) -> None:
    p = make_four_on_floor()
    # Steps 1, 2, 3 should be empty
    sequencer.set_pattern(p)

    transport.position_beats = 0.25  # step 1
    triggers = sequencer.process()
    assert len(triggers) == 0

    transport.position_beats = 0.5  # step 2
    triggers = sequencer.process()
    assert len(triggers) == 0


def test_set_pattern_resets_state(sequencer: DrumSequencer, transport: Transport) -> None:
    sequencer.set_pattern(make_four_on_floor())
    transport.position_beats = 0.0
    sequencer.process()  # triggers step 0

    # Set a new pattern — first process() will fire at current step
    new_pattern = DrumPattern(name="New", steps=16)
    new_pattern.kick[0].active = True
    sequencer.set_pattern(new_pattern)

    triggers = sequencer.process()
    assert len(triggers) == 1  # re-fires at step 0 after pattern change
    assert triggers[0].drum_type == "kick"

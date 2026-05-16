"""Tests for PianoRollSequencer."""

import pytest

from src.sequencer.pattern import Note, Pattern
from src.sequencer.piano_roll_sequencer import PianoRollSequencer
from src.sequencer.transport import Transport


class MockEngine:
    """Minimal mock for AudioEngine direct note methods."""

    def __init__(self) -> None:
        self.note_ons: list[tuple[int, int]] = []
        self.note_offs: list[int] = []

    def _note_on_direct(self, note: int, velocity: int, track_index: int = 0) -> None:
        self.note_ons.append((note, velocity))

    def _note_off_direct(self, note: int, track_index: int = 0) -> None:
        self.note_offs.append(note)


class TestPianoRollSequencer:
    @pytest.fixture
    def transport(self) -> Transport:
        return Transport()

    @pytest.fixture
    def sequencer(self, transport: Transport) -> PianoRollSequencer:
        return PianoRollSequencer(transport)

    @pytest.fixture
    def engine(self) -> MockEngine:
        return MockEngine()

    def test_constructs(self, sequencer: PianoRollSequencer) -> None:
        assert sequencer.patterns == {}
        assert sequencer._enabled is True
        assert sequencer._active_notes == {}

    def test_process_no_pattern(self, sequencer: PianoRollSequencer, engine: MockEngine) -> None:
        sequencer.process(engine)  # type: ignore[arg-type]
        assert len(engine.note_ons) == 0
        assert len(engine.note_offs) == 0

    def test_process_disabled(self, sequencer: PianoRollSequencer, engine: MockEngine) -> None:
        pattern = Pattern(notes=[Note(pitch=60, velocity=100, start_time=0.0, duration=1.0)])
        sequencer.set_pattern(0, pattern)
        sequencer.set_enabled(False)
        sequencer.process(engine)  # type: ignore[arg-type]
        assert len(engine.note_ons) == 0

    def test_process_note_on(self, sequencer: PianoRollSequencer, engine: MockEngine, transport: Transport) -> None:
        pattern = Pattern(notes=[Note(pitch=60, velocity=100, start_time=0.0, duration=1.0)])
        sequencer.set_pattern(0, pattern)
        transport.is_playing = True
        transport.position_beats = 1.0  # advance past note start

        sequencer.process(engine)  # type: ignore[arg-type]
        assert len(engine.note_ons) == 1
        assert engine.note_ons[0] == (60, 100)

    def test_process_note_off(self, sequencer: PianoRollSequencer, engine: MockEngine, transport: Transport) -> None:
        pattern = Pattern(notes=[Note(pitch=60, velocity=100, start_time=0.0, duration=1.0)])
        sequencer.set_pattern(0, pattern)
        transport.is_playing = True

        # First advance past note start
        transport.position_beats = 0.5
        sequencer.process(engine)  # type: ignore[arg-type]
        assert len(engine.note_ons) == 1

        # Then advance past note end
        transport.position_beats = 1.5
        sequencer.process(engine)  # type: ignore[arg-type]
        assert len(engine.note_offs) == 1
        assert engine.note_offs[0] == 60

    def test_reset_clears_active_notes(
        self, sequencer: PianoRollSequencer, engine: MockEngine, transport: Transport
    ) -> None:
        pattern = Pattern(notes=[Note(pitch=60, velocity=100, start_time=0.0, duration=1.0)])
        sequencer.set_pattern(0, pattern)
        transport.position_beats = 0.1
        sequencer.process(engine)  # type: ignore[arg-type]

        assert len(sequencer._active_notes) == 1

        sequencer.reset()
        assert len(sequencer._active_notes) == 0
        assert sequencer._last_position_beats == 0.0

    def test_no_retrigger_same_note(
        self, sequencer: PianoRollSequencer, engine: MockEngine, transport: Transport
    ) -> None:
        pattern = Pattern(
            notes=[
                Note(pitch=60, velocity=100, start_time=0.0, duration=2.0),
            ]
        )
        sequencer.set_pattern(0, pattern)
        transport.position_beats = 0.5
        sequencer.process(engine)  # type: ignore[arg-type]
        assert len(engine.note_ons) == 1

        # Advance but don't cross note end
        transport.position_beats = 1.0
        sequencer.process(engine)  # type: ignore[arg-type]
        assert len(engine.note_ons) == 1  # no new note-on

    def test_multiple_notes(self, sequencer: PianoRollSequencer, engine: MockEngine, transport: Transport) -> None:
        pattern = Pattern(
            notes=[
                Note(pitch=60, velocity=100, start_time=0.0, duration=1.0),
                Note(pitch=64, velocity=90, start_time=0.0, duration=1.0),
                Note(pitch=67, velocity=80, start_time=0.0, duration=1.0),
            ]
        )
        sequencer.set_pattern(0, pattern)
        transport.position_beats = 0.3
        sequencer.process(engine)  # type: ignore[arg-type]

        assert len(engine.note_ons) == 3

    def test_set_enabled_clears_active(
        self, sequencer: PianoRollSequencer, engine: MockEngine, transport: Transport
    ) -> None:
        pattern = Pattern(notes=[Note(pitch=60, velocity=100, start_time=0.0, duration=1.0)])
        sequencer.set_pattern(0, pattern)
        transport.position_beats = 0.1
        sequencer.process(engine)  # type: ignore[arg-type]
        assert len(sequencer._active_notes) == 1

        sequencer.set_enabled(False)
        assert len(sequencer._active_notes) == 0

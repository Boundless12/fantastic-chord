"""Tests for DrumPattern, DrumPatternParser, and GM drum map."""

from src.chord.drum_patterns import DrumPatternParser
from src.chord.styles import DrumPatternRef
from src.sequencer.drum_pattern import (
    DRUM_TYPES,
    GM_DRUM_MAP,
    GM_DRUM_REVERSE,
    DrumPattern,
    DrumStep,
)


def test_gm_map_consistency() -> None:
    """Every drum type maps to a unique pitch and back."""
    pitches = set()
    for drum_type in DRUM_TYPES:
        pitch = GM_DRUM_MAP[drum_type]
        assert pitch not in pitches, f"Duplicate pitch {pitch} for {drum_type}"
        pitches.add(pitch)
        assert GM_DRUM_REVERSE[pitch] == drum_type


def test_empty_pattern() -> None:
    p = DrumPattern.empty()
    assert p.name == "Empty"
    assert p.steps == 16
    parts = p.get_parts()
    for drum_type in DRUM_TYPES:
        step_list = parts[drum_type]
        assert len(step_list) == 16
        assert all(not s.active for s in step_list)


def test_drum_step_defaults() -> None:
    s = DrumStep()
    assert not s.active
    assert s.velocity == 1.0
    assert s.micro_offset == 0.0
    assert not s.flam


def test_pattern_to_pattern_roundtrip() -> None:
    drum = DrumPattern(name="Test", steps=16)
    drum.kick[0].active = True
    drum.kick[0].velocity = 0.9
    drum.kick[8].active = True
    drum.snare[4].active = True
    drum.snare[12].active = True
    drum.hh_closed[0].active = True
    drum.hh_closed[2].active = True
    drum.hh_closed[4].active = True
    drum.hh_closed[6].active = True

    pattern = drum.to_pattern(bpm=120.0)
    assert pattern.name == "Test"
    assert len(pattern.notes) == 8
    assert pattern.length_beats == 4.0

    # Round-trip
    restored = DrumPattern.from_pattern(pattern, bpm=120.0)
    assert restored.kick[0].active
    assert restored.kick[8].active
    assert restored.snare[4].active
    assert restored.snare[12].active
    assert restored.hh_closed[0].active
    assert restored.hh_closed[2].active


def test_to_pattern_bpm_affects_timing() -> None:
    drum = DrumPattern(name="Tempo", steps=16)
    drum.kick[0].active = True

    pattern_120 = drum.to_pattern(bpm=120.0)
    pattern_60 = drum.to_pattern(bpm=60.0)

    # 60 BPM = half speed → 16th notes are twice as long
    note_120 = pattern_120.notes[0]
    note_60 = pattern_60.notes[0]
    assert note_60.duration > note_120.duration * 1.5


def test_get_parts_returns_all_types() -> None:
    p = DrumPattern.empty()
    parts = p.get_parts()
    for t in DRUM_TYPES:
        assert t in parts
        assert len(parts[t]) == 16


# -- DrumPatternParser tests --


def test_parser_4_4_kick() -> None:
    ref = DrumPatternRef(kick="4/4")
    pattern = DrumPatternParser.parse(ref)

    expected_active = {0, 4, 8, 12}
    for i in range(16):
        assert pattern.kick[i].active == (i in expected_active), f"Step {i} mismatch"


def test_parser_half_time() -> None:
    ref = DrumPatternRef(kick="half_time")
    pattern = DrumPatternParser.parse(ref)

    expected_active = {0, 8}
    for i in range(16):
        assert pattern.kick[i].active == (i in expected_active), f"Step {i} mismatch"


def test_parser_offbeat_snare() -> None:
    ref = DrumPatternRef(snare="offbeat")
    pattern = DrumPatternParser.parse(ref)

    expected_active = {4, 12}
    for i in range(16):
        assert pattern.snare[i].active == (i in expected_active), f"Step {i} mismatch"


def test_parser_2_4_clap() -> None:
    ref = DrumPatternRef(clap="2_4")
    pattern = DrumPatternParser.parse(ref)

    expected_active = {4, 12}
    for i in range(16):
        assert pattern.clap[i].active == (i in expected_active), f"Step {i} mismatch"


def test_parser_continuous_hh() -> None:
    ref = DrumPatternRef(hh_closed="continuous")
    pattern = DrumPatternParser.parse(ref)

    expected_active = {0, 2, 4, 6, 8, 10, 12, 14}
    for i in range(16):
        assert pattern.hh_closed[i].active == (i in expected_active), f"Step {i} mismatch"


def test_parser_fast_8th_hh() -> None:
    ref = DrumPatternRef(hh_closed="fast_8th")
    pattern = DrumPatternParser.parse(ref)

    expected_active = {0, 2, 4, 6, 8, 10, 12, 14}
    for i in range(16):
        assert pattern.hh_closed[i].active == (i in expected_active), f"Step {i} mismatch"


def test_parser_empty_label_means_no_hits() -> None:
    ref = DrumPatternRef()  # all empty strings
    pattern = DrumPatternParser.parse(ref)

    parts = pattern.get_parts()
    for drum_type in DRUM_TYPES:
        assert all(not s.active for s in parts[drum_type]), f"{drum_type} should be empty"


def test_parser_full_house_pattern() -> None:
    """Simulate a typical house pattern: kick 4/4, snare offbeat, hh continuous, clap 2/4."""
    ref = DrumPatternRef(kick="4/4", snare="offbeat", hh_closed="continuous", clap="2_4")
    pattern = DrumPatternParser.parse(ref)

    assert pattern.kick[0].active and pattern.kick[4].active and pattern.kick[8].active and pattern.kick[12].active
    assert pattern.snare[4].active and pattern.snare[12].active
    assert pattern.hh_closed[0].active and pattern.hh_closed[2].active
    assert pattern.clap[4].active and pattern.clap[12].active


def test_parser_get_available_labels() -> None:
    labels = DrumPatternParser.get_available_labels()
    assert "4/4" in labels
    assert "offbeat" in labels
    assert "half_time" in labels
    assert "continuous" in labels
    assert len(labels) >= 10

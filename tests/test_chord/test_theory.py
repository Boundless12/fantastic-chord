"""Tests for ChordTheory music theory primitives."""

from src.chord.theory import (
    CHORD_QUALITIES,
    NOTE_NAMES,
    SCALE_PATTERNS,
    ChordData,
    ChordTheory,
    ProgressionData,
)


class TestChordTheory:
    def test_note_name_to_midi_c4(self) -> None:
        assert ChordTheory.note_name_to_midi("C4") == 60

    def test_note_name_to_midi_sharp(self) -> None:
        assert ChordTheory.note_name_to_midi("C#4") == 61

    def test_midi_to_note_name(self) -> None:
        assert ChordTheory.midi_to_note_name(60) == "C4"
        assert ChordTheory.midi_to_note_name(69) == "A4"

    def test_get_scale_major_c(self) -> None:
        scale = ChordTheory.get_scale("C", "major")
        assert scale.root == 48  # octave 3
        assert scale.scale_type == "major"
        assert len(scale.notes) == 7
        assert scale.notes[0] == 48  # C

    def test_get_scale_dorian_d(self) -> None:
        scale = ChordTheory.get_scale("D", "dorian")
        assert scale.root == 50  # octave 3
        assert len(scale.notes) == 7

    def test_get_chord_tones_major(self) -> None:
        tones = ChordTheory.get_chord_tones(60, "maj")
        assert tones == [60, 64, 67]

    def test_get_chord_tones_minor(self) -> None:
        tones = ChordTheory.get_chord_tones(60, "min")
        assert tones == [60, 63, 67]

    def test_get_chord_tones_maj7(self) -> None:
        tones = ChordTheory.get_chord_tones(60, "maj7")
        assert tones == [60, 64, 67, 71]

    def test_get_chord_tones_dom7(self) -> None:
        tones = ChordTheory.get_chord_tones(60, "dom7")
        assert tones == [60, 64, 67, 70]

    def test_diatonic_chords_c_major(self) -> None:
        chords = ChordTheory.diatonic_chords("C", "major")
        assert 1 in chords
        assert chords[1][0] == 48  # C in octave 3
        assert chords[5][0] == 55  # G

    def test_chord_to_symbol(self) -> None:
        assert ChordTheory.chord_to_symbol(60, "maj") == "C"
        assert ChordTheory.chord_to_symbol(60, "min") == "Cm"
        assert ChordTheory.chord_to_symbol(61, "maj") == "C#"

    def test_progression_to_symbols(self) -> None:
        prog = ProgressionData(
            chords=[
                ChordData(root=60, quality="maj7", notes=[60, 64, 67, 71], duration=1.0),
                ChordData(root=65, quality="min7", notes=[65, 68, 71, 74], duration=1.0),
            ],
            key="C",
            scale_type="major",
            style="house",
            bpm=120.0,
        )
        symbols = ChordTheory.progression_to_symbols(prog)
        assert len(symbols) == 2
        assert "C" in symbols[0]
        assert "F" in symbols[1]

    def test_all_scales_valid(self) -> None:
        for name, pattern in SCALE_PATTERNS.items():
            assert sum(pattern) == 12, f"Scale {name} doesn't sum to 12"

    def test_all_qualities_valid(self) -> None:
        for name, _ in CHORD_QUALITIES.items():
            tones = ChordTheory.get_chord_tones(60, name)
            assert tones[0] == 60

    def test_note_names_count(self) -> None:
        assert len(NOTE_NAMES) == 12
        assert "C" in NOTE_NAMES
        assert "B" in NOTE_NAMES

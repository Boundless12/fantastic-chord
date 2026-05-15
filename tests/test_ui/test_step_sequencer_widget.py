"""Tests for StepSequencerWidget and StepButton."""

import pytest
from PySide6.QtWidgets import QApplication

from src.sequencer.drum_pattern import DRUM_TYPES, DrumPattern
from src.ui.step_sequencer_widget import StepButton, StepSequencerWidget


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestStepButton:
    def test_constructs_default(self, qapp: QApplication) -> None:
        btn = StepButton()
        assert btn is not None
        assert not btn.isChecked()

    def test_set_active_toggles(self, qapp: QApplication) -> None:
        btn = StepButton()
        btn.set_active(True)
        assert btn.isChecked()
        btn.set_active(False)
        assert not btn.isChecked()

    def test_mark_current_does_not_crash(self, qapp: QApplication) -> None:
        btn = StepButton()
        btn.mark_current(True)
        btn.mark_current(False)

    def test_set_color_updates(self, qapp: QApplication) -> None:
        btn = StepButton("#ff0000")
        assert btn._color == "#ff0000"
        btn.set_color("#00ff00")
        assert btn._color == "#00ff00"


class TestStepSequencerWidget:
    @pytest.fixture
    def widget(self, qapp: QApplication) -> StepSequencerWidget:
        return StepSequencerWidget()

    def test_constructs(self, widget: StepSequencerWidget) -> None:
        assert widget is not None
        assert len(widget._buttons) == 10

    def test_all_drum_types_have_buttons(self, widget: StepSequencerWidget) -> None:
        for drum_type in DRUM_TYPES:
            assert drum_type in widget._buttons
            assert len(widget._buttons[drum_type]) == 16

    def test_get_pattern_returns_empty_by_default(self, widget: StepSequencerWidget) -> None:
        pattern = widget.get_pattern()
        assert isinstance(pattern, DrumPattern)
        parts = pattern.get_parts()
        for step_list in parts.values():
            assert all(not s.active for s in step_list)

    def test_set_pattern_populates_buttons(self, widget: StepSequencerWidget) -> None:
        pattern = DrumPattern.empty()
        pattern.kick[0].active = True
        pattern.kick[4].active = True
        pattern.snare[4].active = True
        pattern.snare[12].active = True
        pattern.hh_closed[0].active = True
        pattern.hh_closed[2].active = True
        pattern.hh_closed[4].active = True

        widget.set_pattern(pattern)
        result = widget.get_pattern()
        assert result.kick[0].active
        assert result.kick[4].active
        assert result.snare[4].active
        assert result.snare[12].active
        assert result.hh_closed[0].active
        assert result.hh_closed[2].active
        assert result.hh_closed[4].active

    def test_pattern_changed_emitted_on_toggle(self, widget: StepSequencerWidget) -> None:
        changes: list[None] = []
        widget.pattern_changed.connect(lambda: changes.append(None))

        # Simulate toggling a step button
        widget._buttons["kick"][0].set_active(True)
        assert len(changes) >= 1

    def test_set_current_step_updates_highlight(self, widget: StepSequencerWidget) -> None:
        widget.set_current_step(3)
        assert widget._current_step == 3

        widget.set_current_step(-1)
        assert widget._current_step == -1

    def test_clear_removes_all_activations(self, widget: StepSequencerWidget) -> None:
        widget._buttons["kick"][0].set_active(True)
        widget._buttons["snare"][4].set_active(True)
        widget._buttons["hh_closed"][8].set_active(True)

        widget.clear()
        pattern = widget.get_pattern()
        for step_list in pattern.get_parts().values():
            assert all(not s.active for s in step_list)

    def test_button_count_per_drum_type(self, widget: StepSequencerWidget) -> None:
        for drum_type in DRUM_TYPES:
            assert len(widget._buttons[drum_type]) == 16

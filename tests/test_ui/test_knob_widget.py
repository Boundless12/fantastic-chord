"""Tests for KnobWidget enhancements: display_map, set_range, context_menu."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from src.ui.knob_widget import KnobWidget


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_display_map_formatting(qapp: QApplication) -> None:
    knob = KnobWidget(display_name="Wave", display_map=["sine", "saw", "square", "tri"], step=0.333)
    knob.set_value(0.0, emit=False)
    assert "sine" in knob._format_value()
    knob.set_value(0.333, emit=False)
    assert "saw" in knob._format_value()


def test_display_map_two_items(qapp: QApplication) -> None:
    knob = KnobWidget(display_name="Toggle", display_map=["Off", "On"], step=1.0, default_value=1.0)
    knob.set_value(1.0, emit=False)
    assert knob._format_value() == "On"
    knob.set_value(0.0, emit=False)
    assert knob._format_value() == "Off"


def test_set_range_unipolar(qapp: QApplication) -> None:
    knob = KnobWidget(display_name="Range", default_value=2.0, step=1.0)
    knob.set_range(2, 24)
    assert knob.value() == 2.0
    knob.set_value(5.0, emit=False)
    assert knob.value() == 5.0
    knob.set_value(30.0, emit=False)  # Should clamp
    assert knob.value() == 24.0
    knob.set_value(0.0, emit=False)
    assert knob.value() == 2.0  # Clamped to min


def test_set_range_bipolar(qapp: QApplication) -> None:
    knob = KnobWidget(display_name="Oct", default_value=0.0, value_format="int", bipolar=True, step=1.0)
    knob.set_range(-3, 3)
    knob.set_value(-3.0, emit=False)
    assert knob.value() == -3.0
    knob.set_value(3.0, emit=False)
    assert knob.value() == 3.0
    knob.set_value(-5.0, emit=False)
    assert knob.value() == -3.0  # Clamped


def test_context_menu_signal(qapp: QApplication) -> None:
    knob = KnobWidget(display_name="Test")
    received: list[bool] = []

    def on_menu() -> None:
        received.append(True)

    knob.context_menu_requested.connect(on_menu)

    # Simulate right-click
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        knob.rect().center(),
        Qt.MouseButton.RightButton,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
    )
    knob.mousePressEvent(event)
    assert len(received) == 1


def test_integer_stepping(qapp: QApplication) -> None:
    knob = KnobWidget(display_name="Int", step=1.0, default_value=0.0)
    knob.set_value(0.7, emit=False)
    assert knob.value() == 1.0
    knob.set_value(0.3, emit=False)
    assert knob.value() == 0.0


def test_value_changed_signal(qapp: QApplication) -> None:
    knob = KnobWidget(display_name="Test", default_value=0.5)
    values: list[float] = []
    knob.value_changed.connect(lambda v: values.append(v))
    knob.set_value(0.75)
    assert len(values) == 1
    assert values[0] == 0.75


def test_default_reset(qapp: QApplication) -> None:
    knob = KnobWidget(display_name="Test", default_value=0.5)
    knob.set_value(0.8, emit=False)
    knob.set_value(knob._default_value)
    assert knob.value() == 0.5

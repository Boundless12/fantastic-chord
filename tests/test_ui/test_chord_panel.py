"""Tests for ChordPanel."""

import pytest
from PySide6.QtWidgets import QApplication

from src.ui.chord_panel import ChordPanel


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestChordPanel:
    @pytest.fixture
    def panel(self, qapp: QApplication) -> ChordPanel:
        return ChordPanel()

    def test_constructs(self, panel: ChordPanel) -> None:
        assert panel is not None
        assert panel._engine is None
        assert panel._generator is not None

    def test_key_combo_has_all_notes(self, panel: ChordPanel) -> None:
        assert panel._key_combo.count() == 12
        assert panel._key_combo.currentText() == "C"

    def test_scale_combo_has_scales(self, panel: ChordPanel) -> None:
        assert panel._scale_combo.count() >= 9

    def test_style_combo_has_styles(self, panel: ChordPanel) -> None:
        assert panel._style_combo.count() >= 10

    def test_complexity_slider_range(self, panel: ChordPanel) -> None:
        assert panel._complexity_slider.minimum() == 0
        assert panel._complexity_slider.maximum() == 100
        assert panel._complexity_slider.value() == 50

    def test_bars_spin_range(self, panel: ChordPanel) -> None:
        assert panel._bars_spin.minimum() == 1
        assert panel._bars_spin.maximum() == 16
        assert panel._bars_spin.value() == 8

    def test_generate_populates_list(self, panel: ChordPanel) -> None:
        initial_count = panel._list.count()
        assert initial_count == 0

        panel._on_generate()
        assert panel._list.count() == 8
        assert len(panel._progressions) == 8

    def test_clear_removes_all(self, panel: ChordPanel) -> None:
        panel._on_generate()
        assert panel._list.count() == 8

        panel._on_clear()
        assert panel._list.count() == 0
        assert len(panel._progressions) == 0

    def test_random_seed_disables_spin(self, panel: ChordPanel) -> None:
        panel._random_seed_check.setChecked(True)
        assert not panel._seed_spin.isEnabled()

        panel._random_seed_check.setChecked(False)
        assert panel._seed_spin.isEnabled()

    def test_generate_with_specific_key_and_style(self, panel: ChordPanel) -> None:
        panel._key_combo.setCurrentText("D")
        panel._style_combo.setCurrentIndex(0)
        panel._bars_spin.setValue(4)

        panel._on_generate()
        assert panel._list.count() == 8

        # First item should have chord symbols
        item = panel._list.item(0)
        text = item.text()
        assert "[" in text
        assert "BPM" in text

    def test_progression_selected_signal(self, panel: ChordPanel) -> None:
        panels: list[int] = []
        panel.progression_selected.connect(lambda i: panels.append(i))

        panel._on_generate()
        item = panel._list.item(2)
        panel._on_item_clicked(item)

        assert panels == [2]

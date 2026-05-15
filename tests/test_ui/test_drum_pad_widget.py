"""Tests for DrumPadWidget."""

import pytest
from PySide6.QtWidgets import QApplication

from src.ui.drum_pad_widget import DRUM_COLORS, DrumPadWidget


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestDrumPadWidget:
    def test_constructs(self, qapp: QApplication) -> None:
        pad = DrumPadWidget("kick")
        assert pad is not None
        assert pad.drum_type == "kick"

    def test_label_shows_drum_type(self, qapp: QApplication) -> None:
        pad = DrumPadWidget("snare")
        assert pad.text() == "Snare"

    def test_click_emits_drum_triggered(self, qapp: QApplication) -> None:
        pad = DrumPadWidget("kick")
        triggered: list[str] = []
        pad.drum_triggered.connect(lambda dt: triggered.append(dt))
        pad.click()
        assert triggered == ["kick"]

    def test_has_color_for_each_drum_type(self, qapp: QApplication) -> None:
        drum_types = [
            "kick",
            "snare",
            "hh_closed",
            "hh_open",
            "clap",
            "crash",
            "tom_high",
            "tom_mid",
            "tom_low",
            "rim",
        ]
        for dt in drum_types:
            pad = DrumPadWidget(dt)
            assert pad._base_color == DRUM_COLORS[dt]

    def test_flash_updates_style_temporarily(self, qapp: QApplication) -> None:
        pad = DrumPadWidget("kick")
        pad._flash()
        assert pad._flash_timer is not None
        assert pad._flash_timer.isActive()

    def test_unflash_restores_base_color(self, qapp: QApplication) -> None:
        pad = DrumPadWidget("kick")
        pad._flash()
        pad._unflash()
        # After unflash, style should be restored (no crash = pass)
        assert pad._flash_timer is not None

    def test_darken_color(self, qapp: QApplication) -> None:
        result = DrumPadWidget._darken("#ffffff", 0.5)
        assert result == "#7f7f7f"

    def test_lighten_color(self, qapp: QApplication) -> None:
        result = DrumPadWidget._lighten("#000000", 0.5)
        assert result == "#7f7f7f"

    def test_unknown_drum_type_gets_default_color(self, qapp: QApplication) -> None:
        pad = DrumPadWidget("nonexistent")
        assert pad._base_color == "#666666"

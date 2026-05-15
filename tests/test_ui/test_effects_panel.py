"""Tests for EffectsPanel."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from src.ui.effects_panel import EffectsPanel


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestEffectsPanel:
    @pytest.fixture
    def panel(self, qapp: QApplication) -> EffectsPanel:
        return EffectsPanel()

    def test_constructs(self, panel: EffectsPanel) -> None:
        assert panel is not None
        assert panel._engine is None

    def test_knobs_created(self, panel: EffectsPanel) -> None:
        expected = [
            "reverb_room_size",
            "reverb_damping",
            "reverb_wet",
            "delay_time",
            "delay_feedback",
            "delay_wet",
            "chorus_rate",
            "chorus_depth",
            "chorus_wet",
            "distortion_drive",
            "volume",
        ]
        for key in expected:
            assert key in panel._knobs, f"Missing knob: {key}"

    def test_bypasses_created(self, panel: EffectsPanel) -> None:
        expected = ["reverb", "delay", "chorus", "distortion"]
        for key in expected:
            assert key in panel._bypasses, f"Missing bypass: {key}"

    def test_set_engine(self, panel: EffectsPanel) -> None:
        engine = MagicMock()
        panel.set_engine(engine)
        assert panel._engine is not None

    def test_knob_change_calls_engine(self, panel: EffectsPanel) -> None:
        engine = MagicMock()
        panel.set_engine(engine)
        panel._on_knob_changed("reverb_room_size", 0.7)
        engine.set_master_param.assert_called_with("reverb_room_size", 0.7)

    def test_bypass_stores_and_restores(self, panel: EffectsPanel) -> None:
        engine = MagicMock()
        panel.set_engine(engine)

        # Bypass reverb
        panel._on_bypass_toggled("reverb", True)
        engine.set_master_param.assert_called_with("reverb_wet", 0.0)

        # Un-bypass
        engine.set_master_param.reset_mock()
        panel._on_bypass_toggled("reverb", False)
        engine.set_master_param.assert_called()

"""Tests for DrumPanel."""

import pytest
from PySide6.QtWidgets import QApplication

from src.sequencer.transport import Transport
from src.ui.drum_panel import DrumPanel


class MockAudioEngine:
    """Minimal mock for AudioEngine drum methods."""

    def __init__(self) -> None:
        self.transport = Transport()
        self.trigger_calls: list[tuple[str, int]] = []
        self.load_kit_calls: list[str] = []
        self.set_pattern_calls: list[object] = []

    def trigger_drum(self, drum_type: str, velocity: int, pan: float = 0.0) -> None:
        self.trigger_calls.append((drum_type, velocity))

    def load_drum_kit(self, kit_name: str) -> None:
        self.load_kit_calls.append(kit_name)

    def set_drum_pattern(self, pattern: object) -> None:
        self.set_pattern_calls.append(pattern)


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def engine() -> MockAudioEngine:
    return MockAudioEngine()


class TestDrumPanel:
    @pytest.fixture
    def panel(self, qapp: QApplication) -> DrumPanel:
        return DrumPanel()

    def test_constructs(self, panel: DrumPanel) -> None:
        assert panel is not None
        assert panel._engine is None
        assert panel._transport is None

    def test_set_engine_connects_and_loads_default_kit(self, panel: DrumPanel, engine: MockAudioEngine) -> None:
        panel.set_engine(engine)  # type: ignore[arg-type]
        assert panel._engine is not None
        assert panel._transport is not None
        assert len(engine.load_kit_calls) >= 1
        assert len(engine.set_pattern_calls) >= 1

    def test_pad_hit_triggers_drum(self, panel: DrumPanel, engine: MockAudioEngine) -> None:
        panel.set_engine(engine)  # type: ignore[arg-type]
        panel._on_pad_hit("kick")
        assert len(engine.trigger_calls) >= 1
        assert engine.trigger_calls[-1][0] == "kick"
        assert engine.trigger_calls[-1][1] == 100

    def test_kit_change_reloads_kit(self, panel: DrumPanel, engine: MockAudioEngine) -> None:
        panel.set_engine(engine)  # type: ignore[arg-type]
        engine.load_kit_calls.clear()
        panel._on_kit_changed("808 Classic")
        assert engine.load_kit_calls == ["808 Classic"]

    def test_pattern_change_sends_to_engine(self, panel: DrumPanel, engine: MockAudioEngine) -> None:
        panel.set_engine(engine)  # type: ignore[arg-type]
        engine.set_pattern_calls.clear()
        panel._on_pattern_changed()
        assert len(engine.set_pattern_calls) == 1

    def test_kit_combo_has_all_presets(self, panel: DrumPanel) -> None:
        count = panel._kit_combo.count()
        assert count >= 6

    def test_pads_created_for_all_drum_types(self, panel: DrumPanel) -> None:
        assert len(panel._pads) == 10
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
            assert dt in panel._pads

    def test_label_combos_created(self, panel: DrumPanel) -> None:
        assert len(panel._label_combos) == 10
        for dt in panel._pads:
            assert dt in panel._label_combos

    def test_start_stop_polling(self, panel: DrumPanel) -> None:
        panel.start_polling()
        assert panel._poll_timer.isActive()
        panel.stop_polling()
        assert not panel._poll_timer.isActive()

    def test_apply_style_populates_sequencer(self, panel: DrumPanel, engine: MockAudioEngine) -> None:
        panel.set_engine(engine)  # type: ignore[arg-type]
        # Set combo selections
        panel._label_combos["kick"].setCurrentText("4/4")
        panel._label_combos["snare"].setCurrentText("2_4")
        panel._label_combos["hh_closed"].setCurrentText("offbeat")
        panel._label_combos["hh_open"].setCurrentText("—")
        panel._label_combos["clap"].setCurrentText("2_4")
        panel._label_combos["crash"].setCurrentText("—")

        engine.set_pattern_calls.clear()
        panel._on_apply_style()

        pattern = panel._sequencer.get_pattern()
        # Kick on 4/4 should have steps 0, 4, 8, 12 active
        assert pattern.kick[0].active
        assert pattern.kick[4].active
        assert pattern.kick[8].active
        assert pattern.kick[12].active
        # Snare on 2_4 should have steps 4, 12 active
        assert pattern.snare[4].active
        assert pattern.snare[12].active
        # HH closed offbeat should have steps 4, 12 active
        assert pattern.hh_closed[4].active
        assert pattern.hh_closed[12].active
        # Pattern should be sent to engine
        assert len(engine.set_pattern_calls) >= 1

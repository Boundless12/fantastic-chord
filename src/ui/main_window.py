"""MainWindow: Application main window with dock-based layout."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QMainWindow,
    QStatusBar,
    QWidget,
)

from ..audio.engine import AudioEngine
from ..sequencer.piano_roll import PianoRollModel
from ..sequencer.transport import Transport
from .keyboard_widget import KeyboardWidget
from .piano_roll_widget import PianoRollWidget
from .synth_panel import SynthPanel
from .transport import TransportWidget
from .waveform_display import WaveformDisplay

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """酷和弦 main application window."""

    midi_cc_received = Signal(int, int)

    audio_engine: AudioEngine
    sequencer_transport: Transport
    piano_roll_model: PianoRollModel
    keyboard_widget: KeyboardWidget
    transport_widget: TransportWidget
    piano_roll_widget: PianoRollWidget
    waveform_display: WaveformDisplay
    synth_panel: SynthPanel

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("酷和弦 — Cool Chord EDM Synthesizer")
        self.resize(1400, 900)

        self.sequencer_transport = Transport()
        self.audio_engine = AudioEngine(transport=self.sequencer_transport)
        self.piano_roll_model = PianoRollModel(self.sequencer_transport)

        self._setup_central()
        self._setup_docks()
        self._setup_menu()
        self._setup_statusbar()
        self._connect_signals()

    def _setup_central(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

    def _setup_docks(self) -> None:
        # Piano roll dock — center
        self.piano_roll_widget = PianoRollWidget(self.piano_roll_model)
        piano_roll_dock = QDockWidget("Piano Roll", self)
        piano_roll_dock.setWidget(self.piano_roll_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, piano_roll_dock)

        # Keyboard dock — bottom
        self.keyboard_widget = KeyboardWidget()
        keyboard_dock = QDockWidget("Virtual Keyboard", self)
        keyboard_dock.setWidget(self.keyboard_widget)
        keyboard_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, keyboard_dock)

        # Transport dock — top
        self.transport_widget = TransportWidget()
        transport_dock = QDockWidget("Transport", self)
        transport_dock.setWidget(self.transport_widget)
        transport_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        transport_dock.setMaximumHeight(60)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, transport_dock)

        # Synth panel dock — right
        self.synth_panel = SynthPanel()
        self.synth_panel.set_engine(self.audio_engine)
        synth_dock = QDockWidget("Synthesizer", self)
        synth_dock.setWidget(self.synth_panel)
        synth_dock.setMinimumWidth(320)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, synth_dock)

        # Waveform dock — right (below synth panel)
        self.waveform_display = WaveformDisplay()
        waveform_dock = QDockWidget("Oscilloscope", self)
        waveform_dock.setWidget(self.waveform_display)
        waveform_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, waveform_dock)

    def _setup_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction("&New Project", self._on_new_project)
        file_menu.addAction("&Open MIDI...", self._on_open_midi)
        file_menu.addAction("&Save MIDI...", self._on_save_midi)
        file_menu.addSeparator()
        file_menu.addAction("Export &WAV...", self._on_export_wav)
        file_menu.addAction("Export &MIDI...", self._on_export_midi)
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close)

        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction("&Undo", self._on_undo, "Ctrl+Z")
        edit_menu.addAction("&Redo", self._on_redo, "Ctrl+Y")

        view_menu = menubar.addMenu("&View")
        view_menu.addAction("Toggle &Keyboard", self._on_toggle_keyboard)
        view_menu.addAction("Toggle &Transport", self._on_toggle_transport)
        view_menu.addAction("Toggle &Synth Panel", self._on_toggle_synth_panel)

        audio_menu = menubar.addMenu("&Audio")
        audio_menu.addAction("Audio &Settings...", self._on_audio_settings)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&About 酷和弦", self._on_about)

    def _setup_statusbar(self) -> None:
        status = QStatusBar()
        status.showMessage("Ready — 酷和弦 EDM Synthesizer")
        self.setStatusBar(status)

    def _connect_signals(self) -> None:
        self.keyboard_widget.note_on.connect(self._on_keyboard_note_on)
        self.keyboard_widget.note_off.connect(self._on_keyboard_note_off)
        self.synth_panel.cc_learn_started.connect(self._on_cc_learn_started)
        self.synth_panel.cc_learn_finished.connect(self._on_cc_learn_finished)

    def _on_keyboard_note_on(self, note: int, velocity: int) -> None:
        self.audio_engine.note_on(note, velocity)

    def _on_keyboard_note_off(self, note: int) -> None:
        self.audio_engine.note_off(note)

    def _on_cc_learn_started(self) -> None:
        self.statusBar().showMessage("MIDI CC Learn: move a controller on your MIDI device...")

    def _on_cc_learn_finished(self, cc_number: int, param_path: str) -> None:
        self.statusBar().showMessage(f"CC {cc_number} mapped to {param_path}")

    def _on_new_project(self) -> None:
        logger.info("New project")

    def _on_open_midi(self) -> None:
        logger.info("Open MIDI")

    def _on_save_midi(self) -> None:
        logger.info("Save MIDI")

    def _on_export_wav(self) -> None:
        logger.info("Export WAV")

    def _on_export_midi(self) -> None:
        logger.info("Export MIDI")

    def _on_undo(self) -> None:
        logger.debug("Undo")

    def _on_redo(self) -> None:
        logger.debug("Redo")

    def _on_toggle_keyboard(self) -> None:
        logger.debug("Toggle keyboard")

    def _on_toggle_transport(self) -> None:
        logger.debug("Toggle transport")

    def _on_toggle_synth_panel(self) -> None:
        logger.debug("Toggle synth panel")

    def _on_audio_settings(self) -> None:
        logger.info("Audio settings")

    def _on_about(self) -> None:
        logger.info("About 酷和弦")

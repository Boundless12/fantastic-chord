"""MainWindow: Application main window with dock-based layout."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QWidget,
)

from ..audio.engine import AudioEngine
from ..chord.theory import ProgressionData
from ..export.midi_exporter import MidiExporter
from ..export.wav_exporter import WavExporter
from ..sequencer.piano_roll import PianoRollModel
from ..sequencer.transport import Transport
from .chord_panel import ChordPanel
from .drum_panel import DrumPanel
from .effects_panel import EffectsPanel
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
    drum_panel: DrumPanel
    chord_panel: ChordPanel
    effects_panel: EffectsPanel
    _piano_roll_dock: QDockWidget
    _keyboard_dock: QDockWidget
    _transport_dock: QDockWidget
    _synth_dock: QDockWidget
    _chord_dock: QDockWidget
    _drum_dock: QDockWidget
    _waveform_dock: QDockWidget
    _effects_dock: QDockWidget

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
        self._setup_shortcuts()

    def _setup_central(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

    def _setup_docks(self) -> None:
        # Piano roll dock — center
        self.piano_roll_widget = PianoRollWidget(self.piano_roll_model)
        self._piano_roll_dock = QDockWidget("Piano Roll", self)
        self._piano_roll_dock.setWidget(self.piano_roll_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._piano_roll_dock)

        # Keyboard dock — bottom
        self.keyboard_widget = KeyboardWidget()
        self._keyboard_dock = QDockWidget("Virtual Keyboard", self)
        self._keyboard_dock.setWidget(self.keyboard_widget)
        self._keyboard_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._keyboard_dock)

        # Transport dock — top
        self.transport_widget = TransportWidget()
        self._transport_dock = QDockWidget("Transport", self)
        self._transport_dock.setWidget(self.transport_widget)
        self._transport_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self._transport_dock.setMaximumHeight(60)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self._transport_dock)

        # Synth panel dock — right
        self.synth_panel = SynthPanel()
        self.synth_panel.set_engine(self.audio_engine)
        self._synth_dock = QDockWidget("Synthesizer", self)
        self._synth_dock.setWidget(self.synth_panel)
        self._synth_dock.setMinimumWidth(320)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._synth_dock)

        # Chord panel dock — right (below synth)
        self.chord_panel = ChordPanel()
        self._chord_dock = QDockWidget("Chord Generator", self)
        self._chord_dock.setWidget(self.chord_panel)
        self._chord_dock.setMinimumWidth(340)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._chord_dock)

        # Drum panel dock — right (below chord panel)
        self.drum_panel = DrumPanel()
        self._drum_dock = QDockWidget("Drum Machine", self)
        self._drum_dock.setWidget(self.drum_panel)
        self._drum_dock.setMinimumWidth(340)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._drum_dock)

        # Waveform dock — right (below drum panel)
        self.waveform_display = WaveformDisplay()
        self._waveform_dock = QDockWidget("Oscilloscope", self)
        self._waveform_dock.setWidget(self.waveform_display)
        self._waveform_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._waveform_dock)

        # Effects panel dock — right (bottom)
        self.effects_panel = EffectsPanel()
        self._effects_dock = QDockWidget("Effects Mixer", self)
        self._effects_dock.setWidget(self.effects_panel)
        self._effects_dock.setMinimumWidth(300)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._effects_dock)

        # Initialize drum panel engine connection
        self.drum_panel.set_engine(self.audio_engine)
        self.chord_panel.set_engine(self.audio_engine)
        self.effects_panel.set_engine(self.audio_engine)

    def _setup_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction("&New Project", self._on_new_project)
        file_menu.addAction("&Open MIDI...", self._on_open_midi)
        file_menu.addAction("&Save MIDI...", self._on_save_midi)
        file_menu.addSeparator()
        file_menu.addAction("Export &WAV...", self._on_export_wav)
        file_menu.addAction("Export &Stems...", self._on_export_stems)
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
        view_menu.addAction("Toggle &Drum Panel", self._on_toggle_drum_panel)
        view_menu.addAction("Toggle &Chord Panel", self._on_toggle_chord_panel)
        view_menu.addAction("Toggle &Effects Mixer", self._on_toggle_effects_panel)

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

        # Transport → sequencer
        self.transport_widget.play_clicked.connect(self._on_transport_play)
        self.transport_widget.stop_clicked.connect(self._on_transport_stop)
        self.transport_widget.bpm_changed.connect(self._on_bpm_changed)

        # Chord panel → piano roll
        self.chord_panel.progression_changed.connect(self._on_progression_pushed)

    def _setup_shortcuts(self) -> None:
        QShortcut(Qt.Key.Key_Space, self, self._on_transport_play)
        QShortcut(Qt.Key.Key_Escape, self, self._on_transport_stop)

    def _on_transport_play(self) -> None:
        self.sequencer_transport.is_playing = not self.sequencer_transport.is_playing
        if self.sequencer_transport.is_playing:
            self.drum_panel.start_polling()
        else:
            self.drum_panel.stop_polling()

    def _on_transport_stop(self) -> None:
        self.sequencer_transport.is_playing = False
        self.sequencer_transport.reset()
        self.drum_panel.stop_polling()

    def _on_bpm_changed(self, bpm: float) -> None:
        self.sequencer_transport.set_bpm(bpm)

    def _on_progression_pushed(self, progression: ProgressionData) -> None:
        """Convert a ProgressionData to Note objects and push to piano roll."""

        # Clear existing pattern
        pattern = self.piano_roll_model.current_pattern
        pattern.notes.clear()

        # Ensure piano roll sequencer is enabled
        self.audio_engine.enable_piano_roll_playback(True)

        start_beat = 0.0
        for chord in progression.chords:
            for pitch in chord.notes:
                self.piano_roll_model.insert_note(
                    pitch=pitch,
                    start=start_beat,
                    duration=chord.duration * 0.85,
                    velocity=100,
                )
            start_beat += chord.duration

        pattern.length_beats = max(start_beat, 4.0)
        self.piano_roll_widget.refresh_notes()

        # Push pattern to engine for playback
        self.audio_engine.set_piano_roll_pattern(pattern)

        self.statusBar().showMessage(f"Pushed {len(progression.chords)} chords to piano roll")

    def _on_keyboard_note_on(self, note: int, velocity: int) -> None:
        self.audio_engine.note_on(note, velocity)

    def _on_keyboard_note_off(self, note: int) -> None:
        self.audio_engine.note_off(note)

    def _on_cc_learn_started(self) -> None:
        self.statusBar().showMessage("MIDI CC Learn: move a controller on your MIDI device...")

    def _on_cc_learn_finished(self, cc_number: int, param_path: str) -> None:
        self.statusBar().showMessage(f"CC {cc_number} mapped to {param_path}")

    def _on_new_project(self) -> None:
        self.piano_roll_model.current_pattern.notes.clear()
        self.piano_roll_model.current_pattern.length_beats = 16.0
        self.piano_roll_widget.refresh_notes()
        self.sequencer_transport.reset()
        self.statusBar().showMessage("New project created")

    def _on_open_midi(self) -> None:
        from ..midi.file_io import MidiFileIO

        filepath, _ = QFileDialog.getOpenFileName(self, "Open MIDI", "", "MIDI Files (*.mid)")
        if not filepath:
            return
        data = MidiFileIO.load(filepath)
        if data.tracks:
            pattern = self.piano_roll_model.current_pattern
            pattern.notes.clear()
            for track in data.tracks:
                beat_duration = 60.0 / data.bpm
                for midi_note in track.notes:
                    self.piano_roll_model.insert_note(
                        pitch=midi_note.pitch,
                        start=midi_note.start_time / beat_duration if beat_duration else 0,
                        duration=midi_note.duration / beat_duration if beat_duration else 0.5,
                        velocity=midi_note.velocity,
                    )
            self.piano_roll_widget.refresh_notes()
            self.statusBar().showMessage(f"MIDI loaded: {filepath}")

    def _on_save_midi(self) -> None:
        filepath, _ = QFileDialog.getSaveFileName(self, "Save MIDI", "", "MIDI Files (*.mid)")
        if not filepath:
            return
        bpm = float(self.transport_widget._bpm_spin.value())
        success = MidiExporter.export_piano_roll(self.piano_roll_model.current_pattern, bpm, filepath)
        if success:
            self.statusBar().showMessage(f"MIDI saved: {filepath}")
        else:
            self.statusBar().showMessage("MIDI save failed")

    def _on_export_wav(self) -> None:
        filepath, _ = QFileDialog.getSaveFileName(self, "Export WAV", "", "WAV Files (*.wav)")
        if not filepath:
            return
        bpm = float(self.transport_widget._bpm_spin.value())
        success = WavExporter.export(self.audio_engine, filepath, duration_beats=32.0, bpm=bpm)
        if success:
            self.statusBar().showMessage(f"WAV exported: {filepath}")
        else:
            self.statusBar().showMessage("WAV export failed")

    def _on_export_stems(self) -> None:
        output_dir = QFileDialog.getExistingDirectory(self, "Export Stems — Select Output Directory")
        if not output_dir:
            return
        bpm = float(self.transport_widget._bpm_spin.value())
        success = WavExporter.export_stems(self.audio_engine, output_dir, duration_beats=32.0, bpm=bpm)
        if success:
            self.statusBar().showMessage(f"Stems exported to: {output_dir}")
        else:
            self.statusBar().showMessage("Stem export failed")

    def _on_export_midi(self) -> None:
        filepath, _ = QFileDialog.getSaveFileName(self, "Export MIDI", "", "MIDI Files (*.mid)")
        if not filepath:
            return
        bpm = float(self.transport_widget._bpm_spin.value())
        success = MidiExporter.export_project(
            self.piano_roll_model.current_pattern,
            self.drum_panel._sequencer.get_pattern(),
            bpm,
            filepath,
        )
        if success:
            self.statusBar().showMessage(f"MIDI exported: {filepath}")
        else:
            self.statusBar().showMessage("MIDI export failed")

    def _on_undo(self) -> None:
        if self.piano_roll_model.undo():
            self.piano_roll_widget.refresh_notes()

    def _on_redo(self) -> None:
        if self.piano_roll_model.redo():
            self.piano_roll_widget.refresh_notes()

    def _on_toggle_keyboard(self) -> None:
        self._keyboard_dock.setVisible(not self._keyboard_dock.isVisible())

    def _on_toggle_transport(self) -> None:
        self._transport_dock.setVisible(not self._transport_dock.isVisible())

    def _on_toggle_synth_panel(self) -> None:
        self._synth_dock.setVisible(not self._synth_dock.isVisible())

    def _on_toggle_drum_panel(self) -> None:
        self._drum_dock.setVisible(not self._drum_dock.isVisible())

    def _on_toggle_chord_panel(self) -> None:
        self._chord_dock.setVisible(not self._chord_dock.isVisible())

    def _on_toggle_effects_panel(self) -> None:
        self._effects_dock.setVisible(not self._effects_dock.isVisible())

    def _on_audio_settings(self) -> None:
        devices = AudioEngine.list_devices()
        names = "\n".join(f"  {d}" for d in devices[:20]) if devices else "  (no devices found)"
        QMessageBox.information(self, "Audio Devices", f"Available audio devices:\n{names}")

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "About 酷和弦",
            "酷和弦 — Cool Chord EDM Synthesizer\n\n"
            "A Python desktop synthesizer for EDM chord generation.\n"
            "Version: 1.0.0\n\n"
            "Built with PySide6 + sounddevice + numpy",
        )

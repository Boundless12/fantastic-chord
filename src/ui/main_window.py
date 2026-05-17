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
    QSplitter,
    QStatusBar,
    QWidget,
)

from ..audio.engine import AudioEngine
from ..chord.theory import ProgressionData
from ..export.midi_exporter import MidiExporter
from ..export.wav_exporter import WavExporter
from ..sequencer.piano_roll import PianoRollModel
from ..sequencer.track import InstrumentType
from ..sequencer.transport import Transport
from .chord_panel import ChordPanel
from .drum_panel import DrumPanel
from .effects_panel import EffectsPanel
from .keyboard_widget import KeyboardWidget
from .mod_matrix_panel import ModMatrixPanel
from .piano_roll_widget import PianoRollWidget
from .synth_panel import SynthPanel
from .theme import COLOR_SURFACE
from .track_list import TrackListWidget
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
    _track_list: TrackListWidget
    _keyboard_dock: QDockWidget
    _transport_dock: QDockWidget

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
        self._start_audio_engine()

    def _setup_central(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {COLOR_SURFACE}; width: 3px; }}")

        self._track_list = TrackListWidget()
        self._track_list.set_model(self.piano_roll_model)
        self._track_list.setMaximumWidth(180)
        splitter.addWidget(self._track_list)

        self.piano_roll_widget = PianoRollWidget(self.piano_roll_model)
        splitter.addWidget(self.piano_roll_widget)

        right_panel = self._build_right_panel_stack()
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 7)
        splitter.setStretchFactor(2, 3)
        splitter.setSizes([160, 880, 440])

        self.setCentralWidget(splitter)

    def _build_right_panel_stack(self) -> QWidget:
        from PySide6.QtWidgets import QTabWidget

        tabs = QTabWidget()
        tabs.setMinimumWidth(320)
        tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{ border: none; background: {COLOR_SURFACE}; }}
            QTabBar::tab {{ color: #a0a0c0; background: #252538; padding: 6px 12px; border: none; }}
            QTabBar::tab:selected {{ color: #e0e0ff; background: {COLOR_SURFACE}; }}
        """
        )

        self.synth_panel = SynthPanel()
        self.synth_panel.set_engine(self.audio_engine)
        tabs.addTab(self.synth_panel, "Synth")

        self.chord_panel = ChordPanel()
        self.chord_panel.set_engine(self.audio_engine)
        tabs.addTab(self.chord_panel, "Chords")

        self.drum_panel = DrumPanel()
        self.drum_panel.set_engine(self.audio_engine)
        tabs.addTab(self.drum_panel, "Drums")

        self.effects_panel = EffectsPanel()
        self.effects_panel.set_engine(self.audio_engine)
        tabs.addTab(self.effects_panel, "FX")

        self.mod_matrix_panel = ModMatrixPanel()
        self.mod_matrix_panel.set_engine(self.audio_engine)
        tabs.addTab(self.mod_matrix_panel, "Mod")

        self.waveform_display = WaveformDisplay()
        self.waveform_display.setMinimumHeight(80)
        self.waveform_display.setMaximumHeight(120)
        tabs.addTab(self.waveform_display, "Wave")

        return tabs

    def _setup_docks(self) -> None:
        self.transport_widget = TransportWidget()
        self._transport_dock = QDockWidget("Transport", self)
        self._transport_dock.setWidget(self.transport_widget)
        self._transport_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self._transport_dock.setMaximumHeight(60)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self._transport_dock)

        self.keyboard_widget = KeyboardWidget()
        self._keyboard_dock = QDockWidget("Virtual Keyboard", self)
        self._keyboard_dock.setWidget(self.keyboard_widget)
        self._keyboard_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self._keyboard_dock.setMinimumHeight(100)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._keyboard_dock)
        self._keyboard_dock.setVisible(True)

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

        # Drum panel → piano roll
        self.drum_panel.drum_to_piano_roll.connect(self._on_drum_to_piano_roll)

        # Track list → model → piano roll refresh
        self._track_list.active_track_changed.connect(self._on_track_changed)
        self._track_list.track_types_changed.connect(self._on_track_types_changed)
        self.piano_roll_model.active_track_changed.connect(self._on_active_track_changed)

    def _setup_shortcuts(self) -> None:
        QShortcut(Qt.Key.Key_Space, self, self._on_transport_play)
        QShortcut(Qt.Key.Key_Escape, self, self._on_transport_stop)

    def _start_audio_engine(self) -> None:
        try:
            self.audio_engine.start()
            logger.info("Audio engine started")
            self.statusBar().showMessage("Audio engine running — 44100 Hz, 512 samples")
        except Exception as e:
            logger.error(f"Failed to start audio engine: {e}")
            self.statusBar().showMessage(f"Audio error: {e}")

    def _on_transport_play(self) -> None:
        self.sequencer_transport.is_playing = not self.sequencer_transport.is_playing
        if self.sequencer_transport.is_playing:
            self.drum_panel.start_polling()
            self.piano_roll_widget.start_playhead_polling()
        else:
            self.drum_panel.stop_polling()
            self.piano_roll_widget.stop_playhead_polling()

    def _on_transport_stop(self) -> None:
        self.sequencer_transport.is_playing = False
        self.sequencer_transport.reset()
        self.transport_widget._play_btn.setText("▶")
        self.transport_widget._play_btn.setChecked(False)
        self.transport_widget._is_playing = False
        self.drum_panel.stop_polling()
        self.piano_roll_widget.stop_playhead_polling()
        self.audio_engine.panic()
        self.drum_panel._preview_running = False
        self.chord_panel._preview_running = False

    def _on_bpm_changed(self, bpm: float) -> None:
        self.sequencer_transport.set_bpm(bpm)

    def _on_progression_pushed(self, progression: ProgressionData) -> None:
        """Push chord progression to a NEW track (FL Studio style)."""

        # Check if current track is empty — if so reuse it, otherwise create new
        current_pattern = self.piano_roll_model.current_pattern
        if current_pattern.notes:
            self.piano_roll_model.add_track()
            self.piano_roll_model.set_active_track(len(self.piano_roll_model.tracks) - 1)
            self._track_list._rebuild_list()
            self._track_list._list.setCurrentRow(self.piano_roll_model.active_track_index)

        pattern = self.piano_roll_model.current_pattern
        pattern.notes.clear()
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
        self.piano_roll_widget.update_scene_rect()

        self.audio_engine.set_piano_roll_pattern(pattern, self.piano_roll_model.active_track_index)
        self._track_list.track_types_changed.emit()

        self.sequencer_transport.reset()
        self.sequencer_transport.is_playing = True
        self.transport_widget._play_btn.setText("⏸")
        self.transport_widget._play_btn.setChecked(True)
        self.transport_widget._is_playing = True
        self.drum_panel.start_polling()

        self.statusBar().showMessage(
            f"Pushed {len(progression.chords)} chords → {self.piano_roll_model.current_track.name} — playing"
        )

    def _on_drum_to_piano_roll(self, drum_pattern: object) -> None:
        from ..sequencer.drum_pattern import GM_DRUM_MAP, DrumPattern
        from ..sequencer.pattern import Note

        if not isinstance(drum_pattern, DrumPattern):
            return

        self.piano_roll_model.add_track()
        new_idx = len(self.piano_roll_model.tracks) - 1
        self.piano_roll_model.set_active_track(new_idx)
        self._track_list._rebuild_list()
        self._track_list._list.setCurrentRow(new_idx)

        track = self.piano_roll_model.current_track
        track.name = f"Drums {new_idx}"
        track.instrument_type = InstrumentType.DRUMS

        pattern = self.piano_roll_model.current_pattern
        pattern.notes.clear()
        pattern.name = drum_pattern.name
        pattern.length_beats = 4.0

        step_beats = 4.0 / drum_pattern.steps
        parts = drum_pattern.get_parts()
        for drum_type, steps in parts.items():
            pitch = GM_DRUM_MAP.get(drum_type, 0)
            for i, step in enumerate(steps):
                if step.active:
                    pattern.notes.append(
                        Note(
                            pitch=pitch,
                            velocity=int(step.velocity * 127),
                            start_time=i * step_beats,
                            duration=step_beats * 0.8,
                        )
                    )

        self.piano_roll_widget.refresh_notes()
        self.piano_roll_widget.update_scene_rect()
        self.piano_roll_widget.scroll_to_pitch_range(36, 50)
        self._track_list.track_types_changed.emit()
        self.statusBar().showMessage(f"Pushed drum pattern → {track.name} ({len(pattern.notes)} hits)")

    def _on_keyboard_note_on(self, note: int, velocity: int) -> None:
        self.audio_engine.note_on(note, velocity)

    def _on_keyboard_note_off(self, note: int) -> None:
        self.audio_engine.note_off(note)

    def _on_cc_learn_started(self) -> None:
        self.statusBar().showMessage("MIDI CC Learn: move a controller on your MIDI device...")

    def _on_cc_learn_finished(self, cc_number: int, param_path: str) -> None:
        self.statusBar().showMessage(f"CC {cc_number} mapped to {param_path}")

    def _on_new_project(self) -> None:
        self.piano_roll_model.set_active_track(0)
        for track in self.piano_roll_model.tracks:
            for pattern in track.patterns:
                pattern.notes.clear()
        self.piano_roll_model.tracks = self.piano_roll_model.tracks[:1]
        self.piano_roll_model.tracks[0].patterns.clear()
        self.piano_roll_model.current_pattern.length_beats = 16.0
        self.piano_roll_widget.refresh_notes()
        self._track_list._rebuild_list()
        self._track_list._list.setCurrentRow(0)
        self.sequencer_transport.reset()
        self.statusBar().showMessage("New project created")

    def _on_open_midi(self) -> None:
        from ..midi.file_io import MidiFileIO

        filepath, _ = QFileDialog.getOpenFileName(self, "Open MIDI", "", "MIDI Files (*.mid)")
        if not filepath:
            return
        data = MidiFileIO.load(filepath)
        if data.tracks:
            beat_duration = 60.0 / data.bpm
            for t_idx, midi_track in enumerate(data.tracks):
                if t_idx >= len(self.piano_roll_model.tracks):
                    self.piano_roll_model.add_track()
                self.piano_roll_model.set_active_track(t_idx)
                pattern = self.piano_roll_model.current_pattern
                pattern.notes.clear()
                for midi_note in midi_track.notes:
                    self.piano_roll_model.insert_note(
                        pitch=midi_note.pitch,
                        start=midi_note.start_time / beat_duration if beat_duration else 0,
                        duration=midi_note.duration / beat_duration if beat_duration else 0.5,
                        velocity=midi_note.velocity,
                    )
            self.piano_roll_model.set_active_track(0)
            self.piano_roll_widget.refresh_notes()
            self._track_list._rebuild_list()
            self._track_list._list.setCurrentRow(0)
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
            self.piano_roll_model,
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

    def _on_track_changed(self, index: int) -> None:
        self.piano_roll_widget.refresh_notes()
        self.statusBar().showMessage(f"Active track: {self.piano_roll_model.current_track.name}")

    def _on_track_types_changed(self) -> None:
        types = self._track_list._get_track_types()
        self.audio_engine.set_track_types(types)

    def _on_active_track_changed(self, index: int) -> None:
        self.piano_roll_widget.refresh_notes()

    def _on_toggle_keyboard(self) -> None:
        self._keyboard_dock.setVisible(not self._keyboard_dock.isVisible())

    def _on_toggle_transport(self) -> None:
        self._transport_dock.setVisible(not self._transport_dock.isVisible())

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

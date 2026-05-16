"""ChordPanel: Chord progression generation and piano roll integration."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..audio.engine import AudioEngine
from ..chord.generator import ProgressionGenerator
from ..chord.styles import StyleManager
from ..chord.theory import NOTE_NAMES, SCALE_PATTERNS, ChordTheory, ProgressionData

STYLE_MANAGER = StyleManager()
STYLE_MANAGER.load_all()


class ChordPanel(QWidget):
    """Chord progression generation panel with piano roll push."""

    progression_selected = Signal(int)  # emits chord index in the progression

    _engine: AudioEngine | None
    _generator: ProgressionGenerator
    _progressions: list[ProgressionData]
    _chord_items: list[QListWidgetItem]
    _preview_running: bool

    _key_combo: QComboBox
    _scale_combo: QComboBox
    _style_combo: QComboBox
    _complexity_slider: QSlider
    _bars_spin: QSpinBox
    _seed_spin: QSpinBox
    _random_seed_check: QCheckBox
    _generate_btn: QPushButton
    _list: QListWidget
    _push_btn: QPushButton
    _preview_btn: QPushButton
    _clear_btn: QPushButton

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = None
        self._generator = ProgressionGenerator(STYLE_MANAGER)
        self._progressions = []
        self._chord_items = []
        self._preview_running = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # -- Key & Scale --
        key_scale_group = QGroupBox("Key & Scale")
        ks_layout = QHBoxLayout(key_scale_group)

        ks_layout.addWidget(QLabel("Key:"))
        self._key_combo = QComboBox()
        for note in NOTE_NAMES:
            self._key_combo.addItem(note)
        self._key_combo.setCurrentText("C")
        ks_layout.addWidget(self._key_combo)

        ks_layout.addWidget(QLabel("Scale:"))
        self._scale_combo = QComboBox()
        for scale_name in sorted(SCALE_PATTERNS.keys()):
            display = scale_name.replace("_", " ").title()
            self._scale_combo.addItem(display, scale_name)
        ks_layout.addWidget(self._scale_combo)

        layout.addWidget(key_scale_group)

        # -- Style --
        style_group = QGroupBox("Style")
        style_layout = QHBoxLayout(style_group)

        self._style_combo = QComboBox()
        for slug in sorted(STYLE_MANAGER.list_styles()):
            style_def = STYLE_MANAGER.get(slug)
            desc = style_def.description if style_def else ""
            self._style_combo.addItem(slug.replace("_", " ").title(), slug)
            idx = self._style_combo.count() - 1
            self._style_combo.setItemData(idx, desc, Qt.ItemDataRole.ToolTipRole)
        style_layout.addWidget(self._style_combo, 1)

        layout.addWidget(style_group)

        # -- Generation controls --
        gen_group = QGroupBox("Generation")
        gen_outer = QVBoxLayout(gen_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Complexity:"))
        self._complexity_slider = QSlider(Qt.Orientation.Horizontal)
        self._complexity_slider.setRange(0, 100)
        self._complexity_slider.setValue(50)
        self._complexity_slider.setToolTip("Low: triads only. High: extended chords.")
        row1.addWidget(self._complexity_slider)

        row1.addWidget(QLabel("Bars:"))
        self._bars_spin = QSpinBox()
        self._bars_spin.setRange(1, 16)
        self._bars_spin.setValue(8)
        row1.addWidget(self._bars_spin)
        gen_outer.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Seed:"))
        self._seed_spin = QSpinBox()
        self._seed_spin.setRange(0, 9999)
        self._seed_spin.setValue(42)
        row2.addWidget(self._seed_spin)

        self._random_seed_check = QCheckBox("Random")
        self._random_seed_check.toggled.connect(lambda checked: self._seed_spin.setEnabled(not checked))
        row2.addWidget(self._random_seed_check)

        row2.addStretch()

        self._generate_btn = QPushButton("Generate")
        self._generate_btn.clicked.connect(self._on_generate)
        row2.addWidget(self._generate_btn)
        gen_outer.addLayout(row2)

        layout.addWidget(gen_group)

        # -- Progression list --
        list_group = QGroupBox("Progressions")
        list_layout = QVBoxLayout(list_group)

        self._list = QListWidget()
        self._list.setMinimumHeight(100)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        list_layout.addWidget(self._list)

        layout.addWidget(list_group, 1)

        # -- Actions --
        actions_layout = QHBoxLayout()

        self._push_btn = QPushButton("Push to Piano Roll")
        self._push_btn.clicked.connect(self._on_push_to_piano_roll)
        actions_layout.addWidget(self._push_btn)

        self._preview_btn = QPushButton("Preview")
        self._preview_btn.clicked.connect(self._on_preview)
        actions_layout.addWidget(self._preview_btn)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self._on_clear)
        actions_layout.addWidget(self._clear_btn)

        layout.addLayout(actions_layout)

    def set_engine(self, engine: AudioEngine) -> None:
        self._engine = engine

    # -- Slots --

    def _on_generate(self) -> None:
        key = self._key_combo.currentText()
        scale_type = self._scale_combo.currentData()
        style_slug = self._style_combo.currentData()
        complexity = self._complexity_slider.value() / 100.0
        bars = self._bars_spin.value()

        seed: int | None = None
        if not self._random_seed_check.isChecked():
            seed = self._seed_spin.value()

        self._progressions = self._generator.generate_multiple(
            key=key,
            scale_type=scale_type,
            style=style_slug,
            bars=bars,
            complexity=complexity,
            count=8,
            seed=seed or 0,
        )

        self._list.clear()
        self._chord_items.clear()

        for i, prog in enumerate(self._progressions):
            symbols = ChordTheory.progression_to_symbols(prog)
            bpm = f" ({prog.bpm:.0f} BPM)"
            text = f"[{i + 1}] {' | '.join(symbols)}{bpm}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self._list.addItem(item)
            self._chord_items.append(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is not None and idx < len(self._progressions):
            self.progression_selected.emit(idx)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is not None and idx < len(self._progressions) and self._engine is not None:
            self._preview_progression(self._progressions[idx])

    def _on_push_to_piano_roll(self) -> None:
        current_item = self._list.currentItem()
        if current_item is None:
            return
        idx = current_item.data(Qt.ItemDataRole.UserRole)
        if idx is None or idx >= len(self._progressions):
            return
        self.progression_changed.emit(self._progressions[idx])

    def _on_preview(self) -> None:
        current_item = self._list.currentItem()
        if current_item is None or self._engine is None:
            return
        idx = current_item.data(Qt.ItemDataRole.UserRole)
        if idx is not None and idx < len(self._progressions):
            self._preview_progression(self._progressions[idx])

    def _on_clear(self) -> None:
        self._list.clear()
        self._chord_items.clear()
        self._progressions.clear()

    def _preview_progression(self, progression: ProgressionData) -> None:
        """Trigger each chord in the progression through the engine as a preview."""
        if self._engine is None:
            return

        import time as _time
        from threading import Thread

        bpm = progression.bpm
        beat_duration = 60.0 / bpm
        self._preview_running = True
        engine = self._engine

        def _play() -> None:
            for chord in progression.chords:
                if not self._preview_running:
                    break
                for pitch in chord.notes:
                    engine.note_on(pitch, 80)
                _time.sleep(chord.duration * beat_duration * 0.8)
                if not self._preview_running:
                    for pitch in chord.notes:
                        engine.note_off(pitch)
                    break
                for pitch in chord.notes:
                    engine.note_off(pitch)
                _time.sleep(chord.duration * beat_duration * 0.2)
            self._preview_running = False

        Thread(target=_play, daemon=True).start()

    # Signal for MainWindow to handle push-to-piano-roll
    progression_changed = Signal(object)

"""TrackListWidget: Multi-track list with color indicators and add/remove controls."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..sequencer.piano_roll import PianoRollModel


class TrackListWidget(QWidget):
    """Track list panel with color indicators for multi-track editing."""

    active_track_changed = Signal(int)
    track_types_changed = Signal()

    _model: PianoRollModel | None
    _list: QListWidget

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header = QHBoxLayout()
        label = QLabel("Tracks")
        label.setStyleSheet("color: #8888a0; font-size: 10px; font-weight: bold;")
        header.addWidget(label)
        header.addStretch()

        add_btn = QPushButton("+")
        add_btn.setFixedSize(22, 22)
        add_btn.setToolTip("Add track")
        add_btn.clicked.connect(self._on_add_track)
        header.addWidget(add_btn)

        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(22, 22)
        remove_btn.setToolTip("Remove selected track")
        remove_btn.clicked.connect(self._on_remove_track)
        header.addWidget(remove_btn)

        layout.addLayout(header)

        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { background: #1e1e2e; border: none; }"
            "QListWidget::item { padding: 4px 6px; border-bottom: 1px solid #333355; }"
            "QListWidget::item:selected { background: #7c3aed; color: white; }"
        )
        self._list.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list)

    def set_model(self, model: PianoRollModel) -> None:
        self._model = model
        self._rebuild_list()
        self._list.setCurrentRow(0)

    def _rebuild_list(self) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        if self._model is None:
            self._list.blockSignals(False)
            return
        for idx, track in enumerate(self._model.tracks):
            item = QListWidgetItem()
            item.setSizeHint(self._list.sizeHint())

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(2, 2, 2, 2)
            row_layout.setSpacing(4)

            color_dot = QLabel("●")
            color_dot.setStyleSheet(f"color: {track.color}; font-size: 14px; background: transparent;")
            row_layout.addWidget(color_dot)

            name_label = QLabel(track.name)
            name_label.setStyleSheet("color: #e0e0e0; background: transparent;")
            row_layout.addWidget(name_label, 1)

            type_combo = QComboBox()
            type_combo.addItems(["Synth", "Drums"])
            type_combo.setCurrentText(track.instrument_type.name.title())
            type_combo.setFixedWidth(70)
            type_combo.setStyleSheet(
                "QComboBox { background: #2a2a3c; color: #e0e0e0; border: 1px solid #444477;"
                " padding: 1px 4px; font-size: 9px; }"
                "QComboBox::drop-down { border: none; }"
                "QComboBox QAbstractItemView { background: #2a2a3c; color: #e0e0e0; }"
            )
            type_combo.currentTextChanged.connect(lambda text, t=track, ti=idx: self._on_type_changed(t, text, ti))
            row_layout.addWidget(type_combo)

            self._list.addItem(item)
            self._list.setItemWidget(item, row_widget)
        self._list.blockSignals(False)

    def _on_type_changed(self, track: object, text: str, track_index: int) -> None:
        from ..sequencer.track import InstrumentType

        t = track
        if hasattr(t, "instrument_type"):
            t.instrument_type = InstrumentType.DRUMS if text == "Drums" else InstrumentType.SYNTH
        self.track_types_changed.emit()

    def _get_track_types(self) -> list[str]:
        if self._model is None:
            return ["synth"]
        return [t.instrument_type.name.lower() for t in self._model.tracks]

    def _on_selection_changed(self, row: int) -> None:
        if row < 0 or self._model is None:
            return
        self._model.set_active_track(row)
        self.active_track_changed.emit(row)

    def _on_add_track(self) -> None:
        if self._model is None:
            return
        self._model.add_track()
        self._rebuild_list()
        self._list.setCurrentRow(len(self._model.tracks) - 1)
        self.track_types_changed.emit()

    def _on_remove_track(self) -> None:
        if self._model is None:
            return
        row = self._list.currentRow()
        if row < 0 or len(self._model.tracks) <= 1:
            return
        self._model.remove_track(row)
        self._rebuild_list()
        new_row = min(row, len(self._model.tracks) - 1)
        self._list.setCurrentRow(new_row)
        self.track_types_changed.emit()

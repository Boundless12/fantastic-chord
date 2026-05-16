"""ModMatrixPanel: Serum-style modulation matrix table widget."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ..audio.engine import AudioEngine
from ..audio.mod_matrix import MOD_DESTINATIONS, MOD_SOURCES


class ModMatrixPanel(QWidget):
    """Table-based modulation matrix editor with source/destination/amount rows."""

    slot_changed = Signal()

    _engine: AudioEngine | None
    _table: QTableWidget
    _num_slots: int

    def __init__(self, num_slots: int = 8, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = None
        self._num_slots = num_slots
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        group = QGroupBox("Mod Matrix")
        group.setStyleSheet(
            "QGroupBox { color: #c0c0d0; border: 1px solid #444477; border-radius: 4px; margin-top: 8px; padding-top: 12px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; }"
        )
        gl = QVBoxLayout(group)
        gl.setSpacing(2)

        self._table = QTableWidget(self._num_slots, 3)
        self._table.setHorizontalHeaderLabels(["Source", "Destination", "Amount"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(2, 70)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet(
            "QTableWidget { background: #1e1e2e; border: none; gridline-color: #333355; }"
            "QTableWidget::item { padding: 1px; }"
            "QHeaderView::section { background: #2a2a3c; color: #8888a0; border: 1px solid #333355; padding: 2px; font-size: 9px; }"
        )

        for row in range(self._num_slots):
            src_combo = QComboBox()
            src_combo.addItems(MOD_SOURCES)
            src_combo.setStyleSheet(
                "QComboBox { background: #2a2a3c; color: #e0e0e0; border: none; padding: 2px; font-size: 9px; }"
                "QComboBox::drop-down { border: none; }"
                "QComboBox QAbstractItemView { background: #2a2a3c; color: #e0e0e0; font-size: 9px; }"
            )
            src_combo.currentIndexChanged.connect(lambda idx, r=row: self._on_slot_changed(r))
            self._table.setCellWidget(row, 0, src_combo)

            dst_combo = QComboBox()
            dst_combo.addItems(MOD_DESTINATIONS)
            dst_combo.setStyleSheet(
                "QComboBox { background: #2a2a3c; color: #e0e0e0; border: none; padding: 2px; font-size: 9px; }"
                "QComboBox::drop-down { border: none; }"
                "QComboBox QAbstractItemView { background: #2a2a3c; color: #e0e0e0; font-size: 9px; }"
            )
            dst_combo.currentIndexChanged.connect(lambda idx, r=row: self._on_slot_changed(r))
            self._table.setCellWidget(row, 1, dst_combo)

            amount_spin = QDoubleSpinBox()
            amount_spin.setRange(-1.0, 1.0)
            amount_spin.setSingleStep(0.05)
            amount_spin.setValue(0.0)
            amount_spin.setDecimals(2)
            amount_spin.setStyleSheet(
                "QDoubleSpinBox { background: #2a2a3c; color: #e0e0e0; border: none; padding: 2px; font-size: 9px; }"
            )
            amount_spin.valueChanged.connect(lambda val, r=row: self._on_slot_changed(r))
            self._table.setCellWidget(row, 2, amount_spin)

        gl.addWidget(self._table)

        btn_row = QHBoxLayout()
        clear_btn = QPushButton("Clear All")
        clear_btn.setFixedHeight(22)
        clear_btn.clicked.connect(self._on_clear)
        clear_btn.setStyleSheet("QPushButton { font-size: 9px; }")
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        gl.addLayout(btn_row)

        layout.addWidget(group)

    def _on_slot_changed(self, row: int) -> None:
        if self._engine:
            src_w = self._table.cellWidget(row, 0)
            dst_w = self._table.cellWidget(row, 1)
            amt_w = self._table.cellWidget(row, 2)
            if isinstance(src_w, QComboBox) and isinstance(dst_w, QComboBox) and isinstance(amt_w, QDoubleSpinBox):
                src = src_w.currentText()
                dst = dst_w.currentText()
                amt = amt_w.value()
                self._engine.command_queue.put(("set_mod_slot", str(row), src, dst, str(amt)))
        self.slot_changed.emit()

    def _on_clear(self) -> None:
        for row in range(self._num_slots):
            amt_w = self._table.cellWidget(row, 2)
            if isinstance(amt_w, QDoubleSpinBox):
                amt_w.setValue(0.0)

    def set_engine(self, engine: AudioEngine) -> None:
        self._engine = engine

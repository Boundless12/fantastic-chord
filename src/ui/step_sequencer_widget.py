"""StepSequencerWidget: 16-step drum pattern grid with toggle buttons."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..sequencer.drum_pattern import DRUM_COLORS, DRUM_LABELS, DRUM_TYPES, DrumPattern


class StepButton(QPushButton):
    """A single step toggle button in the sequencer grid."""

    _color: str

    def __init__(self, color: str = "#555555", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self.setCheckable(True)
        self.setFixedSize(26, 26)
        self.setCursor(self.cursor())
        self._apply_style(active=False, is_current=False)

    def set_color(self, color: str) -> None:
        self._color = color
        self._apply_style(active=self.isChecked(), is_current=False)

    def _apply_style(self, active: bool, is_current: bool) -> None:
        if active:
            bg = self._color
            border = "#ffffff" if is_current else self._color
            border_width = "3px" if is_current else "1px"
        else:
            bg = "#1a1a2e"
            border = "#444477" if not is_current else "#ffffff"
            border_width = "3px" if is_current else "1px"

        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {bg};
                border: {border_width} solid {border};
                border-radius: 2px;
            }}
            QPushButton:hover {{
                background-color: {"#888888" if not active else self._color};
            }}
        """
        )

    def set_active(self, active: bool) -> None:
        self.setChecked(active)
        self._apply_style(active=active, is_current=False)

    def mark_current(self, is_current: bool) -> None:
        self._apply_style(active=self.isChecked(), is_current=is_current)


class StepSequencerWidget(QWidget):
    """10-row × 16-step drum pattern grid with labels and playhead."""

    pattern_changed = Signal()

    _buttons: dict[str, list[StepButton]]
    _labels: dict[str, QLabel]
    _current_step: int

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons = {}
        self._labels = {}
        self._current_step = -1

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header: step numbers 1-16 with beat group separators
        header = QWidget()
        header_layout = QGridLayout(header)
        header_layout.setContentsMargins(36, 0, 0, 0)
        header_layout.setSpacing(1)

        for step in range(16):
            label = QLabel(str(step + 1))
            label.setFixedWidth(26)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #8888a0; font-size: 9px; background: transparent;")
            header_layout.addWidget(label, 0, step)
        layout.addWidget(header)

        # Grid rows: one per drum type
        grid = QWidget()
        grid_layout = QGridLayout(grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(1)

        for row, drum_type in enumerate(DRUM_TYPES):
            # Row label
            row_label = QLabel(DRUM_LABELS.get(drum_type, drum_type))
            row_label.setFixedWidth(32)
            row_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row_label.setStyleSheet(
                f"color: {DRUM_COLORS.get(drum_type, '#888')}; font-size: 9px; "
                "font-weight: bold; background: transparent;"
            )
            grid_layout.addWidget(row_label, row, 0)
            self._labels[drum_type] = row_label

            # Step buttons
            buttons: list[StepButton] = []
            color = DRUM_COLORS.get(drum_type, "#555555")
            for col in range(16):
                btn = StepButton(color)
                btn.toggled.connect(lambda checked, dt=drum_type, c=col: self._on_step_toggled(dt, c, checked))
                grid_layout.addWidget(btn, row, col + 1)
                buttons.append(btn)

            # Beat separator markers: thicker gap every 4 steps
            if row == 0:
                for beat_sep in (4, 8, 12):
                    sep = QLabel("")
                    sep.setFixedWidth(3)
                    sep.setStyleSheet("background: transparent;")
                    grid_layout.addWidget(sep, row, col + 1 + beat_sep)

            self._buttons[drum_type] = buttons

        layout.addWidget(grid)

    def _on_step_toggled(self, drum_type: str, col: int, checked: bool) -> None:
        btn = self._buttons[drum_type][col]
        btn._apply_style(active=checked, is_current=(col == self._current_step))
        self.pattern_changed.emit()

    def get_pattern(self) -> DrumPattern:
        pattern = DrumPattern.empty()
        parts = pattern.get_parts()
        for drum_type, buttons in self._buttons.items():
            step_list = parts[drum_type]
            for col, btn in enumerate(buttons):
                step_list[col].active = btn.isChecked()
        return pattern

    def set_pattern(self, pattern: DrumPattern) -> None:
        parts = pattern.get_parts()
        for drum_type, buttons in self._buttons.items():
            step_list = parts.get(drum_type, [])
            for col, btn in enumerate(buttons):
                if col < len(step_list):
                    btn.set_active(step_list[col].active)

    def set_current_step(self, step_index: int) -> None:
        prev = self._current_step
        if prev == step_index:
            return
        self._current_step = step_index

        # Clear previous highlight
        if 0 <= prev < 16:
            for buttons in self._buttons.values():
                buttons[prev].mark_current(False)

        # Set new highlight
        if 0 <= step_index < 16:
            for buttons in self._buttons.values():
                buttons[step_index].mark_current(True)

    def clear(self) -> None:
        for buttons in self._buttons.values():
            for btn in buttons:
                btn.set_active(False)

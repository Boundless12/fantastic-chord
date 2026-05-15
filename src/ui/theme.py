"""UI theme constants and dark theme application."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

COLOR_BG = "#1e1e2e"
COLOR_SURFACE = "#2a2a3c"
COLOR_SURFACE_LIGHT = "#333350"
COLOR_ACCENT = "#7c3aed"
COLOR_ACCENT_HOVER = "#9d6fff"
COLOR_TEXT = "#e0e0e0"
COLOR_TEXT_DIM = "#8888a0"
COLOR_GRID = "#333355"
COLOR_GRID_STRONG = "#444477"
COLOR_WHITE_KEY = "#f0f0f0"
COLOR_BLACK_KEY = "#333333"
COLOR_ACTIVE_KEY = "#7c3aed"
COLOR_RECORD = "#ef4444"
COLOR_METER_LOW = "#22c55e"
COLOR_METER_MID = "#eab308"
COLOR_METER_HIGH = "#ef4444"
COLOR_KNOB_TRACK = "#444466"
COLOR_KNOB_ARC = "#7c3aed"

TRACK_COLORS: list[str] = [
    "#4ecdc4",
    "#ff6b6b",
    "#ffd93d",
    "#6bcb77",
    "#4d96ff",
    "#ff922b",
    "#845ef7",
    "#f06595",
]

FONT_FAMILY = "Segoe UI"
FONT_SIZE_SM = 10
FONT_SIZE_MD = 12
FONT_SIZE_LG = 14

DARK_STYLESHEET = """
QMainWindow {
    background-color: #1e1e2e;
    color: #e0e0e0;
}
QWidget {
    background-color: #1e1e2e;
    color: #e0e0e0;
    font-family: "Segoe UI";
    font-size: 12px;
}
QMenuBar {
    background-color: #16162a;
    border-bottom: 1px solid #333355;
    padding: 2px;
}
QMenuBar::item:selected {
    background-color: #7c3aed;
}
QMenu {
    background-color: #2a2a3c;
    border: 1px solid #444477;
    padding: 4px;
}
QMenu::item:selected {
    background-color: #7c3aed;
}
QStatusBar {
    background-color: #16162a;
    color: #8888a0;
    border-top: 1px solid #333355;
}
QDockWidget {
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}
QDockWidget::title {
    background-color: #252538;
    padding: 4px 8px;
    border-bottom: 1px solid #333355;
}
QPushButton {
    background-color: #2a2a3c;
    border: 1px solid #444477;
    border-radius: 4px;
    padding: 6px 12px;
    color: #e0e0e0;
}
QPushButton:hover {
    background-color: #333350;
    border-color: #7c3aed;
}
QPushButton:pressed {
    background-color: #7c3aed;
}
QPushButton:checked {
    background-color: #7c3aed;
}
QComboBox {
    background-color: #2a2a3c;
    border: 1px solid #444477;
    border-radius: 4px;
    padding: 4px 8px;
    color: #e0e0e0;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #2a2a3c;
    selection-background-color: #7c3aed;
    color: #e0e0e0;
}
QSpinBox {
    background-color: #2a2a3c;
    border: 1px solid #444477;
    border-radius: 4px;
    padding: 4px;
    color: #e0e0e0;
}
QSlider::groove:horizontal {
    height: 6px;
    background-color: #333350;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 14px;
    height: 14px;
    margin: -4px 0;
    background-color: #7c3aed;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background-color: #7c3aed;
    border-radius: 3px;
}
QGroupBox {
    border: 1px solid #444477;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #e0e0e0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #c0c0d0;
}
QScrollBar:vertical {
    width: 8px;
    background-color: #1e1e2e;
}
QScrollBar::handle:vertical {
    background-color: #444477;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QSplitter::handle {
    background-color: #333355;
    width: 2px;
}
QLabel {
    color: #e0e0e0;
    background-color: transparent;
}
"""


def apply_dark_theme(app: QApplication) -> None:
    """Apply dark stylesheet globally to the application."""
    app.setStyleSheet(DARK_STYLESHEET)
    font = QFont(FONT_FAMILY, FONT_SIZE_MD)
    app.setFont(font)

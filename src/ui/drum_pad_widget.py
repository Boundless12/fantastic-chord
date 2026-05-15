"""DrumPadWidget: Clickable percussion pads for auditioning drum sounds."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QPushButton, QSizePolicy

from ..sequencer.drum_pattern import DRUM_COLORS

# Longer labels for drum pad buttons
DRUM_LABELS_FULL: dict[str, str] = {
    "kick": "Kick",
    "snare": "Snare",
    "hh_closed": "HH C",
    "hh_open": "HH O",
    "clap": "Clap",
    "crash": "Crash",
    "tom_high": "Tom H",
    "tom_mid": "Tom M",
    "tom_low": "Tom L",
    "rim": "Rim",
}


class DrumPadWidget(QPushButton):
    """A single drum pad that triggers a drum sound when clicked."""

    drum_triggered = Signal(str)

    _drum_type: str
    _base_color: str
    _flash_timer: QTimer | None

    def __init__(self, drum_type: str, parent: DrumPadWidget | None = None) -> None:
        super().__init__(parent)
        self._drum_type = drum_type
        self._base_color = DRUM_COLORS.get(drum_type, "#666666")
        self._flash_timer = None

        label = DRUM_LABELS_FULL.get(drum_type, drum_type)
        self.setText(label)
        self.setCheckable(False)
        self.setMinimumSize(72, 48)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(self.cursor())  # keep default

        self._update_style(self._base_color)
        self.clicked.connect(self._on_click)

    def _update_style(self, color: str) -> None:
        darker = self._darken(color, 0.6)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {darker};
                border: 2px solid {color};
                border-radius: 8px;
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {color};
                border-color: {self._lighten(color, 0.3)};
            }}
            QPushButton:pressed {{
                background-color: {self._lighten(color, 0.2)};
                border-color: #ffffff;
            }}
        """
        )

    def _on_click(self) -> None:
        self.drum_triggered.emit(self._drum_type)
        self._flash()

    def _flash(self) -> None:
        lighter = self._lighten(self._base_color, 0.4)
        self._update_style(lighter)
        if self._flash_timer is not None:
            self._flash_timer.stop()
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._unflash)
        self._flash_timer.start(80)

    def _unflash(self) -> None:
        self._update_style(self._base_color)

    @staticmethod
    def _darken(hex_color: str, factor: float) -> str:
        r = int(int(hex_color[1:3], 16) * factor)
        g = int(int(hex_color[3:5], 16) * factor)
        b = int(int(hex_color[5:7], 16) * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _lighten(hex_color: str, amount: float) -> str:
        r = min(255, int(int(hex_color[1:3], 16) + 255 * amount))
        g = min(255, int(int(hex_color[3:5], 16) + 255 * amount))
        b = min(255, int(int(hex_color[5:7], 16) + 255 * amount))
        return f"#{r:02x}{g:02x}{b:02x}"

    @property
    def drum_type(self) -> str:
        return self._drum_type

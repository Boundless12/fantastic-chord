"""MidiHandler: Real-time MIDI I/O via python-rtmidi."""

from __future__ import annotations

import logging
from collections.abc import Callable

import rtmidi

from .event import MidiEvent, MidiParser

logger = logging.getLogger(__name__)


class MidiHandler:
    """Real-time MIDI input/output handler wrapping python-rtmidi."""

    _midi_in: rtmidi.MidiIn | None
    _midi_out: rtmidi.MidiOut | None
    _on_event: Callable[[MidiEvent], None] | None

    def __init__(self, on_event: Callable[[MidiEvent], None] | None = None) -> None:
        self._midi_in = None
        self._midi_out = None
        self._on_event = on_event

    def set_callback(self, callback: Callable[[MidiEvent], None]) -> None:
        self._on_event = callback

    def list_input_ports(self) -> list[str]:
        try:
            midi_in = rtmidi.MidiIn()
            ports: list[str] = midi_in.get_ports()
            del midi_in
            return ports
        except Exception as e:
            logger.warning(f"Failed to list MIDI input ports: {e}")
            return []

    def list_output_ports(self) -> list[str]:
        try:
            midi_out = rtmidi.MidiOut()
            ports: list[str] = midi_out.get_ports()
            del midi_out
            return ports
        except Exception as e:
            logger.warning(f"Failed to list MIDI output ports: {e}")
            return []

    def open_input(self, port_name: str | None = None) -> str | None:
        """Open a MIDI input port. Returns the port name, or None on failure."""
        try:
            self._midi_in = rtmidi.MidiIn()
            ports = self._midi_in.get_ports()

            if not ports:
                logger.warning("No MIDI input ports available")
                self._midi_in = None
                return None

            target: str = port_name if port_name else ports[0]
            if target not in ports:
                logger.warning(f"MIDI input port '{target}' not found, using '{ports[0]}'")
                target = ports[0]

            self._midi_in.open_port(ports.index(target))
            self._midi_in.set_callback(self._midi_callback)
            logger.info(f"Opened MIDI input: {target}")
            return target
        except Exception as e:
            logger.error(f"Failed to open MIDI input: {e}")
            self._midi_in = None
            return None

    def open_output(self, port_name: str | None = None) -> str | None:
        """Open a MIDI output port. Returns the port name, or None on failure."""
        try:
            self._midi_out = rtmidi.MidiOut()
            ports = self._midi_out.get_ports()

            if not ports:
                logger.warning("No MIDI output ports available. Creating virtual port.")
                self._midi_out.open_virtual_port("CoolChord Out")
                return "CoolChord Out (virtual)"

            target: str = port_name if port_name else ports[0]
            if target not in ports:
                logger.warning(f"MIDI output port '{target}' not found, using '{ports[0]}'")
                target = ports[0]

            self._midi_out.open_port(ports.index(target))
            logger.info(f"Opened MIDI output: {target}")
            return target
        except Exception as e:
            logger.error(f"Failed to open MIDI output: {e}")
            self._midi_out = None
            return None

    def open_virtual_input(self, name: str = "CoolChord In") -> bool:
        """Open a virtual MIDI input port (for receiving MIDI from other apps)."""
        try:
            self._midi_in = rtmidi.MidiIn()
            self._midi_in.open_virtual_port(name)
            self._midi_in.set_callback(self._midi_callback)
            logger.info(f"Opened virtual MIDI input: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to open virtual MIDI input: {e}")
            return False

    def open_virtual_output(self, name: str = "CoolChord Out") -> bool:
        """Open a virtual MIDI output port (for sending MIDI to other apps)."""
        try:
            self._midi_out = rtmidi.MidiOut()
            self._midi_out.open_virtual_port(name)
            logger.info(f"Opened virtual MIDI output: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to open virtual MIDI output: {e}")
            return False

    def send(self, event: MidiEvent) -> None:
        """Send a MidiEvent to the output port."""
        if self._midi_out is None:
            logger.warning("MIDI output not open, cannot send")
            return
        try:
            status, data1, data2 = MidiParser.to_midi_bytes(event)
            self._midi_out.send_message([status, data1, data2])
        except Exception as e:
            logger.error(f"Failed to send MIDI message: {e}")

    def send_raw(self, message: list[int]) -> None:
        """Send raw MIDI bytes."""
        if self._midi_out is None:
            return
        try:
            self._midi_out.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send raw MIDI: {e}")

    def is_input_open(self) -> bool:
        return self._midi_in is not None

    def is_output_open(self) -> bool:
        return self._midi_out is not None

    def close(self) -> None:
        if self._midi_in is not None:
            try:
                self._midi_in.close_port()
                del self._midi_in
            except Exception:
                pass
            self._midi_in = None
        if self._midi_out is not None:
            try:
                self._midi_out.close_port()
                del self._midi_out
            except Exception:
                pass
            self._midi_out = None
        logger.info("MIDI handler closed")

    def _midi_callback(self, message: tuple[float, list[int]], data: object = None) -> None:  # noqa: ARG002
        """Internal rtmidi callback. Runs on rtmidi's thread."""
        timestamp, msg_bytes = message
        if len(msg_bytes) < 2:
            return

        status = msg_bytes[0]
        data1 = msg_bytes[1]
        data2 = msg_bytes[2] if len(msg_bytes) > 2 else 0

        event = MidiParser.parse(status, data1, data2, timestamp)
        if event is not None and self._on_event is not None:
            try:
                self._on_event(event)
            except Exception as e:
                logger.error(f"Error in MIDI event callback: {e}")

"""Passive RS485 receiver and frame logger for Tigo TAP Local."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone

import serial

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import CONF_BAUDRATE, CONF_SERIAL_PORT, DEFAULT_BAUDRATE, SIGNAL_FRAME

_LOGGER = logging.getLogger(__name__)

START = b"\x7e\x07"
END = b"\x7e\x08"
MAX_BUFFER = 8192


class TapReceiver:
    """Receive bytes from TAP/CCA RS485 and extract observed framed traffic.

    This class never writes to the serial port.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.port = entry.data[CONF_SERIAL_PORT]
        self.baudrate = entry.data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)
        self._serial: serial.Serial | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.bytes_received = 0
        self.frames_received = 0
        self.last_frame_hex: str | None = None
        self.last_frame_time: str | None = None
        self.connected = False

    def start(self) -> None:
        """Start passive serial reader."""
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="tigo-tap-rs485", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop reader."""
        self._stop.set()
        if self._serial is not None:
            try:
                self._serial.close()
            except serial.SerialException:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run(self) -> None:
        buffer = bytearray()
        while not self._stop.is_set():
            try:
                with serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=0.25,
                    write_timeout=0,
                ) as ser:
                    self._serial = ser
                    self.connected = True
                    self._notify()
                    _LOGGER.info(
                        "Passive Tigo TAP RS485 receiver opened %s at %s 8N1",
                        self.port,
                        self.baudrate,
                    )
                    while not self._stop.is_set():
                        chunk = ser.read(512)
                        if not chunk:
                            continue
                        self.bytes_received += len(chunk)
                        _LOGGER.debug("RS485 RX raw: %s", chunk.hex(" "))
                        buffer.extend(chunk)
                        self._extract_frames(buffer)
                        if len(buffer) > MAX_BUFFER:
                            del buffer[:-64]
                        self._notify()
            except (serial.SerialException, OSError) as err:
                self.connected = False
                self._notify()
                _LOGGER.warning("RS485 receiver error on %s: %s", self.port, err)
                if not self._stop.wait(5):
                    continue
            finally:
                self.connected = False
                self._serial = None
                self._notify()

    def _extract_frames(self, buffer: bytearray) -> None:
        while True:
            start = buffer.find(START)
            if start < 0:
                if len(buffer) > 1:
                    del buffer[:-1]
                return
            if start:
                del buffer[:start]

            end = buffer.find(END, len(START))
            if end < 0:
                return

            end += len(END)
            frame = bytes(buffer[:end])
            del buffer[:end]
            self.frames_received += 1
            self.last_frame_hex = frame.hex(" ").upper()
            self.last_frame_time = datetime.now(timezone.utc).isoformat()
            _LOGGER.info(
                "Tigo RS485 frame #%d (%d bytes): %s",
                self.frames_received,
                len(frame),
                self.last_frame_hex,
            )

    def _notify(self) -> None:
        self.hass.loop.call_soon_threadsafe(
            async_dispatcher_send, self.hass, SIGNAL_FRAME
        )

"""Passive RS485 receiver and persistent frame logger for Tigo TAP Local."""
from __future__ import annotations
from collections import deque
import csv
import logging
from pathlib import Path
import threading
from datetime import datetime, timezone
import serial
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from .const import CONF_BAUDRATE, CONF_SERIAL_PORT, DEFAULT_BAUDRATE, SIGNAL_FRAME

_LOGGER=logging.getLogger(__name__)
START=b"\x7e\x07"; END=b"\x7e\x08"; MAX_BUFFER=8192; FRAME_HISTORY_SIZE=500

class TapReceiver:
    """Receive-only TAP/CCA RS485 logger. Never transmits."""
    def __init__(self,hass:HomeAssistant,entry:ConfigEntry)->None:
        self.hass=hass; self.port=entry.data[CONF_SERIAL_PORT]; self.baudrate=entry.data.get(CONF_BAUDRATE,DEFAULT_BAUDRATE)
        self._serial=None; self._thread=None; self._stop=threading.Event()
        self.bytes_received=0; self.frames_received=0; self.last_frame_hex=None; self.last_frame_time=None; self.last_frame_length=0; self.connected=False
        self.frame_history=deque(maxlen=FRAME_HISTORY_SIZE)
        self.capture_dir=Path(hass.config.path("www","tigo_tap_local")); self.csv_path=self.capture_dir/"frames.csv"; self.log_path=self.capture_dir/"frames.log"

    def start(self):
        self.capture_dir.mkdir(parents=True,exist_ok=True)
        if not self.csv_path.exists():
            with self.csv_path.open("w",newline="",encoding="utf-8") as f: csv.writer(f).writerow(["number","timestamp_utc","length","hex"])
        if self._thread and self._thread.is_alive(): return
        self._stop.clear(); self._thread=threading.Thread(target=self._run,name="tigo-tap-rs485",daemon=True); self._thread.start()

    def stop(self):
        self._stop.set()
        if self._serial is not None:
            try:self._serial.close()
            except serial.SerialException:pass
        if self._thread and self._thread.is_alive():self._thread.join(timeout=2)

    def _run(self):
        buffer=bytearray()
        while not self._stop.is_set():
            try:
                with serial.Serial(port=self.port,baudrate=self.baudrate,bytesize=serial.EIGHTBITS,parity=serial.PARITY_NONE,stopbits=serial.STOPBITS_ONE,timeout=.25,write_timeout=0) as ser:
                    self._serial=ser; self.connected=True; self._notify(); _LOGGER.info("Passive RS485 receiver opened %s at %s 8N1",self.port,self.baudrate)
                    while not self._stop.is_set():
                        chunk=ser.read(512)
                        if not chunk:continue
                        self.bytes_received+=len(chunk); _LOGGER.debug("RS485 RX raw: %s",chunk.hex(" ")); buffer.extend(chunk); self._extract_frames(buffer)
                        if len(buffer)>MAX_BUFFER:del buffer[:-64]
                        self._notify()
            except (serial.SerialException,OSError) as err:
                self.connected=False; self._notify(); _LOGGER.warning("RS485 receiver error on %s: %s",self.port,err)
                if not self._stop.wait(5):continue
            finally:self.connected=False; self._serial=None; self._notify()

    def _extract_frames(self,buffer):
        while True:
            start=buffer.find(START)
            if start<0:
                if len(buffer)>1:del buffer[:-1]
                return
            if start:del buffer[:start]
            end=buffer.find(END,len(START))
            if end<0:return
            end+=len(END); frame=bytes(buffer[:end]); del buffer[:end]
            ts=datetime.now(timezone.utc).isoformat(); hx=frame.hex(" ").upper(); self.frames_received+=1; self.last_frame_hex=hx; self.last_frame_time=ts; self.last_frame_length=len(frame)
            record={"number":self.frames_received,"timestamp_utc":ts,"length":len(frame),"hex":hx}; self.frame_history.append(record); self._persist(record)
            _LOGGER.info("Tigo RS485 frame #%d (%d bytes): %s",self.frames_received,len(frame),hx); self._notify()

    def _persist(self,r):
        try:
            with self.csv_path.open("a",newline="",encoding="utf-8") as f: csv.writer(f).writerow([r["number"],r["timestamp_utc"],r["length"],r["hex"]])
            with self.log_path.open("a",encoding="utf-8") as f: f.write(f'{r["timestamp_utc"]} #{r["number"]} {r["length"]}B {r["hex"]}\n')
        except OSError as err:_LOGGER.warning("Could not persist frame capture: %s",err)

    def recent_frames(self,count=20):return list(reversed(list(self.frame_history)[-count:]))
    @property
    def csv_url(self):return "/local/tigo_tap_local/frames.csv"
    @property
    def log_url(self):return "/local/tigo_tap_local/frames.log"
    def _notify(self):self.hass.loop.call_soon_threadsafe(async_dispatcher_send,self.hass,SIGNAL_FRAME)

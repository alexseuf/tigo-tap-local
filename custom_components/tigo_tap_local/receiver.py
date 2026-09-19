"""Passive RS485 receiver with rotating raw capture and ZIP export."""
from __future__ import annotations
from collections import deque
import csv, json, logging, threading, zipfile
from pathlib import Path
from datetime import datetime, timezone
import serial
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from .const import CONF_BAUDRATE, CONF_SERIAL_PORT, DEFAULT_BAUDRATE, SIGNAL_FRAME
from .decoder import TapProtocolDecoder

_LOGGER=logging.getLogger(__name__)
START=b"\x7e\x07"; END=b"\x7e\x08"; MAX_BUFFER=8192; FRAME_HISTORY_SIZE=500
MAX_FILE_BYTES=10*1024*1024; ROTATED_FILES=10

class TapReceiver:
    """Receive-only TAP/CCA logger. Persistent data is stored once as raw text."""
    def __init__(self,hass:HomeAssistant,entry:ConfigEntry)->None:
        self.hass=hass; self.port=entry.data[CONF_SERIAL_PORT]; self.baudrate=entry.data.get(CONF_BAUDRATE,DEFAULT_BAUDRATE)
        self._serial=None; self._thread=None; self._stop=threading.Event()
        self.bytes_received=0; self.frames_received=0; self.last_frame_hex=None; self.last_frame_time=None; self.last_frame_length=0; self.connected=False
        self.frame_history=deque(maxlen=FRAME_HISTORY_SIZE)
        self.capture_dir=Path(hass.config.path("www","tigo_tap_local")); self.raw_path=self.capture_dir/"capture.raw"
        self.identity_path=Path(hass.config.path(".storage","tigo_tap_local_nodes.json"))
        identities=self._load_identities()
        self.decoder=TapProtocolDecoder(identities)
        self._saved_identities=self.decoder.persistent_snapshot()
        self.zip_path=self.capture_dir/"tigo-tap-diagnostics.zip"

    def start(self):
        self.capture_dir.mkdir(parents=True,exist_ok=True)
        if self._thread and self._thread.is_alive():return
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
                    self._serial=ser; self.connected=True; self._notify()
                    while not self._stop.is_set():
                        chunk=ser.read(512)
                        if not chunk:continue
                        self.bytes_received+=len(chunk); buffer.extend(chunk); self._extract_frames(buffer)
                        if len(buffer)>MAX_BUFFER:del buffer[:-64]
                        self._notify()
            except (serial.SerialException,OSError) as err:
                self.connected=False; self._notify(); _LOGGER.warning("RS485 error on %s: %s",self.port,err)
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
            ts=datetime.now(timezone.utc).isoformat(); hx=frame.hex(" ").upper(); self.frames_received+=1
            self.last_frame_hex=hx; self.last_frame_time=ts; self.last_frame_length=len(frame)
            r={"number":self.frames_received,"timestamp_utc":ts,"length":len(frame),"hex":hx}; self.frame_history.append(r)
            self.decoder.consume_wire_frame(frame); self._persist_identities_if_changed(); self._persist(r); self._notify()

    def _load_identities(self):
        try:
            if self.identity_path.exists():
                data=json.loads(self.identity_path.read_text(encoding="utf-8"))
                return data if isinstance(data,dict) else {}
        except (OSError,json.JSONDecodeError) as err:
            _LOGGER.warning("Could not load persisted Tigo node identities: %s",err)
        return {}

    def _persist_identities_if_changed(self):
        identities=self.decoder.persistent_snapshot()
        if identities==self._saved_identities:return
        try:
            self.identity_path.parent.mkdir(parents=True,exist_ok=True)
            tmp=self.identity_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(identities,indent=2,sort_keys=True),encoding="utf-8")
            tmp.replace(self.identity_path)
            self._saved_identities=identities
        except OSError as err:
            _LOGGER.warning("Could not persist Tigo node identities: %s",err)

    def _rotate(self):
        if not self.raw_path.exists() or self.raw_path.stat().st_size<MAX_FILE_BYTES:return
        oldest=self.capture_dir/f"capture.raw.{ROTATED_FILES}"
        if oldest.exists():oldest.unlink()
        for i in range(ROTATED_FILES-1,0,-1):
            src=self.capture_dir/f"capture.raw.{i}"; dst=self.capture_dir/f"capture.raw.{i+1}"
            if src.exists():src.replace(dst)
        self.raw_path.replace(self.capture_dir/"capture.raw.1")

    def _persist(self,r):
        try:
            self._rotate()
            with self.raw_path.open("a",encoding="utf-8") as f:f.write(f'{r["number"]}\t{r["timestamp_utc"]}\t{r["length"]}\t{r["hex"]}\n')
        except OSError as err:_LOGGER.warning("Could not persist capture: %s",err)

    def _raw_files(self):
        files=[p for p in [self.raw_path]+[self.capture_dir/f"capture.raw.{i}" for i in range(1,ROTATED_FILES+1)] if p.exists()]
        return sorted(files,key=lambda p:p.name,reverse=True)

    def create_diagnostics_zip(self):
        """Create one downloadable ZIP containing CSV, LOG, raw captures and system info."""
        rows=[]
        for p in reversed(self._raw_files()):
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    parts=line.split("\t",3)
                    if len(parts)==4:rows.append(parts)
            except OSError as err:_LOGGER.warning("Could not read %s: %s",p,err)
        csv_file=self.capture_dir/"frames-export.csv"; log_file=self.capture_dir/"frames-export.log"
        with csv_file.open("w",newline="",encoding="utf-8") as f:
            w=csv.writer(f); w.writerow(["number","timestamp_utc","length","hex"]); w.writerows(rows)
        with log_file.open("w",encoding="utf-8") as f:
            for n,ts,length,hx in rows:f.write(f"{ts} #{n} {length}B {hx}\n")
        info=self.capture_dir/"system-info.txt"
        info.write_text(f"Tigo TAP Local diagnostics\nGenerated: {datetime.now(timezone.utc).isoformat()}\nMode: passive_rx_only\nSerial port: {self.port}\nBaudrate: {self.baudrate}\nFrames this session: {self.frames_received}\nBytes this session: {self.bytes_received}\nRotation: {ROTATED_FILES} x {MAX_FILE_BYTES//1024//1024} MiB\nCRC valid: {self.decoder.crc_valid}\nCRC errors: {self.decoder.crc_errors}\nDecode errors: {self.decoder.decode_errors}\nReceive responses: {self.decoder.receive_responses}\nPV packets: {self.decoder.pv_packets}\nPower reports: {self.decoder.power_reports}\nRejected power reports: {self.decoder.power_report_rejected}\nTopology reports: {self.decoder.topology_reports}\n",encoding="utf-8")
        with zipfile.ZipFile(self.zip_path,"w",zipfile.ZIP_DEFLATED) as z:
            z.write(csv_file,"frames.csv"); z.write(log_file,"frames.log"); z.write(info,"system-info.txt")
            for p in self._raw_files():z.write(p,p.name)
        csv_file.unlink(missing_ok=True); log_file.unlink(missing_ok=True); info.unlink(missing_ok=True)
        self._notify(); return self.zip_path

    def recent_frames(self,count=20):return list(reversed(list(self.frame_history)[-count:]))
    @property
    def zip_url(self):return "/local/tigo_tap_local/tigo-tap-diagnostics.zip"
    def _notify(self):self.hass.loop.call_soon_threadsafe(async_dispatcher_send,self.hass,SIGNAL_FRAME)

"""Passive decoder for Tigo CCA <-> TAP traffic.

Protocol layout follows the interoperability work documented by willglynn/taptap.
This module is intentionally receive-only.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

_ESC={0x00:0x7E,0x01:0x24,0x02:0x23,0x03:0x25,0x04:0xA4,0x05:0xA3,0x06:0xA5}

@dataclass
class NodeTelemetry:
    node_id:int
    serial:str|None=None
    long_address:str|None=None
    voltage_in:float|None=None
    voltage_out:float|None=None
    current_in:float|None=None
    current_out:float|None=None
    power:float|None=None
    duty_cycle:float|None=None
    temperature:float|None=None
    rssi:int|None=None
    slot_counter:int|None=None
    last_seen:str|None=None
    reports:int=0

class TapProtocolDecoder:
    def __init__(self)->None:
        self.packet_numbers={}
        self.nodes={}
        self.power_reports=0
        self.topology_reports=0
        self.pv_packets=0
        self.decode_errors=0

    @staticmethod
    def _unescape(data:bytes)->bytes:
        out=bytearray(); i=0
        while i<len(data):
            if data[i]==0x7E and i+1<len(data) and data[i+1] in _ESC:
                out.append(_ESC[data[i+1]]); i+=2
            else:
                out.append(data[i]); i+=1
        return bytes(out)

    @staticmethod
    def _barcode(addr:bytes)->str|None:
        if len(addr)!=8 or addr[:3]!=b"\x04\xc0\x5b":
            return None
        n2h="0123456789ABCDEF"
        nibbles=[addr[3]&15,addr[4]>>4,addr[4]&15,addr[5]>>4,addr[5]&15,addr[6]>>4,addr[6]&15,addr[7]>>4,addr[7]&15]
        middle="".join(n2h[n] for n in nibbles).lstrip("0") or "0"
        table=[0x0,0x3,0x6,0x5,0xc,0xf,0xa,0x9,0xb,0x8,0xd,0xe,0x7,0x4,0x1,0x2,0x5,0x6,0x3,0x0,0x9,0xa,0xf,0xc,0xe,0xd,0x8,0xb,0x2,0x1,0x4,0x7,0xa,0x9,0xc,0xf,0x6,0x5,0x0,0x3,0x1,0x2,0x7,0x4,0xd,0xe,0xb,0x8,0xf,0xc,0x9,0xa,0x3,0x0,0x5,0x6,0x4,0x7,0x2,0x1,0x8,0xb,0xe,0xd,0x7,0x4,0x1,0x2,0xb,0x8,0xd,0xe,0xc,0xf,0xa,0x9,0x0,0x3,0x6,0x5,0x2,0x1,0x4,0x7,0xe,0xd,0x8,0xb,0x9,0xa,0xf,0xc,0x5,0x6,0x3,0x0,0xd,0xe,0xb,0x8,0x1,0x2,0x7,0x4,0x6,0x5,0x0,0x3,0xa,0x9,0xc,0xf,0x8,0xb,0xe,0xd,0x4,0x7,0x2,0x1,0x3,0x0,0x5,0x6,0xf,0xc,0x9,0xa,0xe,0xd,0x8,0xb,0x2,0x1,0x4,0x7,0x5,0x6,0x3,0x0,0x9,0xa,0xf,0xc,0xb,0x8,0xd,0xe,0x7,0x4,0x1,0x2,0x0,0x3,0x6,0x5,0xc,0xf,0xa,0x9,0x4,0x7,0x2,0x1,0x8,0xb,0xe,0xd,0xf,0xc,0x9,0xa,0x3,0x0,0x5,0x6,0x1,0x2,0x7,0x4,0xd,0xe,0xb,0x8,0xa,0x9,0xc,0xf,0x6,0x5,0x0,0x3,0x9,0xa,0xf,0xc,0x5,0x6,0x3,0x0,0x2,0x1,0x4,0x7,0xe,0xd,0x8,0xb,0xc,0xf,0xa,0x9,0x0,0x3,0x6,0x5,0x7,0x4,0x1,0x2,0xb,0x8,0xd,0xe,0x3,0x0,0x5,0x6,0xf,0xc,0x9,0xa,0x8,0xb,0xe,0xd,0x4,0x7,0x2,0x1,0x6,0x5,0x0,0x3,0xa,0x9,0xc,0xf,0xd,0xe,0xb,0x8,0x1,0x2,0x7,0x4]
        c=2
        for b in addr:c=table[b^(c<<4)]
        check="GHJKLMNPRSTVWXYZ"[c]
        return f"{n2h[addr[3]>>4]}-{middle}{check}"

    @staticmethod
    def _u12pair(data:bytes)->tuple[int,int]:
        return ((data[0]<<4)|(data[1]>>4),((data[1]&15)<<8)|data[2])

    def consume_wire_frame(self,wire:bytes)->None:
        try:
            if not (wire.startswith(b"\x7e\x07") and wire.endswith(b"\x7e\x08")): return
            body=self._unescape(wire[2:-2])
            if len(body)<6:return
            addr=int.from_bytes(body[0:2],"big"); ftype=int.from_bytes(body[2:4],"big")
            payload=body[4:-2]; gateway=addr&0x7FFF
            if ftype==0x0148 and not(addr&0x8000) and len(payload)>=4:
                self.packet_numbers[gateway]=int.from_bytes(payload[2:4],"big")
            elif ftype==0x0149 and (addr&0x8000):
                self._receive_response(gateway,payload)
        except (IndexError,ValueError,OverflowError):
            self.decode_errors+=1

    def _receive_response(self,gateway:int,payload:bytes)->None:
        if gateway not in self.packet_numbers or len(payload)<2:return
        status=int.from_bytes(payload[:2],"big")
        if status&0x00E0!=0x00E0:return
        rest=payload[2:]; pos=0
        def take(n):
            nonlocal pos
            if pos+n>len(rest):raise ValueError
            v=rest[pos:pos+n];pos+=n;return v
        if status&1==0:take(1)
        if status&2==0:take(1)
        if status&4==0:take(2)
        if status&8==0:take(2)
        old=self.packet_numbers[gateway]
        if status&0x10==0:new=int.from_bytes(take(2),"big")
        else:
            lo=take(1)[0]; old_hi=old>>8; old_lo=old&255
            new=(((old_hi if lo>=old_lo else (old_hi+1)&255)<<8)|lo)
        self.packet_numbers[gateway]=new
        take(2) # gateway slot counter
        packets=rest[pos:]
        while packets:
            if len(packets)<7:raise ValueError
            ptype=packets[0]; node=int.from_bytes(packets[1:3],"big"); length=packets[6]
            if len(packets)<7+length:raise ValueError
            data=packets[7:7+length]; packets=packets[7+length:]
            self.pv_packets+=1
            if ptype==0x31:self._power(node,data)
            elif ptype==0x09:self._topology(node,data)

    def _node(self,node:int)->NodeTelemetry:
        return self.nodes.setdefault(node,NodeTelemetry(node_id=node))

    def _power(self,node:int,data:bytes)->None:
        if len(data) not in (13,15):return
        vin,vout=self._u12pair(data[0:3]); current,temp=self._u12pair(data[4:7])
        vin*=0.05; vout*=0.10; iin=current*0.005; power=vin*iin
        n=self._node(node); n.voltage_in=round(vin,2); n.voltage_out=round(vout,2)
        n.current_in=round(iin,3); n.current_out=round(power/vout,3) if vout else None
        n.power=round(power,1); n.duty_cycle=round(data[3]*100/255,2); n.temperature=round(temp*0.1,1)
        n.slot_counter=int.from_bytes(data[10:12],"big"); n.rssi=data[12]
        n.last_seen=datetime.now(timezone.utc).isoformat(); n.reports+=1; self.power_reports+=1

    def _topology(self,node:int,data:bytes)->None:
        if len(data)!=23:return
        long_addr=data[8:16]
        n=self._node(node); n.long_address=":".join(f"{b:02X}" for b in long_addr); n.serial=self._barcode(long_addr)
        n.last_seen=datetime.now(timezone.utc).isoformat(); self.topology_reports+=1

    def snapshot(self)->dict:
        return {f"{node:04X}":asdict(value) for node,value in sorted(self.nodes.items())}

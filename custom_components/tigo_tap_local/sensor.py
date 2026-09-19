"""Diagnostic sensors for Tigo TAP Local."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DATA_RECEIVER, DOMAIN, SIGNAL_FRAME


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    receiver = hass.data[DOMAIN][entry.entry_id][DATA_RECEIVER]
    async_add_entities([
        TapStatusSensor(entry, receiver),
        TapFramesSensor(entry, receiver),
        TapBytesSensor(entry, receiver),
        TapLastFrameSensor(entry, receiver),
        TapFrameHistorySensor(entry, receiver),
        TapDecodedNodesSensor(entry, receiver),
        TapPowerReportsSensor(entry, receiver),
    ])

    known_nodes = set()

    def add_node_entities() -> None:
        new_nodes = sorted(set(receiver.decoder.nodes) - known_nodes)
        if not new_nodes:
            return
        known_nodes.update(new_nodes)
        async_add_entities(
            [TapNodeStatusSensor(entry, receiver, node_id) for node_id in new_nodes]
        )

    add_node_entities()
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_FRAME, add_node_entities)
    )


class TapSensorBase(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, entry, receiver, key, name):
        self.entry = entry
        self.receiver = receiver
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._remove_dispatcher = None

    async def async_added_to_hass(self):
        self._remove_dispatcher = async_dispatcher_connect(self.hass, SIGNAL_FRAME, self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        if self._remove_dispatcher:
            self._remove_dispatcher()


class TapStatusSensor(TapSensorBase):
    def __init__(self, entry, receiver):
        super().__init__(entry, receiver, "status", "RS485 status")
    @property
    def native_value(self):
        return "connected" if self.receiver.connected else "disconnected"


class TapFramesSensor(TapSensorBase):
    _attr_native_unit_of_measurement = "frames"
    def __init__(self, entry, receiver):
        super().__init__(entry, receiver, "frames", "Received frames")
    @property
    def native_value(self):
        return self.receiver.frames_received


class TapBytesSensor(TapSensorBase):
    _attr_native_unit_of_measurement = "B"
    def __init__(self, entry, receiver):
        super().__init__(entry, receiver, "bytes", "Received bytes")
    @property
    def native_value(self):
        return self.receiver.bytes_received


class TapLastFrameSensor(TapSensorBase):
    def __init__(self, entry, receiver):
        super().__init__(entry, receiver, "last_frame", "Last frame")
    @property
    def native_value(self):
        if not self.receiver.last_frame_hex:
            return "none"
        value = self.receiver.last_frame_hex
        return value if len(value) <= 255 else value[:252] + "..."
    @property
    def extra_state_attributes(self):
        return {
            "timestamp_utc": self.receiver.last_frame_time,
            "length": self.receiver.last_frame_length,
            "full_frame_hex": self.receiver.last_frame_hex,
            "serial_port": self.receiver.port,
            "baudrate": self.receiver.baudrate,
            "mode": "passive_rx_only",
        }


class TapFrameHistorySensor(TapSensorBase):
    """Expose a compact recent-frame list for HA diagnostics."""

    def __init__(self, entry, receiver):
        super().__init__(entry, receiver, "frame_history", "Frame logger")

    @property
    def native_value(self):
        return len(self.receiver.frame_history)

    @property
    def extra_state_attributes(self):
        # Keep HA state attributes bounded; full in-memory buffer remains 500 frames.
        recent = self.receiver.recent_frames(20)
        return {
            "buffered_frames": len(self.receiver.frame_history),
            "buffer_capacity": 500,
            "recent_20": recent,
            "note": "Newest frame first; full 500-frame buffer is kept in memory.",
            "diagnostics_zip": self.receiver.zip_url,
            "download_hint": "Press Diagnosepaket erstellen, then open diagnostics_zip.",
        }


class TapDecodedNodesSensor(TapSensorBase):
    """Nodes recognized from passive PV traffic."""
    def __init__(self, entry, receiver):
        super().__init__(entry, receiver, "decoded_nodes", "Decoded nodes")
    @property
    def native_value(self):
        return len(self.receiver.decoder.nodes)
    @property
    def extra_state_attributes(self):
        return {
            "nodes": self.receiver.decoder.snapshot(),
            "topology_reports": self.receiver.decoder.topology_reports,
            "pv_packets": self.receiver.decoder.pv_packets,
            "decode_errors": self.receiver.decoder.decode_errors,
            "note": "Serial becomes available after a topology report for that node is observed.",
        }

class TapPowerReportsSensor(TapSensorBase):
    """Number of successfully decoded TS4 power reports."""
    def __init__(self, entry, receiver):
        super().__init__(entry, receiver, "power_reports", "Decoded power reports")
    @property
    def native_value(self):
        return self.receiver.decoder.power_reports


class TapNodeStatusSensor(TapSensorBase):
    """One lightweight entity per TS4 node so Home Assistant creates a device."""

    _attr_icon = "mdi:solar-panel"

    def __init__(self, entry, receiver, node_id):
        self.node_id = node_id
        super().__init__(entry, receiver, f"node_{node_id:04x}_status", "Status")

    @property
    def _node(self):
        return self.receiver.decoder.nodes.get(self.node_id)

    @property
    def device_info(self):
        node = self._node
        serial = node.serial if node else None
        name = f"Tigo TS4 {serial}" if serial else f"Tigo TS4 Node {self.node_id}"
        info = DeviceInfo(
            identifiers={(DOMAIN, f"{self.entry.entry_id}_node_{self.node_id}")},
            name=name,
            manufacturer="Tigo Energy",
            model="TS4",
        )
        if serial:
            info["serial_number"] = serial
        return info

    @property
    def native_value(self):
        node = self._node
        return "online" if node and node.last_seen else "discovered"

    @property
    def extra_state_attributes(self):
        node = self._node
        if node is None:
            return {"node_id": self.node_id}
        return {
            "node_id": self.node_id,
            "node_id_hex": f"{self.node_id:04X}",
            "serial": node.serial,
            "long_address": node.long_address,
            "last_seen": node.last_seen,
            "power_reports": node.reports,
            "identity_persisted": bool(node.serial or node.long_address),
        }

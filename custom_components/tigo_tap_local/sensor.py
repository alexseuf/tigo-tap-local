"""Diagnostic sensors for Tigo TAP Local."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_RECEIVER, DOMAIN, SIGNAL_FRAME


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    receiver = hass.data[DOMAIN][entry.entry_id][DATA_RECEIVER]
    async_add_entities([
        TapStatusSensor(entry, receiver),
        TapFramesSensor(entry, receiver),
        TapBytesSensor(entry, receiver),
        TapLastFrameSensor(entry, receiver),
        TapFrameHistorySensor(entry, receiver),
    ])


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
        }

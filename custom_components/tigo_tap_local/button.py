"""Buttons for Tigo TAP Local."""
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DATA_RECEIVER, DOMAIN

async def async_setup_entry(hass:HomeAssistant,entry:ConfigEntry,async_add_entities:AddEntitiesCallback)->None:
    async_add_entities([DiagnosticsZipButton(entry,hass.data[DOMAIN][entry.entry_id][DATA_RECEIVER])])

class DiagnosticsZipButton(ButtonEntity):
    _attr_has_entity_name=True
    _attr_name="Diagnosepaket erstellen"
    _attr_icon="mdi:folder-zip"
    def __init__(self,entry,receiver):
        self._attr_unique_id=f"{entry.entry_id}_create_diagnostics_zip"; self.receiver=receiver
    async def async_press(self)->None:
        await self.hass.async_add_executor_job(self.receiver.create_diagnostics_zip)

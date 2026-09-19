"""Tigo TAP Local Home Assistant integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_RECEIVER, DOMAIN, PLATFORMS
from .receiver import TapReceiver


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tigo TAP Local from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    receiver = TapReceiver(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = {DATA_RECEIVER: receiver}

    await hass.async_add_executor_job(receiver.start)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, {})
    receiver = data.get(DATA_RECEIVER)
    if receiver is not None:
        await hass.async_add_executor_job(receiver.stop)
    return unloaded

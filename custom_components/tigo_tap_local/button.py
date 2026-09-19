"""Buttons for Tigo TAP Local."""
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components import persistent_notification
from .const import DATA_RECEIVER, DOMAIN

async def async_setup_entry(hass:HomeAssistant,entry:ConfigEntry,async_add_entities:AddEntitiesCallback)->None:
    async_add_entities([DiagnosticsZipButton(entry,hass.data[DOMAIN][entry.entry_id][DATA_RECEIVER])])

class DiagnosticsZipButton(ButtonEntity):
    _attr_has_entity_name=True
    _attr_name="Diagnosepaket erstellen"
    _attr_icon="mdi:folder-zip"

    def __init__(self,entry,receiver):
        self._attr_unique_id=f"{entry.entry_id}_create_diagnostics_zip"
        self.receiver=receiver
        self._running=False
        self._last_created=None
        self._last_size=None

    @property
    def extra_state_attributes(self):
        return {
            "status": "creating" if self._running else "ready",
            "download_url": self.receiver.zip_url if self.receiver.zip_path.exists() else None,
            "last_created": self._last_created,
            "zip_size_bytes": self._last_size,
        }

    @property
    def available(self)->bool:
        return not self._running

    async def async_press(self)->None:
        if self._running:
            return

        self._running=True
        self.async_write_ha_state()
        persistent_notification.async_create(
            self.hass,
            "Das Diagnosepaket wird erstellt. Bitte warten; bei großen Mitschnitten kann das etwas dauern.",
            title="Tigo TAP Local – Diagnose läuft",
            notification_id="tigo_tap_local_diagnostics",
        )

        try:
            await self.hass.async_add_executor_job(self.receiver.create_diagnostics_zip)
        except Exception as err:
            persistent_notification.async_create(
                self.hass,
                f"Das Diagnosepaket konnte nicht erstellt werden: {err}",
                title="Tigo TAP Local – Fehler",
                notification_id="tigo_tap_local_diagnostics",
            )
            raise
        else:
            from datetime import datetime, timezone
            self._last_created=datetime.now(timezone.utc).isoformat()
            try:
                self._last_size=self.receiver.zip_path.stat().st_size
            except OSError:
                self._last_size=None
            persistent_notification.async_create(
                self.hass,
                f'Das Diagnosepaket ist fertig. [ZIP jetzt herunterladen]({self.receiver.zip_url})',
                title="Tigo TAP Local – Diagnose fertig",
                notification_id="tigo_tap_local_diagnostics",
            )
        finally:
            self._running=False
            self.async_write_ha_state()

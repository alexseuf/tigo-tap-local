"""Config flow for Tigo TAP Local."""

import voluptuous as vol
from homeassistant import config_entries

from .const import DOMAIN


class TigoTapLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure Tigo TAP Local."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create an initial placeholder entry.

        Serial/TAP configuration will be added once active polling is implemented.
        """
        if user_input is not None:
            await self.async_set_unique_id("tigo_tap_local")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Tigo TAP Local", data={})

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

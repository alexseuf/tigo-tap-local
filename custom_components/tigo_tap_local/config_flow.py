"""Config flow for Tigo TAP Local."""

import glob
import voluptuous as vol
from homeassistant import config_entries

from .const import DOMAIN

CONF_SERIAL_PORT = "serial_port"
CONF_BAUDRATE = "baudrate"
DEFAULT_BAUDRATE = 38400


def _serial_ports() -> list[str]:
    """Return stable serial paths first, then ttyUSB/ttyACM devices."""
    paths = glob.glob("/dev/serial/by-id/*")
    paths += glob.glob("/dev/ttyUSB*")
    paths += glob.glob("/dev/ttyACM*")
    return sorted(dict.fromkeys(paths))


class TigoTapLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure Tigo TAP Local."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Configure the RS485 serial interface."""
        if user_input is not None:
            await self.async_set_unique_id("tigo_tap_local")
            self._abort_if_unique_id_configured()
            port = user_input[CONF_SERIAL_PORT]
            return self.async_create_entry(
                title=f"Tigo TAP Local ({port})",
                data=user_input,
            )

        ports = _serial_ports()
        if ports:
            port_field = vol.In(ports)
        else:
            port_field = str

        schema = vol.Schema(
            {
                vol.Required(CONF_SERIAL_PORT): port_field,
                vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.In(
                    [38400]
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

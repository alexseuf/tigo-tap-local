"""Config flow for Tigo TAP Local."""
import glob
import voluptuous as vol
from homeassistant import config_entries
from .const import CONF_BAUDRATE, CONF_SERIAL_PORT, DEFAULT_BAUDRATE, DOMAIN

def _serial_ports() -> list[str]:
    """Return stable serial paths first, then ttyUSB/ttyACM devices."""
    paths=glob.glob("/dev/serial/by-id/*")+glob.glob("/dev/ttyUSB*")+glob.glob("/dev/ttyACM*")
    return sorted(dict.fromkeys(paths))

class TigoTapLocalConfigFlow(config_entries.ConfigFlow,domain=DOMAIN):
    """Configure Tigo TAP Local."""
    VERSION=1
    async def async_step_user(self,user_input=None):
        if user_input is not None:
            await self.async_set_unique_id("tigo_tap_local")
            self._abort_if_unique_id_configured()
            port=user_input[CONF_SERIAL_PORT]
            return self.async_create_entry(title=f"Tigo TAP Local ({port})",data=user_input)
        ports=_serial_ports()
        port_field=vol.In(ports) if ports else str
        return self.async_show_form(step_id="user",data_schema=vol.Schema({
            vol.Required(CONF_SERIAL_PORT):port_field,
            vol.Required(CONF_BAUDRATE,default=DEFAULT_BAUDRATE):vol.In([38400]),
        }))

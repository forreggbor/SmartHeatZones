"""
SmartHeatZones – Config Flow (initial zone setup)
"""
from __future__ import annotations
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from .const import DOMAIN, CONF_TITLE, DEFAULT_TITLE

_LOGGER = logging.getLogger(__name__)


class SmartHeatZonesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup flow for each heating zone."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle zone creation step."""
        errors = {}

        if user_input is not None:
            title = user_input.get(CONF_TITLE, DEFAULT_TITLE)
            _LOGGER.info("[SmartHeatZones] New zone created: %s", title)
            return self.async_create_entry(title=title, data={})

        schema = vol.Schema({
            vol.Optional(CONF_TITLE, default=DEFAULT_TITLE): str
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        from .options_flow import SmartHeatZonesOptionsFlowHandler
        return SmartHeatZonesOptionsFlowHandler(config_entry)

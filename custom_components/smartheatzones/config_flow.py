"""
SmartHeatZones - Config Flow
Version: 1.4.3 (HA 2025.10+ compatible)
Author: forreggbor
"""

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_TITLE,
    CONF_SENSOR,
    CONF_ZONE_RELAYS,
    CONF_DOOR_SENSORS,
    CONF_BOILER_MAIN,
    CONF_HYSTERESIS,
    DEFAULT_HYSTERESIS,
    LOG_PREFIX,
)

_LOGGER = logging.getLogger(__name__)


class SmartHeatZonesFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow kezelő SmartHeatZones integrációhoz."""

    VERSION = 1

    def __init__(self):
        self._data = {}
        _LOGGER.debug("%s ConfigFlow initialized", LOG_PREFIX)

    async def async_step_user(self, user_input=None):
        """Első lépés - új zóna hozzáadása."""
        _LOGGER.debug("%s Entered async_step_user", LOG_PREFIX)

        if user_input is not None:
            self._data.update(user_input)
            title = user_input.get(CONF_TITLE, "Unnamed Zone")
            _LOGGER.info("%s New zone configured: %s", LOG_PREFIX, title)
            return self.async_create_entry(title=title, data=self._data)

        schema = vol.Schema(
            {
                vol.Required(CONF_TITLE): str,
                vol.Optional(CONF_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_ZONE_RELAYS): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch", multiple=True)
                ),
                vol.Optional(CONF_DOOR_SENSORS): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
                ),
                vol.Optional(CONF_BOILER_MAIN): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                ),
                vol.Optional(CONF_HYSTERESIS, default=DEFAULT_HYSTERESIS): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        max=2.0,
                        step=0.1,
                        unit_of_measurement="°C",
                        mode="box",
                    )
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @config_entries.HANDLERS.register(DOMAIN)
    def async_get_options_flow(config_entry):
        """Visszaadja az options flow handler-t a fogaskerékhez."""
        from .options_flow import SmartHeatZonesOptionsFlowHandler
        _LOGGER.debug("%s Loading OptionsFlowHandler for %s", LOG_PREFIX, config_entry.title)
        return SmartHeatZonesOptionsFlowHandler(config_entry)

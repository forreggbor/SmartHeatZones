"""
SmartHeatZones - Config Flow
Version: 1.7.0

NEW in v1.7.0:
- Added thermostat type field to zone creation
- Added temperature offset field to zone creation

NEW in v1.6.0:
- Common settings flow (mandatory first step)
- Zone creation only after common settings exist
- Validation and error handling
"""

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_TITLE,
    CONF_SENSOR,
    CONF_ZONE_RELAYS,
    CONF_DOOR_SENSORS,
    CONF_BOILER_MAIN,
    CONF_HYSTERESIS,
    CONF_OVERHEAT_PROTECTION,
    CONF_OUTDOOR_SENSOR,
    CONF_ADAPTIVE_HYSTERESIS,
    CONF_HEATING_MODE,
    CONF_THERMOSTAT_TYPE,
    CONF_TEMP_OFFSET,
    CONF_IS_COMMON_SETTINGS,
    DEFAULT_HYSTERESIS,
    DEFAULT_OVERHEAT_TEMP,
    DEFAULT_ADAPTIVE_HYSTERESIS,
    DEFAULT_HEATING_MODE,
    DEFAULT_THERMOSTAT_TYPE,
    DEFAULT_TEMP_OFFSET,
    HEATING_MODES,
    THERMOSTAT_TYPES,
    COMMON_SETTINGS_TITLE,
    ERR_NO_COMMON_SETTINGS,
    LOG_PREFIX,
)

_LOGGER = logging.getLogger(__name__)


class SmartHeatZonesFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow handler for SmartHeatZones."""

    VERSION = 2  # Bumped to v2 for v1.6.0

    def __init__(self):
        self._data = {}
        _LOGGER.debug("%s ConfigFlow initialized", LOG_PREFIX)

    @staticmethod
    def _has_common_settings(hass) -> bool:
        """Check if common settings entry exists."""
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.data.get(CONF_IS_COMMON_SETTINGS):
                return True
        return False

    async def async_step_user(self, user_input=None):
        """Entry point - determine if common settings or zone creation."""
        _LOGGER.debug("%s Entered async_step_user", LOG_PREFIX)

        # Check if common settings exist
        if not self._has_common_settings(self.hass):
            # No common settings → Force common settings creation
            _LOGGER.info("%s No common settings found, redirecting to common_settings step", LOG_PREFIX)
            return await self.async_step_common_settings()
        else:
            # Common settings exist → Create new zone
            _LOGGER.info("%s Common settings exist, proceeding to zone creation", LOG_PREFIX)
            return await self.async_step_zone()

    async def async_step_common_settings(self, user_input=None):
        """Step 1: Create common settings (mandatory first step)."""
        _LOGGER.debug("%s Entered async_step_common_settings", LOG_PREFIX)

        errors = {}

        if user_input is not None:
            # Validate required fields
            if not user_input.get(CONF_BOILER_MAIN):
                errors["boiler_main"] = "boiler_required"
            
            if not errors:
                # Clean up empty outdoor sensor (makes it truly optional)
                if CONF_OUTDOOR_SENSOR in user_input and not user_input[CONF_OUTDOOR_SENSOR]:
                    user_input.pop(CONF_OUTDOOR_SENSOR, None)

                # Mark as common settings
                user_input[CONF_IS_COMMON_SETTINGS] = True

                _LOGGER.info("%s Creating common settings entry", LOG_PREFIX)
                return self.async_create_entry(
                    title=COMMON_SETTINGS_TITLE,
                    data=user_input
                )

        # Schema for common settings
        schema = vol.Schema(
            {
                vol.Required(CONF_BOILER_MAIN): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                ),
                vol.Optional(CONF_OUTDOOR_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(
                    CONF_HYSTERESIS, 
                    default=DEFAULT_HYSTERESIS
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1, max=2.0, step=0.1,
                        unit_of_measurement="°C",
                        mode="box"
                    )
                ),
                vol.Optional(
                    CONF_OVERHEAT_PROTECTION,
                    default=DEFAULT_OVERHEAT_TEMP
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=22.0, max=35.0, step=0.5,
                        unit_of_measurement="°C",
                        mode="box"
                    )
                ),
                vol.Optional(
                    CONF_ADAPTIVE_HYSTERESIS,
                    default=DEFAULT_ADAPTIVE_HYSTERESIS
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="common_settings",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "info": "Ezek a beállítások minden fűtési zónára érvényesek."
            }
        )

    async def async_step_zone(self, user_input=None):
        """Step 2: Create new heating zone."""
        _LOGGER.debug("%s Entered async_step_zone", LOG_PREFIX)

        errors = {}

        if user_input is not None:
            # Validate required fields
            if not user_input.get(CONF_TITLE):
                errors["title"] = "title_required"
            if not user_input.get(CONF_SENSOR):
                errors["sensor_entity_id"] = "sensor_required"
            if not user_input.get(CONF_ZONE_RELAYS):
                errors["relay_entities"] = "relay_required"

            if not errors:
                title = user_input[CONF_TITLE]
                _LOGGER.info("%s Creating zone: %s", LOG_PREFIX, title)
                return self.async_create_entry(title=title, data=user_input)

        # Schema for zone creation
        schema = vol.Schema(
            {
                vol.Required(CONF_TITLE): str,
                vol.Required(
                    CONF_HEATING_MODE,
                    default=DEFAULT_HEATING_MODE
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=HEATING_MODES,
                        mode="dropdown"
                    )
                ),
                vol.Required(
                    CONF_THERMOSTAT_TYPE,
                    default=DEFAULT_THERMOSTAT_TYPE
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=THERMOSTAT_TYPES,
                        mode="dropdown"
                    )
                ),
                vol.Optional(
                    CONF_TEMP_OFFSET,
                    default=DEFAULT_TEMP_OFFSET
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0, max=10.0, step=0.5,
                        unit_of_measurement="°C",
                        mode="box"
                    )
                ),
                vol.Optional(CONF_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_ZONE_RELAYS): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch", multiple=True)
                ),
                vol.Optional(CONF_DOOR_SENSORS): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
                ),
            }
        )

        return self.async_show_form(
            step_id="zone",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "info": "Új fűtési zóna létrehozása"
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return options flow handler."""
        from .options_flow import SmartHeatZonesOptionsFlowHandler
        _LOGGER.debug("%s Loading OptionsFlowHandler for %s", LOG_PREFIX, config_entry.title)
        return SmartHeatZonesOptionsFlowHandler(config_entry)

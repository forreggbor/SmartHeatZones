"""
SmartHeatZones - Options Flow
Version: 1.8.0 (HA 2025.10+)
Author: forreggbor

NEW in v1.8.0:
- Added tempering heating toggle to common settings options
- Display tempering heating status in zone info panel

NEW in v1.7.0:
- Added thermostat type field to zone options
- Added temperature offset field to zone options

NEW in v1.6.1:
- Uses INTEGRATION_VERSION constant for version display

NEW in v1.6.0:
- Common settings info panel (read-only display)
- Separate options flow for common settings vs zones
- Underfloor heating mode selector
"""

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import (
    DOMAIN,
    CONF_SENSOR,
    CONF_ZONE_RELAYS,
    CONF_DOOR_SENSORS,
    CONF_BOILER_MAIN,
    CONF_HYSTERESIS,
    CONF_SCHEDULE,
    CONF_OVERHEAT_PROTECTION,
    CONF_OUTDOOR_SENSOR,
    CONF_ADAPTIVE_HYSTERESIS,
    CONF_TEMPERING_HEATING,
    CONF_HEATING_MODE,
    CONF_THERMOSTAT_TYPE,
    CONF_TEMP_OFFSET,
    CONF_IS_COMMON_SETTINGS,
    DEFAULT_HYSTERESIS,
    DEFAULT_OVERHEAT_TEMP,
    DEFAULT_ADAPTIVE_HYSTERESIS,
    DEFAULT_TEMPERING_HEATING,
    DEFAULT_HEATING_MODE,
    DEFAULT_THERMOSTAT_TYPE,
    DEFAULT_TEMP_OFFSET,
    HEATING_MODES,
    THERMOSTAT_TYPES,
    DATA_COMMON_SETTINGS,
    INTEGRATION_VERSION,
)

_LOGGER = logging.getLogger(__name__)


def _get_common_settings_data(hass):
    """Get common settings data for info display."""
    common_entry = hass.data.get(DOMAIN, {}).get(DATA_COMMON_SETTINGS)
    if common_entry:
        data = common_entry.options if common_entry.options else common_entry.data
        return {
            "boiler": data.get(CONF_BOILER_MAIN, "N/A"),
            "outdoor": data.get(CONF_OUTDOOR_SENSOR, "Nincs beállítva"),
            "hysteresis": data.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS),
            "overheat": data.get(CONF_OVERHEAT_PROTECTION, DEFAULT_OVERHEAT_TEMP),
            "adaptive": data.get(CONF_ADAPTIVE_HYSTERESIS, DEFAULT_ADAPTIVE_HYSTERESIS),
            "tempering": data.get(CONF_TEMPERING_HEATING, DEFAULT_TEMPERING_HEATING),
        }
    return None


class SmartHeatZonesOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow handler for SmartHeatZones."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize."""
        self._entry = config_entry
        self._data = dict(config_entry.options)
        _LOGGER.debug("[SmartHeatZones] OptionsFlow initialized for %s", config_entry.title)

    async def async_step_init(self, user_input=None):
        """Main entry point - determine if common settings or zone options."""
        is_common = self._entry.data.get(CONF_IS_COMMON_SETTINGS, False)

        if is_common:
            # Common settings options flow
            return await self.async_step_common_settings(user_input)
        else:
            # Zone options flow
            return await self.async_step_zone(user_input)

    # ==================================================================================
    # COMMON SETTINGS OPTIONS FLOW
    # ==================================================================================

    async def async_step_common_settings(self, user_input=None):
        """Options flow for common settings."""
        _LOGGER.debug("[SmartHeatZones] Entered async_step_common_settings (options)")

        if user_input is not None:
            # Handle outdoor sensor removal BEFORE updating self._data
            if CONF_OUTDOOR_SENSOR in user_input:
                if not user_input[CONF_OUTDOOR_SENSOR]:
                    # User removed/cleared the outdoor sensor
                    _LOGGER.info("[SmartHeatZones] Outdoor sensor removed, disabling adaptive hysteresis")
                    # Remove from both user_input and self._data
                    user_input.pop(CONF_OUTDOOR_SENSOR, None)
                    self._data.pop(CONF_OUTDOOR_SENSOR, None)
                    # Disable adaptive hysteresis since it requires outdoor sensor
                    user_input[CONF_ADAPTIVE_HYSTERESIS] = False

            self._data.update(user_input)
            _LOGGER.info("[SmartHeatZones] Common settings options updated")
            return await self._save_and_exit()

        # Schema for common settings
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BOILER_MAIN,
                    default=self._data.get(CONF_BOILER_MAIN, "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                ),
                vol.Optional(
                    CONF_OUTDOOR_SENSOR,
                    default=self._data.get(CONF_OUTDOOR_SENSOR) if self._data.get(CONF_OUTDOOR_SENSOR) else None
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(
                    CONF_HYSTERESIS,
                    default=self._data.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1, max=2.0, step=0.1,
                        unit_of_measurement="°C",
                        mode="box"
                    )
                ),
                vol.Optional(
                    CONF_OVERHEAT_PROTECTION,
                    default=self._data.get(CONF_OVERHEAT_PROTECTION, DEFAULT_OVERHEAT_TEMP)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=22.0, max=35.0, step=0.5,
                        unit_of_measurement="°C",
                        mode="box"
                    )
                ),
                vol.Optional(
                    CONF_ADAPTIVE_HYSTERESIS,
                    default=self._data.get(CONF_ADAPTIVE_HYSTERESIS, DEFAULT_ADAPTIVE_HYSTERESIS)
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_TEMPERING_HEATING,
                    default=self._data.get(CONF_TEMPERING_HEATING, DEFAULT_TEMPERING_HEATING)
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="common_settings",
            data_schema=schema,
            description_placeholders={
                "title": self._entry.title,
                "version": INTEGRATION_VERSION,
            },
        )

    # ==================================================================================
    # ZONE OPTIONS FLOW (with common settings info panel)
    # ==================================================================================

    async def async_step_zone(self, user_input=None):
        """Options flow for heating zone - v1.6.0 with common settings info."""
        _LOGGER.debug("[SmartHeatZones] Entered async_step_zone (options)")

        if user_input is not None:
            self._data.update(user_input)
            _LOGGER.info("[SmartHeatZones] Zone options updated for %s", self._entry.title)
            return await self._save_and_exit()

        # Get common settings for info display
        common_info = _get_common_settings_data(self.hass)
        
        # Build info text for common settings
        if common_info:
            outdoor_temp = ""
            if common_info["outdoor"] != "Nincs beállítva":
                outdoor_state = self.hass.states.get(common_info["outdoor"])
                if outdoor_state and outdoor_state.state not in ["unavailable", "unknown"]:
                    outdoor_temp = f" ({outdoor_state.state}°C)"
            
            info_text = (
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 Közös beállítások (módosítás: 🔧 Közös beállítások zónában)\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔥 Kazán főkapcsoló: {common_info['boiler']}\n"
                f"🌡️ Kültéri hőmérő: {common_info['outdoor']}{outdoor_temp}\n"
                f"📊 Hiszterézis: {common_info['hysteresis']}°C\n"
                f"🔥 Túlmelegedés védelem: {common_info['overheat']}°C\n"
                f"🔄 Adaptív hiszterézis: {'BE' if common_info['adaptive'] else 'KI'}\n"
                f"♨️  Melegítő fűtés: {'BE' if common_info['tempering'] else 'KI'}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        else:
            info_text = "⚠️ Közös beállítások nem találhatók!"

        # Load schedule
        schedule = self._data.get(CONF_SCHEDULE, [])
        if not schedule:
            schedule = [
                {"label": "1. napszak", "start": "00:00", "end": "06:00", "temp": 20.0},
                {"label": "2. napszak", "start": "06:00", "end": "12:00", "temp": 21.0},
                {"label": "3. napszak", "start": "12:00", "end": "18:00", "temp": 20.0},
                {"label": "4. napszak", "start": "18:00", "end": "00:00", "temp": 22.0},
            ]

        # Schema for zone options
        schema = vol.Schema(
            {
                # Heating mode (NEW v1.6.0)
                vol.Required(
                    CONF_HEATING_MODE,
                    default=self._data.get(CONF_HEATING_MODE, DEFAULT_HEATING_MODE)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "radiator", "label": "Radiátor"},
                            {"value": "underfloor", "label": "Padlófűtés"}
                        ],
                        mode="dropdown"
                    )
                ),

                # Thermostat type (NEW v1.7.0)
                vol.Required(
                    CONF_THERMOSTAT_TYPE,
                    default=self._data.get(CONF_THERMOSTAT_TYPE, DEFAULT_THERMOSTAT_TYPE)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "wall", "label": "Fali termosztát"},
                            {"value": "radiator", "label": "Radiátor termosztát"}
                        ],
                        mode="dropdown"
                    )
                ),

                # Temperature offset (NEW v1.7.0)
                vol.Optional(
                    CONF_TEMP_OFFSET,
                    default=self._data.get(CONF_TEMP_OFFSET, DEFAULT_TEMP_OFFSET)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0, max=10.0, step=0.5,
                        unit_of_measurement="°C",
                        mode="box"
                    )
                ),

                # Zone sensor
                vol.Optional(
                    CONF_SENSOR,
                    default=self._data.get(CONF_SENSOR, "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),

                # Zone relays
                vol.Optional(
                    CONF_ZONE_RELAYS,
                    default=self._data.get(CONF_ZONE_RELAYS, [])
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch", multiple=True)
                ),

                # Door/window sensors
                vol.Optional(
                    CONF_DOOR_SENSORS,
                    default=self._data.get(CONF_DOOR_SENSORS, [])
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
                ),
            }
        )

        # Add schedule blocks
        for i, block in enumerate(schedule[:4], start=1):
            schema = schema.extend({
                vol.Optional(
                    f"label_{i}",
                    default=block.get("label", f"{i}. napszak"),
                    description=f"🕐 {i}. időszak neve"
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type="text")
                ),
            })

            schema = schema.extend({
                vol.Optional(
                    f"start_{i}",
                    default=block.get("start", "00:00")[:5],
                    description=f"⏰ Kezdés (óra:perc)"
                ): selector.TimeSelector(
                    selector.TimeSelectorConfig()
                ),
            })

            schema = schema.extend({
                vol.Optional(
                    f"end_{i}",
                    default=block.get("end", "06:00")[:5],
                    description=f"⏰ Vége (óra:perc)"
                ): selector.TimeSelector(
                    selector.TimeSelectorConfig()
                ),
            })

            schema = schema.extend({
                vol.Optional(
                    f"temp_{i}",
                    default=block.get("temp", 20.0),
                    description=f"🌡️ Célhőmérséklet"
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5, max=30, step=0.5,
                        unit_of_measurement="°C",
                        mode="box"
                    )
                ),
            })

        return self.async_show_form(
            step_id="zone",
            data_schema=schema,
            description_placeholders={
                "title": self._entry.title,
                "version": INTEGRATION_VERSION,
                "common_info": info_text,
            },
        )

    # ==================================================================================
    # SAVE AND EXIT
    # ==================================================================================

    async def _save_and_exit(self):
        """Save and exit."""
        is_common = self._entry.data.get(CONF_IS_COMMON_SETTINGS, False)

        if not is_common:
            # Zone entry - save schedule
            schedule = []
            for i in range(1, 5):
                label = self._data.get(f"label_{i}")
                start = self._data.get(f"start_{i}")
                end = self._data.get(f"end_{i}")
                temp = self._data.get(f"temp_{i}")

                if label and start and end and temp is not None:
                    start_str = str(start)[:5] if isinstance(start, str) else f"{start.hour:02d}:{start.minute:02d}"
                    end_str = str(end)[:5] if isinstance(end, str) else f"{end.hour:02d}:{end.minute:02d}"

                    schedule.append(
                        {
                            "label": label,
                            "start": start_str,
                            "end": end_str,
                            "temp": float(temp),
                        }
                    )

            self._data[CONF_SCHEDULE] = schedule
        else:
            # Common settings entry - clean up empty outdoor sensor
            if CONF_OUTDOOR_SENSOR in self._data and not self._data[CONF_OUTDOOR_SENSOR]:
                # Remove empty string outdoor sensor (makes it truly optional)
                self._data.pop(CONF_OUTDOOR_SENSOR, None)
                # Disable adaptive hysteresis since it requires outdoor sensor
                _LOGGER.info("[SmartHeatZones] No outdoor sensor configured, disabling adaptive hysteresis")
                self._data[CONF_ADAPTIVE_HYSTERESIS] = False

        _LOGGER.debug("[SmartHeatZones] Saving final options: %s", self._data)

        # Save
        self.hass.config_entries.async_update_entry(self._entry, options=self._data)
        _LOGGER.info("[SmartHeatZones] Options saved successfully for %s", self._entry.title)
        return self.async_create_entry(title=self._entry.title, data=self._data)

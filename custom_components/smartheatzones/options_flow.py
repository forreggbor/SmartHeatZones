"""
SmartHeatZones - Options Flow
Version: 1.4.3 (HA 2025.10+)
Author: forreggbor
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
    DEFAULT_HYSTERESIS,
    DEFAULT_AUTO_SCHEDULE,
)

_LOGGER = logging.getLogger(__name__)


class SmartHeatZonesOptionsFlowHandler(config_entries.OptionsFlow):
    """Handles the configuration options for SmartHeatZones zones."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize."""
        self._entry = config_entry
        self._data = dict(config_entry.options)
        _LOGGER.debug("[SmartHeatZones] OptionsFlow initialized for %s", config_entry.title)

    async def async_step_init(self, user_input=None):
        """Main entry step."""
        _LOGGER.debug("[SmartHeatZones] Entered async_step_init")

        # Ha nincs user_input, mutatjuk a formot
        if user_input is not None:
            self._data.update(user_input)
            _LOGGER.info("[SmartHeatZones] Options updated for %s: %s", self._entry.title, self._data)
            return await self._save_and_exit()

        # Napszakos beállítások betöltése (ha nincs, alapértelmezett)
        schedule = self._data.get(CONF_SCHEDULE, DEFAULT_AUTO_SCHEDULE)

        # Űrlap mezők definiálása
        schema = vol.Schema(
            {
                vol.Optional(CONF_SENSOR, default=self._data.get(CONF_SENSOR, "")): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_ZONE_RELAYS, default=self._data.get(CONF_ZONE_RELAYS, [])): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch", multiple=True)
                ),
                vol.Optional(CONF_DOOR_SENSORS, default=self._data.get(CONF_DOOR_SENSORS, [])): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
                ),
                vol.Optional(CONF_BOILER_MAIN, default=self._data.get(CONF_BOILER_MAIN, "")): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                ),
                vol.Optional(CONF_HYSTERESIS, default=self._data.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1, max=2.0, step=0.1, unit_of_measurement="°C", mode="box"
                    )
                ),
            }
        )

        # Napszak beállítások: egy sor = label, start, end, temp
        for i, block in enumerate(schedule, start=1):
            schema = schema.extend(
                {
                    vol.Optional(f"label_{i}", default=block.get("label", f"Period {i}")): str,
                    vol.Optional(f"start_{i}", default=block.get("start", "00:00")): selector.TimeSelector(),
                    vol.Optional(f"end_{i}", default=block.get("end", "06:00")): selector.TimeSelector(),
                    vol.Optional(f"temp_{i}", default=block.get("temp", 20.0)): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=5, max=30, step=0.5, unit_of_measurement="°C", mode="box"
                        )
                    ),
                }
            )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "title": self._entry.title,
                "version": "1.4.3",
            },
        )

    async def _save_and_exit(self):
        """Mentés és kilépés."""
        # Napszakos értékek mentése
        schedule = []
        for i in range(1, 5):
            label = self._data.get(f"label_{i}")
            start = self._data.get(f"start_{i}")
            end = self._data.get(f"end_{i}")
            temp = self._data.get(f"temp_{i}")

            if label and start and end and temp is not None:
                schedule.append(
                    {
                        "label": label,
                        "start": str(start),
                        "end": str(end),
                        "temp": float(temp),
                    }
                )

        self._data[CONF_SCHEDULE] = schedule
        _LOGGER.debug("[SmartHeatZones] Saving final options: %s", self._data)

        # Mentés
        self.hass.config_entries.async_update_entry(self._entry, options=self._data)
        _LOGGER.info("[SmartHeatZones] Options saved successfully for %s", self._entry.title)
        return self.async_create_entry(title=self._entry.title, data=self._data)

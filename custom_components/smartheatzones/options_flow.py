"""
SmartHeatZones - Options Flow
Version: 1.5.1 (HA 2025.10+)
Author: forreggbor

NEW in v1.5.1:
- Removed DEFAULT_AUTO_SCHEDULE (empty schedule = no default)
- Reordered input fields for better UX

NEW in v1.5.0:
- Overheat protection setting per zone
- Outdoor temperature sensor (global)
- Adaptive hysteresis toggle
- Napszakok egy sorban (kompakt UI)
- Time selector másodperc nélkül
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
    DEFAULT_HYSTERESIS,
    DEFAULT_OVERHEAT_TEMP,
    DEFAULT_ADAPTIVE_HYSTERESIS,
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
        """Main entry step - v1.5.1 reordered UI."""
        _LOGGER.debug("[SmartHeatZones] Entered async_step_init")

        if user_input is not None:
            self._data.update(user_input)
            _LOGGER.info("[SmartHeatZones] Options updated for %s", self._entry.title)
            return await self._save_and_exit()

        # Napszakos beállítások betöltése
        # FIX v1.5.1: Ha nincs schedule, használjunk üres listát (figyelmeztetés a climate.py-ban)
        schedule = self._data.get(CONF_SCHEDULE, [])

        # Ha még nincs schedule, létrehozunk egy alapértelmezett 4 üres blokkot a UI-hoz
        if not schedule:
            schedule = [
                {"label": "1. napszak", "start": "00:00", "end": "06:00", "temp": 20.0},
                {"label": "2. napszak", "start": "06:00", "end": "12:00", "temp": 21.0},
                {"label": "3. napszak", "start": "12:00", "end": "18:00", "temp": 20.0},
                {"label": "4. napszak", "start": "18:00", "end": "00:00", "temp": 22.0},
            ]

        # ========================================================================
        # ALAPVETŐ BEÁLLÍTÁSOK - ÚJ SORREND v1.5.1
        # ========================================================================
        # 1. Kazán főkapcsoló
        # 2. Kültéri hőmérő szenzor
        # 3. Zóna hőmérő szenzor
        # 4. Zóna relék
        # 5. Zóna ajtó/ablakérzékelők

        schema = vol.Schema(
            {
                # 1. Kazán főkapcsoló
                vol.Optional(
                    CONF_BOILER_MAIN,
                    default=self._data.get(CONF_BOILER_MAIN, "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                ),

                # 2. Kültéri hőmérő szenzor
                vol.Optional(
                    CONF_OUTDOOR_SENSOR,
                    default=self._data.get(CONF_OUTDOOR_SENSOR, "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),

                # 3. Zóna hőmérő szenzor
                vol.Optional(
                    CONF_SENSOR,
                    default=self._data.get(CONF_SENSOR, "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),

                # 4. Zóna relék
                vol.Optional(
                    CONF_ZONE_RELAYS,
                    default=self._data.get(CONF_ZONE_RELAYS, [])
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch", multiple=True)
                ),

                # 5. Zóna ajtó/ablakérzékelők
                vol.Optional(
                    CONF_DOOR_SENSORS,
                    default=self._data.get(CONF_DOOR_SENSORS, [])
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
                ),

                # 6. Hiszterézis
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
            }
        )

        # ========================================================================
        # VÉDELMEK ÉS ADAPTÍV VEZÉRLÉS
        # ========================================================================
        schema = schema.extend(
            {
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
            }
        )

        # ========================================================================
        # NAPSZAKOK - EGYSZERŰSÍTETT UI
        # ========================================================================
        for i, block in enumerate(schedule[:4], start=1):
            # Napszak címke
            schema = schema.extend({
                vol.Optional(
                    f"label_{i}",
                    default=block.get("label", f"{i}. napszak"),
                    description=f"🕐 {i}. időszak neve"
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type="text")
                ),
            })

            # Kezdés idő
            schema = schema.extend({
                vol.Optional(
                    f"start_{i}",
                    default=block.get("start", "00:00")[:5],
                    description=f"⏰ Kezdés (óra:perc)"
                ): selector.TimeSelector(
                    selector.TimeSelectorConfig()
                ),
            })

            # Vége idő
            schema = schema.extend({
                vol.Optional(
                    f"end_{i}",
                    default=block.get("end", "06:00")[:5],
                    description=f"⏰ Vége (óra:perc)"
                ): selector.TimeSelector(
                    selector.TimeSelectorConfig()
                ),
            })

            # Hőmérséklet
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
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "title": self._entry.title,
                "version": "1.5.1",
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
                # Csak HH:MM formátum (másodperc nélkül)
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
        _LOGGER.debug("[SmartHeatZones] Saving final options: %s", self._data)

        # Mentés
        self.hass.config_entries.async_update_entry(self._entry, options=self._data)
        _LOGGER.info("[SmartHeatZones] Options saved successfully for %s", self._entry.title)
        return self.async_create_entry(title=self._entry.title, data=self._data)

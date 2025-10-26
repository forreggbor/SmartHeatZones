"""
SmartHeatZones – Options Flow (per-zone configuration)
- Hőmérő szenzor kiválasztás
- Közös kazán főkapcsoló (minden zónára érvényes, egyetlen switch)
- Zónaszintű relék (szivattyúk/szelepek) – több is megadható
- Ajtó/ablak nyitásérzékelők – több is megadható
- Hiszterézis (°C) – vol.Coerce(float)
- 1–4 napszak (idősáv): start/end/temp
- Mentéskor visszatöltés (suggested values), 2025.12 kompatibilis (nincs self.config_entry felülírás)
"""
from __future__ import annotations

from typing import Any, Dict, List
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import (
    DOMAIN,
    # opció kulcsok
    CONF_SENSOR,
    CONF_ZONE_RELAYS,
    CONF_BOILER_MAIN,
    CONF_DOOR_SENSORS,
    CONF_HYSTERESIS,
    CONF_SCHEDULE,
    CONF_ACTIVE_BLOCKS,
    # defaultok
    DEFAULT_HYSTERESIS,
    DEFAULT_SCHEDULE,
)

_LOGGER = logging.getLogger(__name__)


def _sel(domain: str, multiple: bool = False):
    """Entity selector rövidítő."""
    return EntitySelector(EntitySelectorConfig(domain=domain, multiple=multiple))


class SmartHeatZonesOptionsFlowHandler(config_entries.OptionsFlow):
    """Opciós űrlap egy zónához. A kazán főkapcsoló közös, minden zónára érvényes."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        super().__init__()
        # Figyelem: nem írjuk felül a self.config_entry attribútumot (deprecated lenne)
        self.entry = config_entry

    async def async_step_init(self, user_input=None):
        """Belépési pont – ugyanaz, mint a zóna step."""
        return await self.async_step_zone(user_input)

    async def async_step_zone(self, user_input=None):
        """Zóna konfigurációs űrlap és mentés."""
        hass: HomeAssistant = self.hass
        existing: Dict[str, Any] = dict(self.entry.options or {})

        if user_input is not None:
            # 1) Bejövő értékek → normalizálás
            opts: Dict[str, Any] = dict(existing)  # megőrizzük a többit is

            # szenzor / relék / ajtó-ablak / hiszterézis
            opts[CONF_SENSOR] = user_input.get(CONF_SENSOR) or None
            opts[CONF_BOILER_MAIN] = user_input.get(CONF_BOILER_MAIN) or None
            opts[CONF_ZONE_RELAYS] = list(user_input.get(CONF_ZONE_RELAYS, []))
            opts[CONF_DOOR_SENSORS] = list(user_input.get(CONF_DOOR_SENSORS, []))

            try:
                opts[CONF_HYSTERESIS] = float(user_input.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS))
            except (TypeError, ValueError):
                opts[CONF_HYSTERESIS] = DEFAULT_HYSTERESIS

            # 2) Napszakok (1–4)
            try:
                active_blocks = int(user_input.get(CONF_ACTIVE_BLOCKS, 4))
            except (TypeError, ValueError):
                active_blocks = 4
            active_blocks = max(1, min(4, active_blocks))
            opts[CONF_ACTIVE_BLOCKS] = active_blocks

            blocks: List[Dict[str, Any]] = []
            for i in range(1, active_blocks + 1):
                s = (user_input.get(f"b{i}_start") or "").strip()
                e = (user_input.get(f"b{i}_end") or "").strip()
                t = user_input.get(f"b{i}_temp")
                if s and e and t is not None:
                    try:
                        blocks.append({"start": s, "end": e, "temp": float(t)})
                    except (TypeError, ValueError):
                        # ha hibás a szám, kihagyjuk a blokkot
                        pass

            opts[CONF_SCHEDULE] = blocks if blocks else DEFAULT_SCHEDULE

            # 3) Kazán főkapcsoló propagálása MINDEN zónára (közös egyetlen relé)
            main_relay = opts.get(CONF_BOILER_MAIN)
            if main_relay:
                for other in hass.config_entries.async_entries(DOMAIN):
                    if other.entry_id == self.entry.entry_id:
                        continue
                    merged = dict(other.options or {})
                    merged[CONF_BOILER_MAIN] = main_relay
                    hass.config_entries.async_update_entry(other, options=merged)
                _LOGGER.info(
                    "[SmartHeatZones] Main boiler relay propagated to all zones: %s",
                    main_relay,
                )

            _LOGGER.debug("[SmartHeatZones] Options updated for %s: %s", self.entry.title, opts)
            # A create_entry data-ja lesz a végleges options a config_entry-ben
            return self.async_create_entry(title="", data=opts)

        # ─────────────────────────────────────────────
        # Form megjelenítése – suggested values
        # ─────────────────────────────────────────────

        # jelenlegi vagy default javaslatok
        suggested: Dict[str, Any] = {
            CONF_SENSOR: existing.get(CONF_SENSOR),
            CONF_BOILER_MAIN: existing.get(CONF_BOILER_MAIN),
            CONF_ZONE_RELAYS: list(existing.get(CONF_ZONE_RELAYS, [])),
            CONF_DOOR_SENSORS: list(existing.get(CONF_DOOR_SENSORS, [])),
            CONF_HYSTERESIS: existing.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS),
            CONF_ACTIVE_BLOCKS: existing.get(CONF_ACTIVE_BLOCKS, 4),
        }

        schedule = existing.get(CONF_SCHEDULE, DEFAULT_SCHEDULE)
        # max 4 blokkot támogatunk, a többit nem jelenítjük meg
        for i, blk in enumerate(schedule[:4], start=1):
            suggested[f"b{i}_start"] = blk.get("start", "")
            suggested[f"b{i}_end"] = blk.get("end", "")
            suggested[f"b{i}_temp"] = blk.get("temp", 20.0)

        # űrlap – egy sorban megjelenő mezőnevek azonos prefixel: b1_, b2_, ...
        schema = vol.Schema({
            vol.Optional(CONF_SENSOR, default=suggested[CONF_SENSOR]): _sel("sensor"),
            vol.Optional(CONF_BOILER_MAIN, default=suggested[CONF_BOILER_MAIN]): _sel("switch"),
            vol.Optional(CONF_ZONE_RELAYS, default=suggested[CONF_ZONE_RELAYS]): _sel("switch", multiple=True),
            vol.Optional(CONF_DOOR_SENSORS, default=suggested[CONF_DOOR_SENSORS]): _sel("binary_sensor", multiple=True),
            vol.Optional(CONF_HYSTERESIS, default=suggested[CONF_HYSTERESIS]): vol.Coerce(float),
            vol.Optional(CONF_ACTIVE_BLOCKS, default=suggested[CONF_ACTIVE_BLOCKS]): vol.In([1, 2, 3, 4]),

            vol.Optional("b1_start", default=suggested.get("b1_start", "")): str,
            vol.Optional("b1_end",   default=suggested.get("b1_end", "")): str,
            vol.Optional("b1_temp",  default=suggested.get("b1_temp", 20.0)): vol.Coerce(float),

            vol.Optional("b2_start", default=suggested.get("b2_start", "")): str,
            vol.Optional("b2_end",   default=suggested.get("b2_end", "")): str,
            vol.Optional("b2_temp",  default=suggested.get("b2_temp", 20.0)): vol.Coerce(float),

            vol.Optional("b3_start", default=suggested.get("b3_start", "")): str,
            vol.Optional("b3_end",   default=suggested.get("b3_end", "")): str,
            vol.Optional("b3_temp",  default=suggested.get("b3_temp", 20.0)): vol.Coerce(float),

            vol.Optional("b4_start", default=suggested.get("b4_start", "")): str,
            vol.Optional("b4_end",   default=suggested.get("b4_end", "")): str,
            vol.Optional("b4_temp",  default=suggested.get("b4_temp", 20.0)): vol.Coerce(float),
        })

        # a suggested értékeket a schema defaultok már tartalmazzák
        return self.async_show_form(step_id="zone", data_schema=schema)

"""
SmartHeatZones - Boiler Manager
Version: 1.9.0

Central boiler relay coordinator - manages shared boiler switch across all zones.

NEW in v1.9.0:
- Lovelace Dashboard Phase 1 (no changes to boiler manager)

NEW in v1.8.1:
- Piggyback heating: When boiler turns on, all zones with temp < target turn on immediately
"""

import logging
from typing import Optional, TYPE_CHECKING
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    DATA_BOILER_MAIN,
    DATA_ACTIVE_ZONES,
    LOG_PREFIX,
)

if TYPE_CHECKING:
    from .climate import SmartHeatZoneClimate

_LOGGER = logging.getLogger(__name__)


class BoilerManager:
    """
    Központi kazánvezérlő osztály.

    Feladata:
      - közös kazán relé kezelése (pl. switch.shelly_2pm_relay_1)
      - aktív zónák számlálása
      - redundáns kapcsolások elkerülése
      - piggyback heating: más zónák bekapcsolása amikor a kazán már megy
    """

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._boiler_entity_id: Optional[str] = None
        self._active_zones: set[str] = set()
        self._zone_entities: dict[str, "SmartHeatZoneClimate"] = {}
        _LOGGER.info("%s BoilerManager initialized", LOG_PREFIX)

    # --------------------------------------------------------------------------
    # Alapműveletek
    # --------------------------------------------------------------------------

    def register_zone_entity(self, zone_name: str, entity: "SmartHeatZoneClimate"):
        """Register a zone climate entity for piggyback heating."""
        self._zone_entities[zone_name] = entity
        _LOGGER.debug("%s Zone entity registered: %s", LOG_PREFIX, zone_name)

    def unregister_zone_entity(self, zone_name: str):
        """Unregister a zone climate entity."""
        if zone_name in self._zone_entities:
            del self._zone_entities[zone_name]
            _LOGGER.debug("%s Zone entity unregistered: %s", LOG_PREFIX, zone_name)

    async def register_boiler(self, entity_id: str):
        """Kazán főkapcsoló regisztrálása."""
        if self._boiler_entity_id and self._boiler_entity_id != entity_id:
            _LOGGER.warning(
                "%s Boiler entity changed from %s → %s",
                LOG_PREFIX,
                self._boiler_entity_id,
                entity_id,
            )
        self._boiler_entity_id = entity_id
        _LOGGER.info("%s Boiler entity registered: %s", LOG_PREFIX, entity_id)

    async def turn_on(self, entity_id: Optional[str], zone: str):
        """Kazán bekapcsolása zónából."""
        if entity_id and self._boiler_entity_id is None:
            await self.register_boiler(entity_id)

        was_off = len(self._active_zones) == 0
        self._active_zones.add(zone)
        _LOGGER.debug("%s Zone '%s' requested boiler ON (active_zones=%d)", LOG_PREFIX, zone, len(self._active_zones))

        if was_off:
            # Boiler is turning on - physically turn it on
            await self._call_boiler_service("turn_on")
            # Trigger piggyback heating for all other zones
            await self._trigger_piggyback_heating(initiating_zone=zone)

    async def turn_off(self, entity_id: Optional[str], zone: str):
        """Kazán kikapcsolása zónából."""
        if zone in self._active_zones:
            self._active_zones.remove(zone)

        _LOGGER.debug("%s Zone '%s' released boiler (active_zones=%d)", LOG_PREFIX, zone, len(self._active_zones))

        # Ha nincs több aktív zóna, akkor kapcsoljuk ki a kazánt
        if not self._active_zones:
            await self._call_boiler_service("turn_off")

    # --------------------------------------------------------------------------
    # Piggyback heating
    # --------------------------------------------------------------------------

    async def _trigger_piggyback_heating(self, initiating_zone: str):
        """
        Trigger piggyback heating check in all zones.

        When boiler turns on, all zones should check if current_temp < target_temp
        and turn on immediately without hysteresis or waiting for sensor update.
        """
        _LOGGER.info(
            "%s Piggyback heating triggered by zone '%s' - checking all zones",
            LOG_PREFIX, initiating_zone
        )

        for zone_name, zone_entity in self._zone_entities.items():
            if zone_name != initiating_zone:
                # Trigger piggyback check in other zones
                await zone_entity.check_piggyback_heating()

    # --------------------------------------------------------------------------
    # Segédfüggvények
    # --------------------------------------------------------------------------

    async def _call_boiler_service(self, action: str):
        """Service hívás a kazán kapcsolóhoz."""
        if not self._boiler_entity_id:
            _LOGGER.warning("%s No boiler entity configured", LOG_PREFIX)
            return

        try:
            await self.hass.services.async_call(
                "switch",
                action,
                {"entity_id": self._boiler_entity_id},
                blocking=True,
            )
            _LOGGER.info("%s Boiler relay %s → %s", LOG_PREFIX, self._boiler_entity_id, action.upper())
        except Exception as e:
            _LOGGER.error("%s Boiler relay control failed: %s", LOG_PREFIX, e)

    # --------------------------------------------------------------------------
    # Állapot lekérdezés és debug
    # --------------------------------------------------------------------------

    def get_active_zones(self) -> list[str]:
        """Aktív fűtési zónák listája."""
        return list(self._active_zones)

    def get_boiler_state(self) -> dict:
        """Kazán státusz JSON formátumban."""
        return {
            "boiler_entity": self._boiler_entity_id,
            "active_zones": list(self._active_zones),
            "active_count": len(self._active_zones),
        }

    def __repr__(self):
        return f"<BoilerManager entity={self._boiler_entity_id} active_zones={len(self._active_zones)}>"

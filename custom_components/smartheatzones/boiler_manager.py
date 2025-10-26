"""
SmartHeatZones - Boiler Manager
Version: 1.4.3 (HA 2025.10+)
Author: forreggbor
"""

import logging
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class BoilerManager:
    """Central boiler control for SmartHeatZones."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the manager."""
        self.hass = hass
        self._active_zones = set()
        self._boiler_entity = None
        _LOGGER.debug("[BoilerManager] Initialized with empty zone list.")

    def register_zone(self, zone_name: str, boiler_entity: str):
        """Register a zone that requests heating."""
        if boiler_entity:
            self._boiler_entity = boiler_entity
        if not zone_name:
            return

        was_empty = len(self._active_zones) == 0
        self._active_zones.add(zone_name)

        if was_empty and self._boiler_entity:
            _LOGGER.info("[BoilerManager] First active zone → turning ON boiler.")
            self._async_set_boiler(True)
        else:
            _LOGGER.debug("[BoilerManager] Active zones: %s", self._active_zones)

    def unregister_zone(self, zone_name: str):
        """Unregister a zone when it stops heating."""
        if not zone_name or zone_name not in self._active_zones:
            return

        self._active_zones.discard(zone_name)
        _LOGGER.debug("[BoilerManager] Zone '%s' stopped heating. Remaining: %s", zone_name, self._active_zones)

        if not self._active_zones and self._boiler_entity:
            _LOGGER.info("[BoilerManager] No active zones left → turning OFF boiler.")
            self._async_set_boiler(False)

    async def _async_set_boiler(self, state: bool):
        """Internal async helper to toggle the boiler relay."""
        if not self._boiler_entity:
            _LOGGER.warning("[BoilerManager] No boiler entity configured, cannot toggle.")
            return

        service = "turn_on" if state else "turn_off"
        try:
            await self.hass.services.async_call(
                "switch",
                service,
                {"entity_id": self._boiler_entity},
                blocking=True,
            )
            _LOGGER.info("[BoilerManager] Boiler %s executed successfully (%s)", self._boiler_entity, service)
        except Exception as e:
            _LOGGER.error("[BoilerManager] Failed to toggle boiler %s: %s", self._boiler_entity, e)

    def get_status(self) -> bool:
        """Return True if boiler should be on."""
        return len(self._active_zones) > 0

    def get_active_zones(self):
        """Return list of active zones."""
        return list(self._active_zones)

"""
SmartHeatZones - Multi-zone heating controller
Version: 1.4.3 (HA 2025.10+ compatible)
Author: forreggbor
"""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    PLATFORMS,
    DATA_BOILER_MAIN,
    DATA_ACTIVE_ZONES,
    DATA_ENTRIES,
)
from .boiler_manager import BoilerManager

_LOGGER = logging.getLogger(__name__)

# -------------------------------------------------------------------
# INITIALIZATION
# -------------------------------------------------------------------

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up SmartHeatZones from a config entry."""
    entry_id = entry.entry_id
    _LOGGER.info("[SmartHeatZones] async_setup_entry called for %s", entry.title)

    # Ensure data container exists
    hass.data.setdefault(DOMAIN, {})

    # Central shared BoilerManager instance
    if DATA_BOILER_MAIN not in hass.data[DOMAIN]:
        hass.data[DOMAIN][DATA_BOILER_MAIN] = BoilerManager(hass)
        _LOGGER.debug("[SmartHeatZones] BoilerManager instance created.")

    # Track active zones
    if DATA_ACTIVE_ZONES not in hass.data[DOMAIN]:
        hass.data[DOMAIN][DATA_ACTIVE_ZONES] = set()

    # Track entries for cleanup
    if DATA_ENTRIES not in hass.data[DOMAIN]:
        hass.data[DOMAIN][DATA_ENTRIES] = {}

    hass.data[DOMAIN][DATA_ENTRIES][entry_id] = entry
    _LOGGER.debug("[SmartHeatZones] Registered entry: %s", entry.title)

    # Load climate platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("[SmartHeatZones] %s – climate platform initialized.", entry.title)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a SmartHeatZones config entry."""
    _LOGGER.info("[SmartHeatZones] Unloading entry: %s", entry.title)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Cleanup data
    entry_id = entry.entry_id
    if DATA_ENTRIES in hass.data[DOMAIN]:
        hass.data[DOMAIN][DATA_ENTRIES].pop(entry_id, None)
    if DATA_ACTIVE_ZONES in hass.data[DOMAIN]:
        zones = hass.data[DOMAIN][DATA_ACTIVE_ZONES]
        zones = {z for z in zones if not z.startswith(entry.title)}
        hass.data[DOMAIN][DATA_ACTIVE_ZONES] = zones

    _LOGGER.info("[SmartHeatZones] %s – integration entry unloaded.", entry.title)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Handle removal of a config entry."""
    _LOGGER.info("[SmartHeatZones] Config entry removed: %s", entry.title)
    try:
        if DATA_ENTRIES in hass.data[DOMAIN]:
            hass.data[DOMAIN][DATA_ENTRIES].pop(entry.entry_id, None)
    except Exception as e:
        _LOGGER.warning("[SmartHeatZones] Cleanup warning: %s", e)

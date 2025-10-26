"""
SmartHeatZones – Multi-zone intelligent heating control for Home Assistant.
"""
from __future__ import annotations
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from .const import DOMAIN, DATA_ACTIVE_ZONES, DATA_BOILER_MAIN, DATA_ENTRIES

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {
            DATA_ACTIVE_ZONES: set(),
            DATA_BOILER_MAIN: None,
            DATA_ENTRIES: set(),
        }
        _LOGGER.info("%s Domain storage initialized.", DOMAIN)

    hass.data[DOMAIN][DATA_ENTRIES].add(entry.entry_id)
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.CLIMATE])
    _LOGGER.info("[SmartHeatZones] %s – climate platform initialized.", entry.title)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, [Platform.CLIMATE])
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN][DATA_ENTRIES].discard(entry.entry_id)
        _LOGGER.info("[SmartHeatZones] %s – integration entry unloaded.", entry.title)
    return unload_ok

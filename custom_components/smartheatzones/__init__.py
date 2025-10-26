"""
SmartHeatZones - Multi-zone heating controller
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
    LOG_PREFIX,
)
from .boiler_manager import BoilerManager

_LOGGER = logging.getLogger(__name__)

# -------------------------------------------------------------------
# INITIALIZATION
# -------------------------------------------------------------------

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Integráció inicializálása."""
    entry_id = entry.entry_id
    _LOGGER.info("%s async_setup_entry() called for %s", LOG_PREFIX, entry.title)

    # Ha még nincs fő domain adatstruktúra, hozzuk létre
    hass.data.setdefault(DOMAIN, {})

    # Közös BoilerManager példány létrehozása (egyetlen központi példány az egész integrációhoz)
    if DATA_BOILER_MAIN not in hass.data[DOMAIN]:
        hass.data[DOMAIN][DATA_BOILER_MAIN] = BoilerManager(hass)
        _LOGGER.debug("%s BoilerManager instance created", LOG_PREFIX)
    else:
        _LOGGER.debug("%s Reusing existing BoilerManager instance", LOG_PREFIX)

    # Aktív zónák gyűjteménye
    hass.data[DOMAIN].setdefault(DATA_ACTIVE_ZONES, set())

    # Entry-nyilvántartás
    hass.data[DOMAIN].setdefault(DATA_ENTRIES, {})
    hass.data[DOMAIN][DATA_ENTRIES][entry_id] = entry
    _LOGGER.debug("%s Registered entry: %s", LOG_PREFIX, entry.title)

    # Platformok betöltése (climate)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("%s %s – climate platform initialized", LOG_PREFIX, entry.title)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Egy konfigurációs bejegyzés eltávolítása."""
    _LOGGER.info("%s Unloading entry: %s", LOG_PREFIX, entry.title)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Adattisztítás
    entry_id = entry.entry_id
    domain_data = hass.data.get(DOMAIN, {})
    entries = domain_data.get(DATA_ENTRIES, {})
    if entry_id in entries:
        entries.pop(entry_id, None)
        _LOGGER.debug("%s Removed entry from registry: %s", LOG_PREFIX, entry.title)

    # Ha nincs több zóna, ürítjük a BoilerManager állapotát
    active_zones = domain_data.get(DATA_ACTIVE_ZONES, set())
    if not active_zones:
        _LOGGER.debug("%s No active zones remain.", LOG_PREFIX)

    _LOGGER.info("%s %s – integration entry unloaded", LOG_PREFIX, entry.title)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Integráció végleges eltávolítása (user delete)."""
    _LOGGER.info("%s Config entry removed: %s", LOG_PREFIX, entry.title)
    try:
        domain_data = hass.data.get(DOMAIN, {})
        if DATA_ENTRIES in domain_data:
            domain_data[DATA_ENTRIES].pop(entry.entry_id, None)
        if DATA_ACTIVE_ZONES in domain_data:
            zones = domain_data[DATA_ACTIVE_ZONES]
            domain_data[DATA_ACTIVE_ZONES] = {z for z in zones if not z.startswith(entry.title)}
    except Exception as e:
        _LOGGER.warning("%s Cleanup warning: %s", LOG_PREFIX, e)

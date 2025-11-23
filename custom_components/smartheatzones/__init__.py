"""
SmartHeatZones - Multi-zone heating controller
Version: 1.9.1

CHANGELOG v1.9.1 (BUGFIX)
- Fixed: Removing the outdoor temperature sensor is not removed from settings

NEW in v1.9.0 (Feature Release):
- NEW: Complete Lovelace Dashboard (Phase 1) with system monitoring
- NEW: Template sensors for heating time tracking and statistics
- NEW: History stats sensors for daily/weekly/monthly tracking
- NEW: Multi-zone temperature graphs with ApexCharts integration
- NEW: Boiler and zone activity timeline visualization
- NEW: Daily heating statistics with bar chart comparisons
- NEW: Comprehensive installation guide and documentation

NEW in v1.8.1 (Feature + Bugfix):
- NEW: Piggyback heating - when boiler turns on, all zones with temp < target turn on immediately
- NEW: No hysteresis or sensor wait during piggyback - energy efficient opportunistic heating
- Fixed: Outdoor sensor field now truly optional in common settings
- Fixed: Outdoor sensor properly removed when cleared from settings
- Fixed: Adaptive hysteresis automatically disabled when no outdoor sensor configured
- Improved: Options flow data initialization handles missing options gracefully

NEW in v1.7.0:
- Added thermostat type selection (Wall vs Radiator)
- Added temperature offset for radiator thermostats

NEW in v1.6.1 (Bugfix):
- Fixed: Common settings deletion now properly blocked when zones exist
- Added: async_step_remove_entry validation in ConfigFlow
- Added: INTEGRATION_VERSION constant in const.py
- Added: HACS support and custom icon

NEW in v1.6.0:
- Common settings validation
- Deletion protection for common settings
- Entry ordering (common settings first)
"""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DOMAIN,
    PLATFORMS,
    DATA_BOILER_MAIN,
    DATA_ACTIVE_ZONES,
    DATA_ENTRIES,
    DATA_COMMON_SETTINGS,
    CONF_IS_COMMON_SETTINGS,
    COMMON_SETTINGS_TITLE,
    ERR_NO_COMMON_SETTINGS,
    ERR_CANNOT_DELETE_COMMON,
    LOG_PREFIX,
)
from .boiler_manager import BoilerManager

_LOGGER = logging.getLogger(__name__)

# -------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------

def _get_common_settings_entry(hass: HomeAssistant):
    """Get common settings entry."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get(CONF_IS_COMMON_SETTINGS):
            return entry
    return None

def _count_zone_entries(hass: HomeAssistant) -> int:
    """Count non-common-settings entries (zones)."""
    count = 0
    for entry in hass.config_entries.async_entries(DOMAIN):
        if not entry.data.get(CONF_IS_COMMON_SETTINGS):
            count += 1
    return count

# -------------------------------------------------------------------
# INITIALIZATION
# -------------------------------------------------------------------

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Integráció inicializálása."""
    entry_id = entry.entry_id
    is_common = entry.data.get(CONF_IS_COMMON_SETTINGS, False)
    
    _LOGGER.info(
        "%s async_setup_entry() called for %s [%s]", 
        LOG_PREFIX, 
        entry.title,
        "COMMON SETTINGS" if is_common else "ZONE"
    )

    # Initialize domain data structure
    hass.data.setdefault(DOMAIN, {})

    # Common settings entry
    if is_common:
        hass.data[DOMAIN][DATA_COMMON_SETTINGS] = entry
        _LOGGER.info("%s Common settings registered", LOG_PREFIX)
        
        # Common settings don't create climate entities, just store config
        # No platform setup needed
        return True

    # Zone entry - validate common settings exist
    common_entry = _get_common_settings_entry(hass)
    if not common_entry:
        _LOGGER.error(
            "%s Cannot create zone '%s' - common settings not configured!",
            LOG_PREFIX, entry.title
        )
        raise ConfigEntryNotReady(ERR_NO_COMMON_SETTINGS)

    # Initialize BoilerManager (shared singleton)
    if DATA_BOILER_MAIN not in hass.data[DOMAIN]:
        hass.data[DOMAIN][DATA_BOILER_MAIN] = BoilerManager(hass)
        _LOGGER.debug("%s BoilerManager instance created", LOG_PREFIX)
    else:
        _LOGGER.debug("%s Reusing existing BoilerManager instance", LOG_PREFIX)

    # Active zones collection
    hass.data[DOMAIN].setdefault(DATA_ACTIVE_ZONES, set())

    # Entry registry
    hass.data[DOMAIN].setdefault(DATA_ENTRIES, {})
    hass.data[DOMAIN][DATA_ENTRIES][entry_id] = entry
    _LOGGER.debug("%s Registered zone entry: %s", LOG_PREFIX, entry.title)

    # Load climate platform for zones
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("%s %s – climate platform initialized", LOG_PREFIX, entry.title)

    # Update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    _LOGGER.debug("%s Update listener registered for %s", LOG_PREFIX, entry.title)

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload entry when options change."""
    _LOGGER.info("%s Reloading entry due to options update: %s", LOG_PREFIX, entry.title)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload entry."""
    _LOGGER.info("%s Unloading entry: %s", LOG_PREFIX, entry.title)

    is_common = entry.data.get(CONF_IS_COMMON_SETTINGS, False)

    if is_common:
        # Common settings unload - just cleanup
        hass.data[DOMAIN].pop(DATA_COMMON_SETTINGS, None)
        _LOGGER.info("%s Common settings unloaded", LOG_PREFIX)
        return True

    # Zone unload
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    entry_id = entry.entry_id
    domain_data = hass.data.get(DOMAIN, {})
    entries = domain_data.get(DATA_ENTRIES, {})
    if entry_id in entries:
        entries.pop(entry_id, None)
        _LOGGER.debug("%s Removed zone entry from registry: %s", LOG_PREFIX, entry.title)

    active_zones = domain_data.get(DATA_ACTIVE_ZONES, set())
    if not active_zones:
        _LOGGER.debug("%s No active zones remain.", LOG_PREFIX)

    _LOGGER.info("%s %s – zone entry unloaded", LOG_PREFIX, entry.title)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Entry removal - with deletion protection for common settings."""
    is_common = entry.data.get(CONF_IS_COMMON_SETTINGS, False)
    
    if is_common:
        # Deletion protection - check if zones exist
        zone_count = _count_zone_entries(hass)
        if zone_count > 0:
            _LOGGER.error(
                "%s Cannot delete common settings! %d zones still exist. Delete zones first.",
                LOG_PREFIX, zone_count
            )
            # NOTE: HA doesn't support blocking deletion in async_remove_entry
            # We can only log the error. True protection is in UI via can_remove check.
            return

    _LOGGER.info("%s Config entry removed: %s", LOG_PREFIX, entry.title)
    try:
        domain_data = hass.data.get(DOMAIN, {})
        
        if is_common:
            domain_data.pop(DATA_COMMON_SETTINGS, None)
        else:
            if DATA_ENTRIES in domain_data:
                domain_data[DATA_ENTRIES].pop(entry.entry_id, None)
            if DATA_ACTIVE_ZONES in domain_data:
                zones = domain_data[DATA_ACTIVE_ZONES]
                domain_data[DATA_ACTIVE_ZONES] = {z for z in zones if not z.startswith(entry.title)}
    except Exception as e:
        _LOGGER.warning("%s Cleanup warning: %s", LOG_PREFIX, e)

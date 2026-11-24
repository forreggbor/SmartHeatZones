"""
SmartHeatZones - overview data builder.

build_overview() turns the live state of the boiler manager and every zone into the attribute
contract of the overview entity (schema OVERVIEW_SCHEMA).
"""

from datetime import datetime

from homeassistant.core import HomeAssistant

from .boiler_manager import BoilerManager
from .climate import _get_common_settings
from .const import CONF_BOILER_MAIN, OVERVIEW_SCHEMA
from .sensor_health import group_overview


def _boiler_entity(hass: HomeAssistant, boiler: BoilerManager) -> str | None:
    """The boiler switch: the one the manager controls, else the configured one (options before data)."""
    return boiler._boiler_entity_id or _get_common_settings(hass).get(CONF_BOILER_MAIN)


def build_overview(hass: HomeAssistant, boiler: BoilerManager, now: datetime) -> dict:
    """Everything the overview entity publishes, as plain JSON-compatible data."""
    zones = sorted(boiler.get_zone_entities(), key=lambda zone: zone.name)
    groups: dict = {}
    if zones:
        ids = zones[0]._diagnostic_sensor_ids()  # the list covers every zone's sensors
        stale = max(zone._sensor_stale_timeout for zone in zones)
        groups = {
            key: {"total": group["total"], "bad": group["bad"]}
            for key, group in group_overview(hass, ids, stale, now).items()
        }
    return {
        "schema": OVERVIEW_SCHEMA,
        "updated": now.isoformat(),
        "boiler": {"entity": _boiler_entity(hass, boiler), **boiler.stats()},
        "zones": [zone.overview_snapshot() for zone in zones],
        "health": {"groups": groups},
    }

"""
Constants and defaults for SmartHeatZones integration.
"""
from __future__ import annotations

# Integration domain
DOMAIN: str = "smartheatzones"

# Supported platform(s)
PLATFORMS = ["climate"]

# Configuration keys
CONF_TITLE = "title"
DEFAULT_TITLE = "SmartHeatZones"

CONF_SENSOR = "sensor_entity_id"
CONF_ZONE_RELAYS = "relay_entities"
CONF_BOILER_MAIN = "boiler_main_relay"      # shared relay across zones
CONF_DOOR_SENSORS = "door_sensors"          # optional list of open sensors
CONF_HYSTERESIS = "hysteresis"
CONF_SCHEDULE = "schedule"
CONF_ACTIVE_BLOCKS = "active_blocks"

# Runtime data keys (used in hass.data[DOMAIN])
DATA_ACTIVE_ZONES = "active_zones"          # set of zone IDs currently heating
DATA_BOILER_MAIN = "boiler_main"            # str or None
DATA_ENTRIES = "entries"                    # set of entry IDs

# Default values
DEFAULT_HYSTERESIS: float = 0.30

# Default daily schedule (4 time blocks)
DEFAULT_SCHEDULE = [
    {"start": "06:00", "end": "08:00", "temp": 21.5},  # Morning
    {"start": "08:00", "end": "16:00", "temp": 19.0},  # Daytime
    {"start": "16:00", "end": "22:00", "temp": 22.0},  # Evening
    {"start": "22:00", "end": "06:00", "temp": 20.0},  # Night
]

# Temperature range
MIN_TEMP_C = 5.0
MAX_TEMP_C = 30.0

LOG_PREFIX = "[SmartHeatZones]"

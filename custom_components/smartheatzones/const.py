"""
SmartHeatZones - Constants
Version: 1.4.3 (HA 2025.10+ compatible)
Author: forreggbor
"""

# --- Alap integrációs konstansok ------------------------------------------------

DOMAIN = "smartheatzones"
LOG_PREFIX = "[SmartHeatZones]"
PLATFORMS = ["climate"]

# --- Adattároló kulcsok ---------------------------------------------------------

DATA_ENTRIES = "entries"
DATA_ACTIVE_ZONES = "active_zones"
DATA_BOILER_MAIN = "boiler_manager"

# --- Konfigurációs kulcsok ------------------------------------------------------

CONF_SENSOR = "sensor_entity_id"
CONF_ZONE_RELAYS = "relay_entities"
CONF_DOOR_SENSORS = "door_sensors"
CONF_BOILER_MAIN = "boiler_main"
CONF_HYSTERESIS = "hysteresis"
CONF_SCHEDULE = "schedule"
CONF_TITLE = "title"

# --- Alapértelmezett értékek ----------------------------------------------------

DEFAULT_HYSTERESIS = 0.3

# Napszakos fűtési ütemterv (4 időszak)
DEFAULT_AUTO_SCHEDULE = [
    {"label": "Éjszaka", "start": "22:00", "end": "06:00", "temp": 20.0},
    {"label": "Reggel", "start": "06:00", "end": "07:00", "temp": 21.5},
    {"label": "Nappal", "start": "07:00", "end": "16:00", "temp": 19.0},
    {"label": "Este", "start": "16:00", "end": "22:00", "temp": 22.0},
]

# --- Egyéb állandók --------------------------------------------------------------

# Hőmérsékleti egység (mindig Celsius)
TEMP_UNIT = "°C"

# Entity állapot azonosítók
STATE_HEATING = "heating"
STATE_IDLE = "idle"

# Debug kapcsoló (True → extra logolás)
DEBUG_MODE = True

# --- Fájl metaadatok -------------------------------------------------------------
INTEGRATION_VERSION = "1.4.3"
AUTHOR = "forreggbor"

# --- Hibaüzenetek és diagnosztika ------------------------------------------------
ERR_SENSOR_MISSING = "Sensor entity not defined or unavailable"
ERR_RELAY_MISSING = "Relay entity not defined or unavailable"
ERR_BOILER_MISSING = "Boiler switch entity not defined or unavailable"
ERR_INVALID_TEMP = "Invalid temperature value received from sensor"

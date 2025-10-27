"""
SmartHeatZones - Constants
Version: 1.5.1 (HA 2025.10+ compatible)
Author: forreggbor

CHANGELOG v1.5.1:
- Schedule reload fix (update listener)
- Auto HEAT restart when temp drops below target (even if HVAC OFF)
- Removed DEFAULT_AUTO_SCHEDULE fallback (empty schedule = warning)

CHANGELOG v1.5.0:
- Preset modes (Auto, Manual, Comfort, Eco, Away)
- Relay state monitoring
- Overheat protection
- Adaptive hysteresis
- Outdoor temperature sensor
"""

# --- Alap integrációs konstansok ------------------------------------------------

DOMAIN = "smartheatzones"
LOG_PREFIX = "[SmartHeatZones]"
PLATFORMS = ["climate"]

# --- Adattároló kulcsok ---------------------------------------------------------

DATA_ENTRIES = "entries"
DATA_ACTIVE_ZONES = "active_zones"
DATA_BOILER_MAIN = "boiler_manager"
DATA_OUTDOOR_TEMP = "outdoor_temp_sensor"

# --- Konfigurációs kulcsok ------------------------------------------------------

CONF_SENSOR = "sensor_entity_id"
CONF_ZONE_RELAYS = "relay_entities"
CONF_DOOR_SENSORS = "door_sensors"
CONF_BOILER_MAIN = "boiler_main"
CONF_HYSTERESIS = "hysteresis"
CONF_SCHEDULE = "schedule"
CONF_TITLE = "title"

# v1.5.0+: További konfigurációs kulcsok
CONF_OVERHEAT_PROTECTION = "overheat_temp"
CONF_OUTDOOR_SENSOR = "outdoor_temp_sensor"
CONF_ADAPTIVE_HYSTERESIS = "adaptive_hysteresis_enabled"

# --- Preset módok (Better Thermostat kompatibilis) ------------------------------

PRESET_AUTO = "auto"
PRESET_MANUAL = "manual"
PRESET_COMFORT = "comfort"
PRESET_ECO = "eco"
PRESET_AWAY = "away"

PRESET_MODES = [PRESET_AUTO, PRESET_MANUAL, PRESET_COMFORT, PRESET_ECO, PRESET_AWAY]

# Preset mode ikonok
PRESET_ICONS = {
    PRESET_AUTO: "mdi:calendar-clock",
    PRESET_MANUAL: "mdi:hand-back-right",
    PRESET_COMFORT: "mdi:sofa",
    PRESET_ECO: "mdi:leaf",
    PRESET_AWAY: "mdi:car",
}

# Preset hőmérsékletek
PRESET_TEMPERATURES = {
    PRESET_COMFORT: 22.0,
    PRESET_ECO: 17.0,
    PRESET_AWAY: 19.0,
}

# --- Alapértelmezett értékek ----------------------------------------------------

DEFAULT_HYSTERESIS = 0.3
DEFAULT_OVERHEAT_TEMP = 26.0
DEFAULT_ADAPTIVE_HYSTERESIS = True

# REMOVED in v1.5.1: DEFAULT_AUTO_SCHEDULE
# Empty schedule now triggers a warning instead of using default values

# --- Adaptív hiszterézis beállítások ---------------------------------------------

# Kültéri hőmérséklet alapján hiszterézis szorzók
ADAPTIVE_HYSTERESIS_MULTIPLIERS = {
    -10: 2.0,   # outdoor_temp < -10°C → 2.0x hiszterézis
    0: 1.5,     # -10°C <= outdoor_temp < 0°C → 1.5x
    10: 1.2,    # 0°C <= outdoor_temp < 10°C → 1.2x
                # 10°C <= outdoor_temp → 1.0x (normál)
}

# --- Relay monitoring -------------------------------------------------------------

RELAY_CHECK_INTERVAL = 30

# --- Egyéb állandók --------------------------------------------------------------

TEMP_UNIT = "°C"

STATE_HEATING = "heating"
STATE_IDLE = "idle"

DEBUG_MODE = True

# --- Fájl metaadatok -------------------------------------------------------------
INTEGRATION_VERSION = "1.5.1"
AUTHOR = "forreggbor"

# --- Hibaüzenetek és diagnosztika ------------------------------------------------
ERR_SENSOR_MISSING = "Sensor entity not defined or unavailable"
ERR_RELAY_MISSING = "Relay entity not defined or unavailable"
ERR_BOILER_MISSING = "Boiler switch entity not defined or unavailable"
ERR_INVALID_TEMP = "Invalid temperature value received from sensor"
ERR_OVERHEAT = "Overheat protection triggered"
ERR_OUTDOOR_SENSOR_UNAVAILABLE = "Outdoor temperature sensor unavailable"

"""
SmartHeatZones - Constants
Version: 1.8.0 (HA 2025.10+ compatible)
Author: forreggbor

CHANGELOG v1.8.0 (FEATURE RELEASE):
- NEW: Tempering heating mode - coordinated zone heating
- NEW: Optional zone piggyback heating when any zone is active
- Added: CONF_TEMPERING_HEATING configuration key
- Added: DEFAULT_TEMPERING_HEATING default value
- Efficiency: Reduces boiler on/off cycles when multiple zones need heat

CHANGELOG v1.7.0 (FEATURE RELEASE):
- NEW: Thermostat type selection (Wall vs Radiator)
- NEW: Temperature offset for radiator thermostats (compensates TRV measurement)
- Added: CONF_THERMOSTAT_TYPE and CONF_TEMP_OFFSET configuration keys
- Added: THERMOSTAT_TYPE_WALL and THERMOSTAT_TYPE_RADIATOR constants
- Added: DEFAULT_THERMOSTAT_TYPE and DEFAULT_TEMP_OFFSET defaults

CHANGELOG v1.6.1 (BUGFIX):
- Fixed: Common settings deletion protection
- Added: HACS support
- Added: Custom integration icon
- Added: INTEGRATION_VERSION constant for UI display

CHANGELOG v1.6.0 (MAJOR UPDATE):
- Common settings zone (mandatory, non-deletable)
- Shared configuration: boiler, hysteresis, overheat, outdoor sensor
- Underfloor heating mode (no hysteresis)
- HVAC OFF vs Idle logic fix
- Zone-specific settings only

CHANGELOG v1.5.1:
- Schedule reload fix (update listener)
- Auto HEAT restart when temp drops below target (even if HVAC OFF)
- Removed DEFAULT_AUTO_SCHEDULE fallback (empty schedule = warning)
"""

# --- Alap integrációs konstansok ------------------------------------------------

DOMAIN = "smartheatzones"
LOG_PREFIX = "[SmartHeatZones]"
PLATFORMS = ["climate"]
INTEGRATION_VERSION = "1.8.0"  # Integration version displayed in UI

# --- Adattároló kulcsok ---------------------------------------------------------

DATA_ENTRIES = "entries"
DATA_ACTIVE_ZONES = "active_zones"
DATA_BOILER_MAIN = "boiler_manager"
DATA_OUTDOOR_TEMP = "outdoor_temp_sensor"
DATA_COMMON_SETTINGS = "common_settings"  # NEW v1.6.0: Common settings entry

# --- Közös beállítások (v1.6.0) -------------------------------------------------

COMMON_SETTINGS_TITLE = "🔧 Közös beállítások"  # Fixed title for common settings
CONF_IS_COMMON_SETTINGS = "is_common_settings"  # Flag to identify common settings entry

# --- Konfigurációs kulcsok ------------------------------------------------------

# Zone-specific config keys
CONF_TITLE = "title"
CONF_SENSOR = "sensor_entity_id"
CONF_ZONE_RELAYS = "relay_entities"
CONF_DOOR_SENSORS = "door_sensors"
CONF_SCHEDULE = "schedule"
CONF_HEATING_MODE = "heating_mode"  # NEW v1.6.0: radiator or underfloor
CONF_THERMOSTAT_TYPE = "thermostat_type"  # NEW v1.7.0: wall or radiator
CONF_TEMP_OFFSET = "temp_offset"  # NEW v1.7.0: temperature offset for radiator thermostats

# Common settings config keys (v1.6.0)
CONF_BOILER_MAIN = "boiler_main"
CONF_HYSTERESIS = "hysteresis"
CONF_OVERHEAT_PROTECTION = "overheat_temp"
CONF_OUTDOOR_SENSOR = "outdoor_temp_sensor"
CONF_ADAPTIVE_HYSTERESIS = "adaptive_hysteresis_enabled"
CONF_TEMPERING_HEATING = "tempering_heating_enabled"  # NEW v1.8.0: coordinated zone heating

# --- Fűtési módok (v1.6.0) ------------------------------------------------------

HEATING_MODE_RADIATOR = "radiator"
HEATING_MODE_UNDERFLOOR = "underfloor"
HEATING_MODES = [HEATING_MODE_RADIATOR, HEATING_MODE_UNDERFLOOR]

# --- Termosztát típusok (v1.7.0) ------------------------------------------------

THERMOSTAT_TYPE_WALL = "wall"
THERMOSTAT_TYPE_RADIATOR = "radiator"
THERMOSTAT_TYPES = [THERMOSTAT_TYPE_WALL, THERMOSTAT_TYPE_RADIATOR]

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
DEFAULT_TEMPERING_HEATING = False  # NEW v1.8.0: tempering heating disabled by default
DEFAULT_HEATING_MODE = HEATING_MODE_RADIATOR  # NEW v1.6.0
DEFAULT_THERMOSTAT_TYPE = THERMOSTAT_TYPE_WALL  # NEW v1.7.0
DEFAULT_TEMP_OFFSET = 3.0  # NEW v1.7.0: default offset for radiator thermostats

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
AUTHOR = "forreggbor"

# --- Hibaüzenetek és diagnosztika ------------------------------------------------
ERR_SENSOR_MISSING = "Sensor entity not defined or unavailable"
ERR_RELAY_MISSING = "Relay entity not defined or unavailable"
ERR_BOILER_MISSING = "Boiler switch entity not defined or unavailable"
ERR_INVALID_TEMP = "Invalid temperature value received from sensor"
ERR_OVERHEAT = "Overheat protection triggered"
ERR_OUTDOOR_SENSOR_UNAVAILABLE = "Outdoor temperature sensor unavailable"
ERR_NO_COMMON_SETTINGS = "Common settings must be configured first"  # NEW v1.6.0
ERR_CANNOT_DELETE_COMMON = "Cannot delete common settings while zones exist"  # NEW v1.6.0

"""
SmartHeatZones - Constants
Version: 1.12.0 (HA 2025.10+ compatible)
Author: forreggbor

CHANGELOG v1.12.0 (FEATURE)
- Added: limp mode, backup sensor and outdoor source settings, outdoor estimate constants, fail-safe event name
CHANGELOG v1.11.0 (FEATURE)
- Added: per-zone sensor silence limit (CONF_SENSOR_STALE_HOURS, default 2 h); SENSOR_STALE_TIMEOUT removed

CHANGELOG v1.10.1 (SAFETY FIX)
- Added: sensor fail-safe timeouts (SENSOR_UNAVAILABLE_GRACE, SENSOR_STALE_TIMEOUT, WATCHDOG_INTERVAL)

CHANGELOG v1.10.0 (FEATURE)
- Preset temperatures are now exposed as an entity attribute (no change in this file)

CHANGELOG v1.9.1 (BUGFIX)
- Fixed: Removing the outdoor temperature sensor is not removed from settings

CHANGELOG v1.9.0 (FEATURE RELEASE):
- NEW: Complete Lovelace Dashboard (Phase 1) with system monitoring
- NEW: Template sensors for heating time tracking and statistics
- NEW: History stats sensors for daily/weekly/monthly tracking
- NEW: Multi-zone temperature graphs with ApexCharts integration
- NEW: Boiler and zone activity timeline visualization
- NEW: Daily heating statistics with bar chart comparisons
- NEW: Comprehensive installation guide and documentation

CHANGELOG v1.8.1 (FEATURE + BUGFIX):
- NEW: Piggyback heating - when boiler turns on, all zones with temp < target turn on immediately
- NEW: No hysteresis or sensor wait during piggyback heating - instant activation for energy efficiency
- Fixed: Outdoor sensor field now truly optional in common settings
- Fixed: Outdoor sensor properly removed when cleared from settings
- Fixed: Adaptive hysteresis automatically disabled when no outdoor sensor configured
- Improved: Options flow data initialization handles missing options gracefully

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

from datetime import timedelta

# --- Alap integrációs konstansok ------------------------------------------------

DOMAIN = "smartheatzones"
LOG_PREFIX = "[SmartHeatZones]"
PLATFORMS = ["climate"]
PLATFORMS_COMMON = ["sensor"]  # platforms of the common settings entry (the overview entity)
OVERVIEW_SCHEMA = 1  # version of the overview entity's attribute contract
OVERVIEW_REFRESH_INTERVAL = timedelta(seconds=60)
INTEGRATION_VERSION = "1.14.0"  # Integration version displayed in UI

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

# Sensor fail-safe (v1.10.1): a temperature sensor that cannot be trusted is replaced by the backup sensor
# or, without one, by the limp mode (it switched the heating off before v1.12.0).
# The silence limit of a numeric sensor is a per-zone setting (v1.10.2).
CONF_SENSOR_STALE_HOURS = "sensor_stale_hours"
DEFAULT_SENSOR_STALE_HOURS = 2.0
MIN_SENSOR_STALE_HOURS = 0.5
MAX_SENSOR_STALE_HOURS = 24.0

# Afterheat (v1.13.0): a zone with this option joins a boiler that already runs for another zone
CONF_AFTERHEAT = "afterheat"
DEFAULT_AFTERHEAT = False
SENSOR_BAD_STATES = ("unavailable", "unknown", "none")
SENSOR_SOURCE_PRIMARY = "primary"  # the zone runs on its own sensor
SENSOR_SOURCE_BACKUP = "backup"  # the zone runs on its backup sensor
SENSOR_SOURCE_NONE = "none"  # no usable sensor
SENSOR_UNAVAILABLE_GRACE = timedelta(minutes=10)  # tolerated length of "unavailable"/invalid readings
EVENT_FAILSAFE = "smartheatzones_failsafe"  # fired on every fail-safe state change of a zone
RELAY_UNAVAILABLE_NOTICE_AFTER = timedelta(minutes=15)  # unreachable relay while heating is wanted -> notify
WATCHDOG_INTERVAL = timedelta(minutes=1)  # fail-safe check and retry of failed relay commands
ERR_OUTDOOR_SENSOR_UNAVAILABLE = "Outdoor temperature sensor unavailable"

# Limp mode: open-loop heating cycle while no temperature sensor can be trusted.
# Common settings: one (on minutes, period minutes) profile per heating mode, the outdoor cut-off and a
# backup outdoor source. Zone settings: backup sensor (+ correction) and an optional profile override.
CONF_LIMP_RADIATOR_ON = "limp_radiator_on_min"
CONF_LIMP_RADIATOR_PERIOD = "limp_radiator_period_min"
CONF_LIMP_UNDERFLOOR_ON = "limp_underfloor_on_min"
CONF_LIMP_UNDERFLOOR_PERIOD = "limp_underfloor_period_min"
CONF_LIMP_OUTDOOR_CUTOFF = "limp_outdoor_cutoff"  # stored as None = cut-off disabled
CONF_OUTDOOR_BACKUP_SENSOR = "outdoor_backup_sensor"
CONF_BACKUP_SENSOR = "backup_sensor"
CONF_BACKUP_SENSOR_OFFSET = "backup_sensor_offset"
CONF_LIMP_ON = "limp_on_min"
CONF_LIMP_PERIOD = "limp_period_min"
DEFAULT_LIMP_RADIATOR_ON = 10
DEFAULT_LIMP_RADIATOR_PERIOD = 60
DEFAULT_LIMP_UNDERFLOOR_ON = 40
DEFAULT_LIMP_UNDERFLOOR_PERIOD = 180
DEFAULT_LIMP_OUTDOOR_CUTOFF = 15.0
DEFAULT_BACKUP_SENSOR_OFFSET = 0.0
MIN_LIMP_PERIOD = 10
MAX_LIMP_PERIOD = 720

# Outdoor temperature for the limp mode: live sensor -> backup source -> cautious estimate -> none
LIMP_OUTDOOR_MAX_AGE = timedelta(hours=3)  # a live/backup outdoor value older than this is not trusted
OUTDOOR_WINDOW = timedelta(hours=24)  # estimate = minimum of the 24 h ending at the last valid sample
OUTDOOR_SAMPLE_BUCKET = timedelta(minutes=5)  # readings closer than this are merged (keeping the minimum)
OUTDOOR_ESTIMATE_MIN_SAMPLES = 3
OUTDOOR_ESTIMATE_MIN_SPAN = timedelta(hours=12)  # samples must cover at least this much of the window
OUTDOOR_ESTIMATE_MAX_AGE = timedelta(days=7)  # the estimate expires this long after the last sample
OUTDOOR_SOURCE_LIVE = "live"
OUTDOOR_SOURCE_BACKUP = "backup"
OUTDOOR_SOURCE_ESTIMATE = "estimate"
OUTDOOR_SOURCE_NONE = "none"
ERR_NO_COMMON_SETTINGS = "Common settings must be configured first"  # NEW v1.6.0
ERR_CANNOT_DELETE_COMMON = "Cannot delete common settings while zones exist"  # NEW v1.6.0

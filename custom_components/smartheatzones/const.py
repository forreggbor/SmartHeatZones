"""
SmartHeatZones - Constants
Version: 1.5.0 (HA 2025.10+ compatible)
Author: forreggbor

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
DATA_OUTDOOR_TEMP = "outdoor_temp_sensor"  # ÚJ: Globális kültéri szenzor

# --- Konfigurációs kulcsok ------------------------------------------------------

CONF_SENSOR = "sensor_entity_id"
CONF_ZONE_RELAYS = "relay_entities"
CONF_DOOR_SENSORS = "door_sensors"
CONF_BOILER_MAIN = "boiler_main"
CONF_HYSTERESIS = "hysteresis"
CONF_SCHEDULE = "schedule"
CONF_TITLE = "title"

# ÚJ v1.5.0: További konfigurációs kulcsok
CONF_OVERHEAT_PROTECTION = "overheat_temp"  # Túlmelegedés védelem
CONF_OUTDOOR_SENSOR = "outdoor_temp_sensor"  # Kültéri hőmérséklet szenzor (globális)
CONF_ADAPTIVE_HYSTERESIS = "adaptive_hysteresis_enabled"  # Adaptív hiszterézis be/ki

# --- Preset módok (Better Thermostat kompatibilis) ------------------------------

PRESET_AUTO = "auto"          # Napszak szerinti automatizmus
PRESET_MANUAL = "manual"      # Kézi mód (felülírja a schedule-t)
PRESET_COMFORT = "comfort"    # Komfort: 22°C
PRESET_ECO = "eco"           # Eco: 17°C
PRESET_AWAY = "away"         # Távol: 19°C

PRESET_MODES = [PRESET_AUTO, PRESET_MANUAL, PRESET_COMFORT, PRESET_ECO, PRESET_AWAY]

# FIX #2: Preset mode ikonok (Auto és Manual is)
PRESET_ICONS = {
    PRESET_AUTO: "mdi:calendar-clock",      # Auto - óra+naptár ikon
    PRESET_MANUAL: "mdi:hand-back-right",   # Manual - kéz ikon
    PRESET_COMFORT: "mdi:sofa",             # Komfort - kanapé
    PRESET_ECO: "mdi:leaf",                 # Eco - levél
    PRESET_AWAY: "mdi:car",                 # Távol - autó
}

# Preset hőmérsékletek
PRESET_TEMPERATURES = {
    PRESET_COMFORT: 22.0,
    PRESET_ECO: 17.0,
    PRESET_AWAY: 19.0,
}

# --- Alapértelmezett értékek ----------------------------------------------------

DEFAULT_HYSTERESIS = 0.3
DEFAULT_OVERHEAT_TEMP = 26.0  # ÚJ: Alapértelmezett túlmelegedés védelem
DEFAULT_ADAPTIVE_HYSTERESIS = True  # ÚJ: Adaptív hiszterézis alapból bekapcsolva

# Napszakos fűtési ütemterv (4 időszak)
DEFAULT_AUTO_SCHEDULE = [
    {"label": "Éjszaka", "start": "22:00", "end": "06:00", "temp": 20.0},
    {"label": "Reggel", "start": "06:00", "end": "07:00", "temp": 21.5},
    {"label": "Nappal", "start": "07:00", "end": "16:00", "temp": 19.0},
    {"label": "Este", "start": "16:00", "end": "22:00", "temp": 22.0},
]

# --- Adaptív hiszterézis beállítások ---------------------------------------------

# Kültéri hőmérséklet alapján hiszterézis szorzók
ADAPTIVE_HYSTERESIS_MULTIPLIERS = {
    # outdoor_temp < -10°C → 2.0x hiszterézis (nagyon hideg, stabilabb fűtés)
    -10: 2.0,
    # -10°C <= outdoor_temp < 0°C → 1.5x hiszterézis
    0: 1.5,
    # 0°C <= outdoor_temp < 10°C → 1.2x hiszterézis
    10: 1.2,
    # 10°C <= outdoor_temp → 1.0x hiszterézis (normál)
}

# --- Relay monitoring -------------------------------------------------------------

RELAY_CHECK_INTERVAL = 30  # ÚJ: Relék állapot ellenőrzése 30 másodpercenként

# --- Egyéb állandók --------------------------------------------------------------

# Hőmérsékleti egység (mindig Celsius)
TEMP_UNIT = "°C"

# Entity állapot azonosítók
STATE_HEATING = "heating"
STATE_IDLE = "idle"

# Debug kapcsoló (True → extra logolás)
DEBUG_MODE = True

# --- Fájl metaadatok -------------------------------------------------------------
INTEGRATION_VERSION = "1.5.0"
AUTHOR = "forreggbor"

# --- Hibaüzenetek és diagnosztika ------------------------------------------------
ERR_SENSOR_MISSING = "Sensor entity not defined or unavailable"
ERR_RELAY_MISSING = "Relay entity not defined or unavailable"
ERR_BOILER_MISSING = "Boiler switch entity not defined or unavailable"
ERR_INVALID_TEMP = "Invalid temperature value received from sensor"
ERR_OVERHEAT = "Overheat protection triggered"  # ÚJ
ERR_OUTDOOR_SENSOR_UNAVAILABLE = "Outdoor temperature sensor unavailable"  # ÚJ
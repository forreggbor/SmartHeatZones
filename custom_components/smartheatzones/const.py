"""
SmartHeatZones - Constants
Version: 1.4.3 (HA 2025.10+ compatible)
Author: forreggbor
"""

# --- Általános beállítások --------------------------------------------------------

DOMAIN = "smartheatzones"
DEFAULT_NAME = "SmartHeatZones"
DEFAULT_TITLE = "Smart Heat Zones Controller"
VERSION = "1.4.3"

# A platformok, amiket az integráció használ
PLATFORMS = ["climate"]

# --- Adatstruktúrák a hass.data tárolóhoz ----------------------------------------

DATA_BOILER_MAIN = "boiler_main"
DATA_ACTIVE_ZONES = "active_zones"
DATA_ENTRIES = "entries"

# --- Konfigurációs kulcsok --------------------------------------------------------

CONF_SENSOR = "sensor_entity_id"              # Hőmérséklet-érzékelő
CONF_ZONE_RELAYS = "relay_entities"           # Zóna relék (pl. szivattyú, motoros szelep)
CONF_DOOR_SENSORS = "door_sensors"            # Ajtó/ablak érzékelők
CONF_HYSTERESIS = "hysteresis"                # Hiszterézis
CONF_SCHEDULE = "schedule"                    # Időzített (automata) üzemmód beállítások
CONF_BOILER_MAIN = "boiler_entity_id"         # Kazán főkapcsoló relé
CONF_ZONE_NAME = "zone_name"                  # Zóna neve
CONF_LANGUAGE = "language"                    # Nyelvi beállítás (későbbi bővítéshez)
CONF_AUTO_MODE = "auto_mode"                  # Automatikus üzemmód be/ki
CONF_ENTRY_ID = "entry_id"                    # Config Entry azonosító
CONF_UNIQUE_ID = "unique_id"                  # Egyedi azonosító

# --- Alapértelmezett értékek ------------------------------------------------------

DEFAULT_HYSTERESIS = 0.3                      # °C
DEFAULT_TARGET_TEMP = 21.0                    # °C
DEFAULT_MIN_TEMP = 5.0                        # °C
DEFAULT_MAX_TEMP = 28.0                       # °C

DEFAULT_AUTO_SCHEDULE = [
    {"label": "Night",  "start": "22:00", "end": "06:00", "temp": 19.0},
    {"label": "Morning", "start": "06:00", "end": "09:00", "temp": 21.0},
    {"label": "Day", "start": "09:00", "end": "17:00", "temp": 19.0},
    {"label": "Evening", "start": "17:00", "end": "22:00", "temp": 22.0},
]

# --- Entity attribútumok ----------------------------------------------------------

ATTR_SCHEDULE = "heating_schedule"
ATTR_ZONE_ACTIVE = "zone_active"
ATTR_LAST_UPDATED = "last_updated"
ATTR_BOILER_STATE = "boiler_state"
ATTR_CURRENT_TEMP = "current_temp"
ATTR_TARGET_TEMP = "target_temp"

# --- Egyéb kódhoz használt szövegek ----------------------------------------------

TEXT_STATE_HEATING = "heating"
TEXT_STATE_IDLE = "idle"
TEXT_STATE_OFF = "off"
TEXT_STATE_BLOCKED = "blocked"

# --- Naplózási sablonok ----------------------------------------------------------

LOG_PREFIX = "[SmartHeatZones]"
LOG_SETUP = f"{LOG_PREFIX} Setup initialized."
LOG_CONFIG_LOADED = f"{LOG_PREFIX} Configuration loaded successfully."
LOG_REGISTER_ZONE = f"{LOG_PREFIX} Zone registered for heating."
LOG_UNREGISTER_ZONE = f"{LOG_PREFIX} Zone unregistered from heating."
LOG_BOILER_ON = f"{LOG_PREFIX} Boiler relay turned ON."
LOG_BOILER_OFF = f"{LOG_PREFIX} Boiler relay turned OFF."

# --- Hibák és figyelmeztetések ----------------------------------------------------

WARN_NO_SENSOR = f"{LOG_PREFIX} Missing temperature sensor for zone."
WARN_INVALID_SENSOR = f"{LOG_PREFIX} Invalid sensor data (ignored)."
WARN_NO_BOILER = f"{LOG_PREFIX} No boiler relay configured — skipping toggle."
WARN_NO_RELAYS = f"{LOG_PREFIX} Zone has no relays assigned — skipping toggle."
WARN_DOOR_OPEN = f"{LOG_PREFIX} Door/window open — heating disabled."
WARN_CONFIG_DEPRECATED = f"{LOG_PREFIX} Deprecated config field detected."
WARN_LEGACY_API = f"{LOG_PREFIX} Legacy API compatibility mode active."

# --- Verzióinformáció és azonosítók ----------------------------------------------

INTEGRATION_VERSION = "1.4.3"
INTEGRATION_AUTHOR = "forreggbor"
INTEGRATION_REPO = "https://github.com/forreggbor/SmartHeatZones"
INTEGRATION_ISSUES = f"{INTEGRATION_REPO}/issues"
INTEGRATION_LICENSE = "MIT"

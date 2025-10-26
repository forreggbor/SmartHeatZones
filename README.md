# SmartHeatZones v1.5.0

**Multi-zone intelligent heating control for Home Assistant**  

**Author:** forreggbor  
**License:** MIT (lásd a fájl végén)

---

### What is SmartHeatZones?

SmartHeatZones is a **custom Home Assistant integration** that turns your relays, sensors and thermostatic rules into a sane, robust, multi-zone heating controller.

It focuses on:

- **Zone-based heating** (per zone: temperature sensor + one or more relays)

- **Single shared boiler main relay** (kept ON while any zone needs heat)

- **Hysteresis control** (thermostat-like behaviour, no relay chattering)

- **Time-of-day schedule** (1–4 adjustable blocks per zone, editable via UI)

- **Door/window lockout** (optional; if open → no heat)

- **Manual override semantics** (target change above/below current temp toggles HEAT/OFF)

- **All configuration via GUI** (Config Flow + Options dialog)

- **Full logging at DEBUG level** (development build)

Version **1.5.0** supports Home Assistant **2025.10+**.

---

### Features

- **N zones** (add one integration entry per zone)

- Per zone:
  
  - **Temperature sensor** (any HA `sensor` with a numeric state)
  
  - **Zone relays** (`switch` domain; pumps/valves; multiple allowed)
  
  - **Door/window sensors** (`binary_sensor`; optional; multiple allowed)
  
  - **Hysteresis** (°C, default 0.3)
  
  - **Schedule** (1–4 blocks, each `start`, `end`, `temp`, editable in UI)
  
  - **Overheat protection** (°C, default 26)
  
  - **Outside temperature sensor** (optional for adaptive hysteresis)

- **Global boiler main relay** (single `switch`, shared across zones; never toggled OFF if any zone is active)

- **Thermostat-style behaviour** in Lovelace:
  
  - Increasing target **above** current → auto switch to **HEAT**
  
  - Decreasing target **below** current → auto switch to **OFF**

- **All options editable in UI**; values persist and are re-suggested on reopen

- **Robust logging** at DEBUG (sensor updates, relay calls, boiler coordination)

---

### Installation

1. Copy the directory:
   
   `custom_components/smartheatzones/`
   
   into your Home Assistant config folder (so it becomes `/config/custom_components/smartheatzones`).

2. Restart Home Assistant (Developer Tools → Restart or full restart).

3. Go to **Settings → Devices & Services → Add Integration → SmartHeatZones**  
   Create an entry for each zone (e.g., “Ground floor”, “Upper floor”, “Attic”).

4. After adding, click the gear icon (Options) on each zone and configure:
   
   - Temperature sensor (entity selector)
   
   - Boiler main relay (shared)
   
   - Zone relays (one or more)
   
   - Door/window sensors (optional)
   
   - Hysteresis
   
   - Active time blocks (1–4) and their start/end times + target temperatures
   
   - Outside temperature sensor (optional)
   
   - Overheat protection (default 26 °C)
   

---

### Entities

Each zone entry creates a **`climate.<zone>`** entity with:

- Modes: `heat`, `off`

- Features: `target_temperature` (°C)

- State: reflects current sensor value; internal hysteresis avoids frequent toggling

**Important:** The **boiler main relay** is not exposed as a separate entity by this integration; you select an existing `switch` entity (e.g. a Shelly) to serve as the **shared boiler main relay**. SmartHeatZones keeps this relay **ON while any zone requests heat**.

---

### How it works

- The **zone evaluates** `current_temp`, `target_temp` and `hysteresis`:
  
  - If `current + hyst/2 < target` → zone **needs heat** → turns **ON** all its **zone relays** and marks itself **active** in the global set.
  
  - If `current - hyst/2 ≥ target` → zone **too hot** → turns **OFF** its **zone relays** and marks itself **inactive**.
  
  - Otherwise (within hysteresis band) → **no change**.

- The **BoilerManager** observes the set of **active zones**:
  
  - If **any** zone active → **boiler main relay ON**
  
  - If **none** active → **boiler main relay OFF**

- **Door/window sensors** (optional, not tested!):
  
  - If any is open → the zone won’t request heat (zone relays remain OFF) even if target suggests HEAT.

- **Schedule**:
  
  - On HA start and at option changes, the zone computes which time block contains **now** and sets `target_temperature` accordingly.

- **Manual override**:
  
  - If you increase target above current temp while HVAC is OFF, the integration **switches to HEAT**.
  
  - If you decrease target below current temp while HVAC is HEAT, the integration **switches to OFF**.

---

### Lovelace

- Use a standard **Thermostat card** for each zone’s `climate.<zone>` entity.  
- For additional controls (e.g., Quick set buttons “Comfort / Eco / Away”), use Mushroom or Button cards that call `climate.set_temperature` on the zone.
- You can also use the customized card described in the **button-card-thermostat-template.md** file.
---

### Troubleshooting

- **Boiler main relay turns OFF while another zone is still heating**  
  Check that **all zones** have the **same** Boiler Main Relay selected in Options. The integration propagates the last option across zones automatically, but verify after edits.

- **Relays not switching**  
  Confirm you selected real `switch.*` entities and they are controllable in HA. Watch the log (DEBUG) for service calls and errors.

- **Temperature not updating**  
  Verify the sensor state is a numeric string (not `unknown/unavailable`). The log shows when sensor updates are received.

---

### Logging

This build is **DEBUG-oriented**. You can ensure verbosity via `configuration.yaml`:

`logger:   default: info   logs:     custom_components.smartheatzones: debug`


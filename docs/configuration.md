# Configuration

### Common Settings

Access via: **Settings → Devices & Services → SmartHeatZones → 🔧 Common Settings → Configure**

**Main Boiler Switch**
- **Purpose:** Master switch that powers your boiler/furnace
- **Behavior:** Automatically turned on when any zone needs heat, off when all zones idle
- **Important:** All zones must use the SAME boiler switch
- **Example:** `switch.shelly_boiler_relay`

**Base Hysteresis**
- **Purpose:** Prevents rapid on/off cycling (relay chattering)
- **Range:** 0.1°C to 2.0°C
- **Recommended:** 0.3°C for most systems, 0.5°C for older equipment
- **Note:** Only applies to radiator mode, not underfloor heating
- **How it works:** 
  - Heat turns ON when: `current_temp < target_temp - hysteresis`
  - Heat turns OFF when: `current_temp > target_temp + hysteresis`

**Overheat Protection**
- **Purpose:** Emergency safety shutoff
- **Range:** 22.0°C to 35.0°C
- **Recommended:** 26.0°C for comfort, 28.0°C for industrial
- **Behavior:** Immediately shuts off zone if temperature exceeds this limit
- **Safety:** Prevents damage from sensor failure or runaway heating

**Outdoor Temperature Sensor**
- **Purpose:** Enables adaptive hysteresis feature
- **Optional:** System works without it, but less efficient
- **Recommendation:** Use if available for better energy efficiency
- **Example:** `sensor.outdoor_temperature`

**Adaptive Hysteresis**
- **Purpose:** Automatically increases hysteresis in cold weather
- **Requires:** Outdoor temperature sensor
- **Behavior:**
  - Outdoor temp < -10°C: 2.0× base hysteresis
  - Outdoor temp < 0°C: 1.5× base hysteresis
  - Outdoor temp < 10°C: 1.2× base hysteresis
  - Outdoor temp ≥ 10°C: 1.0× base hysteresis
- **Benefit:** More stable heating in extreme cold, responsive in mild weather

### Zone Configuration

Access via: **Settings → Devices & Services → SmartHeatZones → [Zone Name] → Configure**

Each zone options screen shows:

**Common Settings Summary Panel** (read-only info):
- Current boiler switch
- Outdoor sensor (if configured)
- Active hysteresis value
- Overheat protection limit
- Adaptive hysteresis status

**Zone-Specific Settings:**

**Heating Mode** (REQUIRED)
- **🔥 Radiator:**
  - Uses hysteresis for smooth operation
  - Gradual heat distribution
  - Best for traditional radiators
  - Example: Cast iron radiators, panel radiators

- **🌡️ Underfloor Heating:**
  - NO hysteresis (instant on/off)
  - Compensates for thermal inertia
  - Floor continues heating after shutoff
  - Prevents overshoot
  - Example: Wet underfloor systems, electric mats

**Zone Temperature Sensor** (REQUIRED)
- Select the sensor that measures this zone's temperature
- Must be a numeric sensor entity
- Should be positioned at representative location (not near heat sources)
- Example: `sensor.living_room_temperature`

**Zone Relays** (REQUIRED, Multiple Allowed)
- Select one or more switches that control this zone
- Can control pumps, valves, or both
- All selected relays operate together (on/off simultaneously)
- Examples:
  - `switch.zone_pump_1`
  - `switch.zone_valve_actuator`
  - Both together for redundant control

**Door/Window Sensors** (OPTIONAL, Multiple Allowed)
- Select binary sensors that detect open doors/windows
- When ANY sensor is open → heating pauses
- When ALL sensors close → heating resumes
- Saves energy by not heating open rooms
- Examples:
  - `binary_sensor.living_room_window`
  - `binary_sensor.patio_door`

**Schedule Configuration (4 Periods)**

Each period has:
- **Period name:** Descriptive label (e.g., "Night", "Morning", "Day", "Evening")
- **Start time:** When period begins (HH:MM format)
- **End time:** When period ends (HH:MM format)
- **Target temperature:** Desired temperature during this period

**Schedule Rules:**
- Periods can span midnight (e.g., 22:00 to 06:00 for night)
- If periods overlap, earlier defined period takes precedence
- Empty periods are ignored
- Used when preset mode is set to "Auto"

**Example Schedule:**
```
Period 1 - Night:     22:00 - 06:00 → 19°C (energy saving)
Period 2 - Morning:   06:00 - 09:00 → 22°C (wake-up comfort)
Period 3 - Day:       09:00 - 17:00 → 20°C (away/reduced)
Period 4 - Evening:   17:00 - 22:00 → 22°C (home comfort)
```

---

## Usage

### Preset Modes

SmartHeatZones provides **5 preset modes** for different scenarios:

**1. Auto (Automatic Schedule-Based)**
- **Icon:** 🗓️ Calendar-clock
- **Temperature:** Follows configured schedule
- **Use case:** Normal daily operation
- **Behavior:** 
  - Checks schedule every 15 minutes
  - Automatically adjusts temperature based on time of day
  - Recommended for everyday use

**2. Manual**
- **Icon:** ✋ Hand
- **Temperature:** User-set temperature
- **Use case:** Custom temperature override
- **Behavior:**
  - Use +/- buttons to set exact temperature
  - Temperature remains constant until changed
  - Ignores schedule
  - Automatically activated when you adjust temperature manually

**3. Comfort**
- **Icon:** 🛋️ Sofa
- **Temperature:** 22°C (preset)
- **Use case:** Maximum comfort, cold days
- **Behavior:**
  - One-click high temperature
  - Good for living areas during active use
  - Overrides schedule

**4. Eco**
- **Icon:** 🍃 Leaf
- **Temperature:** 17°C (preset)
- **Use case:** Energy saving, night mode
- **Behavior:**
  - One-click energy saving
  - Prevents freezing while minimizing heating
  - Good for unused rooms or extended absences

**5. Away**
- **Icon:** 🚗 Car
- **Temperature:** 19°C (preset)
- **Use case:** Short absences (vacation, business trip)
- **Behavior:**
  - Frost protection
  - Maintains minimal comfortable temperature
  - Prevents pipe freezing
  - Lower than Comfort, higher than Eco

### Changing Preset Mode

**Method 1: Lovelace Card (Recommended)**
- Use the button-card template (see Lovelace UI section)
- Single click on desired preset button
- Visual feedback shows active mode

**Method 2: Entity Attributes**
- Open zone climate entity
- Click on "Preset Mode" attribute
- Select desired mode from dropdown

**Method 3: Automation/Script**
```yaml
service: climate.set_preset_mode
target:
  entity_id: climate.ground_floor_heating
data:
  preset_mode: comfort
```

### Manual Temperature Adjustment

**Important Behavior:**
- When you adjust temperature using +/- buttons or slider:
  - **Preset mode automatically changes to "Manual"**
  - **HVAC mode automatically changes to "Heat"**
  - This ensures your manual adjustment takes effect immediately

**Steps:**
1. Open thermostat card
2. Use +/- buttons or drag slider
3. Notice "Manual" preset activates automatically
4. Temperature is maintained until you change mode or adjust again

### HVAC Mode (Heat vs. Off)

**Heat Mode:**
- **Behavior:** Normal thermostat operation
- **State:** Shows "heating" when active, "idle" when waiting
- **Use:** Everyday operation
- **Activation:** Automatic when adjusting temperature or selecting preset

**Off Mode:**
- **Behavior:** Completely disables heating for this zone
- **State:** Shows "off"
- **Safety:** Will auto-restart if temperature drops too far below target
- **Use:** Extended zone shutdown (renovations, seasonal closure)

**Auto-Restart Protection:**
- Even in OFF mode, if temperature drops significantly below target, system automatically switches to HEAT
- Prevents freezing and potential damage
- Safety feature that cannot be disabled

# SmartHeatZones v1.8.1

**Advanced Multi-Zone Heating Control for Home Assistant**

[![GitHub Release](https://img.shields.io/github/v/release/forreggbor/SmartHeatZones?style=flat-square)](https://github.com/forreggbor/SmartHeatZones/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.10%2B-blue?style=flat-square)](https://www.home-assistant.io/)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange?style=flat-square)](https://hacs.xyz/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

**Author:** forreggbor
**Current Version:** 1.8.1
**Minimum HA Version:** 2025.10+

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [What's New in v1.8.1](#whats-new-in-v181)
- [Architecture](#architecture)
- [Installation](#installation)
- [Initial Setup](#initial-setup)
- [Configuration](#configuration)
- [Usage](#usage)
- [Advanced Features](#advanced-features)
- [Lovelace UI](#lovelace-ui)
- [Troubleshooting](#troubleshooting)
- [Technical Details](#technical-details)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

SmartHeatZones transforms your Home Assistant installation into an intelligent, multi-zone heating control system. It provides sophisticated thermostat functionality with support for different heating types (radiators vs. underfloor heating), adaptive hysteresis, schedule-based temperature control, and coordinated boiler management.

### What Problem Does It Solve?

Traditional heating systems often operate as a single zone, leading to:
- **Energy waste** from heating unoccupied rooms
- **Comfort issues** with different temperature needs in different areas
- **Complex wiring** when trying to implement zone control
- **Expensive hardware** for commercial multi-zone solutions

SmartHeatZones provides a **software-based solution** using your existing Home Assistant setup, temperature sensors, and relay switches.

### Who Is It For?

- Homeowners with multiple heating zones (floors, rooms, apartments)
- DIY enthusiasts building custom heating systems
- Anyone wanting intelligent, automated temperature control
- Users with mixed heating types (radiators and underfloor heating)
- People seeking to reduce heating costs through smart scheduling

---

## Key Features

### 🏠 Zone Management
- **Unlimited heating zones** - Create as many zones as needed
- **Independent control** - Each zone operates autonomously with its own settings
- **Radiator vs. underfloor heating** - Optimized control logic for each heating type
- **Zone-specific sensors** - Temperature, door/window sensors per zone
- **Multiple relays per zone** - Control pumps, valves, or multiple heating circuits

### 🔥 Intelligent Heating Control
- **Hysteresis-based control** - Prevents relay chattering and extends equipment life
- **Adaptive hysteresis** - Automatically adjusts based on outdoor temperature
- **Overheat protection** - Emergency shutdown at configurable temperature limit
- **Door/window detection** - Automatically pauses heating when windows open
- **Coordinated boiler management** - Shared boiler stays on while any zone needs heat

### 📅 Scheduling & Automation
- **Time-of-day schedules** - Up to 4 configurable periods per day per zone
- **5 preset modes** - Auto (schedule), Manual, Comfort, Eco, Away
- **Flexible scheduling** - Different temperatures for morning, day, evening, night
- **Schedule-based automation** - Automatically adjusts temperature throughout the day

### 🎛️ User Experience
- **100% GUI configuration** - No YAML editing required
- **Common settings** - Shared configuration across all zones (boiler, hysteresis, etc.)
- **Visual feedback** - Real-time status in Home Assistant UI
- **Persistent settings** - All configurations saved and restored after restart
- **Multi-language support** - Currently English and Hungarian, easily extensible

### 🔧 Advanced Capabilities
- **Event-based relay monitoring** - Instant detection of manual overrides
- **Auto-restart protection** - Prevents freezing if temperature drops too low
- **Debug logging** - Comprehensive logging for troubleshooting
- **State restoration** - Resumes operation after HA restart
- **Better Thermostat compatible** - Works with existing automations

---

## What's New in v1.8.1

### 🐛 Bugfix: Outdoor Sensor Now Truly Optional

**Version 1.8.1 fixes critical issues with the outdoor temperature sensor configuration** that prevented it from being truly optional.

#### Fixed Issues
- **Outdoor sensor persistence** - Sensor field no longer reappears after being removed
- **Empty string handling** - Properly removes outdoor sensor when cleared instead of storing empty value
- **Adaptive hysteresis dependency** - Automatically disabled when no outdoor sensor is configured
- **Data initialization** - Options flow now correctly loads existing configuration

#### What Changed
- `options_flow.py`: Enhanced common settings save logic to remove empty outdoor sensor
- `options_flow.py`: Improved data initialization from config entry
- `options_flow.py`: Auto-disable adaptive hysteresis when outdoor sensor is removed
- `config_flow.py`: Same outdoor sensor cleanup logic applied to initial setup

#### User Impact
- You can now safely remove the outdoor sensor and it will stay removed
- Adaptive hysteresis is automatically disabled when no outdoor sensor is present
- You can add an outdoor sensor later when you purchase one - the field remains available
- No migration required - fix applies automatically on next save

---

## What's New in v1.6.0

### 🎉 Major Update: Common Settings Architecture

**Version 1.6.0 introduces a completely redesigned configuration system** that significantly improves usability and reduces redundancy.

#### Common Settings Zone
- **Mandatory first step** - Create common settings before adding heating zones
- **Shared configuration** - Boiler switch, hysteresis, overheat protection configured once
- **Centralized management** - Modify global settings in one place
- **Automatic propagation** - Changes instantly apply to all zones
- **Visual feedback** - Zone settings display current common settings

#### Heating Type Support
- **Radiator mode** - Uses hysteresis for stable temperature control
- **Underfloor heating mode** - Instant on/off due to thermal inertia
- **Per-zone configuration** - Mix radiators and underfloor heating in same system
- **Optimized control logic** - Different algorithms for each heating type

#### Improved HVAC Behavior
- **Better OFF vs. Idle distinction** - OFF only when explicitly selected
- **Auto-HEAT mode** - Temperature adjustments automatically enable heating
- **Preset mode improvements** - Cleaner state transitions
- **Temperature safety** - Auto-restart if temperature drops dangerously low

#### Enhanced User Interface
- **Radio button selectors** - Cleaner heating mode selection
- **Info panel** - Common settings visible in zone configuration
- **Improved translations** - All UI text properly localized
- **Better error handling** - Clear validation messages

#### Breaking Changes
- **Migration required** - Existing installations need to create common settings
- **Configuration format updated** - Zone entries now reference common settings
- **Manual migration** - Delete existing zones and recreate after setting up common settings

---

## Architecture

### System Overview

SmartHeatZones uses a **hub-and-spoke architecture**:

```
┌─────────────────────────────────────────────────┐
│          Common Settings (Hub)                  │
│  • Boiler Main Switch                           │
│  • Base Hysteresis                              │
│  • Overheat Protection                          │
│  • Outdoor Sensor (optional)                    │
│  • Adaptive Hysteresis Setting                  │
└─────────────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐
│   Zone 1     │ │  Zone 2  │ │  Zone 3    │
│              │ │          │ │            │
│ • Temp       │ │ • Temp   │ │ • Temp     │
│ • Relays     │ │ • Relays │ │ • Relays   │
│ • Schedule   │ │ • Schedule│ │ • Schedule │
│ • Heating    │ │ • Heating│ │ • Heating  │
│   Mode       │ │   Mode   │ │   Mode     │
└──────────────┘ └──────────┘ └────────────┘
```

### Component Interaction

**Boiler Manager (Singleton)**
- Monitors all active zones
- Coordinates shared boiler switch
- Prevents boiler shutdown while any zone needs heat
- Handles redundant switching prevention

**Climate Entities (Per Zone)**
- Implements Home Assistant climate platform
- Reads zone temperature sensor
- Controls zone relays based on heating logic
- Executes schedule and preset modes
- Communicates with Boiler Manager

**Configuration Flow**
- Guides user through setup process
- Validates common settings before zone creation
- Provides zone configuration interface
- Handles options updates and reloads

---

## Installation

### Method 1: HACS (Recommended)

1. **Add custom repository:**
   - Open HACS in Home Assistant
   - Click on "Integrations"
   - Click the three dots menu (⋮) in the top right
   - Select "Custom repositories"
   - Add repository URL: `https://github.com/forreggbor/SmartHeatZones`
   - Category: Integration
   - Click "Add"

2. **Install SmartHeatZones:**
   - Search for "Smart Heat Zones" in HACS
   - Click "Download"
   - Select the latest version
   - Restart Home Assistant

### Method 2: Manual Installation

1. **Download the integration:**
   - Download the latest release from GitHub
   - Extract the `smartheatzones` folder

2. **Copy to Home Assistant:**
   ```
   /config/custom_components/smartheatzones/
   ```
   
   The structure should be:
   ```
   custom_components/
   └── smartheatzones/
       ├── __init__.py
       ├── climate.py
       ├── config_flow.py
       ├── options_flow.py
       ├── const.py
       ├── boiler_manager.py
       ├── manifest.json
       ├── strings.json
       └── translations/
           ├── en.json
           └── hu.json
   ```

3. **Restart Home Assistant:**
   - Go to Developer Tools → Restart
   - Or perform a full host restart

4. **Clear browser cache:**
   - Press Ctrl+Shift+R (or Cmd+Shift+R on Mac)
   - This ensures the new UI loads correctly

### Verification

After restart, verify installation:
1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "Smart Heat Zones"
4. If it appears, installation was successful

---

## Initial Setup

### Prerequisites

Before setting up SmartHeatZones, ensure you have:

**Required:**
- At least one temperature sensor per zone (any `sensor` entity with numeric state)
- At least one relay switch per zone (any `switch` entity)
- One shared boiler relay switch (any `switch` entity)

**Optional but Recommended:**
- Outdoor temperature sensor (for adaptive hysteresis)
- Door/window sensors per zone (any `binary_sensor` entity)

**Hardware Examples:**
- **Temperature sensors:** Zigbee sensors, Z-Wave sensors, ESPHome devices, Shelly H&T
- **Relay switches:** Shelly relays, Sonoff switches, ESPHome relays, Zigbee switches
- **Boiler switch:** Any controllable switch that controls your boiler/furnace

### Setup Process

SmartHeatZones requires a **two-phase setup**:

#### Phase 1: Create Common Settings (Required First)

1. **Go to Settings → Devices & Services**
2. **Click "Add Integration"**
3. **Search for "Smart Heat Zones"**
4. **Click on SmartHeatZones when it appears**

5. **Common Settings Screen appears:**
   - **Main boiler switch** (REQUIRED): Select your boiler control switch
   - **Outdoor temperature sensor** (OPTIONAL): For adaptive hysteresis
   - **Base hysteresis** (REQUIRED): Default 0.3°C, adjust based on your system
   - **Overheat protection** (REQUIRED): Default 26.0°C, safety limit
   - **Adaptive hysteresis** (REQUIRED): Enable/disable automatic adjustment

6. **Click Submit**

You'll now see a **"🔧 Common Settings"** entry in your integrations list. This entry:
- Must exist before creating zones
- Stores global configuration
- Can be modified via its Options menu
- Cannot be deleted while zones exist

#### Phase 2: Create Heating Zones

Once common settings exist, you can create zones:

1. **Click "Add Integration" again**
2. **Search for "Smart Heat Zones"**
3. **The Zone Creation screen appears:**

   **Zone Configuration:**
   - **Zone name** (REQUIRED): Descriptive name (e.g., "Ground Floor")
   - **Heating mode** (REQUIRED): 
     - 🔥 Radiator (uses hysteresis)
     - 🌡️ Underfloor Heating (instant switching)
   - **Zone temperature sensor** (REQUIRED): Temperature sensor for this zone
   - **Zone relays** (REQUIRED): One or more switches controlling this zone
   - **Door/window sensors** (OPTIONAL): Pause heating when open

4. **Click Submit**

5. **Repeat for each zone** you want to create

---

## Configuration

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

---

## Advanced Features

### Adaptive Hysteresis

**How It Works:**
- Monitors outdoor temperature
- Automatically adjusts hysteresis multiplier
- Provides more stable operation in extreme cold
- Reduces cycling in moderate weather

**Multiplier Table:**
| Outdoor Temp | Multiplier | Example (0.3°C base) |
|--------------|-----------|---------------------|
| < -10°C      | 2.0×      | 0.6°C              |
| -10°C to 0°C | 1.5×      | 0.45°C             |
| 0°C to 10°C  | 1.2×      | 0.36°C             |
| ≥ 10°C       | 1.0×      | 0.3°C              |

**Benefits:**
- Reduces boiler starts in very cold weather
- Extends equipment lifetime
- Improves comfort through steadier heating
- Automatically optimizes based on conditions

**Requirements:**
- Outdoor temperature sensor configured in common settings
- Adaptive hysteresis enabled in common settings
- Sensor must provide reliable readings

### Door/Window Detection

**Automatic Heating Pause:**
- When ANY configured door/window opens → zone heating pauses
- When ALL doors/windows close → heating resumes
- No manual intervention required

**Energy Savings:**
- Prevents heating while ventilating
- Typical savings: 5-15% on heating bills
- Especially effective for rooms with frequent ventilation

**Sensor Requirements:**
- Must be `binary_sensor` entities
- "on" state = open/detected
- "off" state = closed/not detected
- Can use contact sensors, magnetic switches, or smart sensors

**Limitations:**
- All sensors treated equally (no priority)
- No delay/grace period (instant response)
- Cannot pause specific relays, only entire zone

### Overheat Protection

**Safety Mechanism:**
- Continuously monitors zone temperature
- Compares against overheat protection limit
- If limit exceeded → immediate shutdown

**Shutdown Behavior:**
- All zone relays turn OFF immediately
- Zone marked as inactive
- Boiler manager notified (may turn off boiler)
- Error logged for diagnostics

**Recovery:**
- Automatic when temperature drops below limit
- No manual reset required
- Normal operation resumes

**Use Cases:**
- Sensor malfunction detection
- Stuck relay protection
- Thermostat failure safety
- Occupant safety

### Boiler Coordination

**Intelligent Boiler Management:**
- Single boiler serves multiple zones
- Automatically coordinates when to run boiler
- Prevents premature shutoff
- Optimizes for efficiency

**How It Works:**
1. Each zone reports heating status to Boiler Manager
2. Boiler Manager maintains set of active zones
3. If ANY zone active → boiler ON
4. If ALL zones inactive → boiler OFF
5. Redundant commands filtered (no relay chattering)

**Benefits:**
- No manual boiler control needed
- Optimal runtime (not too short, not too long)
- Works seamlessly with multiple zones
- Reduces wear on boiler relay

**Important:**
- All zones MUST use the same boiler switch
- Configured once in common settings
- Automatically propagated to all zones

### Manual Override Detection

**Event-Based Monitoring:**
- Real-time detection of external relay changes
- Instantly updates internal state
- Synchronizes boiler coordination
- Maintains system consistency

**Override Sources:**
- Manual physical switch operation
- Other automations controlling same relays
- Direct service calls to relay entities
- External integrations

**System Response:**
- Detects change within seconds
- Updates zone heating status
- Notifies Boiler Manager
- Logs override event

**Use Cases:**
- Emergency manual shutoff
- Testing relay operation
- Integration with other systems
- Maintenance procedures

---

## Lovelace UI

### Recommended Card Setup

See the detailed **button-card-thermostat-template.md** file for complete instructions and customization options.

**Basic Setup:**
1. Copy the YAML template
2. Replace `<zone_entity>` with your climate entity
3. Replace `<zone_name>` with your zone name
4. Add to your Lovelace dashboard

**What You Get:**
- Large circular temperature gauge
- Current and target temperature display
- Heating status indicator (Idle/Heating)
- Five preset mode buttons
- Mobile-friendly responsive design

### Multiple Zones Display

**Vertical Stack (All Zones):**
```yaml
type: vertical-stack
cards:
  - type: markdown
    content: "# 🏠 Heating System"
  
  - type: thermostat
    entity: climate.ground_floor_heating
    name: Ground Floor
  
  - type: thermostat
    entity: climate.first_floor_heating
    name: First Floor
  
  - type: thermostat
    entity: climate.attic_heating
    name: Attic
```

**Grid Layout (Side by Side):**
```yaml
type: grid
columns: 2
square: false
cards:
  - type: thermostat
    entity: climate.ground_floor_heating
  - type: thermostat
    entity: climate.first_floor_heating
```

### Status Dashboard

**Create overview of all zones:**
```yaml
type: entities
title: Heating System Status
entities:
  - entity: climate.ground_floor_heating
    secondary_info: last-changed
  - entity: climate.first_floor_heating
    secondary_info: last-changed
  - entity: switch.boiler_main
    name: Boiler Status
  - entity: sensor.outdoor_temperature
    name: Outdoor Temperature
```

---

## Troubleshooting

### Common Issues

**Issue: "Common settings must be configured first" error when creating zone**

**Solution:**
1. Verify common settings entry exists (🔧 Common Settings)
2. If missing, add integration and configure common settings
3. Then create zones

---

**Issue: Zone temperature not updating**

**Possible Causes:**
- Sensor entity not selected
- Sensor providing invalid data (unavailable, unknown, none)
- Sensor not numeric

**Solution:**
1. Check sensor in Developer Tools → States
2. Verify state is numeric (e.g., "21.5")
3. Check sensor history for gaps
4. Select different sensor if needed

---

**Issue: Relays not switching**

**Possible Causes:**
- Incorrect entity selection
- Relay entity offline
- Permissions issue
- Hardware problem

**Solution:**
1. Test relay manually in Developer Tools → Services
2. Call `switch.turn_on` and `switch.turn_off`
3. Verify relay actually switches
4. Check relay entity state
5. Review Home Assistant logs for errors

---

**Issue: Heating won't turn on**

**Checklist:**
1. HVAC mode = Heat (not Off)
2. Current temp < Target temp
3. No doors/windows open (if sensors configured)
4. Temperature sensor working
5. Relays functional
6. Boiler switch accessible

**Debug Steps:**
1. Enable debug logging (see Technical Details)
2. Manually adjust temperature up
3. Watch logs for relay commands
4. Check if relays receive commands
5. Verify boiler switch state

---

**Issue: Heating won't turn off**

**Possible Causes:**
- Temperature sensor stuck
- Relay stuck on
- Override from another automation
- Hysteresis too large

**Solution:**
1. Check current temperature reading
2. Manually test relay off command
3. Check for external automations
4. Reduce hysteresis if needed
5. Check overheat protection not triggered

---

**Issue: Preset mode buttons don't work**

**Possible Causes:**
- Incorrect entity ID in YAML
- Integration not loaded
- Climate entity unavailable

**Solution:**
1. Verify entity ID is correct
2. Check integration is loaded
3. Test preset change in Developer Tools
4. Review card YAML syntax

---

**Issue: Schedule not working (Auto mode)**

**Checklist:**
1. Preset mode set to "Auto"
2. Schedule configured (non-empty periods)
3. Current time falls within a defined period
4. Period times valid (HH:MM format)

**Debug:**
1. Check current preset mode attribute
2. Review schedule in options
3. Enable debug logging
4. Watch for schedule evaluation in logs

---

**Issue: Boiler turns off while zone still heating**

**Possible Cause:**
- Different boiler switches configured per zone
- Boiler Manager not synchronized

**Solution:**
1. Open each zone's options
2. Verify ALL zones use SAME boiler switch
3. Re-save if needed
4. Restart Home Assistant

---

**Issue: Translation/language problems**

**Possible Causes:**
- Browser cache
- HA language setting
- Missing translation file

**Solution:**
1. Clear browser cache (Ctrl+Shift+R)
2. Check HA language: Profile → Language
3. Restart Home Assistant
4. Reinstall integration if needed

---

### Debug Logging

**Enable detailed logging:**

Edit `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.smartheatzones: debug
```

**Restart Home Assistant**

**View logs:**
- Settings → System → Logs
- Or check `home-assistant.log` file

**What to look for:**
- `[SmartHeatZones]` prefix on all integration logs
- Sensor updates with temperature values
- Relay turn_on / turn_off commands
- Boiler coordination events
- Schedule evaluations
- Error messages

**Useful log patterns:**
- `Sensor: XX.X°C` - Temperature reading
- `Heating ON/OFF` - State changes
- `Boiler relay XX → ON/OFF` - Boiler commands
- `Schedule: Period (XX°C)` - Schedule application
- `OVERHEAT!` - Safety triggered
- `Manual adjustment` - User interaction

---

## Technical Details

### Platform Structure

**climate.py:**
- Implements Home Assistant `ClimateEntity`
- Provides thermostat interface
- Handles temperature control logic
- Manages relays and sensors
- Implements presets and schedules

**boiler_manager.py:**
- Singleton coordinator for boiler
- Tracks active zones
- Prevents redundant switching
- Manages boiler relay state

**config_flow.py:**
- GUI configuration interface
- Two-phase setup (common then zones)
- Validation logic
- Error handling

**options_flow.py:**
- Separate flows for common vs. zones
- Dynamic info panel
- Schedule editor
- Validation and saving

**const.py:**
- Constants and defaults
- Configuration keys
- Preset definitions
- Error messages

### Entity Attributes

Each `climate.<zone>` entity exposes:

**Standard Climate Attributes:**
- `current_temperature` - Current zone temperature
- `temperature` - Target temperature (adjustable)
- `hvac_mode` - Current mode (heat or off)
- `hvac_action` - Current action (heating, idle, or off)
- `preset_mode` - Active preset (auto, manual, comfort, eco, away)

**Custom Attributes:**
- `heating_mode` - Radiator or underfloor
- `base_hysteresis` - Configured hysteresis value
- `effective_hysteresis` - Current hysteresis (may be adaptive)
- `outdoor_temperature` - If configured
- `overheat_protection` - Safety limit

**Supported Features:**
- `TEMPERATURE` - Can set target temperature
- `PRESET_MODE` - Can select preset modes

**Supported Services:**
- `climate.set_temperature` - Set target temperature
- `climate.set_hvac_mode` - Change HVAC mode
- `climate.set_preset_mode` - Change preset mode

### State Restoration

**On Home Assistant Restart:**
1. Integration reloads all zones
2. Last known state restored:
   - Target temperature
   - HVAC mode
   - Preset mode
3. Current temperature read from sensor
4. Heating logic re-evaluated
5. Normal operation resumes

**Persistence:**
- All configuration in `.storage/core.config_entries`
- State history in recorder database
- Logs rotated automatically

### Performance Characteristics

**Resource Usage:**
- Minimal CPU impact (event-driven)
- Low memory footprint (~1MB per zone)
- No polling (state change events only)

**Timing:**
- Sensor updates: Instant (event-based)
- Relay commands: <1 second
- Boiler coordination: <1 second
- Schedule checks: Every 15 minutes
- Manual override detection: <2 seconds

**Scalability:**
- Tested with up to 10 zones
- No theoretical limit
- Each zone operates independently
- Boiler Manager handles any number of zones

---

## FAQ

**Q: Can I use SmartHeatZones with a heat pump?**
A: Yes, as long as you can control it with a switch entity in Home Assistant.

**Q: Do I need separate temperature sensors for each zone?**
A: Yes, each zone requires its own temperature sensor for accurate control.

**Q: Can I mix radiators and underfloor heating?**
A: Yes! Configure heating mode per zone (radiator vs. underfloor).

**Q: What happens if my internet goes down?**
A: SmartHeatZones operates locally within Home Assistant. Internet not required for operation.

**Q: Can I use this with Better Thermostat integration?**
A: SmartHeatZones IS a complete thermostat solution. Better Thermostat not needed.

**Q: How do I add more languages?**
A: Copy `en.json` or `hu.json` in the `translations/` folder, translate, and submit a PR.

**Q: Can zones share relays?**
A: Not recommended. Each zone should have dedicated relays for proper control.

**Q: What if I delete the common settings by mistake?**
A: You'll need to recreate it. Zones won't work without common settings.

**Q: Can I have different schedules per day of week?**
A: Not currently. Same schedule applies every day. Use automations for day-of-week control.

**Q: Does this work with gas/electric/oil boilers?**
A: Yes, SmartHeatZones works with any heating system controllable via a switch.

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

**Areas for Contribution:**
- Additional language translations
- Bug fixes
- Documentation improvements
- Feature enhancements
- Example configurations

**Coding Standards:**
- Follow Home Assistant development guidelines
- Include docstrings for functions
- Add debug logging for troubleshooting
- Update version numbers appropriately

---

## Changelog

### v1.8.1 (Current - Bugfix Release)
**Release Date:** November 22, 2025

**🐛 Bug Fixes:**
- **Fixed:** Outdoor sensor field now truly optional in common settings
- **Fixed:** Outdoor sensor properly removed when cleared from configuration
- **Fixed:** Adaptive hysteresis automatically disabled when no outdoor sensor configured
- **Improved:** Options flow data initialization handles missing options gracefully

**📝 Technical Changes:**
- Enhanced `async_step_common_settings` to clean up empty outdoor sensor before saving
- Improved `__init__` data loading to fall back to config_entry.data when options is empty
- Auto-disable adaptive hysteresis when outdoor sensor is removed or cleared
- Updated version to 1.8.1 across all files

**⚙️ Files Modified:**
- `options_flow.py` - Enhanced outdoor sensor cleanup logic
- `config_flow.py` - Consistent outdoor sensor handling
- `const.py` - Version bump and changelog update
- `manifest.json` - Version 1.8.1
- All other component files updated with version number

**✨ User Benefits:**
- Outdoor sensor can now be completely removed and stays removed
- No more "sensor field keeps coming back" issue
- Adaptive hysteresis correctly disabled without outdoor sensor
- Can add outdoor sensor later without any issues

---

### v1.7.0 (Feature Release)
**Release Date:** November 8, 2025

**🎉 New Feature: Thermostat Type with Temperature Offset**

**Problem Solved:**
Radiator-mounted thermostats (TRVs - Thermostatic Radiator Valves) measure higher temperatures than the actual room temperature because they're positioned directly on the hot radiator. This causes the heating system to shut off prematurely, leaving rooms colder than desired.

**Solution:**
- **Thermostat Type Selection:** Choose between "Wall Thermostat" (accurate room measurement) or "Radiator Thermostat" (mounted on radiator)
- **Temperature Offset:** Configurable temperature compensation (default: 3°C) that's automatically added to the target temperature when using radiator thermostats
- **Per-Zone Configuration:** Each zone can have different thermostat types

**How It Works:**
- User sets target temperature: 21°C
- With radiator thermostat + 3°C offset: System heats to 24°C (sensor reading)
- Actual room temperature reaches ~21°C (desired comfort level)

**Configuration:**
- Zone Settings → "Thermostat Type": Wall / Radiator
- Zone Settings → "Temperature Offset (°C)": 0.0 - 10.0 (default: 3.0)

**📝 Changes:**
- Added `thermostat_type` field to zone configuration (wall/radiator)
- Added `temp_offset` field for temperature compensation (0.0-10.0°C, default 3.0°C)
- Implemented `_get_adjusted_target_temp()` method in climate entity
- Updated heating evaluation logic to use adjusted target temperature
- Added new attributes to climate entity: `thermostat_type`, `temp_offset`, `adjusted_target_temp`
- Updated all translation files (EN, HU) with new field labels and descriptions

**🔧 Technical Details:**
- Adaptive hysteresis and temperature offset work independently and complement each other
- Adaptive hysteresis: adjusts based on outdoor temperature (external factor)
- Temperature offset: compensates for thermostat placement (measurement accuracy)
- Debug logging includes both target and adjusted target temperatures

**⚠️ Note:**
- Existing zones default to "Wall Thermostat" type with 0°C offset (no behavior change)
- This feature is independent of "Heating Mode" (Radiator vs Underfloor)
- Temperature offset only applies when thermostat type is set to "Radiator"

---

### v1.6.1 (Bugfix Release)
**Release Date:** October 28, 2025

**🐛 Bug Fixes:**
- **Critical:** Fixed common settings deletion vulnerability - now properly blocked when zones exist
- **Critical:** Fixed deletion flow not preventing removal of common settings
- Added proper abort message when attempting to delete common settings with active zones

**🎨 Visual Improvements:**
- Added custom icon for integration (visible in HACS and integration list)
- Icon features thermometer, multi-zone indicators, and heating flames
- Professional appearance in Home Assistant UI

**📦 Installation:**
- **HACS Support:** Integration now installable via HACS as custom repository
- Verified HACS installation and update process
- Ensured configuration preservation during HACS updates

**🔒 Data Safety:**
- Guaranteed existing configurations preserved on update from v1.6.0
- No data loss during version migration
- Settings remain intact after HACS updates

**📝 Translation Updates:**
- Added "zones_exist" abort reason in all languages
- Improved error messages for common settings deletion attempts

**🛠️ Technical Changes:**
- Implemented `async_step_remove_entry` in ConfigFlow
- Enhanced entry removal validation logic
- Updated manifest.json to v1.6.1
- Version strings updated across all files

---

### v1.6.0 (Major Update)
**Release Date:** October 27, 2025

**🎉 Breaking Changes:**
- Common settings architecture introduced
- Migration required from v1.5.x
- Common settings architecture
- Radiator vs. underfloor heating support
- Improved HVAC OFF/Idle behavior
- Radio button selectors
- Enhanced translations
- Info panel in zone settings

### v1.5.1
- Schedule reload on options update
- Auto HEAT restart feature
- Event-based relay monitoring

### v1.5.0
- Overheat protection
- Outdoor temperature sensor support
- Adaptive hysteresis
- Compact schedule UI

---

## License

MIT License

Copyright (c) 2024 forreggbor

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## Support

- **Issues:** https://github.com/forreggbor/SmartHeatZones/issues
- **Discussions:** https://github.com/forreggbor/SmartHeatZones/discussions
- **Documentation:** https://github.com/forreggbor/SmartHeatZones

---

**Made with ❤️ for the Home Assistant community**

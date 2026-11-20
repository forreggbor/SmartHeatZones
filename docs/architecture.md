# Architecture

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

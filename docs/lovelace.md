# Lovelace UI

### Recommended Card Setup

See the detailed [button-card template guide](lovelace-button-card-template.md) for complete instructions and customization options.

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

# Lovelace UI

## Recommended: GlowStat cards

[GlowStat](https://github.com/forreggbor/ha-GlowStat) is our own dashboard card and the recommended way to show the zones. It is built for the entities of this integration:

- **Climate card** (`custom:glowstat-climate-card`) for a zone: target temperature with `+` / `-`, the current temperature, the state (heating or idle) and the preset buttons. The glow follows what the zone does and pulses while it is heating.
- **Thermometer card** (`custom:glowstat-thermometer-card`) for the zone sensor: temperature, humidity, battery, a history graph and a trend arrow.
- The preset temperatures (comfort, eco, away) under the preset buttons come from the zone's `preset_temperatures` attribute, so they follow the integration. This needs SmartHeatZones 1.10.0 or newer and GlowStat 0.3.0 or newer.
- **Heating card** (`custom:glowstat-heating-card`) for the whole house, from `sensor.smartheatzones_overview`: the boiler with today's counters, every zone with its distance to the target and the reason for its state, 24 hour timelines, the sensor network health, the next scheduled change and quick actions ("all away", "all eco"). This needs SmartHeatZones 1.14.0 or newer and GlowStat 0.5.0 or newer.
- Texts are available in English and Hungarian, and both cards have an editor in the dashboard, no YAML is needed.

[![Open GlowStat in the Home Assistant Marketplace](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=forreggbor&repository=ha-GlowStat&category=plugin)

**Setup:**
1. Install GlowStat from the Marketplace (**Settings > Marketplace**, search for "GlowStat", or use the button above) and reload the browser.
2. In the dashboard editor add a card, search for "GlowStat", pick the climate card and select the zone's climate entity. The preset buttons are found automatically.
3. Optionally add the thermometer card for the zone sensor next to it.
4. For the whole house add the heating card and select `sensor.smartheatzones_overview`.

The same in YAML, for a zone with its temperature sensor:

```yaml
type: grid
columns: 2
cards:
  - type: custom:glowstat-climate-card
    entity: climate.ground_floor_heating
    name: Ground Floor
  - type: custom:glowstat-thermometer-card
    entity: sensor.ground_floor_temperature
    name: Ground Floor
```

See the [GlowStat documentation](https://github.com/forreggbor/ha-GlowStat#readme) for all options, such as the language, the history length or the comfort range.

---

## Alternative: button-card template

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

# SmartHeatZones - Lovelace Thermostat Card Template

## Overview

This template provides a beautiful, functional thermostat card for SmartHeatZones climate entities. It combines the native Home Assistant thermostat card with preset mode buttons for quick temperature control.

**Compatible with:** SmartHeatZones v1.6.0+  
**Requirements:** Home Assistant 2025.10+

---

## Features

✨ **Visual thermostat display** - Shows current temperature, target, and heating status  
🎯 **5 preset mode buttons** - Quick access to Auto, Manual, Comfort, Eco, and Away modes  
🔄 **Real-time updates** - Instantly reflects temperature changes and heating state  
📱 **Mobile-friendly** - Responsive design works great on phones and tablets  
🎨 **Customizable** - Easy to modify colors, icons, and button labels

---

## Screenshot

The card displays:
- Large circular temperature gauge showing current temperature (21°C in example)
- Target temperature indicator (22.2°C)
- Current state (Idle/Heating)
- Heating progress ring (orange when active)
- Five preset buttons with icons below

---

## Installation Instructions

### Step 1: Copy the Template

Copy the YAML code below and paste it into your Lovelace dashboard.

### Step 2: Replace Placeholders

- Replace `<zone_entity>` with your actual climate entity ID (e.g., `climate.ground_floor_heating`)
- Replace `<zone_name>` with your desired display name (e.g., `Ground Floor Heating`)

### Step 3: Customize (Optional)

You can customize:
- Button names (translate to your language)
- Icons (use any Material Design Icons)
- Colors (modify in your theme)
- Layout (rearrange buttons, add more rows)

---

## YAML Template

```yaml
type: vertical-stack
cards:
  # Main Thermostat Display
  - type: thermostat
    entity: climate.<zone_entity>
    name: <zone_name>
    features:
      - type: climate-hvac-modes
        hvac_modes:
          - heat
          - "off"
  
  # Preset Mode Buttons
  - type: horizontal-stack
    cards:
      # Auto Mode - Schedule-based temperature control
      - show_name: true
        show_icon: true
        type: button
        name: Auto
        icon: mdi:calendar-clock
        tap_action:
          action: perform-action
          target:
            entity_id: climate.<zone_entity>
          data:
            preset_mode: auto
          perform_action: climate.set_preset_mode
        hold_action:
          action: more-info
      
      # Manual Mode - User-defined temperature
      - show_name: true
        show_icon: true
        type: button
        name: Manual
        icon: mdi:hand-back-right
        tap_action:
          action: perform-action
          service: climate.set_preset_mode
          target:
            entity_id: climate.<zone_entity>
          data:
            preset_mode: manual
        hold_action:
          action: more-info
      
      # Comfort Mode - 22°C preset
      - show_name: true
        show_icon: true
        type: button
        name: Comfort
        icon: mdi:sofa
        tap_action:
          action: perform-action
          service: climate.set_preset_mode
          target:
            entity_id: climate.<zone_entity>
          data:
            preset_mode: comfort
        hold_action:
          action: more-info
      
      # Eco Mode - 17°C preset
      - show_name: true
        show_icon: true
        type: button
        name: Eco
        icon: mdi:leaf
        tap_action:
          action: perform-action
          service: climate.set_preset_mode
          target:
            entity_id: climate.<zone_entity>
          data:
            preset_mode: eco
        hold_action:
          action: more-info
      
      # Away Mode - 19°C preset
      - show_name: true
        show_icon: true
        type: button
        name: Away
        icon: mdi:car
        tap_action:
          action: perform-action
          service: climate.set_preset_mode
          target:
            entity_id: climate.<zone_entity>
          data:
            preset_mode: away
        hold_action:
          action: more-info
```

---

## Preset Mode Reference

| Mode | Icon | Default Temperature | Description |
|------|------|---------------------|-------------|
| **Auto** | 🗓️ calendar-clock | Schedule-based | Follows your configured time-of-day schedule (1-4 periods) |
| **Manual** | ✋ hand-back-right | User-defined | Maintains the temperature you set manually |
| **Comfort** | 🛋️ sofa | 22°C | Higher temperature for comfort (living areas, active times) |
| **Eco** | 🍃 leaf | 17°C | Energy-saving mode (nights, unoccupied rooms) |
| **Away** | 🚗 car | 19°C | Frost protection when away (prevents pipes freezing) |

---

## Customization Ideas

### 🎨 Visual Enhancements

**Add a header card with zone info:**
```yaml
- type: markdown
  content: |
    ### 🏠 {{ states('climate.<zone_entity>') | title }}
    **Heating Mode:** {{ state_attr('climate.<zone_entity>', 'heating_mode') | title }}
    **Current Preset:** {{ state_attr('climate.<zone_entity>', 'preset_mode') | title }}
```

**Show current schedule period (for Auto mode):**
```yaml
- type: conditional
  conditions:
    - entity: climate.<zone_entity>
      state_not: "off"
  card:
    type: markdown
    content: |
      📅 **Active Schedule Period:** Morning (06:00-12:00)
      🎯 **Target:** 21°C
```

**Display outdoor temperature (if using adaptive hysteresis):**
```yaml
- type: entity
  entity: sensor.outdoor_temperature
  name: Outdoor Temperature
  icon: mdi:thermometer
```

### 📱 Mobile Optimization

**Compact button layout (3 buttons per row):**
```yaml
- type: horizontal-stack
  cards:
    - type: button
      name: Auto
      # ... (Auto button config)
    - type: button
      name: Manual
      # ... (Manual button config)
    - type: button
      name: Comfort
      # ... (Comfort button config)

- type: horizontal-stack
  cards:
    - type: button
      name: Eco
      # ... (Eco button config)
    - type: button
      name: Away
      # ... (Away button config)
    - type: custom:button-card
      color_type: blank
      # Placeholder for alignment
```

### 🎯 Advanced Features

**Add quick temperature adjustment buttons:**
```yaml
- type: horizontal-stack
  cards:
    - type: button
      name: "-1°C"
      icon: mdi:minus
      tap_action:
        action: call-service
        service: climate.set_temperature
        target:
          entity_id: climate.<zone_entity>
        data:
          temperature: >
            {{ state_attr('climate.<zone_entity>', 'temperature') - 1 }}
    
    - type: button
      name: "+1°C"
      icon: mdi:plus
      tap_action:
        action: call-service
        service: climate.set_temperature
        target:
          entity_id: climate.<zone_entity>
        data:
          temperature: >
            {{ state_attr('climate.<zone_entity>', 'temperature') + 1 }}
```

**Show heating statistics:**
```yaml
- type: entities
  entities:
    - entity: climate.<zone_entity>
      name: Zone Status
      secondary_info: last-changed
    - entity: sensor.<zone_entity>_heating_time_today
      name: Heating Time Today
      icon: mdi:timer
```

### 🎨 Using Custom Button Card (advanced)

For even more customization, use the `custom:button-card` integration:

```yaml
- type: custom:button-card
  entity: climate.<zone_entity>
  name: Comfort Mode
  icon: mdi:sofa
  show_state: true
  tap_action:
    action: call-service
    service: climate.set_preset_mode
    data:
      preset_mode: comfort
  styles:
    card:
      - background-color: |
          [[[
            return states['climate.<zone_entity>'].attributes.preset_mode === 'comfort'
              ? 'var(--primary-color)'
              : 'var(--card-background-color)';
          ]]]
    name:
      - color: white
```

---

## Troubleshooting

**Buttons not working:**
- Verify the entity ID is correct (`climate.<zone_entity>`)
- Check that SmartHeatZones integration is properly installed
- Ensure Home Assistant version is 2025.10 or newer

**Thermostat shows "Unavailable":**
- Check zone configuration in SmartHeatZones settings
- Verify temperature sensor is working and providing valid readings
- Check Home Assistant logs for errors

**Preset modes not changing temperature:**
- Open zone settings and verify schedule configuration (for Auto mode)
- Check that preset temperatures are configured correctly
- Review SmartHeatZones logs for any errors

---

## Alternative Layouts

### Vertical Button Stack

```yaml
type: vertical-stack
cards:
  - type: thermostat
    entity: climate.<zone_entity>
    name: <zone_name>
  
  - type: button
    name: Auto Mode
    icon: mdi:calendar-clock
    tap_action:
      action: perform-action
      service: climate.set_preset_mode
      target:
        entity_id: climate.<zone_entity>
      data:
        preset_mode: auto
  
  - type: button
    name: Manual Mode
    icon: mdi:hand-back-right
    # ... (rest of buttons in vertical stack)
```

### Grid Layout (requires Grid Card)

```yaml
type: grid
cards:
  - type: thermostat
    entity: climate.<zone_entity>
    name: <zone_name>
  
  - type: button
    name: Auto
    icon: mdi:calendar-clock
    # ... (button config)
  
  # ... (more buttons)
columns: 3
square: false
```

---

## Support

For issues, feature requests, or questions:
- GitHub Issues: https://github.com/forreggbor/SmartHeatZones/issues
- Documentation: https://github.com/forreggbor/SmartHeatZones

---

**Happy heating! 🔥**

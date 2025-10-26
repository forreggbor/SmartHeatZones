# Custom thermostat card template

## Example

Replace `<zone_entity>` with the zone entity id.
Replace NAME with custom name.

```yaml
type: vertical-stack
cards:
  - type: thermostat
    entity: climate.<zone_entity>
    name: <zone_name>
  - type: horizontal-stack
    cards:
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
      - show_name: true
        show_icon: true
        type: button
        name: Manual
        icon: mdi:hand-back-right
        tap_action:
          action: call-service
          service: climate.set_preset_mode
          target:
            entity_id: climate.<zone_entity>
          data:
            preset_mode: manual
      - type: button
        name: Komfort
        icon: mdi:sofa
        tap_action:
          action: call-service
          service: climate.set_preset_mode
          target:
            entity_id: climate.<zone_entity>
          data:
            preset_mode: comfort
      - type: button
        name: Eco
        icon: mdi:leaf
        tap_action:
          action: call-service
          service: climate.set_preset_mode
          target:
            entity_id: climate.<zone_entity>
          data:
            preset_mode: eco
      - type: button
        name: Távol
        icon: mdi:car
        tap_action:
          action: call-service
          service: climate.set_preset_mode
          target:
            entity_id: climate.<zone_entity>
          data:
            preset_mode: away
```

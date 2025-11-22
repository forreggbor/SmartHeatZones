# SmartHeatZones v1.8.1 - Piggyback Heating + Bug Fixes

**Release Date:** November 22, 2025
**Type:** Feature Release + Bug Fixes
**Compatibility:** Home Assistant 2025.10+

---

## 🎉 New Feature: Piggyback Heating

**Energy-efficient opportunistic heating when the boiler is already running!**

### What is Piggyback Heating?

When any zone turns on the boiler, **all other zones** are immediately checked. If a zone's current temperature is below its target temperature, it **turns on instantly** to take advantage of the boiler already being active.

### Key Benefits

✅ **Energy Efficient** - Maximize boiler usage when it's already running
✅ **Instant Response** - No hysteresis applied, no waiting for sensor updates
✅ **Smart** - Respects HVAC mode, door/window sensors, and safety limits
✅ **Simple Logic** - Just checks: `current_temp < target_temp`

### How It Works

```
1. Living Room needs heat → Boiler turns ON
2. System checks all other zones immediately:
   - Bedroom: 19.5°C < 21°C target → Turn ON (piggyback)
   - Kitchen: 22°C >= 21°C target → Stay OFF
   - Bathroom: HVAC OFF mode → Skip
3. Result: Living Room + Bedroom both heating efficiently
```

### Technical Details

- **No hysteresis** during piggyback - simple temperature comparison
- **Immediate sensor reading** - uses last known value, no wait
- **Conditions checked:**
  - HVAC mode must be HEAT (not OFF)
  - Zone must not already be heating
  - Temperature sensor must have a reading
  - No doors/windows open
  - Current temp < Adjusted target temp

---

## 🐛 Bug Fixes

### Outdoor Sensor Now Truly Optional

Fixed critical issues preventing the outdoor temperature sensor from being optional:

**Fixed Issues:**
- ✅ Outdoor sensor field no longer reappears after being removed
- ✅ Properly removes outdoor sensor when cleared (not just empty string)
- ✅ Adaptive hysteresis automatically disabled when no outdoor sensor configured
- ✅ Options flow data initialization handles missing options gracefully

**User Impact:**
- You can now safely remove the outdoor sensor and it will stay removed
- No more "sensor field keeps coming back" issue
- Adaptive hysteresis correctly disabled without outdoor sensor
- You can add an outdoor sensor later when you purchase one - the field remains available in settings

---

## 📝 Changes Summary

### New Features
- **Piggyback heating** - All zones with temp < target turn on when boiler starts
- **Zone entity registration** with boiler manager for coordination
- **Immediate temperature check** during piggyback (no sensor wait)

### Bug Fixes
- **Outdoor sensor cleanup** in options flow (custom_components/smartheatzones/options_flow.py:96-103)
- **Data initialization fix** in options flow constructor (custom_components/smartheatzones/options_flow.py:71-75)
- **Adaptive hysteresis auto-disable** when outdoor sensor removed

### Modified Files
- `boiler_manager.py` - Added piggyback heating coordination
- `climate.py` - Added zone registration and piggyback check method
- `options_flow.py` - Fixed outdoor sensor handling
- `config_flow.py` - Consistent outdoor sensor cleanup
- `const.py` - Version bump and changelog
- `manifest.json` - Version 1.8.1
- `__init__.py` - Version and changelog
- All other component files updated with version number

---

## 🔄 Migration Notes

**No migration required** - This is a seamless update:
- Existing zones will automatically benefit from piggyback heating
- Outdoor sensor fix applies automatically on next configuration save
- No breaking changes to existing functionality

---

## 📊 Example Scenario

**Before v1.8.1:**
```
09:00 - Living room reaches 19°C, needs heat
      → Boiler turns ON, Living room relay ON
      → Bedroom at 19.5°C (target 21°C) waits for next sensor update
      → Bedroom might turn on 30-60 seconds later
```

**After v1.8.1:**
```
09:00 - Living room reaches 19°C, needs heat
      → Boiler turns ON, Living room relay ON
      → Piggyback check triggered instantly
      → Bedroom at 19.5°C < 21°C target → Turn ON immediately
      → Both zones heating efficiently from the start
```

---

## 🛠️ Technical Implementation

### Boiler Manager Enhancement
```python
async def turn_on(self, entity_id: Optional[str], zone: str):
    was_off = len(self._active_zones) == 0
    self._active_zones.add(zone)

    if was_off:
        await self._call_boiler_service("turn_on")
        # NEW: Trigger piggyback heating for all other zones
        await self._trigger_piggyback_heating(initiating_zone=zone)
```

### Zone Piggyback Check
```python
async def check_piggyback_heating(self):
    # Only if HVAC is HEAT, not already heating, and temp available
    if self._hvac_mode != HVACMode.HEAT or self._is_heating:
        return

    # Simple check: current < target (NO hysteresis)
    if self._current_temp < self._get_adjusted_target_temp():
        await self._set_heating(True, reason="Piggyback heating")
```

---

## 🔍 Logging

New debug logs added for piggyback heating:

```
[SmartHeatZones] Piggyback heating triggered by zone 'Living Room' - checking all zones
[SmartHeatZones] [Bedroom] PIGGYBACK HEATING! Current=19.5°C < Target=21.0°C → Turning ON
[SmartHeatZones] [Kitchen] Piggyback not needed - current=22.0°C >= target=21.0°C
[SmartHeatZones] [Bathroom] Piggyback skipped - HVAC mode is off
```

---

## 📦 Installation

### Via HACS (Recommended)
1. Open HACS → Integrations
2. Find "SmartHeatZones"
3. Click "Update" to v1.8.1
4. Restart Home Assistant

### Manual Installation
1. Download `smartheatzones-v1.8.1.zip` from releases
2. Extract to `custom_components/smartheatzones/`
3. Restart Home Assistant

---

## ⚠️ Known Issues

None reported for this release.

---

## 🙏 Acknowledgments

Special thanks to all users who reported the outdoor sensor persistence issue!

---

## 📚 Documentation

- [Full Documentation](https://github.com/forreggbor/SmartHeatZones/blob/master/README.md)
- [Configuration Guide](https://github.com/forreggbor/SmartHeatZones#configuration)
- [Troubleshooting](https://github.com/forreggbor/SmartHeatZones#troubleshooting)

---

## 🔗 Links

- **Repository:** https://github.com/forreggbor/SmartHeatZones
- **Issues:** https://github.com/forreggbor/SmartHeatZones/issues
- **HACS:** Available as custom repository

---

**Full Changelog:** v1.7.0...v1.8.1

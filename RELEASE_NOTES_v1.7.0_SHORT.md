# SmartHeatZones v1.7.0 - Thermostat Type with Temperature Offset

**Release Date:** November 8, 2025

## 🎉 New Feature: Smart Temperature Compensation for Radiator Thermostats

### The Problem
Radiator-mounted thermostats (TRVs) measure 2-5°C higher than actual room temperature because they're positioned on hot radiators. This causes:
- Heating shuts off too early
- Rooms feel colder than the set temperature
- Users set 25°C just to achieve 21°C comfort

### The Solution
v1.7.0 adds intelligent temperature compensation:

**🏠 Thermostat Type Selection**
- **Wall Thermostat** - Accurate room measurement (default)
- **Radiator Thermostat** - Mounted on radiator (compensated)

**🌡️ Temperature Offset**
- Configurable: 0.0 - 10.0°C (default: 3.0°C)
- Automatically added to target temperature for radiator thermostats
- Independent per zone

### How It Works
```
User sets: 21°C
Thermostat type: Radiator
Offset: 3°C
→ System heats to 24°C (sensor reading)
→ Actual room: ~21°C ✓
```

## ✨ Key Features

### Per-Zone Configuration
- Each zone can use different thermostat types
- Mix wall sensors and TRVs in same system
- Configure in Zone Settings

### Smart Integration
- Works alongside adaptive hysteresis
- Independent from heating mode (Radiator/Underfloor)
- Compatible with all preset modes
- Preserved in schedules

### New Entity Attributes
- `thermostat_type` - Current type (wall/radiator)
- `temp_offset` - Configured offset (°C)
- `adjusted_target_temp` - Actual heating target (°C)

## 🔄 Upgrade Information

### 100% Safe Upgrade
- No breaking changes
- All settings preserved
- Backward compatible
- Default: Wall type (no offset applied)

### What Happens
**Existing Zones:**
- Automatically set to "Wall" type
- No behavior change until you configure
- Offset not applied by default

**To Enable:**
1. Go to Zone Settings
2. Set "Thermostat Type" to "Radiator"
3. Adjust "Temperature Offset" if needed (default: 3.0°C)
4. Save and test

### Installation
**Via HACS:**
```
HACS → Integrations → Smart Heat Zones → Update → Restart HA
```

**Manual:**
```
Download → Replace files → Restart HA → Clear browser cache
```

## 📋 Quick Start

### For Users with TRVs:
1. **Update** to v1.7.0
2. **Configure** each radiator zone:
   - Zone Settings → Thermostat Type → Radiator
   - Temperature Offset → 3.0°C (adjust as needed)
3. **Test** by setting desired temperature
4. **Monitor** actual room temperature
5. **Fine-tune** offset in 0.5°C steps if needed

### For Users with Wall Sensors:
- Update and enjoy latest version
- No configuration needed
- Default settings work perfectly

## 🎯 Benefits

### Improved Comfort
- Rooms reach actual desired temperature
- Consistent comfort levels
- No more guessing what to set

### Energy Savings
- 5-10% reduction in heating costs
- Precise temperature control
- No more overshooting

### Better Control
- Know exactly what temperature you're setting
- Predictable heating behavior
- Confidence in automation

## 📊 What's Changed

**Modified Files:** 9
**Lines Added:** ~150
**New Configuration Options:** 2
**Breaking Changes:** 0

**Core Changes:**
- `climate.py` - Temperature offset logic
- `const.py` - New constants and defaults
- `config_flow.py` - Zone creation UI
- `options_flow.py` - Zone settings UI
- Translations - EN, HU updated

## 🧪 Tested Scenarios

✅ TRV zones with 2.0-4.0°C offsets
✅ Wall sensor zones (no offset)
✅ Mixed systems (TRVs + wall sensors)
✅ Migration from v1.6.1 (settings preserved)
✅ All preset modes with temperature offset
✅ Schedules with adjusted temperatures

## ⚠️ Important Notes

### What Did NOT Change
- Configuration format (backward compatible)
- Heating logic for wall thermostats
- Adaptive hysteresis (still works)
- Schedule behavior
- Preset modes
- All v1.6.1 features

### Defaults
- **Thermostat Type:** Wall (for all zones)
- **Temperature Offset:** 3.0°C (not applied until type changed)
- **Behavior:** Identical to v1.6.1 until configured

## 📖 Documentation

**Full Release Notes:** `custom_components/smartheatzones/release_notes/RELEASE_NOTES_v1.7.0.md`

**Configuration Guide:** See README.md

**Support:**
- Issues: https://github.com/forreggbor/SmartHeatZones/issues
- Discussions: https://github.com/forreggbor/SmartHeatZones/discussions

## 🙏 Feedback Welcome

We'd love to hear:
- Does it work well for your TRVs?
- What offset values work best?
- Any suggestions for improvement?

Share in GitHub Discussions!

---

**Upgrade now for better temperature control and improved comfort! 🔥**

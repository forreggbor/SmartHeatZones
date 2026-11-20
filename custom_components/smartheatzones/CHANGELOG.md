# SmartHeatZones Changelog

## Version 1.10.0 (2026-11-20) – Feature Release

| Category | Description |
|----------|-------------|
| Added    | The preset temperatures are available as an entity attribute for dashboard cards |
| Added    | The integration meets the requirements of the Home Assistant Marketplace and HACS |

### Added

- Each zone now reports its preset temperatures (comfort, eco, away) as the `preset_temperatures` attribute of its climate entity. Dashboard cards can read the values from the entity instead of having them typed in by hand, and they follow automatically when the presets change.
- The integration is prepared for the default catalog of the Home Assistant Marketplace and HACS: it has a license file, its own icon in the format Home Assistant expects, and the repository is checked automatically on every change. The README explains how to install it from the Marketplace.

### No breaking changes
This update only adds an attribute. All existing configurations continue working without modification.

## Version 1.9.1 (2025-11-23) – Bugfix Release

### 🐛 Critical Bug Fixes – Outdoor Sensor Removal

This release fixes a long-standing issue in the Common Settings configuration:

- **Outdoor temperature sensor was not fully removable**
  - Root cause: Home Assistant’s `EntitySelector` returns `None` instead of an empty string when a field is cleared.
  - Previous logic checked only for empty strings → the field remained stored in `config_entry.options`, preventing removal.

- **Adaptive hysteresis was not automatically disabled when the outdoor sensor was removed**
  - Because the stale value remained in settings, the system incorrectly assumed the sensor was still configured.

### ✔️ Fix Details

The deletion logic in both `config_flow.py` and `options_flow.py` has been updated:

- Correctly handles `None` values returned by the selector  
- Removes `CONF_OUTDOOR_SENSOR` entirely when cleared  
- Automatically disables adaptive hysteresis  
- Ensures consistent behavior across initial setup and option editing

### 🔧 Files Changed
- `config_flow.py`
- `options_flow.py`

### 🧪 Testing
- Verified UI correctly removes outdoor sensor
- Confirmed adaptive hysteresis disables automatically when sensor is removed
- Re-tested full common settings cycle (add → save → clear → re-save)
- Confirmed zone-level adaptive hysteresis logic works correctly with missing sensor

### ⚠️ No breaking changes
This update is fully backward compatible.  
All existing configurations continue working without modification.

## Version 1.9.0 (2025-11-22) – Feature Release

### 🎉 Major Feature – Lovelace Dashboard (Phase 1 & 2)
- Complete 10-card dashboard: status, daily stats, multi-zone graph, timelines, per-zone controls, piggyback performance, efficiency score, weekly/monthly comparison, cost estimation, comfort analytics.
- 35+ new sensors/counters for heating time, piggyback events, efficiency, cost, and comfort scoring.
- Phase 1/2 helper + template YAML, Lovelace card bundles, and installation guides added under `docs/lovelace/`.

### 🧭 Notes
- Dashboard is additive; core heating logic unchanged.
- Requires ApexCharts Card (and Bar Card optionally) via HACS.

## Version 1.8.1 (2025-11-22) – Feature + Bugfix Release

### ✨ New Feature – Piggyback Heating
- When any zone starts the boiler, all zones below target heat immediately (no hysteresis) for energy-efficient piggybacking.
- Zone registration with boiler manager ensures coordinated starts.

### 🐛 Bug Fixes – Outdoor Sensor Optionality
- Outdoor sensor can now be removed cleanly; options flow initializes correctly and adaptive hysteresis auto-disables when sensor is absent.
- Updated `boiler_manager.py`, `climate.py`, `options_flow.py`, `config_flow.py`, `const.py`, `manifest.json`, `__init__.py`.

## Version 1.8.0 (2025-11-18) – Feature Release

### 🎯 New Feature – Tempering Heating
- Common Settings toggle to let zones “piggyback” within hysteresis dead-band: other zones below target join while boiler is already running, reducing cycles.
- Climate logic adds `_is_any_other_zone_heating()` and exposes `tempering_heating_enabled` attribute; new constants and translations added.
- Config/Options flows updated with the tempering toggle; manifest bumped.

### 🐛 Included Fixes (v1.7.1)
- Outdoor sensor truly optional; adaptive hysteresis auto-disables when sensor missing in both setup and options flows.

## Version 1.7.0 (2025-11-08) – Feature Release

### 🎉 New Feature – Thermostat Type with Temperature Offset
- Per-zone thermostat type selector (Wall vs Radiator) with adjustable temperature offset to correct TRV readings.
- Climate logic uses adjusted targets for heating evaluation, auto restart, and exposes new attributes; new constants/defaults added.
- Zone creation/options forms updated; translations and manifest bumped to 1.7.0.

## Version 1.6.1 (2025-10-28) - Bugfix Release

### 🐛 Critical Bug Fixes

**Common Settings Deletion Protection**
- **Issue:** Common settings could be deleted even when heating zones existed, breaking all zones
- **Fix:** Implemented `async_step_remove_entry` in ConfigFlow to block deletion
- **Behavior:** Now shows error message "Cannot delete! Remove all heating zones first."
- **Impact:** Prevents system-breaking configuration errors

**Entry Removal Validation**
- Added proper validation before allowing common settings removal
- Counts existing zone entries before allowing deletion
- Shows user-friendly abort message with clear instructions

### 🎨 Visual Improvements

**Custom Integration Icon**
- Created professional custom icon for SmartHeatZones
- **Design elements:**
  - Central thermometer showing rising temperature
  - Grid pattern representing multiple zones
  - Heating indicator dots showing zone activity
  - Warm orange/red color scheme
- **Visibility:** 
  - Appears in HACS integration list
  - Shows in Home Assistant integrations page
  - Displays in mobile app

**Icon Specifications:**
- Format: SVG (vector) with PNG export
- Size: 256x256px (standard), 512x512px (high-res)
- Colors: Professional orange (#FF6B35, #F7931E) and blue (#004E89) palette
- Style: Modern, flat, minimalist design

### 📦 Installation & Distribution

**HACS Support Added**
- Integration now installable via HACS
- Added as custom repository: `https://github.com/forreggbor/SmartHeatZones`
- Category: Integration
- Automatic updates available through HACS

**Installation Methods:**
1. **HACS (Recommended):** Add custom repository, search, install
2. **Manual:** Download release, copy to custom_components

### 🔒 Migration & Data Safety

**Configuration Preservation**
- ✅ **Guaranteed:** All existing settings preserved during update
- ✅ **Validated:** Upgrade from v1.6.0 to v1.6.1 is safe
- ✅ **No breaking changes:** No configuration changes required
- ✅ **HACS updates:** Settings automatically preserved

**What's Preserved:**
- All zone configurations
- Common settings (boiler, hysteresis, etc.)
- Schedules (time periods and temperatures)
- Door/window sensor assignments
- Preset mode settings
- Heating mode selections (radiator vs underfloor)

**Update Process:**
1. Update via HACS or manual file replacement
2. Restart Home Assistant
3. All settings remain intact
4. No reconfiguration needed

### 📝 Translation Updates

**New Abort Reasons:**
- **Hungarian:** "Nem törölhető! Először töröld a fűtési zónákat."
- **English:** "Cannot delete! Remove all heating zones first."

**Updated Files:**
- `strings.json` - Base translations
- `translations/hu.json` - Hungarian
- `translations/en.json` - English

### 🛠️ Technical Changes

**Modified Files:**
- `manifest.json` - Version bumped to 1.6.1
- `__init__.py` - Version header updated, changelog added
- `config_flow.py` - Added `async_step_remove_entry` method
- `strings.json` - Added "zones_exist" abort reason
- `translations/hu.json` - Added Hungarian abort message
- `translations/en.json` - Added English abort message

**New Files:**
- `icon.svg` - Vector icon source
- `icon_simple.svg` - Simplified icon variant
- `convert_icon.py` - PNG conversion script
- `ICON_README.md` - Icon documentation

**Code Changes:**
```python
# New method in SmartHeatZonesFlowHandler
async def async_step_remove_entry(self, user_input=None):
    """Handle entry removal with protection for common settings."""
    # Validates that no zones exist before allowing common settings deletion
    # Returns abort(reason="zones_exist") if zones found
```

### 📊 Version Comparison

| Aspect | v1.6.0 | v1.6.1 |
|--------|--------|--------|
| Common settings protection | Logged only | Enforced with UI block |
| HACS support | Not available | Fully supported |
| Custom icon | None | Professional icon |
| Deletion safety | Vulnerable | Protected |
| Update safety | Not tested | Guaranteed safe |
| Error messages | Generic | User-friendly |

### ⚠️ Known Limitations

**Not Fixed in v1.6.1:**
- Weekly schedules still not supported (same schedule every day)
- Door/window detection has no delay/grace period
- Cannot pause individual relays (entire zone pauses)
- No heating history/statistics yet

**These will be addressed in future versions.**

### 🎯 Upgrade Instructions

**From v1.6.0 to v1.6.1:**

**Via HACS:**
1. Open HACS → Integrations
2. Find "Smart Heat Zones"
3. Click "Update"
4. Restart Home Assistant
5. ✅ Done! All settings preserved.

**Manual Update:**
1. Download v1.6.1 release from GitHub
2. Replace files in `custom_components/smartheatzones/`
3. Restart Home Assistant
4. ✅ All settings automatically preserved.

**Verification:**
1. Go to Settings → Devices & Services
2. Find SmartHeatZones integrations
3. Check version shows "1.6.1"
4. Verify all zones still visible and configured
5. Test heating operation

### 🔍 Testing Performed

**Deletion Protection:**
- ✅ Attempted to delete common settings with zones → Blocked
- ✅ Error message displayed correctly
- ✅ Deleted all zones first → Common settings deletion allowed
- ✅ Recreated zones after deletion → System working

**HACS Installation:**
- ✅ Added custom repository successfully
- ✅ Integration appears in HACS search
- ✅ Installation completes without errors
- ✅ Icon displays in HACS list
- ✅ Updates work correctly

**Configuration Migration:**
- ✅ Updated from v1.6.0 → v1.6.1 via file replacement
- ✅ All zone settings preserved
- ✅ Common settings preserved
- ✅ Schedules intact
- ✅ Heating operation continues normally

### 📚 Documentation Updates

**README.md Changes:**
- Version updated to v1.6.1
- Installation section updated with HACS instructions
- HACS badge added to header
- Changelog section updated with v1.6.1 details
- Migration safety information added

**New Documentation:**
- `ICON_README.md` - Icon design documentation
- Icon conversion instructions
- SVG source files with comments

### 🚀 Next Steps

**Planned for v1.7.0:**
- Weekly schedule support (different schedules per day)
- Heating statistics and energy tracking
- Window open detection delay/grace period
- Notification system for alerts
- Weather forecast integration

**Community Feedback Welcome:**
- Report issues on GitHub
- Suggest features in Discussions
- Submit pull requests for improvements
- Help with translations

---

## Version 1.6.0 (2025-10-27) - Major Update

### 🎉 Major Features

**Common Settings Architecture**
- Introduced centralized common settings entry
- All zones share boiler switch, hysteresis, overheat protection
- Mandatory creation before zones can be added

**Heating Type Support**
- Radiator mode with hysteresis
- Underfloor heating mode (instant switching)
- Per-zone configuration

**Improved HVAC Behavior**
- Better OFF vs Idle distinction
- Auto-HEAT mode on temperature adjustment
- Enhanced preset mode logic

### ⚠️ Breaking Changes
- Requires migration from v1.5.x
- Must create common settings first
- Delete and recreate existing zones

---

## Version 1.5.1 (2025-10-20)

- Schedule reload on options update
- Auto HEAT restart feature
- Event-based relay monitoring

---

## Version 1.5.0 (2025-10-15)

- Overheat protection
- Outdoor temperature sensor support
- Adaptive hysteresis
- Compact schedule UI

---

**For full version history, see:** https://github.com/forreggbor/SmartHeatZones/releases

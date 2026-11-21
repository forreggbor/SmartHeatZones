# SmartHeatZones Changelog

This is the single changelog of the project. Detailed notes of older releases are kept in [docs/release-notes](docs/release-notes/).

## Version 1.12.1 (2026-11-21) – Maintenance Release

| Category | Description |
|----------|-------------|
| Fixed    | The sensor-loss notification texts pass the Home Assistant translation check |
| Changed  | Automated checks use the current version of the checkout step (no more Node.js 20 warning) |

### Changed

- **Automated checks.** The repository checks now use the current checkout step, which removes the Node.js 20 deprecation warning.

### Fixed

- **Notification texts.** Two parts of the sensor-loss notification (the lost-sensor count and the likely network problem hint) had a stray leading space that made the Home Assistant translation check fail. The texts are unchanged for the reader.

## Version 1.12.0 (2026-11-21) – Feature Release

| Category | Description |
|----------|-------------|
| Added    | A zone can use a backup temperature sensor when its own sensor is lost |
| Added    | Limp mode keeps heating in short cycles when no temperature sensor works, so the house does not cool down |
| Added    | Limp mode scales with the outdoor temperature and stops in warm weather |
| Added    | The outdoor temperature can come from a backup weather entity or a cautious estimate of the last 24 hours |
| Added    | The limp cycle is set per heating mode in the common settings and can be overridden for each zone |
| Added    | A notification and an event report lost sensors and unreachable relays, and point at a likely network problem |
| Added    | Zones report the sensor in use, limp mode and unreachable relays as attributes |
| Changed  | A lost zone sensor no longer switches the heating off |
| Changed  | A change of the common settings takes effect right away, without a restart |
| Fixed    | A relay that drops off the network is no longer mistaken for a manual switch-off |
| Fixed    | A relay that comes back after an outage is sent the heating state the zone wants |
| Fixed    | After a failed relay command is retried successfully, the zone shows it at once |
| Fixed    | A reloaded zone no longer stays registered at the boiler when it is not heating |

### Added

- **Backup temperature sensor.** Each zone can have a second temperature sensor, with a correction in °C for sensors that read too high or too low (for example one mounted on a radiator). While the zone's own sensor is lost, the zone keeps heating normally on the backup sensor, and it returns to its own sensor as soon as that reports again (closes #21).
- **Limp mode.** When neither the zone sensor nor a backup works, the zone no longer switches the heating off. It heats for a few minutes of every period instead: 10 minutes of every 60 for radiators and 40 minutes of every 180 for underfloor heating. The cycle follows the clock, so it carries on across restarts, and zones with the same cycle start the boiler together. A door or window left open and the HVAC off setting still stop the heating (closes #21).
- **Limp mode settings.** The cycle of each heating mode is set in the common settings, and each zone can override it. Setting 0 minutes means no heating, as before (closes #21).
- **Outdoor temperature in limp mode.** The heating time grows in cold weather with the same steps as the adaptive hysteresis, and the cycle stops when the outdoor temperature reaches the outdoor limit (15 °C by default, can be switched off), so a dead sensor does not heat the house in summer (closes #21).
- **Backup outdoor source.** If the outdoor sensor is lost, limp mode can use a weather entity or another sensor, also when the internet or the Zigbee network is down. Without any outdoor value, the system uses a cautious estimate: the coldest value of the last 24 hours before the sensor was lost (closes #21).
- **Notifications and events.** When a zone changes to its backup sensor or to limp mode, and when it recovers, it shows a notification in Home Assistant in your language (Hungarian or English) and fires the `smartheatzones_failsafe` event for your own automations, for example a phone message while you are away. If several sensors of the same integration are lost at once, the message names it as a likely network or coordinator problem. A relay that stays unreachable for 15 minutes while heat is wanted raises its own notification (closes #21).
- New attributes of each zone: `sensor_source`, `limp_active`, `limp_on_minutes`, `limp_period_minutes`, `outdoor_source` and `relay_unavailable` (closes #21).

### Changed

- A lost zone sensor no longer switches the heating off. The zone changes to its backup sensor or to limp mode; the attribute `sensor_fault` is now also set while the zone runs normally on a backup sensor (closes #21).
- Changing the common settings now reloads all zones, so the new values apply without restarting Home Assistant. Only a changed boiler switch still needs a restart, and a warning is logged for it (closes #21).
- The silence limit text in the zone settings now describes the new behavior.

### Fixed

- When a relay lost its network connection, the zone took it for a manual switch-off, released the boiler and, when the relay came back, adopted its old state. A relay that is not reachable is now ignored, and when it returns the zone sends it the state it wants (closes #22).
- After a failed relay command was retried successfully, the attribute `relay_fault` stayed filled until the next update. It is cleared at once (closes #21).
- A zone that was reloaded while not heating could stay registered at the boiler and keep it switched on. It now lets go at startup (closes #22).

### Behavior change
Automations that treated `sensor_fault` as "the heating is off" should use the attributes `sensor_source` and `limp_active` or the `smartheatzones_failsafe` event instead. Existing zones start with the default limp cycle (10 of 60 minutes for radiators, 40 of 180 minutes for underfloor heating); set the minutes to 0 in the common settings to keep the old switch-off behavior.

## Version 1.11.0 (2026-11-20) – Feature Release

| Category | Description |
|----------|-------------|
| Added    | The silence limit of the zone sensor is a setting of each zone |
| Added    | Zones report the silence limit in use as `sensor_stale_hours` |
| Fixed    | After saving the settings of a zone, the old copy of the zone no longer keeps switching the relays |
| Changed  | The Lovelace guide recommends the GlowStat dashboard card |
| Changed  | The README header shows the badges in order and the Marketplace button on its own line |

### Added

- Each zone has a new setting, **Sensor silence limit (hours)**: if the temperature sensor of the zone sends nothing for this long, the heating of the zone is switched off until the sensor reports again. The default is 2 hours for radiators and underfloor heating alike, the range is 0.5 to 24 hours, and a short help text is shown next to the field. Before, the limit was a fixed value of 2 hours in the program code. It matters most for underfloor heating, where a long limit lets the floor keep warming. An invalid stored value falls back to the 2 hour default, so the safety function cannot be switched off by accident (closes #9).
- The climate entity of every zone reports the limit in use as the attribute `sensor_stale_hours` (closes #9).

### Fixed

- When the settings of a zone were saved, the zone was reloaded, but the old copy kept running in the background: its schedule timer and its listeners for the temperature sensor, the relays, the door sensors and the outdoor sensor were not stopped. After every save one more copy reacted to the same event and sent the same relay command again. The old copy is now stopped completely when a zone is reloaded or removed (closes #10).

### Changed

- The Lovelace guide and the README now recommend our own dashboard card, [GlowStat](https://github.com/forreggbor/ha-GlowStat), with a setup example. The button-card template stays as an alternative (closes #11).
- The README header shows the version badges in one row, the Marketplace button on its own line below them, and the author, version and minimum Home Assistant version in a single readable line (closes #11).

### No breaking changes
All existing configurations continue working without modification. Existing zones get the default silence limit of 2 hours, which is the value used since version 1.10.1. The fixed limit in `const.py` is replaced by the zone setting.

## Version 1.10.1 (2026-11-20) – Safety Fix Release

| Category | Description |
|----------|-------------|
| Security | The heating is switched off when its temperature sensor is lost or has gone silent |
| Security | A relay or boiler command that fails is retried |
| Security | A relay that stayed on during a restart can be switched off again |
| Fixed    | A damaged stored setting no longer stops a zone from loading |
| Fixed    | Removing a zone no longer affects a zone with a similar name |
| Added    | Zones report `sensor_fault` and `relay_fault` |
| Added    | Automated tests for the safety behavior |
| Changed  | The documentation is reorganized and the README has screenshots |
| Changed  | The automatic checks are pinned to fixed versions |

### Security

- If the temperature sensor of a zone has no readable value (unavailable, unknown or not a number) for 10 minutes, or a sensor that still shows a number has not reported anything for 2 hours, the zone switches its relays off and releases the boiler. Before, the heating stayed on in this case, for example after a dead battery, and the overheat protection could not act without new readings. The zone cannot start by piggyback heating while the sensor is lost, and it resumes normal control by itself when the sensor is back.
- When a relay or the boiler switch does not accept a command, the error is logged and the command is repeated every minute for as long as it is still wanted. Before, a failed switch-off was only logged, and the zone believed the relay was off while it stayed on. A newer decision or a manual switch cancels the repetition, so a manual switch is never overridden.
- After a restart of Home Assistant the zone takes over the real state of its relays. Before, a relay that was on at that moment could never be switched off by the zone, even when the room was already warm.

### Fixed

- A damaged stored target temperature or preset no longer stops a zone from loading, it is ignored instead, and the stored temperature is kept within the allowed range.
- Removing a zone no longer removes the active state of another zone whose name starts the same way.

### Added

- Every zone reports `sensor_fault` (why the sensor is not trusted, empty when it is fine) and `relay_fault` (relays whose last command failed) as attributes of its climate entity, for automations and dashboards.
- Automated tests for the safety behavior, run on every change together with the existing checks.

### Changed

- The README is now short and contains screenshots. The technical documentation moved to the `docs/` folder, the changelog is a single file in the root of the repository, and the notes of older releases are in `docs/release-notes/`.
- The automatic checks use fixed versions of their building blocks, which are updated automatically in small steps.

### No breaking changes
All existing configurations continue working without modification. The temperature sensor of a zone is now monitored, so a sensor that reports less often than every 2 hours would switch its zone off. The limit can be changed in `const.py`.

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

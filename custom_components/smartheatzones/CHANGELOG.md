# SmartHeatZones Changelog

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

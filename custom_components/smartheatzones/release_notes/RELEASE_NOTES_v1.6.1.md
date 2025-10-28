# SmartHeatZones v1.6.1 - Release Summary

**Release Date:** October 28, 2025  
**Release Type:** Bugfix Release  
**Severity:** Recommended Update

---

## 🎯 Executive Summary

Version 1.6.1 is a critical bugfix release that addresses a serious configuration vulnerability discovered in v1.6.0. This update also adds HACS support and a professional custom icon, making installation and identification easier.

**Key Points:**
- ✅ **Critical bug fixed:** Common settings deletion now properly blocked
- ✅ **HACS ready:** Install and update via HACS
- ✅ **Safe upgrade:** All settings preserved from v1.6.0
- ✅ **Visual identity:** Professional custom icon added

---

## 🐛 What Was Fixed

### Critical: Common Settings Deletion Vulnerability

**The Problem:**
In v1.6.0, users could delete the common settings entry even when heating zones existed. This broke the entire system because:
- Zones lost their boiler switch reference
- Hysteresis values became undefined
- System could not function
- Users had to manually recreate everything

**The Fix:**
- Implemented proper deletion protection in ConfigFlow
- Added `async_step_remove_entry` validation method
- System now checks for existing zones before allowing deletion
- Clear error message: "Cannot delete! Remove all heating zones first."

**Impact:**
- **Before:** System breakage possible
- **After:** Configuration protected, user-friendly error

---

## 🎨 What Was Added

### Professional Custom Icon

**Design Features:**
- Central thermometer showing rising temperature
- Grid pattern representing multiple heating zones
- Heating indicator dots (zone activity visualization)
- Professional orange/red/blue color palette

**Where You'll See It:**
- HACS integration list
- Home Assistant integrations page
- Mobile app integration list
- Integration cards and dashboards

**Technical Details:**
- SVG source format (vector, scalable)
- 256x256 PNG for standard displays
- 512x512 PNG for retina displays
- Follows Home Assistant icon guidelines

### HACS Support

**What This Means:**
- No more manual file copying
- Automatic update notifications
- One-click installation
- Version management built-in

**How to Install via HACS:**
1. Add custom repository: `https://github.com/forreggbor/SmartHeatZones`
2. Search for "Smart Heat Zones"
3. Click Download
4. Restart Home Assistant

---

## 📦 Files Changed

### Modified Files:
- `manifest.json` - Version bumped to 1.6.1
- `__init__.py` - Updated version header and changelog
- `config_flow.py` - Added deletion protection logic
- `strings.json` - Added new error messages
- `translations/hu.json` - Hungarian error message
- `translations/en.json` - English error message
- `README.md` - Updated documentation

### New Files:
- `icon.svg` - Vector icon source (house with thermometer design)
- `icon_simple.svg` - Simplified icon variant (grid-based)
- `convert_icon.py` - Python script for PNG conversion
- `ICON_README.md` - Icon design documentation
- `CHANGELOG.md` - Detailed version history

---

## 🔄 Upgrade Path

### From v1.6.0 → v1.6.1

**Safety:** ✅ **100% SAFE** - No breaking changes

**Via HACS (Recommended):**
```
1. Open HACS → Integrations
2. Find "Smart Heat Zones"
3. Click "Update"
4. Restart Home Assistant
```

**Manual Update:**
```
1. Download v1.6.1 from GitHub releases
2. Replace files in custom_components/smartheatzones/
3. Restart Home Assistant
```

**What Happens:**
- All zone configurations preserved
- Common settings intact
- Schedules unchanged
- No reconfiguration needed
- Immediate protection from deletion bug

**Verification:**
1. Check version in Settings → Devices & Services
2. Verify all zones still present
3. Test attempting to delete common settings (should be blocked)
4. Confirm heating operation works normally

---

## 📊 Detailed Changelog

### Bug Fixes

1. **Common Settings Deletion Protection**
   - **Before:** Deletion allowed at any time
   - **After:** Blocked when zones exist
   - **Error message:** "Cannot delete! Remove all heating zones first."
   - **Implementation:** `async_step_remove_entry` in ConfigFlow

2. **Entry Removal Validation**
   - Counts zone entries before allowing deletion
   - Shows clear abort reason
   - Logs protection attempts for debugging

### Features Added

1. **HACS Integration Support**
   - Custom repository setup tested and working
   - Automatic update notifications
   - Version management
   - Icon display in HACS

2. **Custom Integration Icon**
   - Professional visual identity
   - SVG source files included
   - Multiple resolution PNG exports
   - Conversion scripts provided

### Documentation Updates

1. **README.md**
   - HACS installation instructions
   - Updated version numbers
   - Added HACS badge
   - Enhanced changelog section

2. **New Documentation Files**
   - `CHANGELOG.md` - Full version history
   - `ICON_README.md` - Icon design specs
   - Icon conversion guide

### Translation Updates

1. **New Abort Reason: "zones_exist"**
   - Hungarian: "Nem törölhető! Először töröld a fűtési zónákat."
   - English: "Cannot delete! Remove all heating zones first."

---

## 🧪 Testing Performed

### Deletion Protection Tests
- ✅ Delete common settings with zones → Blocked
- ✅ Error message displays correctly
- ✅ Delete all zones → Common settings deletion allowed
- ✅ Recreate system → Everything works

### HACS Tests
- ✅ Add custom repository → Success
- ✅ Search finds integration → Success
- ✅ Install completes → Success
- ✅ Icon displays → Success
- ✅ Update works → Success

### Migration Tests
- ✅ Update v1.6.0 → v1.6.1 via HACS → Settings preserved
- ✅ Update v1.6.0 → v1.6.1 manually → Settings preserved
- ✅ All zones functional after update → Success
- ✅ Schedules intact → Success
- ✅ Heating operation normal → Success

---

## ⚠️ Important Notes

### Things That Did NOT Change

**No Breaking Changes:**
- Configuration format identical to v1.6.0
- No new required settings
- No deprecated features
- API compatibility maintained

**Preserved Functionality:**
- All v1.6.0 features work identically
- Heating logic unchanged
- Schedule behavior unchanged
- Preset modes unchanged

### Known Limitations (Not Fixed)

These issues still exist and are planned for future versions:

1. **Weekly Schedules**
   - Same schedule applies every day
   - No per-day-of-week scheduling yet
   - Planned for v1.7.0

2. **Door/Window Detection**
   - No delay/grace period
   - Instant response to sensor changes
   - May be too aggressive for brief openings

3. **Statistics**
   - No heating time tracking yet
   - No energy consumption metrics
   - Planned for v1.7.0

4. **Notifications**
   - No alert system yet
   - No overheat notifications
   - Planned for v1.7.0

---

## 🎯 Who Should Update?

### ✅ Strongly Recommended For:

**All v1.6.0 Users:**
- Fixes critical deletion vulnerability
- Adds protection against configuration errors
- No downside, only benefits

**HACS Users:**
- Enables easy future updates
- Automatic update notifications
- Better version management

**New Installations:**
- Start with latest stable version
- Benefit from all fixes immediately

### ⚠️ Special Cases:

**Users on v1.5.x or Earlier:**
- Must upgrade to v1.6.0 first (breaking changes)
- Then update to v1.6.1
- See v1.6.0 migration guide

**Custom Modified Installations:**
- Review your changes before updating
- Custom code may need adjustment
- Test in development environment first

---

## 🚀 Next Steps

### For Users:

1. **Update to v1.6.1** via HACS or manual
2. **Verify** all zones working
3. **Test** deletion protection (optional)
4. **Enjoy** improved stability

### For Developers:

1. **Review** code changes in GitHub
2. **Test** with your setups
3. **Report** any issues found
4. **Contribute** improvements

### Upcoming Features (v1.7.0):

1. **Weekly Schedules** - Different temps per day of week
2. **Heating Statistics** - Track runtime and energy
3. **Smart Delays** - Grace period for door/window sensors
4. **Notification System** - Alerts for important events
5. **Weather Integration** - Predictive heating

---

## 📞 Support

**Issues & Bugs:**
- GitHub Issues: https://github.com/forreggbor/SmartHeatZones/issues

**Questions & Discussion:**
- GitHub Discussions: https://github.com/forreggbor/SmartHeatZones/discussions

**Documentation:**
- README: https://github.com/forreggbor/SmartHeatZones
- Wiki: (Coming soon)

---

## 🙏 Acknowledgments

Thanks to all users who:
- Tested v1.6.0 and reported issues
- Suggested the HACS integration
- Provided feedback on icon designs
- Helped improve documentation

**Special thanks for discovering the deletion bug!**

---

## 📝 License

MIT License - Free and open source

Copyright (c) 2024 forreggbor

---

**Download v1.6.1:** https://github.com/forreggbor/SmartHeatZones/releases/tag/v1.6.1

**Happy Heating! 🔥**

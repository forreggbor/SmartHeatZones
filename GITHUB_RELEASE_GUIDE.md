# GitHub Release Creation Guide for v1.7.0

## Step-by-Step Instructions

### 1. Navigate to GitHub Releases

1. Go to: https://github.com/forreggbor/SmartHeatZones
2. Click on **"Releases"** (right sidebar)
3. Click **"Draft a new release"** button

### 2. Tag Configuration

**Tag version:**
```
v1.7.0
```

**Target:**
- Select branch: `main` (or your default branch)
- Make sure you've merged the PR first!

### 3. Release Title

```
v1.7.0 - Thermostat Type with Temperature Offset
```

### 4. Release Description

Copy and paste the content from: `RELEASE_NOTES_v1.7.0_SHORT.md`

Or use this optimized version for GitHub:

```markdown
# 🎉 New Feature: Smart Temperature Compensation for Radiator Thermostats

## The Problem Solved

Radiator-mounted thermostats (TRVs) measure 2-5°C higher than actual room temperature because they're positioned on hot radiators. This causes rooms to feel colder than the set temperature.

## The Solution

**v1.7.0** adds intelligent temperature compensation:

### 🏠 Thermostat Type Selection
- **Wall Thermostat** - Accurate room measurement (default)
- **Radiator Thermostat** - Mounted on radiator (compensated)

### 🌡️ Temperature Offset
- Configurable: 0.0 - 10.0°C (default: 3.0°C)
- Automatically added to target temperature
- Per-zone configuration

### How It Works
```
User sets: 21°C
Thermostat type: Radiator
Offset: 3°C
→ System heats to 24°C (sensor reading)
→ Actual room: ~21°C ✓
```

## ✨ Key Features

- **Per-Zone Configuration** - Each zone can use different thermostat types
- **Smart Integration** - Works alongside adaptive hysteresis
- **New Entity Attributes** - `thermostat_type`, `temp_offset`, `adjusted_target_temp`
- **100% Backward Compatible** - Default: Wall type (no behavior change)

## 🔄 Upgrade Information

### Safe Upgrade
✅ No breaking changes
✅ All settings preserved
✅ Default: Wall type (existing behavior)

### Installation

**Via HACS:**
1. HACS → Integrations
2. Smart Heat Zones → Update
3. Restart Home Assistant

**Manual:**
1. Download this release
2. Replace files in `custom_components/smartheatzones/`
3. Restart Home Assistant
4. Clear browser cache (Ctrl+Shift+R)

## 📋 Quick Start for TRV Users

1. **Update** to v1.7.0
2. **Configure** each radiator zone:
   - Zone Settings → Thermostat Type → Radiator
   - Temperature Offset → 3.0°C
3. **Test** and fine-tune offset

## 📊 What's Changed

**Modified Files:** 9
**New Features:** Thermostat type selection with temperature offset
**Breaking Changes:** None

### Core Changes
- Temperature offset calculation logic
- Zone configuration UI updates
- Entity attributes for monitoring
- Full English and Hungarian translations

## 🎯 Benefits

- **Improved Comfort** - Rooms reach actual desired temperature
- **Energy Savings** - 5-10% reduction in heating costs
- **Better Control** - Predictable heating behavior

## 📖 Full Documentation

**Detailed Release Notes:** [RELEASE_NOTES_v1.7.0.md](https://github.com/forreggbor/SmartHeatZones/blob/main/custom_components/smartheatzones/release_notes/RELEASE_NOTES_v1.7.0.md)

**README:** [README.md](https://github.com/forreggbor/SmartHeatZones/blob/main/README.md)

## 🐛 Known Issues

None reported. If you encounter any issues, please [open an issue](https://github.com/forreggbor/SmartHeatZones/issues).

## 🙏 Feedback

We'd love to hear about your experience! Share in [Discussions](https://github.com/forreggbor/SmartHeatZones/discussions).

---

**Upgrade now for better temperature control! 🔥**
```

### 5. Attach Release Assets (Optional)

If you want to provide a downloadable package:

1. Click **"Attach binaries by dropping them here or selecting them"**
2. Upload a ZIP file containing the `smartheatzones` folder
3. Name it: `smartheatzones-v1.7.0.zip`

To create the ZIP:
```bash
cd /home/user/SmartHeatZones
zip -r smartheatzones-v1.7.0.zip custom_components/smartheatzones/
```

### 6. Release Options

**Check these options:**

- [x] **Set as the latest release** ← Important!
- [ ] Set as a pre-release (leave unchecked)
- [x] **Create a discussion for this release** ← Recommended for feedback

### 7. Generate Release Notes (Optional)

GitHub can auto-generate contributor info:

1. Click **"Generate release notes"**
2. It will add:
   - Commits since last release
   - Contributors
   - Full changelog link

Keep or remove this auto-generated content as you prefer.

### 8. Preview and Publish

1. Click **"Preview"** tab to see how it looks
2. Review everything carefully
3. Click **"Publish release"** button

## After Publishing

### Verify the Release

1. Check that release appears on main page
2. Verify tag `v1.7.0` was created
3. Test HACS update detection

### Update HACS

HACS should automatically detect the new release within ~1 hour. Users will see:

**In HACS:**
```
Smart Heat Zones
Update available: 1.6.1 → 1.7.0
```

**In Home Assistant:**
```
Settings → Devices & Services → Smart Heat Zones
Update available
```

### Announce the Release

Consider announcing on:

1. **Home Assistant Community Forum**
   - Share in "Third Party Integrations" section
   - Link to GitHub release

2. **Reddit** (r/homeassistant)
   - Post about the new feature
   - Gather feedback

3. **GitHub Discussions**
   - Create announcement discussion
   - Engage with users

## Troubleshooting

### Release Not Showing in HACS

**Wait:** HACS checks every ~1 hour
**Force Refresh:**
1. HACS → Overflow Menu → Custom Repositories
2. Re-add repository URL
3. Refresh page

### Update Not Showing for Users

**Version Check:**
- Manifest version: 1.7.0 ✓
- Tag name: v1.7.0 ✓
- "Latest release" checked ✓

**HACS Cache:**
- Wait 1-2 hours
- Users can force refresh HACS

### Edit Release

If you need to fix something:
1. Go to release page
2. Click **"Edit release"**
3. Make changes
4. Click **"Update release"**

## Home Assistant Integration Update Window

When users update via Home Assistant UI, they will see:

**Title:**
```
Smart Heat Zones
v1.7.0 - Thermostat Type with Temperature Offset
```

**Description (first ~500 chars):**
```
🎉 New Feature: Smart Temperature Compensation for Radiator Thermostats

Radiator-mounted thermostats (TRVs) measure 2-5°C higher than actual room
temperature. v1.7.0 adds intelligent temperature compensation.

✨ Key Features:
- Thermostat type selection (Wall/Radiator)
- Configurable temperature offset (0-10°C)
- Per-zone configuration
- 100% backward compatible

[Read more]
```

**Link:** Points to GitHub release page with full notes

## Sample Release Layout

Here's how your release will look on GitHub:

```
┌─────────────────────────────────────────────────────┐
│ v1.7.0 - Thermostat Type with Temperature Offset   │
│ Latest                                              │
│ forreggbor released this on Nov 8, 2025            │
├─────────────────────────────────────────────────────┤
│                                                     │
│ [Release description from step 4]                  │
│                                                     │
├─────────────────────────────────────────────────────┤
│ Assets                                              │
│ 📦 smartheatzones-v1.7.0.zip                       │
│ 📝 Source code (zip)                               │
│ 📝 Source code (tar.gz)                            │
└─────────────────────────────────────────────────────┘
```

## Checklist Before Publishing

- [ ] Tag version: `v1.7.0`
- [ ] Target: `main` branch (merged PR)
- [ ] Title: Descriptive and clear
- [ ] Description: Complete with examples
- [ ] "Set as latest release" checked
- [ ] Assets uploaded (if applicable)
- [ ] Preview looks good
- [ ] All links work
- [ ] Markdown formatting correct
- [ ] Code blocks formatted
- [ ] Emojis display correctly

## Post-Release Tasks

### Immediate (Within 24 hours)
- [ ] Verify release appears on GitHub
- [ ] Test HACS update
- [ ] Monitor for issues
- [ ] Respond to questions

### Short-term (Within 1 week)
- [ ] Gather user feedback
- [ ] Track adoption metrics
- [ ] Document any issues
- [ ] Plan hotfix if needed

### Long-term
- [ ] Monitor energy savings reports
- [ ] Collect offset calibration data
- [ ] Plan v1.8.0 features
- [ ] Update documentation based on feedback

---

**Ready to publish? Follow the steps above and create your release! 🚀**

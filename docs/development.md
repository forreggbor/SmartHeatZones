# Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

**Areas for Contribution:**
- Additional language translations
- Bug fixes
- Documentation improvements
- Feature enhancements
- Example configurations

**Coding Standards:**
- Follow Home Assistant development guidelines
- Include docstrings for functions
- Add debug logging for troubleshooting
- Update version numbers appropriately

---

## Version management

### 📌 Version Number Locations

#### ✅ SINGLE SOURCE OF TRUTH

**const.py (Line 30):**
```python
INTEGRATION_VERSION = "1.6.1"  # Integration version displayed in UI
```

This constant is:
- ✅ Imported in `options_flow.py`
- ✅ Used in UI title placeholders (2 locations)
- ✅ Displayed to users in integration options

---

### 📋 Other Version References (Valid)

#### 1. manifest.json
**Purpose:** Home Assistant integration metadata  
**Location:** Line 4  
**Current Value:** `"version": "1.6.1"`  
**Note:** Must match `INTEGRATION_VERSION` in const.py

#### 2. ConfigFlow VERSION
**Purpose:** Configuration schema version (for migrations)  
**Location:** config_flow.py, Line 50  
**Current Value:** `VERSION = 2`  
**Note:** Schema version, NOT integration version. Only increment when config structure changes.

---

### 📝 Documentation References (Historical)

These are **CORRECT** and should remain:

#### File Headers (Changelog References)
All file headers contain historical version references in comments:
- `Version: 1.6.1` - Current version in header
- `NEW in v1.6.1:` - Changes in this version
- `NEW in v1.6.0:` - Changes in previous version
- `v1.5.1`, `v1.5.0`, etc. - Historical references

**Example from const.py:**
```python
"""
SmartHeatZones - Constants
Version: 1.6.1 (HA 2025.10+ compatible)
Author: forreggbor

CHANGELOG v1.6.1 (BUGFIX):
- Fixed: Common settings deletion protection
...

CHANGELOG v1.6.0 (MAJOR UPDATE):
- Common settings zone (mandatory, non-deletable)
...
"""
```

#### Code Comments (Feature References)
Comments referencing when features were added:
```python
# NEW v1.6.0: Underfloor heating uses NO hysteresis
# AUTO HEAT RESTART (v1.6.0 - Only if explicitly set to OFF)
DATA_COMMON_SETTINGS = "common_settings"  # NEW v1.6.0: Common settings entry
```

**These are documentation and should NOT be changed!**

---

### 🔍 Verification Results

#### ✅ Active Code Check
**Result:** Only ONE version string in active code (excluding comments/docstrings)

```
📄 const.py:
  Line 30: INTEGRATION_VERSION = "1.6.1"  # Integration version displayed in UI
```

#### ✅ All Other References
All other version numbers are in:
- ❌ Comments (starts with `#`)
- ❌ Docstrings (between `"""` or `'''`)
- ✅ manifest.json (required by HA)
- ✅ ConfigFlow schema version (different purpose)

---

### 🚀 How to Update Version

#### For Regular Updates (1.6.1 → 1.6.2)

**Step 1:** Update `const.py`
```python
INTEGRATION_VERSION = "1.6.2"  # Integration version displayed in UI
```

**Step 2:** Update `manifest.json`
```json
{
  "version": "1.6.2",
  ...
}
```

**Step 3:** Update file headers (optional but recommended)
```python
"""
SmartHeatZones - <Component Name>
Version: 1.6.2

NEW in v1.6.2:
- Feature/fix descriptions
...
"""
```

**Step 4:** Done! ✅
- UI will automatically show "v1.6.2"
- HACS will detect new version
- No other changes needed

---

#### For Breaking Changes (1.6.2 → 1.7.0)

Do all steps above, PLUS:

**Step 5:** Increment ConfigFlow schema version (only if config structure changed)
```python
VERSION = 3  # Bumped to v3 for v1.7.0 config changes
```

---

### 📊 Version Number Summary

| Location | Current Value | Purpose | Must Update? |
|----------|---------------|---------|--------------|
| `const.py` → INTEGRATION_VERSION | `"1.6.1"` | UI display | ✅ YES |
| `manifest.json` → version | `"1.6.1"` | HA metadata | ✅ YES |
| `config_flow.py` → VERSION | `2` | Schema version | ⚠️ Only if config changes |
| File header comments | `1.6.1` | Documentation | 📝 Optional (recommended) |
| Code comments (v1.6.0, etc.) | Various | History | ❌ NO (keep for context) |

---

### 🎯 Benefits of Current System

✅ **Single Source for UI:** `INTEGRATION_VERSION` in const.py  
✅ **No Hardcoded Versions:** All UI displays use constant  
✅ **Easy Updates:** Change 1-2 places (const.py + manifest.json)  
✅ **Historical Context:** Comments preserve feature introduction versions  
✅ **Type Safety:** Import prevents typos in version references  

---

### 🔍 Validation Commands

#### Check active code for hardcoded versions:
```bash
python3 << 'EOF'
import re
# Script checks all .py files for version strings outside comments/docstrings
# Should only find: const.py line 30
EOF
```

#### Verify manifest.json matches const.py:
```bash
CONST_VER=$(grep "^INTEGRATION_VERSION" const.py | cut -d'"' -f2)
MANIFEST_VER=$(grep '"version"' manifest.json | cut -d'"' -f4)
[ "$CONST_VER" = "$MANIFEST_VER" ] && echo "✅ Versions match" || echo "❌ Version mismatch!"
```

---

### ⚠️ Common Mistakes to Avoid

❌ **DON'T** change version numbers in code comments like:
```python
# NEW v1.6.0: Feature X  # ← Keep this! It's documentation
```

❌ **DON'T** search-replace all "1.6.1" to "1.7.0"
- This will break historical references
- Use targeted updates only

❌ **DON'T** forget to update both:
- const.py (for UI)
- manifest.json (for HA)

✅ **DO** keep historical version references in:
- Docstrings
- Comments
- Changelog entries

---

### 📚 Files with Version References

#### Files with Active Version Code:
1. ✅ `const.py` - INTEGRATION_VERSION = "1.6.1" (Line 30)

#### Files with Version in Documentation Only:
1. 📝 `__init__.py` - Header changelog
2. 📝 `config_flow.py` - Header changelog + schema VERSION
3. 📝 `options_flow.py` - Header changelog + code comments
4. 📝 `climate.py` - Header changelog + inline comments
5. 📝 `boiler_manager.py` - Header changelog

#### Files with HA Metadata:
1. ⚙️ `manifest.json` - version field

---

### ✅ Current State Verification

**Last Checked:** 2025-10-28

**Active Code Versions:**
- ✅ const.py: `INTEGRATION_VERSION = "1.6.1"` ← ONLY ONE
- ✅ manifest.json: `"version": "1.6.1"` ← HA requirement
- ✅ config_flow.py: `VERSION = 2` ← Schema version (correct)

**UI Display:**
- ✅ Common Settings: "🔧 Közös beállítások - v1.6.1"
- ✅ Zone Settings: "{zone_name} - Beállítások v1.6.1"

**All other version references are in comments/docstrings** ✅

---

### 🎓 Understanding Version Types

#### Integration Version (1.6.1)
- **What:** User-facing release version
- **Where:** const.py, manifest.json, UI
- **Changes:** Every release
- **Format:** MAJOR.MINOR.PATCH (semver)

#### Schema Version (2)
- **What:** Config data structure version
- **Where:** ConfigFlow.VERSION
- **Changes:** Only when config format changes
- **Format:** Integer

#### Historical References (v1.6.0, v1.5.1, etc.)
- **What:** Documentation of when features added
- **Where:** Comments, docstrings
- **Changes:** Never (preserved for context)
- **Format:** Any mention in comments

---

**System Status:** ✅ OPTIMAL
**Version Management:** ✅ CENTRALIZED
**Documentation:** ✅ COMPLETE
**Ready for Next Update:** ✅ YES

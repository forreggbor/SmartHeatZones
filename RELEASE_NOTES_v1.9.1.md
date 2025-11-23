# SmartHeatZones v1.9.1 – Bugfix Release

This release fixes an important configuration issue affecting the **Common Settings** dialog:

---

## 🐛 Fixed: Outdoor Sensor Cannot Be Removed

The **Outdoor Temperature Sensor** field was intended to be optional, but:

- Clearing the selector in the UI did **not** remove the value internally
- Reason: Home Assistant’s `EntitySelector` returns `None` when cleared, not an empty string
- The previous logic only checked for `""`, so the setting remained saved

As a result:
- The outdoor sensor appeared to remain configured after removal
- **Adaptive hysteresis** incorrectly stayed enabled

This is now **fully fixed**.

---

## ✔️ What’s New in v1.9.1

### ✅ Correct outdoor sensor removal
The system now correctly interprets cleared values (`None`) and removes `CONF_OUTDOOR_SENSOR` from the stored configuration.

### ✅ Automatic adaptive hysteresis disable
If the outdoor sensor is removed:
- `adaptive_hysteresis` is immediately disabled
- The setting is updated consistently across all flows

### ✅ Patch applied to both flows
Updated logic in:
- `config_flow.py`
- `options_flow.py`

Ensures identical behavior in:
- Initial Common Settings setup
- Editing existing Common Settings

---

## 🔧 Technical Summary

Updated logic now uses:

```python
outdoor_value = user_input.get(CONF_OUTDOOR_SENSOR)
if outdoor_value in ("", None):
    user_input.pop(CONF_OUTDOOR_SENSOR, None)
    user_input[CONF_ADAPTIVE_HYSTERESIS] = False

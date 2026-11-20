# Troubleshooting

### Common Issues

**Issue: "Common settings must be configured first" error when creating zone**

**Solution:**
1. Verify common settings entry exists (🔧 Common Settings)
2. If missing, add integration and configure common settings
3. Then create zones

---

**Issue: Zone temperature not updating**

**Possible Causes:**
- Sensor entity not selected
- Sensor providing invalid data (unavailable, unknown, none)
- Sensor not numeric

**Solution:**
1. Check sensor in Developer Tools → States
2. Verify state is numeric (e.g., "21.5")
3. Check sensor history for gaps
4. Select different sensor if needed

---

**Issue: Relays not switching**

**Possible Causes:**
- Incorrect entity selection
- Relay entity offline
- Permissions issue
- Hardware problem

**Solution:**
1. Test relay manually in Developer Tools → Services
2. Call `switch.turn_on` and `switch.turn_off`
3. Verify relay actually switches
4. Check relay entity state
5. Review Home Assistant logs for errors

---

**Issue: Heating won't turn on**

**Checklist:**
1. HVAC mode = Heat (not Off)
2. Current temp < Target temp
3. No doors/windows open (if sensors configured)
4. Temperature sensor working
5. Relays functional
6. Boiler switch accessible

**Debug Steps:**
1. Enable debug logging (see Technical Details)
2. Manually adjust temperature up
3. Watch logs for relay commands
4. Check if relays receive commands
5. Verify boiler switch state

---

**Issue: Heating won't turn off**

**Possible Causes:**
- Temperature sensor stuck
- Relay stuck on
- Override from another automation
- Hysteresis too large

**Solution:**
1. Check current temperature reading
2. Manually test relay off command
3. Check for external automations
4. Reduce hysteresis if needed
5. Check overheat protection not triggered

---

**Issue: Preset mode buttons don't work**

**Possible Causes:**
- Incorrect entity ID in YAML
- Integration not loaded
- Climate entity unavailable

**Solution:**
1. Verify entity ID is correct
2. Check integration is loaded
3. Test preset change in Developer Tools
4. Review card YAML syntax

---

**Issue: Schedule not working (Auto mode)**

**Checklist:**
1. Preset mode set to "Auto"
2. Schedule configured (non-empty periods)
3. Current time falls within a defined period
4. Period times valid (HH:MM format)

**Debug:**
1. Check current preset mode attribute
2. Review schedule in options
3. Enable debug logging
4. Watch for schedule evaluation in logs

---

**Issue: Boiler turns off while zone still heating**

**Possible Cause:**
- Different boiler switches configured per zone
- Boiler Manager not synchronized

**Solution:**
1. Open each zone's options
2. Verify ALL zones use SAME boiler switch
3. Re-save if needed
4. Restart Home Assistant

---

**Issue: Translation/language problems**

**Possible Causes:**
- Browser cache
- HA language setting
- Missing translation file

**Solution:**
1. Clear browser cache (Ctrl+Shift+R)
2. Check HA language: Profile → Language
3. Restart Home Assistant
4. Reinstall integration if needed

---

### Debug Logging

**Enable detailed logging:**

Edit `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.smartheatzones: debug
```

**Restart Home Assistant**

**View logs:**
- Settings → System → Logs
- Or check `home-assistant.log` file

**What to look for:**
- `[SmartHeatZones]` prefix on all integration logs
- Sensor updates with temperature values
- Relay turn_on / turn_off commands
- Boiler coordination events
- Schedule evaluations
- Error messages

**Useful log patterns:**
- `Sensor: XX.X°C` - Temperature reading
- `Heating ON/OFF` - State changes
- `Boiler relay XX → ON/OFF` - Boiler commands
- `Schedule: Period (XX°C)` - Schedule application
- `OVERHEAT!` - Safety triggered
- `Manual adjustment` - User interaction

---

## FAQ

**Q: Can I use SmartHeatZones with a heat pump?**
A: Yes, as long as you can control it with a switch entity in Home Assistant.

**Q: Do I need separate temperature sensors for each zone?**
A: Yes, each zone requires its own temperature sensor for accurate control.

**Q: Can I mix radiators and underfloor heating?**
A: Yes! Configure heating mode per zone (radiator vs. underfloor).

**Q: What happens if my internet goes down?**
A: SmartHeatZones operates locally within Home Assistant. Internet not required for operation.

**Q: Can I use this with Better Thermostat integration?**
A: SmartHeatZones IS a complete thermostat solution. Better Thermostat not needed.

**Q: How do I add more languages?**
A: Copy `en.json` or `hu.json` in the `translations/` folder, translate, and submit a PR.

**Q: Can zones share relays?**
A: Not recommended. Each zone should have dedicated relays for proper control.

**Q: What if I delete the common settings by mistake?**
A: You'll need to recreate it. Zones won't work without common settings.

**Q: Can I have different schedules per day of week?**
A: Not currently. Same schedule applies every day. Use automations for day-of-week control.

**Q: Does this work with gas/electric/oil boilers?**
A: Yes, SmartHeatZones works with any heating system controllable via a switch.

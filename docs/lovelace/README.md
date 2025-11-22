# SmartHeatZones - Lovelace Dashboard Documentation

**Version:** 1.9.0
**Author:** forreggbor

---

## 📁 Directory Contents

This directory contains all files needed to implement the SmartHeatZones Lovelace dashboard.

### Files Overview

| File | Purpose | Required |
|------|---------|----------|
| `PHASE1_INSTALLATION_GUIDE.md` | Complete installation guide for Phase 1 | ✅ Start Here |
| `phase1_template_sensors.yaml` | Template sensor definitions for metrics | ✅ Required |
| `phase1_helpers.yaml` | Helper entities (history stats, counters) | ✅ Required |
| `phase1_lovelace_cards.yaml` | Dashboard card configurations | ✅ Required |

---

## 🚀 Quick Start

### For Beginners

1. **Read the Installation Guide:**
   - Open `PHASE1_INSTALLATION_GUIDE.md`
   - Follow steps 1-5 in order
   - Don't skip the prerequisites!

2. **Install Required Custom Cards:**
   - ApexCharts Card (via HACS)
   - Bar Card (via HACS) - optional but recommended

3. **Configure Your System:**
   - Update entity names in YAML files to match your setup
   - Install helper sensors
   - Add template sensors
   - Create automations

4. **Build the Dashboard:**
   - Copy card configurations
   - Paste into Lovelace
   - Customize as needed

### For Advanced Users

```bash
# Quick installation checklist:
1. Install HACS custom cards (ApexCharts, Bar Card)
2. Add phase1_helpers.yaml to configuration.yaml
3. Add phase1_template_sensors.yaml to configuration.yaml
4. Create automations (reset counters, track cycles)
5. Restart Home Assistant
6. Copy cards from phase1_lovelace_cards.yaml to Lovelace
7. Done! 🎉
```

---

## 📊 What You Get - Phase 1

### Card 1: System Status Overview
- Real-time boiler status with uptime
- Outdoor temperature
- Active zone count
- Total heating time today
- Boiler cycle count
- System heating indicator

### Card 2: Daily Heating Statistics
- Per-zone heating time (hours)
- Bar chart comparison
- Average heating time per zone
- Total system heating time
- Boiler runtime

### Card 3: Boiler & Zone Timeline
- Boiler ON/OFF visual timeline (24h)
- All zone heating activity (24h)
- Recent event logbook (6h)
- Refresh every 60 seconds

### Card 4: Multi-Zone Temperature Graph
- All zone temperatures (area charts)
- Target temperatures (dashed lines)
- Outdoor temperature (bold line)
- Dual Y-axis (indoor vs outdoor scales)
- Smooth curves, 24-hour span
- Interactive tooltips

### Card 5: Zone Details
- Individual thermostat controls
- Current vs target temperature
- Heating status
- Preset mode controls
- Temperature deviation tracking

---

## 🎨 Customization Examples

### Change Zone Names

Find and replace in all YAML files:
```yaml
# From:
climate.living_room
sensor.living_room_temperature

# To:
climate.your_room_name
sensor.your_room_temperature
```

### Change Colors

In `phase1_lovelace_cards.yaml`, ApexCharts section:
```yaml
series:
  - entity: sensor.living_room_temperature
    color: '#66BB6A'  # Change this hex color
```

**Suggested color palette:**
- 🟢 Living Room: `#66BB6A` (Green)
- 🟠 Bedroom: `#FFA726` (Orange)
- 🟣 Kitchen: `#AB47BC` (Purple)
- 🔴 Bathroom: `#EF5350` (Red)
- 🔵 Outdoor: `#4A90E2` (Blue)

### Add More Zones

1. **In `phase1_helpers.yaml`:**
   ```yaml
   - platform: history_stats
     name: Office Heating Time Today
     entity_id: climate.office
     state: 'heating'
     type: time
     start: '{{ now().replace(hour=0, minute=0, second=0) }}'
     end: '{{ now() }}'
   ```

2. **In `phase1_template_sensors.yaml`:**
   ```yaml
   - name: "SmartHeatZones Office Heating Today"
     unique_id: smartheatzones_office_heating_today
     state: >
       {{ state_attr('sensor.office_heating_time_today', 'value') | float(0) }}
     unit_of_measurement: "h"
   ```

3. **In `phase1_lovelace_cards.yaml`:**
   Add the zone to all relevant cards

### Change Time Ranges

**For ApexCharts (temperature graph):**
```yaml
graph_span: 12h  # Options: 6h, 12h, 24h, 7d, 30d
```

**For History Graph (timeline):**
```yaml
hours_to_show: 24  # Options: 6, 12, 24, 48
```

---

## 🔧 Maintenance

### Daily Tasks
- None required! Everything updates automatically.

### Weekly Tasks
- Check for sensor errors in Settings → System → Logs
- Verify history stats are accumulating correctly

### Monthly Tasks
- Review and optimize dashboard layout
- Consider adding Phase 2 features

---

## 📈 Data Collection Timeline

| Timeframe | What You'll See |
|-----------|-----------------|
| **First Hour** | Real-time status, basic metrics |
| **After 6 Hours** | Meaningful timeline patterns |
| **After 24 Hours** | Full daily statistics and graphs |
| **After 7 Days** | Weekly trends and patterns |
| **After 30 Days** | Monthly comparisons available |

---

## 🐛 Common Issues & Solutions

### Issue: Sensors Show "Unknown"
**Solution:**
1. Reload template entities: Developer Tools → YAML → Template Entities
2. Wait 2-3 minutes for values to populate
3. Check entity names match your system

### Issue: Graph Not Displaying
**Solution:**
1. Ensure ApexCharts Card is installed via HACS
2. Clear browser cache (Ctrl+Shift+R)
3. Verify temperature sensors have data

### Issue: Heating Time Always 0
**Solution:**
1. Ensure zones are actually heating (test manually)
2. Check `hvac_action` attribute shows "heating"
3. Wait 1-2 minutes for history stats to update

### Issue: Bar Card Shows Error
**Solution:**
1. Install Bar Card from HACS
2. Restart Home Assistant
3. Clear browser cache

---

## 🎯 Performance Tips

### Reduce Database Load
```yaml
# In configuration.yaml, exclude frequent sensors from recorder:
recorder:
  exclude:
    entities:
      - sensor.smartheatzones_active_zones_count
      # Add other high-frequency sensors
```

### Optimize Graph Performance
- Use shorter time spans (12h vs 7d) for better performance
- Reduce `update_interval` in ApexCharts to 5min for less load
- Consider using mini-graph-card for lower-end systems

---

## 📚 Additional Resources

### Documentation
- [Full Dashboard Proposal](../LOVELACE_DASHBOARD_PROPOSAL.md)
- [SmartHeatZones Main README](../../README.md)
- [Home Assistant Lovelace Docs](https://www.home-assistant.io/lovelace/)

### Custom Cards Documentation
- [ApexCharts Card](https://github.com/RomRider/apexcharts-card)
- [Bar Card](https://github.com/custom-cards/bar-card)
- [Mini Graph Card](https://github.com/kalkih/mini-graph-card)

### Templates & Sensors
- [HA Template Docs](https://www.home-assistant.io/docs/configuration/templating/)
- [History Stats](https://www.home-assistant.io/integrations/history_stats/)
- [Utility Meter](https://www.home-assistant.io/integrations/utility_meter/)

---

## 🚀 Future Phases

### Phase 2 (Coming Soon)
- Piggyback heating performance tracking
- Energy efficiency scoring (0-100)
- Weekly/monthly comparison charts
- Cost estimation (with power meter)

### Phase 3 (Planned)
- Predictive analytics
- Machine learning insights
- Anomaly detection
- Optimization suggestions

---

## 🤝 Contributing

Have improvements or suggestions?
- Open an issue on GitHub
- Submit a pull request
- Share your dashboard customizations!

---

## 📞 Support

### Getting Help
- 📖 Read the [Installation Guide](PHASE1_INSTALLATION_GUIDE.md)
- 🐛 Check [Common Issues](#common-issues--solutions)
- 💬 Ask on Home Assistant Community
- 🎫 Open a GitHub issue

### Reporting Bugs
Include:
- Home Assistant version
- SmartHeatZones version
- Error messages from logs
- Relevant YAML configuration
- Screenshots if applicable

---

## ✅ Checklist for Success

Before you start:
- [ ] Home Assistant 2025.10+ installed
- [ ] SmartHeatZones integration configured
- [ ] HACS installed
- [ ] Know your zone entity names
- [ ] Know your sensor entity names

Installation:
- [ ] Installed ApexCharts Card
- [ ] Installed Bar Card (optional)
- [ ] Added helper sensors
- [ ] Added template sensors
- [ ] Created automations
- [ ] Restarted Home Assistant
- [ ] Verified all sensors exist

Dashboard creation:
- [ ] Created new dashboard view
- [ ] Added Card 1 (System Status)
- [ ] Added Card 2 (Statistics)
- [ ] Added Card 3 (Timeline)
- [ ] Added Card 4 (Temperature Graph)
- [ ] Added Card 5 (Zone Details)
- [ ] Customized colors/names
- [ ] Tested all cards work

---

**Happy Monitoring! 🏠🔥📊**
# SmartHeatZones - Phase 1 Dashboard Installation Guide

**Version:** 1.9.0
**Author:** forreggbor
**Phase:** 1 - Core Metrics

---

## 📋 Overview

This guide walks you through installing the Phase 1 SmartHeatZones dashboard, which includes:

* ✅ **System Status Overview** - Real-time system health 
* ✅ **Daily Heating Statistics** - Per-zone heating time tracking 
* ✅ **Boiler & Zone Timeline** - Visual activity history 
* ✅ **Multi-Zone Temperature Graph** - Temperature trends with targets 
* ✅ **Zone Detail Cards** - Individual zone controls

---

## 🔧 Prerequisites

### Required Home Assistant Version
- **Home Assistant 2025.10+**
- SmartHeatZones integration installed and configured

### Required Custom Components (via HACS)

Install these custom cards from HACS:

1. **ApexCharts Card** - For advanced temperature graphing
   ```
   HACS → Frontend → Search "ApexCharts-card" → Install
   ```

2. **Bar Card** (Optional but recommended) - For heating time comparison
   ```
   HACS → Frontend → Search "Bar Card" → Install
   ```

3. **Mini Graph Card** (Optional) - Alternative graphing option
   ```
   HACS → Frontend → Search "mini-graph-card" → Install
   ```

### Entity Names Configuration

**IMPORTANT:** The configuration files assume the following entity names. If yours are different, you'll need to replace them throughout:

**Climate Entities:**
- `climate.living_room`
- `climate.bedroom`
- `climate.kitchen`
- `climate.bathroom`

**Temperature Sensors:**
- `sensor.living_room_temperature`
- `sensor.bedroom_temperature`
- `sensor.kitchen_temperature`
- `sensor.bathroom_temperature`
- `sensor.outdoor_temperature` (optional)

**Boiler Switch:**
- `switch.boiler_main`

---

## 📥 Installation Steps

### Step 1: Install Helper Sensors

These sensors track heating time and cycles.

1. **Open your `configuration.yaml`** file

2. **Add the helper sensors:**
   - Copy the contents of `phase1_helpers.yaml`
   - Paste into your `configuration.yaml`
   - **Important:** Adjust entity names if yours differ

3. **Alternative (via UI):**
   - Go to **Settings → Devices & Services → Helpers**
   - Click **+ Create Helper**
   - For each zone, create a **History Stats** sensor:
     - **Name:** `Living Room Heating Time Today`
     - **Entity:** `climate.living_room`
     - **State:** `heating`
     - **Type:** Time
     - **Start:** `{{ now().replace(hour=0, minute=0, second=0) }}`
     - **End:** `{{ now() }}`
   - Repeat for all zones and boiler

4. **Create Counter:**
   - Settings → Devices & Services → Helpers
   - Create Helper → Counter
   - **Name:** `Boiler Cycles Today`
   - **Initial Value:** 0
   - **Step:** 1

5. **Check configuration:**
   ```bash
   ha core check
   ```

6. **Restart Home Assistant:**
   ```bash
   ha core restart
   ```

---

### Step 2: Install Template Sensors

These calculate derived metrics like totals and averages.

1. **Open your `configuration.yaml`** file

2. **Locate or create the `template:` section**

3. **Add template sensors:**
   - Copy the contents of `phase1_template_sensors.yaml`
   - Paste into the `template:` section
   - **Important:** Replace entity names with yours if different

   Example structure:
   ```yaml
   # configuration.yaml

   template:
     - sensor:
         # [Paste template sensors here]

     - binary_sensor:
         # [Paste binary sensors here]
   ```

4. **Check configuration:**
   ```bash
   ha core check
   ```

5. **Reload templates:**
   - Developer Tools → YAML → Template Entities

---

### Step 3: Create Automations

These automations reset counters and track boiler cycles.

1. **Option A: Via UI (Recommended)**

   Navigate to: **Settings → Automations → Create Automation**

   **Automation 1: Reset Boiler Cycles Counter**
   ```yaml
   alias: SmartHeatZones - Reset Boiler Cycles Counter
   trigger:
     - platform: time
       at: "00:00:00"
   action:
     - service: counter.reset
       target:
         entity_id: counter.boiler_cycles_today
   mode: single
   ```

   **Automation 2: Increment Boiler Cycles**
   ```yaml
   alias: SmartHeatZones - Increment Boiler Cycles
   trigger:
     - platform: state
       entity_id: switch.boiler_main
       from: 'off'
       to: 'on'
   action:
     - service: counter.increment
       target:
         entity_id: counter.boiler_cycles_today
   mode: single
   ```

2. **Option B: Via Configuration File**
   - Copy automation section from `phase1_helpers.yaml`
   - Add to `automations.yaml` or `configuration.yaml`

---

### Step 4: Verify Sensors

Before creating the dashboard, verify all sensors are working:

1. **Go to Developer Tools → States**

2. **Check these sensors exist and have values:**
   - ✅ `sensor.smartheatzones_active_zones_count`
   - ✅ `sensor.smartheatzones_boiler_status`
   - ✅ `sensor.smartheatzones_total_heating_time_today`
   - ✅ `sensor.living_room_heating_time_today`
   - ✅ `sensor.bedroom_heating_time_today`
   - ✅ `sensor.kitchen_heating_time_today`
   - ✅ `sensor.bathroom_heating_time_today`
   - ✅ `sensor.boiler_runtime_today`
   - ✅ `counter.boiler_cycles_today`

3. **If any sensors are missing:**
   - Check entity names match your system
   - Reload template entities
   - Check configuration for errors

---

### Step 5: Create Lovelace Dashboard

Now create the visual dashboard!

1. **Go to Settings → Dashboards**

2. **Create a new dashboard OR edit existing:**
   - Click **+ Add Dashboard**
   - Name: "SmartHeatZones"
   - Icon: `mdi:radiator`
   - Click **Create**

3. **Add a new view:**
   - Click **+ Add View**
   - Title: "System Overview"
   - Icon: `mdi:home-thermometer`
   - Type: **Sidebar** (recommended) or **Panel**

4. **Add cards one by one:**

   Open `phase1_lovelace_cards.yaml` and copy each card:

   **Card 1: System Status Overview**
   - Click **+ Add Card**
   - Switch to **Code Editor** (bottom right)
   - Paste Card 1 YAML
   - Click **Save**

   **Card 2: Daily Heating Statistics**
   - Click **+ Add Card**
   - Switch to **Code Editor**
   - Paste Card 2 YAML
   - Click **Save**

   **Card 3: Boiler & Zone Timeline**
   - Click **+ Add Card**
   - Switch to **Code Editor**
   - Paste Card 3 YAML
   - Click **Save**

   **Card 4: Multi-Zone Temperature Graph**
   - Click **+ Add Card**
   - Switch to **Code Editor**
   - Paste Card 4 YAML
   - Click **Save**
   - **Note:** Requires ApexCharts Card installed

   **Card 5: Zone Details**
   - Click **+ Add Card**
   - Switch to **Code Editor**
   - Paste Card 5 YAML
   - Click **Save**

5. **Save the dashboard**

---

## 🎨 Customization Tips

### Adjusting Entity Names

If your entity names differ, use **Find & Replace**:

1. Open each YAML file
2. Find: `climate.living_room`
3. Replace with: `climate.your_actual_name`
4. Repeat for all entities

### Customizing Colors

In the ApexCharts card, change colors:

```yaml
color: '#66BB6A'  # Living Room - Green
color: '#FFA726'  # Bedroom - Orange
color: '#AB47BC'  # Kitchen - Purple
color: '#EF5350'  # Bathroom - Red
color: '#4A90E2'  # Outdoor - Blue
```

### Adjusting Graph Time Ranges

Change `graph_span` in ApexCharts:
- `12h` - 12 hours
- `24h` - 24 hours (default)
- `7d` - 7 days
- `30d` - 30 days

Change `hours_to_show` in history-graph:
- `6` - 6 hours
- `12` - 12 hours
- `24` - 24 hours (default)

---

## 🐛 Troubleshooting

### Sensors Show "Unknown" or "Unavailable"

**Problem:** Template sensors show unknown
**Solution:**
1. Check entity names are correct
2. Reload template entities: Developer Tools → YAML → Template Entities
3. Wait a few minutes for history stats to populate

### Bar Card Not Showing

**Problem:** Bar card shows error
**Solution:**
1. Install Bar Card from HACS
2. Clear browser cache (Ctrl+Shift+R)
3. Restart Home Assistant

### ApexCharts Card Not Rendering

**Problem:** Temperature graph shows blank or error
**Solution:**
1. Install ApexCharts Card from HACS
2. Verify sensor names match your entities
3. Check that sensors have temperature data
4. Clear browser cache

### History Stats Showing 0 Hours

**Problem:** Heating time sensors always show 0
**Solution:**
1. Ensure zones have been heating (turn on manually to test)
2. Wait for sensors to update (can take 1-2 minutes)
3. Check `hvac_action` attribute is "heating" when active:
   ```
   Developer Tools → States → climate.living_room
   Look for: hvac_action: heating
   ```

### Counter Not Incrementing

**Problem:** Boiler cycles counter stays at 0
**Solution:**
1. Verify automation is enabled: Settings → Automations
2. Check boiler switch entity name is correct
3. Test by manually turning boiler on/off
4. Check automation logs for errors

---

## 📊 Expected Results

After installation, you should see:

### System Status Card
- ✅ Boiler status (ON/OFF with uptime)
- ✅ Outdoor temperature
- ✅ Number of active zones
- ✅ Total heating time today
- ✅ Boiler cycle count

### Daily Statistics Card
- ✅ Heating time for each zone (hours)
- ✅ Bar chart comparison
- ✅ Average heating time
- ✅ Total system runtime

### Timeline Card
- ✅ Visual timeline of boiler ON periods
- ✅ Visual timeline of zone heating
- ✅ Logbook of recent events

### Temperature Graph
- ✅ Multi-line graph with all zones
- ✅ Target temperature dashed lines
- ✅ Outdoor temperature (bold blue line)
- ✅ 24-hour history

### Zone Details
- ✅ Thermostat controls for each zone
- ✅ Current vs target temperature
- ✅ Heating status
- ✅ Temperature deviation from target

---

## 📈 Next Steps

### Collect Data
- Let the system run for **24 hours** to collect meaningful statistics
- After 7 days, weekly patterns will emerge
- After 30 days, monthly comparisons become available

### Fine-Tune
- Adjust graph colors to your preference
- Rearrange cards for optimal layout
- Add/remove zones as needed

### Phase 2 (Future)
Once Phase 1 is working well, proceed to Phase 2:
- Piggyback heating performance tracking
- Energy efficiency scoring
- Weekly/monthly comparisons
- Cost estimation (if power meter available)

---

## 📝 File Checklist

Ensure you have these files:

- ✅ `phase1_helpers.yaml` - Helper sensors configuration
- ✅ `phase1_template_sensors.yaml` - Template sensors
- ✅ `phase1_lovelace_cards.yaml` - Dashboard card definitions
- ✅ `PHASE1_INSTALLATION_GUIDE.md` - This file

---

## 🆘 Support

### Common Issues
- [See Troubleshooting section above](#troubleshooting)

### Getting Help
- **GitHub Issues:** https://github.com/forreggbor/SmartHeatZones/issues
- **Home Assistant Community:** Tag your post with `smartheatzones`
- **Check Logs:** Settings → System → Logs

### Useful Developer Tools
- **Template Editor:** Developer Tools → Template
- **States Inspector:** Developer Tools → States
- **Service Tester:** Developer Tools → Services

---

## ✅ Installation Complete!

Congratulations! Your Phase 1 SmartHeatZones dashboard is now installed.

**What you can now see:**
- Real-time system status
- Daily heating statistics per zone
- Visual timeline of heating activity
- Temperature trends with targets
- Individual zone controls

**Enjoy your enhanced heating system monitoring!** 🎉
# SmartHeatZones - Phase 2 Dashboard Installation Guide

**Version:** 1.9.0
**Author:** forreggbor
**Phase:** 2 - Advanced Analytics

---

## 📋 Overview

Phase 2 builds on Phase 1 to add advanced analytics, efficiency scoring, and cost tracking.

**Prerequisites:** Phase 1 must be installed and working.

### What Phase 2 Adds:

✅ **Piggyback Heating Analytics** - Track success rate and energy savings
✅ **Efficiency Scoring** - 0-100 score with improvement tips
✅ **Weekly/Monthly Comparisons** - Historical trend analysis
✅ **Cost Estimation** - Energy cost tracking with projections
✅ **Comfort Analytics** - Temperature deviation tracking

---

## 🔧 Prerequisites

### Must Have (from Phase 1):
- ✅ Phase 1 installed and working
- ✅ ApexCharts Card (HACS)
- ✅ Bar Card (HACS)
- ✅ All Phase 1 sensors functioning

### New Requirements for Phase 2:
- Home Assistant 2025.10+
- SmartHeatZones v1.9.0+
- Gauge card (built-in)
- Markdown card (built-in)

---

## 📥 Installation Steps

### Step 1: Install Phase 2 Helper Entities

1. **Open your `configuration.yaml`**

2. **Add Phase 2 helpers:**
   - Copy contents from `phase2_helpers.yaml`
   - Paste into your `configuration.yaml`

3. **Key components to add:**
   ```yaml
   # Counter for piggyback events
   counter:
     piggyback_events_today:
       name: Piggyback Events Today
       icon: mdi:lightning-bolt
       initial: 0
       step: 1

   # Input numbers for configuration
   input_number:
     smartheatzones_average_power:
       name: "SmartHeatZones Average Power"
       min: 0.5
       max: 10.0
       step: 0.1
       initial: 2.5
       unit_of_measurement: "kW"

     smartheatzones_cost_per_kwh:
       name: "SmartHeatZones Cost per kWh"
       min: 0.05
       max: 1.00
       step: 0.01
       initial: 0.20
       unit_of_measurement: "€/kWh"
   ```

4. **Add automations:**
   - Reset piggyback counter at midnight
   - Track piggyback events (customize trigger for your setup)

5. **Customize power and cost values:**
   - Set `smartheatzones_average_power` to your boiler's average power
   - Set `smartheatzones_cost_per_kwh` to your electricity rate

6. **Check configuration:**
   ```bash
   ha core check
   ```

7. **Restart Home Assistant**

---

### Step 2: Install Phase 2 Template Sensors

1. **Open your `configuration.yaml`**

2. **Add Phase 2 template sensors:**
   - Copy contents from `phase2_template_sensors.yaml`
   - Paste into the `template:` section (below Phase 1 sensors)

3. **Key sensors being added:**
   - Piggyback tracking sensors
   - Efficiency score (0-100)
   - Weekly/monthly totals
   - Cost estimation sensors
   - Comfort analytics

4. **Check configuration:**
   ```bash
   ha core check
   ```

5. **Reload templates:**
   - Developer Tools → YAML → Template Entities

---

### Step 3: Configure Power and Cost Settings

1. **Go to Settings → Devices & Services → Helpers**

2. **Verify input numbers were created:**
   - `input_number.smartheatzones_average_power`
   - `input_number.smartheatzones_cost_per_kwh`

3. **Set your actual values:**
   - **Average Power:** Measure or estimate your boiler's average power consumption (typically 2-5 kW)
   - **Cost per kWh:** Check your electricity bill for current rate

4. **Optional: Use actual power meter:**
   - If you have a power meter on your boiler, see Phase 2 helpers for integration example
   - This provides real measurements instead of estimates

---

### Step 4: Verify Phase 2 Sensors

Before creating cards, verify all sensors exist:

1. **Go to Developer Tools → States**

2. **Check Phase 2 sensors:**
   - ✅ `counter.piggyback_events_today`
   - ✅ `sensor.smartheatzones_piggyback_events_today`
   - ✅ `sensor.smartheatzones_piggyback_success_rate`
   - ✅ `sensor.smartheatzones_efficiency_score`
   - ✅ `sensor.smartheatzones_heating_this_week`
   - ✅ `sensor.smartheatzones_heating_this_month`
   - ✅ `sensor.smartheatzones_energy_cost_today`
   - ✅ `sensor.smartheatzones_comfort_score`
   - ✅ `binary_sensor.smartheatzones_high_efficiency`

3. **If sensors show "unknown":**
   - Wait 2-3 minutes for values to populate
   - Check template syntax in configuration
   - Reload template entities

---

### Step 5: Create Phase 2 Dashboard Cards

1. **Go to your SmartHeatZones dashboard**

2. **Create a new view OR add to existing:**
   - Option A: New view "Analytics" for Phase 2 cards
   - Option B: Add Phase 2 cards below Phase 1 cards

3. **Add cards one by one:**

Open `phase2_lovelace_cards.yaml` and copy each card:

#### Card 6: Piggyback Heating Performance
- Shows piggyback events and success rate
- Energy savings estimation
- Visual gauge and bar charts

#### Card 7: Energy Efficiency Score
- 0-100 efficiency score with gauge
- Score breakdown by category
- Star rating visualization
- Improvement suggestions

#### Card 8: Weekly/Monthly Comparison
- Weekly vs monthly heating time
- Bar charts per zone
- 7-day trend graph
- Historical analysis

#### Card 9: Cost Estimation
- Daily, weekly, monthly costs
- Energy consumption tracking
- Cost projections
- Trend graphs

#### Card 10: Comfort Analytics
- Comfort score (0-100%)
- Per-zone deviations
- Temperature stability metrics
- Deviation bar charts

4. **For each card:**
   - Click + Add Card
   - Switch to Code Editor
   - Paste card YAML
   - Click Save

5. **Save the dashboard**

---

## 🎨 Customization

### Adjust Power and Cost

**In the UI:**
- Settings → Devices & Services → Helpers
- Adjust `SmartHeatZones Average Power`
- Adjust `SmartHeatZones Cost per kWh`

**Values update immediately** in cost sensors

### Customize Efficiency Scoring

Edit `phase2_template_sensors.yaml`:

```yaml
# Adjust scoring weights (must total 100 points)
# Piggyback: 0-25 points
# Stability: 0-25 points
# Cycling: 0-25 points
# Adaptive: 0-25 points
```

### Change Comfort Threshold

Edit comfort score calculation:

```yaml
# Default: deviation < 1.0°C is comfortable
{% if deviation < 1.0 %}
  # Change to 0.5 for stricter comfort
  # Change to 1.5 for looser comfort
```

---

## 📊 Understanding the Metrics

### Piggyback Success Rate

**Formula:** `(Piggyback Events / Total Boiler Cycles) × 100`

**What it means:**
- 80%+ : Excellent - Most heating starts use piggyback
- 50-80%: Good - Decent piggyback utilization
- <50% : Room for improvement

### Efficiency Score Breakdown

**Components (25 points each):**

1. **Piggyback Usage (0-25)**
   - Based on success rate
   - Higher = better energy efficiency

2. **Temperature Stability (0-25)**
   - Average deviation from targets
   - Lower deviation = higher score

3. **Boiler Cycling (0-25)**
   - Compared to ideal ~20 cycles/day
   - Fewer cycles = better efficiency

4. **Adaptive Hysteresis (0-25)**
   - Active when outdoor < 10°C
   - 25 points if active, 0 if not

**Total:** 0-100 points

**Rating Scale:**
- 90-100: ⭐⭐⭐⭐⭐ Excellent
- 80-89: ⭐⭐⭐⭐ Good
- 70-79: ⭐⭐⭐ Fair
- 60-69: ⭐⭐ Needs Improvement
- <60: ⭐ Poor

### Cost Estimation

**Calculation:**
`Cost = Heating Hours × Average Power (kW) × Cost per kWh`

**Example:**
- Heating: 6 hours
- Power: 2.5 kW
- Rate: €0.20/kWh
- Cost: 6 × 2.5 × 0.20 = **€3.00**

**Accuracy:**
- With power meter: Very accurate
- With estimates: ±20% typical

---

## 🐛 Troubleshooting

### Efficiency Score Stuck at 0

**Problem:** Score always shows 0
**Solutions:**
1. Check all component sensors exist
2. Verify outdoor sensor has data
3. Wait 24h for meaningful statistics
4. Check template syntax

### Piggyback Counter Not Incrementing

**Problem:** Counter stays at 0
**Solutions:**
1. Verify automation is enabled
2. Check trigger conditions match your setup
3. Test manually by turning zones on while boiler is running
4. Check automation logs

### Cost Sensors Show Very High/Low Values

**Problem:** Unrealistic cost estimates
**Solutions:**
1. Verify average power setting (typical: 2-5 kW)
2. Check cost per kWh (typical: €0.10-0.40)
3. Ensure heating time sensors are accurate
4. Consider installing actual power meter

### Weekly/Monthly Sensors Show 0

**Problem:** No weekly/monthly data
**Solutions:**
1. Ensure Phase 1 utility meters are working
2. Wait for first cycle to complete (week/month)
3. Check utility meter configuration
4. Verify source sensors have data

---

## 📈 Expected Results

### After 1 Day

```
Piggyback Events: 12
Success Rate: 52%
Efficiency Score: 67
Daily Cost: €3.20
```

### After 1 Week

```
Weekly Heating: 42h
Weekly Cost: €21.00
Comfort Score: 94%
Efficiency improved to: 72
```

### After 1 Month

```
Monthly Heating: 180h
Monthly Cost: €90.00
Patterns identified
Optimization opportunities visible
```

---

## 🎯 Optimization Tips

### Improve Efficiency Score

**To increase Piggyback points:**
- Ensure outdoor sensor configured
- Check zone sensors respond quickly
- Review piggyback logic in code

**To increase Stability points:**
- Adjust hysteresis values
- Fine-tune target temperatures
- Ensure good sensor placement

**To increase Cycling points:**
- Increase hysteresis slightly
- Use adaptive hysteresis
- Avoid manual overrides

**To increase Adaptive points:**
- Configure outdoor sensor
- Enable adaptive hysteresis
- Ensure outdoor temp < 10°C for activation

### Reduce Costs

1. **Lower target temps by 1°C** - Saves ~6% energy
2. **Use schedules effectively** - Lower temps when away
3. **Improve insulation** - Reduces heating time needed
4. **Optimize piggyback** - Free heating when boiler running

---

## 🔄 Phase 1 + Phase 2 Complete Dashboard

Once both phases installed, you'll have:

**Phase 1 Cards (Monitoring):**
1. System Status
2. Daily Statistics
3. Timeline
4. Temperature Graph
5. Zone Details

**Phase 2 Cards (Analytics):**
6. Piggyback Performance
7. Efficiency Score
8. Weekly/Monthly Comparison
9. Cost Estimation
10. Comfort Analytics

**Total:** 10 comprehensive cards covering all aspects of your heating system!

---

## 📚 Next Steps

1. **Let it run** - Collect 7 days of data minimum
2. **Review efficiency** - Check score daily
3. **Optimize** - Use insights to improve
4. **Track costs** - Monitor monthly spending
5. **Phase 3** - Coming soon with predictive analytics!

---

## 🆘 Support

### Getting Help
- 📖 Review this guide
- 🐛 Check troubleshooting section
- 💬 Home Assistant Community
- 🎫 GitHub Issues

### Reporting Issues
Include:
- Phase 1 status (working/not working)
- Phase 2 sensor states
- Error logs
- Configuration YAML
- Screenshots

---

**Phase 2 Installation Complete!** 🎉

You now have advanced analytics to optimize your heating system!

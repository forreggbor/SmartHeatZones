# Initial Setup

### Prerequisites

Before setting up SmartHeatZones, ensure you have:

**Required:**
- At least one temperature sensor per zone (any `sensor` entity with numeric state)
- At least one relay switch per zone (any `switch` entity)
- One shared boiler relay switch (any `switch` entity)

**Optional but Recommended:**
- Outdoor temperature sensor (for adaptive hysteresis)
- Door/window sensors per zone (any `binary_sensor` entity)

**Hardware Examples:**
- **Temperature sensors:** Zigbee sensors, Z-Wave sensors, ESPHome devices, Shelly H&T
- **Relay switches:** Shelly relays, Sonoff switches, ESPHome relays, Zigbee switches
- **Boiler switch:** Any controllable switch that controls your boiler/furnace

### Setup Process

SmartHeatZones requires a **two-phase setup**:

#### Phase 1: Create Common Settings (Required First)

1. **Go to Settings → Devices & Services**
2. **Click "Add Integration"**
3. **Search for "Smart Heat Zones"**
4. **Click on SmartHeatZones when it appears**

5. **Common Settings Screen appears:**
   - **Main boiler switch** (REQUIRED): Select your boiler control switch
   - **Outdoor temperature sensor** (OPTIONAL): For adaptive hysteresis
   - **Base hysteresis** (REQUIRED): Default 0.3°C, adjust based on your system
   - **Overheat protection** (REQUIRED): Default 26.0°C, safety limit
   - **Adaptive hysteresis** (REQUIRED): Enable/disable automatic adjustment

6. **Click Submit**

You'll now see a **"🔧 Common Settings"** entry in your integrations list. This entry:
- Must exist before creating zones
- Stores global configuration
- Can be modified via its Options menu
- Cannot be deleted while zones exist

#### Phase 2: Create Heating Zones

Once common settings exist, you can create zones:

1. **Click "Add Integration" again**
2. **Search for "Smart Heat Zones"**
3. **The Zone Creation screen appears:**

   **Zone Configuration:**
   - **Zone name** (REQUIRED): Descriptive name (e.g., "Ground Floor")
   - **Heating mode** (REQUIRED): 
     - 🔥 Radiator (uses hysteresis)
     - 🌡️ Underfloor Heating (instant switching)
   - **Zone temperature sensor** (REQUIRED): Temperature sensor for this zone
   - **Zone relays** (REQUIRED): One or more switches controlling this zone
   - **Door/window sensors** (OPTIONAL): Pause heating when open

4. **Click Submit**

5. **Repeat for each zone** you want to create

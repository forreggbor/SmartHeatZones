# Advanced Features

### Adaptive Hysteresis

**How It Works:**
- Monitors outdoor temperature
- Automatically adjusts hysteresis multiplier
- Provides more stable operation in extreme cold
- Reduces cycling in moderate weather

**Multiplier Table:**
| Outdoor Temp | Multiplier | Example (0.3°C base) |
|--------------|-----------|---------------------|
| < -10°C      | 2.0×      | 0.6°C              |
| -10°C to 0°C | 1.5×      | 0.45°C             |
| 0°C to 10°C  | 1.2×      | 0.36°C             |
| ≥ 10°C       | 1.0×      | 0.3°C              |

**Benefits:**
- Reduces boiler starts in very cold weather
- Extends equipment lifetime
- Improves comfort through steadier heating
- Automatically optimizes based on conditions

**Requirements:**
- Outdoor temperature sensor configured in common settings
- Adaptive hysteresis enabled in common settings
- Sensor must provide reliable readings

### Door/Window Detection

**Automatic Heating Pause:**
- When ANY configured door/window opens → zone heating pauses
- When ALL doors/windows close → heating resumes
- No manual intervention required

**Energy Savings:**
- Prevents heating while ventilating
- Typical savings: 5-15% on heating bills
- Especially effective for rooms with frequent ventilation

**Sensor Requirements:**
- Must be `binary_sensor` entities
- "on" state = open/detected
- "off" state = closed/not detected
- Can use contact sensors, magnetic switches, or smart sensors

**Limitations:**
- All sensors treated equally (no priority)
- No delay/grace period (instant response)
- Cannot pause specific relays, only entire zone

### Overheat Protection

**Safety Mechanism:**
- Continuously monitors zone temperature
- Compares against overheat protection limit
- If limit exceeded → immediate shutdown

**Shutdown Behavior:**
- All zone relays turn OFF immediately
- Zone marked as inactive
- Boiler manager notified (may turn off boiler)
- Error logged for diagnostics

**Recovery:**
- Automatic when temperature drops below limit
- No manual reset required
- Normal operation resumes

**Use Cases:**
- Sensor malfunction detection
- Stuck relay protection
- Thermostat failure safety
- Occupant safety

### Boiler Coordination

**Intelligent Boiler Management:**
- Single boiler serves multiple zones
- Automatically coordinates when to run boiler
- Prevents premature shutoff
- Optimizes for efficiency

**How It Works:**
1. Each zone reports heating status to Boiler Manager
2. Boiler Manager maintains set of active zones
3. If ANY zone active → boiler ON
4. If ALL zones inactive → boiler OFF
5. Redundant commands filtered (no relay chattering)

**Benefits:**
- No manual boiler control needed
- Optimal runtime (not too short, not too long)
- Works seamlessly with multiple zones
- Reduces wear on boiler relay

**Important:**
- All zones MUST use the same boiler switch
- Configured once in common settings
- Automatically propagated to all zones

### Manual Override Detection

**Event-Based Monitoring:**
- Real-time detection of external relay changes
- Instantly updates internal state
- Synchronizes boiler coordination
- Maintains system consistency

**Override Sources:**
- Manual physical switch operation
- Other automations controlling same relays
- Direct service calls to relay entities
- External integrations

**System Response:**
- Detects change within seconds
- Updates zone heating status
- Notifies Boiler Manager
- Logs override event

**Use Cases:**
- Emergency manual shutoff
- Testing relay operation
- Integration with other systems
- Maintenance procedures

---

## Fail-safe and error handling

SmartHeatZones never keeps heating on the strength of a sensor it cannot trust.

| Situation | What happens |
|-----------|--------------|
| The zone temperature sensor is `unavailable`, `unknown` or not a number for **10 minutes** | The zone's relays are switched off, the boiler is released, and the zone reports `sensor_fault: sensor_unavailable`. The current temperature shows as unknown, and the zone cannot start by piggyback heating. |
| The sensor still shows a number but has **not reported anything for 2 hours** (for example a dead battery that leaves the last value in place) | Same as above, with `sensor_fault: sensor_stale`. |
| The sensor is back | Normal control resumes by itself and `sensor_fault` is cleared. |
| A relay or the boiler switch does not accept a command | The error is logged and the command is retried every minute, as long as it is still the wanted one. The zone lists the relays in the `relay_fault` attribute. A newer decision or a manual switch cancels the retry, so a manual switch is never overridden. |
| Home Assistant restarts while a relay is on | The zone takes over the real relay state, so it can still switch that relay off. |

The timeouts are the constants `SENSOR_UNAVAILABLE_GRACE`, `SENSOR_STALE_TIMEOUT` and `WATCHDOG_INTERVAL` in `const.py`. Use the `sensor_fault` and `relay_fault` attributes of the zone's climate entity in automations or on the dashboard to be notified.

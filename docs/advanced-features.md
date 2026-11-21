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

SmartHeatZones never keeps heating on the strength of a sensor it cannot trust, and it never lets the house cool down just because a sensor is silent. A zone follows this chain, evaluated every minute:

1. **Zone sensor healthy** - normal control.
2. **Zone sensor lost, backup sensor healthy** - normal control on the backup sensor (its reading plus the configured correction). Hysteresis and overheat protection apply as usual.
3. **No usable sensor** - **limp mode**: an open-loop cycle that heats for a few minutes of every period (see below).
4. **Zone sensor back** - normal control on the zone sensor resumes immediately.

| Situation | What happens |
|-----------|--------------|
| The zone temperature sensor is `unavailable`, `unknown` or not a number for **10 minutes** | The zone sensor counts as lost: `sensor_fault: sensor_unavailable`. |
| The sensor still shows a number but has **not reported anything for the zone's silence limit** (zone setting, **2 hours** by default; for example a dead battery that leaves the last value in place) | The zone sensor counts as lost: `sensor_fault: sensor_stale`. |
| The sensor is back | Normal control resumes by itself and `sensor_fault` is cleared. |
| A relay or the boiler switch does not accept a command | The error is logged and the command is retried every minute, as long as it is still the wanted one. The zone lists the relays in the `relay_fault` attribute. A newer decision or a manual switch cancels the retry, so a manual switch is never overridden. |
| A relay becomes `unavailable` (for example a wifi outage) | It is not treated as a manual switch-off. It is listed in `relay_unavailable`, and when it is back the zone sends it its wanted state. A relay that stays unreachable for 15 minutes while heating is wanted raises a notification. |
| Home Assistant restarts while a relay is on | The zone takes over the real relay state, so it can still switch that relay off. |

The silence limit is set per zone in the zone settings (**Sensor silence limit**, 0.5 to 24 hours, default 2 hours). The 10 minute tolerance for an unavailable sensor and the one minute check interval are the constants `SENSOR_UNAVAILABLE_GRACE` and `WATCHDOG_INTERVAL` in `const.py`. After a Home Assistant restart with a dead sensor, the fault is declared only after the grace period or the silence limit has passed again, because state timestamps restart with Home Assistant.

### Limp mode

While neither the zone sensor nor a backup sensor can be trusted, the zone heats for **on minutes** of every **period**, counted from local midnight (so the cycle continues across restarts, and zones with the same period switch in the same phase, which starts the boiler once per period).

| Heating mode | Default |
|--------------|---------|
| Radiator | 10 minutes of every 60 |
| Underfloor | 40 minutes of every 180 |

- The profile per heating mode is set in the **common settings**. A zone can override it with its own two fields (both or neither). `0` minutes means no heating, which equals the old "switch off" behavior.
- The target temperature and presets are ignored (there is no reading to compare with). HVAC `off` and an open door/window still switch the heating off.
- If the outdoor temperature is known, the on time is scaled with the same bands as adaptive hysteresis (`< -10°C`: x2.0, `< 0°C`: x1.5, `< 10°C`: x1.2, otherwise x1.0). When the outdoor temperature reaches the **outdoor cut-off** (default 15°C, empty = disabled), limp mode does not heat (summer).
- The outdoor temperature is taken from the first source that works: the **outdoor sensor**, the **backup outdoor source** (a `weather.*` entity or a sensor, useful when Home Assistant has no internet or the Zigbee network is down), or a **cautious estimate**: the minimum of the last 24 hours before the sensor was lost (needs at least 3 readings spanning 12 hours, valid for 7 days). Without any outdoor value the nominal on time is used and the cut-off does not apply. The attribute `outdoor_source` shows which one is in use. The estimate is kept in memory only: it starts empty after a restart and after every change of the common settings.
- A weather entity must report °C; any other unit is ignored with a warning in the log.
- Limp mode is open loop: without a reading there is no overheat protection, the cycle length is the limit. During limp mode a manual switch of the relay is reverted within a minute. When a door closes in limp mode, the cycle resumes at the next one minute check. If the period does not divide 1440 minutes, the phase jumps at midnight and at daylight saving changes.

### Attributes, events and notifications

| Attribute | Meaning |
|-----------|---------|
| `sensor_fault` | Why the **zone sensor** is not trusted (`sensor_unavailable` / `sensor_stale`), `null` when it is fine. **It is also set while the zone runs normally on its backup sensor**: it no longer means "heating is off". |
| `sensor_source` | The sensor the zone runs on: `primary`, `backup` or `none` (limp mode). |
| `limp_active` | `true` while limp mode controls the zone. |
| `limp_on_minutes`, `limp_period_minutes` | The effective profile of the zone. |
| `outdoor_source` | `live`, `backup`, `estimate` or `none` while limp mode is active. |
| `relay_fault` | Relays whose last command failed and is being retried. |
| `relay_unavailable` | Relays that are currently `unavailable`/`unknown`. |

The attributes are the authoritative state. For automations (for example a phone notification while you are away) use `sensor_source`, `limp_active` or the event **`smartheatzones_failsafe`**, which is fired on every change with `zone`, `state` (`backup`, `limp`, `recovered`, `relay_unavailable`, `relay_recovered`), `cause`, a per-integration overview of the sensors (`groups`: several lost sensors in one integration point at a network or coordinator problem) and the unreachable relays. Events are transition hints only.

The zone also shows a persistent notification in Home Assistant (one per cause, replaced when the state changes, dismissed on recovery and at startup). Its text follows the Home Assistant language (Hungarian and English).

### Things to know

- Changing the common settings reloads all zones. Changing the **boiler switch** is the exception: it is registered once per Home Assistant run and needs a restart (a warning is logged).
- A relay that stays ON while Home Assistant or the wifi is down cannot be switched off by software. Use the device's own protection where it exists (for example the safe default state or an auto-off timer on the relay).

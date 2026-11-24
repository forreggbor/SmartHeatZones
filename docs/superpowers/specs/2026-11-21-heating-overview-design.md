# Heating overview: overview sensor + GlowStat card - design

Issues: SmartHeatZones #27, ha-GlowStat #3. Status: approved by Gábor ("build the whole proposed feature set"), scope widened with the next scheduled change and the live failsafe flash.

## Intent
One card for the whole house that answers "is it working, why is it (not) heating, can I trust it while away". SmartHeatZones provides one system-level entity; GlowStat draws the card from it. The data is shared: other GlowStat cards can use the same contract.

## Part 1 - SmartHeatZones (integration, target v1.14.0)

**Entity:** `sensor.smartheatzones_overview`, created once by the common-settings entry (new `sensor` platform). State: `on` while the boiler runs (active zones in the boiler manager), else `off`. Updated at most once per second after any zone/boiler change, and once a minute. All data below is in the attributes; `schema: 1` is a version for card compatibility.

```
schema: 1
updated: ISO time
boiler:  entity, running, since, held_by[zone], afterheat_zones[zone],
         starts_today, runtime_today_s, afterheat_joins_today
zones[]: name, entity_id, sensor_entity, heating_mode, hvac_mode, hvac_action, preset,
         current, target, adjusted_target, hysteresis (effective), on_below, off_above,
         sensor_source, sensor_fault, limp {active, on_min, effective_on_min, period_min, next_in_min},
         next_change {at, in_min, temp, label} (only in preset auto, else null),
         afterheat (option), joined, relay_unavailable[], relay_fault[], reason
health:  groups { "<integration>": {total, bad} }  (from the existing sensor_health.group_overview)
```

**Decision reason** (also an attribute `reason` on every zone climate entity): a language-neutral object `{code, ...params}` produced by one pure function from the zone state. Codes: `needs_heat`, `holding` (heating inside the band), `afterheat`, `in_band` (idle, with `on_below`), `target_reached`, `door_open`, `hvac_off`, `no_reading`, `overheat`, `limp_heating`, `limp_waiting` (with `next_in_min`). The card translates the code; the integration never sends display text.

**Counters** live in the boiler manager and reset at local midnight: `starts_today` (logical start: first active zone), `runtime_today_s`, `afterheat_joins_today`. In memory only: a Home Assistant restart resets them (documented). A listener hook tells the overview entity to refresh.

## Part 2 - ha-GlowStat (`glowstat-heating-card`, target v0.5.0)

Config: `entity` (the overview sensor, required), `history_hours` (default 24), `show_timeline`, `show_eta`, `show_actions`, `language`; GUI editor like the other cards, hu + en texts.

- **Boiler header:** running or off with the duration, who holds it (afterheat zones marked), starts / runtime / afterheat joins today.
- **Zone rows:** name, current -> target, a bar showing the distance to the target with the on/off thresholds marked, a chip for the source (primary / backup / limp / afterheat) and the translated `reason` as the second line. Rows with a fault or lost sensor are marked; red only for real faults (relay not responding).
- **Time to target** `~25 min`: linear fit of the last 60 minutes of the zone's sensor history (`sensor_entity`), shown only while heating and only with a clearly rising trend, always labelled as an estimate.
- **24 h timeline** per zone (`hvac_action` history) and for the boiler (`boiler.entity` history), drawn like the thermometer card's graph.
- **Network line:** `health.groups` as "Zigbee 5/5 ok" or "3/5 silent".
- **Next change:** per zone "-> 22° at 17:00" from `next_change`.
- **Live flash:** the card subscribes to the `smartheatzones_failsafe` event and highlights the named zone row for a few seconds, then the normal rendering (from the overview) takes over.
- **Quick actions:** "All away", "All eco": `climate.set_preset_mode` on every zone of the overview (hidden with `show_actions: false`).
- The card also reads the overview only: no per-zone entity setup.

## Approaches
- **A (chosen):** one overview entity with a versioned contract, card reads only that plus history. One subscription, one place for the data shape, other cards can reuse it.
- B (rejected): the card reads every zone's climate attributes and the boiler switch itself. No integration change, but no counters, no network health, no reason, and the logic is duplicated in JavaScript.

## Decisions made without asking (reversible)
- Counters in memory only (cost: a restart resets "today").
- The reason is a code plus params, not text (cost: the card needs a translation for each code).
- Overview entity belongs to the common-settings entry (cost: it exists only while that entry is loaded).
- ETA is a client-side estimate from sensor history (cost: no estimate for a sensor without history).

## Non-goals
Per-zone target editing in this card (the climate card does that), persisting counters, a boost timer (nothing in the integration supports it). Fixing the "heating off" text of the climate card is GlowStat #2, separate.

## Left to the builder
Exact CSS and layout, entity naming of the device/unique id, translation wording, test fixtures.

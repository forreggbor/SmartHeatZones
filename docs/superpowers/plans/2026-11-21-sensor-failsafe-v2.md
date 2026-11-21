# Sensor fail-safe v2 — limp mode, backup sensor, fault diagnostics (issue #21)

Related: #22 (relay `unavailable` mis-detected as manual override) — Task 0, own commit, done FIRST.
Repo: `custom_components/smartheatzones/`. Tests: `tests/` (pytest-homeassistant-custom-component). HA is NOT installed locally → tests run in CI only (GitHub Actions `tests.yml`, on push). Work on a feature branch; every push needs Gábor's explicit go-ahead. Rule: every task ends with a green CI; existing tests are updated in the same task that changes the behaviour they pin.
No version bump / changelog change (not asked). Docs are English only (existing language). Python error handling: `except Exception` + `_LOGGER.exception` (never bare/`BaseException`, so `CancelledError` passes).

## Goal
Today a silent/dead zone sensor switches the zone's heating OFF (v1.10.1/1.10.2). During a week-long winter absence that lets the house cool down. Replace "off" with a bounded, self-recovering fallback chain:

1. primary sensor healthy → normal control (unchanged)
2. primary bad, backup sensor healthy → normal control on `backup + correction`
3. both bad / no backup → **limp mode**: open-loop time-proportional cycle
4. primary healthy again → immediate return to normal control

Fault classification (one sensor vs. whole Zigbee group) is NOT part of the control decision; it only enriches the notification.

## Environment facts (verified by reading code)
- Sensors Zigbee; relays 2.4 GHz wifi; outdoor sensor probably Zigbee. The HA system must work without internet.
- `_watchdog` runs every 1 min (`WATCHDOG_INTERVAL`); its fault branch runs once (`climate.py:639`, guard `_sensor_fault is None`) and its recovery branch `return`s before `_retry_failed_commands` (`climate.py:653`). A second recovery path exists in `_sensor_changed` (`climate.py:532-538`). `_watchdog` has no exception guard (`climate.py:635-662`).
- `_current_temp = None` on fault; `_evaluate_heating`, piggyback, overheat check early-return on `None`.
- After a HA restart `_sensor_fault` is `None`; a fault is declared only after the 10 min unavailable grace or the zone silence limit (default 2 h; state timestamps restart with HA) → bounded pre-fault window; relay-on-at-startup takeover (`climate.py:380-387`) can keep a relay on meanwhile. Accepted, documented.
- `_relay_state_changed` ignores only a missing `old_state` (`climate.py:477`); relays of a later-loading integration can be unavailable/unknown at zone setup, so the takeover does not see them.
- Zone unload neither switches relays nor releases boiler membership (`climate.py:397-404`); `BoilerManager` is a singleton that survives zone reloads and registers the boiler entity only once (`__init__.py:123-127`, `boiler_manager.py:85-86`).
- Underfloor mode has no hysteresis (`_get_effective_hysteresis`).
- `self._outdoor_sensor` is set whenever configured (`climate.py:166,249`) but tracked/cached only when `adaptive_hysteresis_enabled` (`climate.py:342`); the flow disables adaptive when no outdoor sensor exists (`options_flow.py:121-123`).
- Common-settings entry returns early in `async_setup_entry` and has NO update listener; only zone entries have one (`__init__.py:105-111,142`). Zones read common settings at setup (`climate.py:137,163-167`), so a common-settings change currently needs a restart. `hass.data` holds the same entry object, so new options are visible immediately.
- Flows: no `errors` in the options steps; `vol.Optional(default=...)` hands a cleared field its default back; clean-up of cleared keys lives in `_save_and_exit` / the common step (`options_flow.py:117-123,396-404`, `config_flow.py:113-123`).
- `datetime.now()` (naive) is used elsewhere (`climate.py:847`); new code uses `dt_util.now()`.
- Existing tests pinning "fault = off": `tests/test_failsafe.py:92-122`, `125-138`, `212-223`; test time starts from the freezer's real clock (not pinned).
- `ADAPTIVE_HYSTERESIS_MULTIPLIERS` lookup lives inline in `_get_effective_hysteresis` (`climate.py:763-767`).
- `docs/advanced-features.md:137-143` defines `sensor_fault` as "relays off, boiler released" and recommends automations on it.
- `strings.json` top-level keys: `title, config, options, selector, entity, services`.

## Decision log
| # | Decision | Rung | Claims it rests on (verification) | Reverses if |
|---|----------|------|-----------------------------------|-------------|
| 1 | Limp duty 0 min == old "off"; no mode selector | 5 | on-minutes 0 yields never-on (unit test) | a user needs "off" distinct from "0 duty" |
| 2 | Phase = `dt_util.now()` minutes since local midnight mod period; stateless | 2/4 | no stored timers to lose; period not dividing 1440 jumps at midnight/DST (documented, accepted) | phase jumps prove harmful in practice |
| 3 | Equal-period zones share the phase → boiler starts once per period | 3 | `BoilerManager` counts active zones (`boiler_manager.py:83-107`) | per-zone staggering becomes wanted |
| 4 | Limp ignores target/preset; HVAC OFF and open door/window honoured | 1 | no reading → target meaningless | users want limp to follow presets |
| 5 | Outdoor multipliers = existing `ADAPTIVE_HYSTERESIS_MULTIPLIERS` (Gábor), resolved by ONE shared helper also used by `_get_effective_hysteresis` | 3 | helper extraction keeps hysteresis tests green | — |
| 6 | Limp outdoor scaling + cut-off apply whenever an outdoor sensor is configured, independent of `adaptive_hysteresis_enabled` | 1 | summer cut-off must work even with adaptive off; live state read needs no tracking | — |
| 7 | Cut-off (common, default 15 °C; empty disables): valid outdoor ≥ cut-off → limp does not heat | 1 | summer heating with a dead sensor is wrong | — |
| 8 | Effective outdoor temperature for limp = chain, one shared helper: (a) live outdoor sensor, (b) optional backup source (`weather.*` or `sensor.*`), (c) cautious estimate, (d) none → multiplier 1.0 and no cut-off. (a)/(b) read live from entity state, age limit 3 h (const); bad/unavailable/stale → next level | 2 | cached value never goes stale (`climate.py:557`); HA must work without internet, so a cloud `weather.*` can be unavailable while the Zigbee sensor is also dead | outdoor sensor proves reliable enough to cache |
| 9 | Per-zone override of limp (on, period): both set or both empty (Gábor) | 3/4 | zone options fields optional, empty = inherit | — |
| 10 | HA event `smartheatzones_failsafe` on EVERY state change (primary→backup→limp→recovered) + attributes; no notify-service config; one notification id per cause per zone (sensor, relay); ids dismissed on entity setup | 5 | no schema/dependency added; per-cause ids keep one recovery from dismissing another still-valid notice | users want push without automations |
| 11 | Backup sensor correction = one optional number added to the backup reading | 5 | — | backup type differs in non-additive ways |
| 12 | Common-settings change reloads all LOADED zone entries sequentially (awaited), each isolated; the common entry itself is never reloaded. A changed boiler entity is NOT applied (singleton `BoilerManager`) → warning on mismatch, restart required (documented) | 1 | unloading it removes `DATA_COMMON_SETTINGS` (`__init__.py:162`) and a zone starting meanwhile exits entity-less (`climate.py:139-144`); concurrent reloads can mutate `_zone_entities` during piggyback iteration (`boiler_manager.py:125-128`); boiler registers once (`boiler_manager.py:85-86`) | — |
| 13 | Cautious estimate (c) = minimum of the samples in the 24 h window ending at the LAST valid outdoor sample (window freezes while no data arrives); usable only with ≥3 samples spanning ≥12 h and ≤7 days after the last sample, else (d). In-memory, per zone entity, cleared on reload/restart — incl. every common-settings change (decision 12); with the outdoor sensor dead at that moment the zone stays on (d) until data returns (accepted, documented) | 2 | min embeds day/night swing without a model and errs to the cold side (safe: duty is capped); avg+trend+clock model rejected (unvalidated parameters) | an hour-of-day profile proves needed, or (d) after settings changes proves harmful |
| 14 | Backup outdoor source accepts `weather.*` (reads the `temperature` attribute) or `sensor.*`; a value whose unit is not °C is rejected with a logged warning (no °F conversion — metric installation; loud failure instead of silent conversion code); valid reads of live + backup both feed the estimate window | 2/5 | same pattern as the zone backup sensor | an imperial installation appears |
| 15 | Notification channel + language: (a) `persistent_notification` with title/message from translations (`async_get_translations`, hu + en) or (b) repair issue (translated `issues` category, stable id, deleted on recovery) — **DECIDED by Gábor: (a)**; texts live in the `exceptions` translation category (hassfest-valid) | — | `strings.json` has no category for it today | — |

## Settings (new)
Common (all optional, read with `.get` defaults): `limp_radiator_on_min` 10 · `limp_radiator_period_min` 60 · `limp_underfloor_on_min` 40 · `limp_underfloor_period_min` 180 · `limp_outdoor_cutoff` 15.0 °C (empty = disabled) · `outdoor_backup_sensor` (entity selector, domains `weather` + `sensor`; empty = none).
Zone (all optional): `backup_sensor`, `backup_sensor_offset` (°C, default 0), `limp_on_min` + `limp_period_min` (override the mode profile).
Validation: `0 <= on <= period`, period 10–720, integers; form-level `errors` with translated keys (create + options flows, common + zone); invalid stored values → logged + defaults (pattern of `_stale_timeout_from`). Optional fields use `suggested_value`, not `default`; `_save_and_exit` and the create flow explicitly remove cleared keys (cut-off "empty = disabled", override "empty = inherit", backup sensors).

## Tasks (each: code + the tests it affects + green CI on the feature branch)

### Task 0 — #22 relay `unavailable` (own commit)
- `_relay_state_changed`: ignore transitions where old/new state is `unavailable`/`unknown` (no override, no boiler release).
- On recovery (`unavailable/unknown → on/off`): if the zone has a decision basis (`_current_temp` set or `_sensor_fault` set), push its wanted state (`_is_heating`) to the relay; otherwise a recovery to `on` is adopted like the startup takeover (`_is_heating = True`, boiler `turn_on`). Genuine on↔off changes still count as manual override.
- Per-relay `unavailable_since`: initialised at setup from the current state, set on entering a bad state, cleared on leaving; exposed as attribute `relay_unavailable` (not `relay_fault`).
- End of `async_added_to_hass`: if not heating and the zone name is in `boiler.get_active_zones()`, call `boiler.turn_off` (stale membership left by a reload).
- Tests: unavailable → no override/boiler untouched; return "on" while zone wants off → turned off; return "off" while zone wants on → turned on; unavailable at setup then "on" before the first reading → taken over, not switched off; unavailable at setup → `unavailable_since` set; genuine manual toggle still detected; timestamp set/cleared; stale boiler membership released after reload; a CI test documents what `switch.*` does for an unavailable entity.

### Task 1 — `sensor_health.py` (shared helpers; behaviour-preserving extraction)
- `sensor_problem(hass, entity_id, stale_timeout, bad_since, now) -> (problem, new_bad_since)` extracted from `_sensor_problem` (keeps `last_reported` getattr fallback, `SENSOR_BAD_STATES`, grace); `_sensor_problem` keeps its callers via the returned `bad_since`. Backup gets its own `_backup_bad_since`.
- `outdoor_multiplier(outdoor_temp)`; `_get_effective_hysteresis` calls it.
- `effective_outdoor(hass, live_id, backup_id, window, now) -> (temp, source)`, `source` in `live`/`backup`/`estimate`/`none`, plus `OutdoorWindow` (add valid sample, 24 h window ending at the last sample, min with the ≥3 samples / ≥12 h / ≤7 days rules). Weather-entity read (`temperature` attribute, °C only) lives here.
- `group_overview(hass, entity_ids)`: groups by entity-registry `platform` + `config_entry_id` (verify attribute names in CI), counts bad/total per group.
- Success: `tests/test_failsafe.py` unchanged and green; helper unit tests (incl. stale via `last_reported`, non-°C weather rejected).

### Task 2 — constants, settings plumbing, flows, translations, common reload
- `const.py`: new keys/defaults/bounds, `LIMP_OUTDOOR_MAX_AGE`.
- `__init__.py`: update listener on the common entry: reload every zone entry in state `LOADED`, one at a time (awaited), each in `try/except Exception` + `_LOGGER.exception`, then one info line with the count; never the common entry.
- `boiler_manager.py`: warning log when `turn_on` receives a boiler entity different from the registered one.
- `climate.py` `async_setup_entry`: read common + zone values, resolve effective (on, period): zone override → mode profile → default.
- `config_flow.py` / `options_flow.py`: new fields (create + options), `errors`, `suggested_value`, explicit key removal.
- `strings.json`, `translations/en.json`, `translations/hu.json`: labels, descriptions, error keys (hu informal "te", no Hunglish).
- Tests: validation errors; cleared optional fields remove keys; resolution order; a common limp change reaches a running zone; one zone whose reload raises does not stop the others; boiler mismatch logs a warning.

### Task 3 — watchdog restructure + backup sensor
- `_watchdog`: per-tick chain (primary → backup → limp) inside `try/except Exception` + `_LOGGER.exception` (zone, stage); `_retry_failed_commands` in its own guarded call every tick regardless. Extract `_enter_fault_episode()` / `_end_fault_episode()` used by `_watchdog` and `_sensor_changed`.
- One `_apply_reading()` (overheat check → `_auto_heat_restart` → `_evaluate_heating`) used by the primary and backup paths; listener bodies guarded like the watchdog.
- Backup listener via `async_on_remove`; `_backup_bad_since` initialised at setup; `_sensor_source` (`primary`/`backup`); backup healthy → `_current_temp = backup + offset`, then `_apply_reading()`.
- No healthy backup → off (until Task 4).
- Tests: backup takes over / primary returns; backup bad too; offset; flapping; both recovery paths; injected exception in chain evaluation is logged and a failed relay command is still retried; after a reload one backup event causes exactly one command.

### Task 4 — limp mode
- `_limp_wanted()` per tick while fault and no healthy backup:
  - HVAC OFF → off; any door/window `on` → off;
  - `effective_outdoor(...)`: value ≥ cut-off → off; value → on-minutes × `outdoor_multiplier` (rounded, clamped to period); `none` → ×1.0, no cut-off; logged with its `source`;
  - the zone feeds `OutdoorWindow` from listeners (via `async_on_remove`) on the outdoor sensor AND the backup source whenever configured (independent of `adaptive_hysteresis_enabled`);
  - phase from `dt_util.now()`; on iff phase < effective on-minutes; applied through existing `_set_heating(...)`.
- `_current_temp` stays `None` in limp. Door closing during limp: resumes next tick.
- Update every test pinning "fault = off" (`tests/test_failsafe.py:92-122`, `125-138`, `212-223`): pin the freezer to a known phase or set zone override 0 where the test is about "off"; every new fault test pins its phase relative to local midnight.
- Log one line per limp decision change (on/off, reason, on-minutes, outdoor value, multiplier).
- Tests: ON/OFF phases, boundaries, override beats profile, duty 0 = off, radiator vs underfloor, cut-off, each multiplier band, outdoor chain (live → backup `weather.*` → estimate → none; each level's bad/stale fallthrough; estimate rules: <3 samples, <12 h span, >7 days, freezing window in a multi-day outage, min of a day/night swing), HVAC OFF, open door, restart mid-fault (limp starts only after the fault is declared), limp↔backup↔primary both ways, relay failure retried, boiler started once for two zones in the same phase.

### Task 5 — event, notifications, attributes (needs decision 15)
- Event `smartheatzones_failsafe` on every state change (`backup`/`limp`/`recovered`): zone, cause, `group_overview`, unavailable relays. Notification per cause per zone (sensor, relay) created/replaced, dismissed on recovery; all of a zone's ids dismissed on entity setup. Notifier in `except Exception` + `_LOGGER.exception`; never raises.
- Attributes: `sensor_fault`, `sensor_source`, `limp_active`, `limp_on_minutes`, `limp_period_minutes`, `outdoor_source`, `relay_unavailable`.
- Relay unavailable > 15 min while heating is wanted → relay notification.
- Tests: per-state-change notification/event incl. `backup → limp` in one episode; payload; dismiss on recovery and on setup; sensor recovery leaves the relay notice; notifier failure does not break control; translated text (hu/en).

### Task 6 — docs (English)
- `docs/configuration.md`, `docs/advanced-features.md`, `docs/troubleshooting.md`: fallback chain, settings, event/attributes, GlowStat note, restart pre-fault window, phase jump for periods not dividing 1440, door-close resume.
- Rewrite `advanced-features.md:137-143`: `sensor_fault` no longer means "heating off" (backup = normal control, limp = open-loop); automations should use `sensor_source` / `limp_active` / the event; attributes are authoritative, events are transitions only; during limp a manual relay switch is reverted within a minute.
- Changing the boiler switch in common settings requires a HA restart; after a common-settings change the outdoor estimate starts empty.
- Hardware-side protection: a relay left ON while HA/wifi is down is outside software control — use the device's safe default state/auto-off where available.

## Out of scope
Network-group detection in the control path; notify-service configuration; outdoor handling inside adaptive hysteresis (stale cached value pre-existing); version bump/changelog; boiler relay unavailable/recovery handling (own issue, sibling of #22); `_trigger_piggyback_heating` iterating a live dict (own issue).

## Simplification pass (rung 5, after the critique rounds)
Removed as scope creep: °F conversion for weather entities (decision 14), `limp_next_change` attribute. Kept despite size, each tied to a stated goal: relay `unavailable_since` + relay notification (wifi-outage visibility), stale boiler-membership release (reloads become frequent through decision 12), per-cause notification ids, sequential isolated zone reload.

## Risks accepted
- Limp is open-loop: no overheat protection without a reading; bounded only by the configured duty. Summer + outdoor sensor dead → limp heats at nominal duty.
- A relay stuck ON during a wifi/HA outage cannot be fixed in software.
- After a HA restart with a dead sensor, up to the silence limit passes before the fault is declared.

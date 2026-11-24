# Heating Overview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An overview entity in SmartHeatZones (`sensor.smartheatzones_overview`) and a GlowStat card (`glowstat-heating-card`) that shows the whole house: boiler, zones, reasons, timelines, health, quick actions.

**Architecture:** SmartHeatZones adds a pure decision module, boiler counters, a per-zone snapshot, and one aggregating sensor entity that is created by the common-settings entry. GlowStat adds one card that reads only that entity plus history. The data shape is a versioned contract (`schema: 1`).

**Tech Stack:** Home Assistant custom integration (Python 3.14, pytest-homeassistant-custom-component) in `/home/gabor/Development/2_HomeAssistant/SmartHeatZones`; GlowStat vanilla JS bundle built by `build.sh`, tests with `node --test` + jsdom in `/home/gabor/Development/2_HomeAssistant/ha-GlowStat`.

**Spec:** `docs/superpowers/specs/2026-11-21-heating-overview-design.md` (SmartHeatZones #27, GlowStat #3). **Precondition:** the afterheat work is finished and the suite is green (99 passed at plan time); it is uncommitted in the working tree and this plan builds on it (`boiler_manager.py`, `climate.py`, `const.py`). Work on the current branch of each repo, no worktrees. Line numbers in this plan are hints only; symbols are authoritative. No commit or push without Gábor's request. SmartHeatZones test env: `/tmp/claude-1000/-home-gabor-Development-2-HomeAssistant-SmartHeatZones/68c6a4fe-cf33-4fc8-a16f-dbf571faa616/scratchpad/venv/bin/pytest` (absolute path; if it is missing, rebuild with `python3.14 -m venv <dir> && <dir>/bin/pip install -r requirements_test.txt`); GlowStat: `npm test` after `./build.sh` (needs `node_modules`, present).

## Decision Log

| # | Fork | Chosen | Deciding rung | Claim it rests on (verified) | Reverses if false |
|---|------|--------|---------------|------------------------------|-------------------|
| D1 | Data source of the card | One overview entity, not per-zone attributes | 3 and 5 | Zones are reachable via `BoilerManager.get_zone_entities()` (`BoilerManager.get_zone_entities`); sensor health via `group_overview` (`sensor_health.py`) | The entity limit of one common entry becomes a problem |
| D2 | Entity ownership | Created by the common entry through a `sensor` platform; `PLATFORMS` for zones stays `["climate"]` | 3 | The common branch of `async_setup_entry` forwards no platform today. The common entry can be reloaded or disabled from the UI (`async_unload_entry` exists), unload and setup are symmetric and the BoilerManager persists in `hass.data` | Zones need the overview while the common entry reloads |
| D3 | Reason format | `{code, ...params}`, no display text | 3 (GlowStat already owns hu/en texts, `src/common.js` `GS_I18N`) | The card translates all other texts the same way | A third consumer needs integration-side text |
| D4 | Counters | In memory, reset at local midnight, plus `counters_since` (ISO) in `boiler`, shown by the card as "since HH:MM" when later than local midnight (**Gábor may veto**: the spec accepted "restart resets") | 2 (a silently low "today" is wrong data) | `BoilerManager` is created once per run | "Today" must survive restarts (then RestoreEntity) |
| D5 | Refresh | Zone state changes and boiler changes schedule one refresh, coalesced to at most one per second, plus a 60 s interval | 5 | Zones already `async_write_ha_state()` on every change | A change is missed (the 60 s interval bounds it) |
| D7 | How the overview learns of zone changes | A `@callback` event filter on `hass.bus.async_listen(EVENT_STATE_CHANGED, ...)` that takes `event_data` (HA passes the data dict, not the `Event`) and looks the zone entity ids up at event time; `register_zone_entity`/`unregister_zone_entity` also notify the boiler listeners (a zone unregisters before its state is removed); plus a 60 s interval | 1 | Zones register in the climate entity's `async_added_to_hass`, after the common entry loaded; `async_will_remove_from_hass` runs before the state removal | — |
| D8 | Source of `boiler.entity` | The manager's `_boiler_entity_id` when registered, else `_get_common_settings(hass)` from `climate.py` (options before data) | 1 | The options flow writes `options` (`options_flow.py` `async_update_entry(..., options=...)`); the manager holds the switch actually controlled and a changed boiler needs a restart | The manager re-registers on a settings change |
| D9 | History shapes in the card | Zones: attribute history (no `no_attributes`/`minimal_response`), `attributes.hvac_action === 'heating'`; boiler switch: state `on`; ETA: separate numeric sensor history; no statistics path for the timeline | 1 | A climate entity's state is the HVAC mode, `hvac_action` is an attribute (`climate.py` `hvac_action`); the thermometer card's request drops attributes and parses numbers (`src/thermometer-card.js` ~229-232) | The integration exposes a heating binary sensor |
| D10 | Time-varying values on climate attributes | Climate gets only `reason` and without `next_in_min`; `next_change` and the limp countdown live only in the overview | 1 | The watchdog writes every zone's state every minute (`_watchdog`); an unchanged write fires no `state_changed`, a changing attribute would fire one per zone per minute (recorder rows, user automations) | — |
| D11 | Overview build failure | One guarded `_build()` for the first build and refreshes: `_LOGGER.exception`, `_attr_available = False`; the next good build restores it | 2 | The card renders `h_unavailable` | — |
| D12 | Clock for `next_change` | `datetime.now()` like `_apply_current_schedule_block`; limp countdown with `dt_util.now()` like `_limp_decision` | 1 | HA does not set the OS time zone; the test harness uses US/Pacific, so tests build times with `dt_util.get_default_time_zone()` | The schedule control moves to `dt_util` (separate issue) |
| D6 | Overview `state` | `on` when `boiler.running`, else `off` | 5 | `has_real_demand`/`get_active_zones` exist (`boiler_manager.py`) | Users want a numeric state |

## Global Constraints

- Contract is `schema: 1`; unknown future fields must not break the card (the card ignores what it does not know and shows a hint if `schema` is newer than it supports).
- Reason codes (exact): `needs_heat`, `holding`, `afterheat`, `in_band`, `target_reached`, `door_open`, `hvac_off`, `no_reading`, `overheat`, `limp_heating`, `limp_waiting`.
- Reason params: `on_below`, `off_above`, `target`, `next_in_min` (only where meaningful), all °C / minutes.
- `next_change` object `{at: "HH:MM", in_min: int, temp: float, label: str}` or `null`; only in preset `auto` with a valid schedule.
- Counters: `starts_today` (a logical start: the first active zone while none was active), `runtime_today_s` (time with at least one active zone, closed at midnight), `afterheat_joins_today` (a zone newly joining with `afterheat=True`).
- New files in SmartHeatZones: `decision.py`, `overview.py`, `sensor.py`. Code and comments English; error visibility: every `except` logs with `_LOGGER.exception`.
- Translations for the card: hu + en, same keys (`GS_I18N`). SmartHeatZones needs no new translation (entity name is fixed text; no config strings).
- GlowStat card options: `entity` (required), `history_hours` (default 24, 1-72), `show_timeline`, `show_eta`, `show_actions` (all default true), `language`.
- Do not change the climate card here (its hint bug is GlowStat #2).
- The version/changelog bump in both repos is a separate `/update-version-changelog` run.

## Review Focus

- Zero zones, one zone, a zone being removed while the overview refreshes: no crash, the entity stays available (Task 4).
- A zone without a boiler entity or without a reading: the zone object still has every key (`null` values), never a missing key (Task 3, 4).
- Counters at the midnight rollover and with a zone that joins and releases in the same second (Task 2).
- `next_change` for a schedule period that spans midnight and for preset `manual` (Task 1).
- The card with an overview entity that is `unavailable`/missing, an older `schema`, a zone without history (Tasks 6-8).

---

### Task 1: Pure decision helpers (SmartHeatZones)

**Files:**
- Create: `custom_components/smartheatzones/decision.py`
- Test: `tests/test_decision.py`

**Interfaces:**
- Produces:
  - `decision_reason(*, hvac_off: bool, no_reading: bool, door_open: bool, overheat: bool, limp_active: bool, limp_heating: bool, limp_next_in_min: int | None, heating: bool, joined: bool, current: float | None, target: float, on_below: float, off_above: float) -> dict`; `target` is always the zone's ADJUSTED target (the control compares against it), and so are `on_below`/`off_above` returning `{"code": str, ...params}`. Priority: `hvac_off`, `door_open`, `limp_*` (when `limp_active`), `no_reading`, `overheat`, then heating (`afterheat` if `joined`, `holding` if `current >= target`, else `needs_heat`), then idle (`target_reached` if `current >= target`, `in_band` if `current >= on_below`, else `needs_heat`). Params: `holding` -> `off_above`; `in_band` -> `on_below`, `target`; `target_reached` -> `target`; `limp_waiting` -> `next_in_min`. The caller passes `limp_next_in_min=None` and `limp_heating=False` when limp is not active.
  - `next_schedule_change(schedule: list[dict], now: datetime) -> dict | None` returning the `next_change` object. `schedule` blocks have `start`, `end` (`"HH:MM"`), `temp`, optional `label`. The next change is the nearest period start strictly after `now`, wrapping to tomorrow; a block with `start == end` or a malformed block is skipped; returns `None` for an empty or fully invalid schedule or a single period that covers the whole day.

- [ ] **Step 1: Write failing tests** in `tests/test_decision.py` (plain functions, no hass): one test per reason code with its params asserted exactly (e.g. idle at 20.7 with `on_below=20.5, target=21`: `{"code": "in_band", "on_below": 20.5, "target": 21.0}`); priority tests (`hvac_off` beats `door_open`; `door_open` beats `limp_active`; `door_open` beats `overheat`); `next_schedule_change` for: two periods and `now` between them (`at` equals the later start, `in_min` correct); `now` after the last start of the day (wraps to the first start tomorrow, `in_min` > 0); a period spanning midnight (22:00-06:00); empty schedule `None`; malformed block skipped.
- [ ] **Step 2: Run** `/tmp/claude-1000/-home-gabor-Development-2-HomeAssistant-SmartHeatZones/68c6a4fe-cf33-4fc8-a16f-dbf571faa616/scratchpad/venv/bin/pytest tests/test_decision.py -q`. Expected: FAIL (import error).
- [ ] **Step 3: Implement** both functions in `decision.py` (pure, no Home Assistant imports; `float()` the temperatures; use `datetime.strptime(...)` like `climate.py:1228` for `"HH:MM"`).
- [ ] **Step 4: Run** the same command. Expected: PASS.

### Task 2: Boiler counters and listener (SmartHeatZones)

**Files:**
- Modify: `custom_components/smartheatzones/boiler_manager.py`
- Test: `tests/test_boiler_counters.py`

**Interfaces:**
- Produces on `BoilerManager`:
  - `add_listener(cb: Callable[[], None]) -> Callable[[], None]` (returns the remover); listeners are called (sync, exceptions logged and swallowed) after every `turn_on`/`turn_off` that changes membership, `held_by` or `afterheat_zones` (and on `register_zone_entity`/`unregister_zone_entity`.
  - `stats(now: datetime | None = None) -> dict` returning `{"running": bool, "since": str | None (ISO), "held_by": list[str] (active minus afterheat, sorted), "afterheat_zones": list[str] (sorted), "starts_today": int, "runtime_today_s": int, "afterheat_joins_today": int, "failed_action": str | None, "counters_since": str (ISO: manager creation or the last local midnight, whichever is later)}`; `runtime_today_s` includes the running period up to `now`.
  - Counters roll over when the local date (`dt_util.now()`) changes, checked on every `turn_on`, `turn_off` and `stats` call; a period that runs across midnight is split (the running period restarts at 00:00).
- Consumes: existing `turn_on(entity_id, zone, afterheat=False)`, `turn_off`, `has_real_demand`.

- [ ] **Step 1: Write failing tests** (freezer + `boiler = hass.data[DOMAIN][DATA_BOILER_MAIN]` after `setup_zone`, switches mocked):
  - first `turn_on` of a zone: `starts_today == 1`, `running`, `since` set; a second zone joining: still 1.
  - last `turn_off`: `running` False; `runtime_today_s` equals the elapsed seconds after `freezer.tick`.
  - `afterheat=True` join increments `afterheat_joins_today` once; calling `turn_on(..., afterheat=True)` again for the same zone does not.
  - midnight: running across 23:59 -> 00:01 gives `runtime_today_s == 60` and `starts_today == 0` on the new day; `stats()` is consistent when called with no events in between.
  - bookkeeping runs synchronously right after the membership change and before any await, in its own `try/except` with `_LOGGER.exception`: a patched bookkeeping failure still sends the boiler `turn_on`
  - `register_zone_entity` and `unregister_zone_entity` each notify the listeners once
  - `failed_action` shows a failed boiler command (patch `_call_boiler_service` to fail) and `counters_since` is later than local midnight after a restart-like creation
  - midnight tests build their times with `dt_util.get_default_time_zone()`
  - a listener is called once per membership change and once when a joined zone becomes real demand (`turn_on(..., afterheat=False)` on an active afterheat zone), and a raising listener does not stop the others nor `turn_on`.
- [ ] **Step 2: Run** `/tmp/claude-1000/-home-gabor-Development-2-HomeAssistant-SmartHeatZones/68c6a4fe-cf33-4fc8-a16f-dbf571faa616/scratchpad/venv/bin/pytest tests/test_boiler_counters.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** State: `_since: datetime | None`, `_runtime_s: float`, `_starts: int`, `_afterheat_joins: int`, `_counter_day: date`, `_listeners: list`. Keep the existing control flow untouched; counters are bookkeeping around it.
- [ ] **Step 4: Run** the new file and the whole suite `pytest tests -q`. Expected: PASS.

### Task 3: Zone snapshot, reason and next change (SmartHeatZones)

**Files:**
- Modify: `custom_components/smartheatzones/climate.py` (`_limp_decision` stores `self._limp_effective_on`; new `overview_snapshot()`; `extra_state_attributes` adds only `"reason"`, computed inside try/except with `_LOGGER.exception` (`None` on failure) and without `next_in_min`; a new `_door_open()` used only by the new code)
- Test: `tests/test_zone_snapshot.py`

**Interfaces:**
- Consumes: `decision_reason`, `next_schedule_change` (Task 1).
- Produces: `SmartHeatZoneClimate.overview_snapshot(self) -> dict` with exactly the `zones[]` keys of the spec: `name, entity_id, sensor_entity, heating_mode, hvac_mode, hvac_action, preset, current, target, adjusted_target, hysteresis, on_below, off_above, sensor_source, sensor_fault, limp {active, on_min, effective_on_min, period_min, next_in_min}, next_change, afterheat, joined, relay_unavailable, relay_fault, reason`. Every key is always present (`None` when unknown). `on_below = adjusted_target - hysteresis`, `off_above = adjusted_target + hysteresis`. `limp.next_in_min` is `None` when limp is not active or `_limp_effective_on is None`, `0` while the cycle is on, else `min(period - phase, minutes to local midnight)` using `dt_util.now()`. `_limp_effective_on` is set on every path of `_limp_decision` (`None` on the early returns for HVAC off, open door and the outdoor cut-off), so a stale value is never reported; `effective_on_min` is `None` then.

- [ ] **Step 1: Write failing tests** (`setup_zone`): idle zone in the band shows `reason == {"code": "in_band", ...}` in both the climate attributes and `overview_snapshot()`; cold zone `needs_heat`/`holding`; `afterheat` joined zone `afterheat`; sensor `unknown` -> `no_reading`; limp zone (`LIMP_OFF` -> `limp_waiting` with `next_in_min`, and with `CONF_LIMP_ON=60, CONF_LIMP_PERIOD=60` -> `limp_heating`) after the sensor was lost long enough; a zone with schedule and preset `auto` gets a `next_change` in `overview_snapshot()` with the later period's start (clock: `datetime.now()`), preset `manual` -> `None`; the climate attributes never contain `next_change`; a radiator-thermostat zone (offset 3.0) shows its reason against the adjusted target; a patched `decision_reason` that raises still lets the climate state be written and the error is logged; limp with the outdoor cut-off gives `next_in_min is None`; all keys present for a zone with no reading (`current is None`).
- [ ] **Step 2: Run** `/tmp/claude-1000/-home-gabor-Development-2-HomeAssistant-SmartHeatZones/68c6a4fe-cf33-4fc8-a16f-dbf571faa616/scratchpad/venv/bin/pytest tests/test_zone_snapshot.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** `overview_snapshot()` and the two attributes; compute `hysteresis` with `_get_effective_hysteresis()`; `limp.effective_on_min` from `self._limp_effective_on` (set where `on_minutes` is computed in `_limp_decision`, `None` until then); door-open via the new `_door_open()` (the three existing door loops stay untouched); `overheat = current is not None and current >= self._overheat_temp`.
- [ ] **Step 4: Run** the new file and `pytest tests -q`. Expected: PASS.

### Task 4: Overview entity (SmartHeatZones)

**Files:**
- Create: `custom_components/smartheatzones/overview.py` (`build_overview(hass, boiler, now) -> dict`), `custom_components/smartheatzones/sensor.py` (`async_setup_entry`, `OverviewSensor`)
- Modify: `custom_components/smartheatzones/__init__.py` (common entry creates the BoilerManager if missing, forwards `["sensor"]` and unloads it; the common unload pops `DATA_COMMON_SETTINGS` only after `async_unload_platforms` returned True and logs otherwise), `const.py` (`OVERVIEW_SCHEMA = 1`, `PLATFORMS_COMMON = ["sensor"]`, `OVERVIEW_REFRESH_INTERVAL = timedelta(seconds=60)`)
- Test: `tests/test_overview.py`

**Interfaces:**
- Consumes: `BoilerManager.stats`, `add_listener`, `get_zone_entities`; `SmartHeatZoneClimate.overview_snapshot`; `group_overview(hass, ids, stale_timeout, now)`.
- Produces: `build_overview(hass, boiler, now) -> dict` with keys `schema, updated, boiler {entity, + stats()}, zones (sorted by name), health {groups: {key: {"total", "bad"}}}`; `boiler.entity` comes from the common entry data (D8). `OverviewSensor` entity (`unique_id "smartheatzones_overview"`, `entity_id "sensor.smartheatzones_overview"`, state `"on"`/`"off"`, `extra_state_attributes` = the dict, `should_poll=False`). `health.groups` uses `group_overview` over every zone's diagnostic sensor ids with the largest zone silence limit; `bad_entities` is dropped from the output.

- [ ] **Step 1: Write failing tests**:
  - after `setup_zone(temp="23.0")` (warm, so no heat is requested) the entity exists immediately (no time advance) with `schema == 1`, one zone with the full key set, `boiler.entity == BOILER` (before any zone asked for heat), state `off`; with the boiler running (a zone heating) state `on`, `held_by == ["Living"]`.
  - a zone state change refreshes the entity within the coalescing time (`advance(hass, freezer, seconds=2)` from `tests/test_failsafe.py`); the 60 s interval refreshes without any event.
  - zero zones: only the common entry set up -> entity exists, `zones == []`, state `off`.
  - removing the zone entry: entity stays, `zones == []`, no exception.
  - `health.groups` lists the zone sensor group with `total`/`bad` and no `bad_entities`.
  - the entity is gone when the common entry is unloaded, and a common-entry reload leaves exactly one entity and `len(boiler._listeners) == 1`.
  - a preset change on a warm zone (no boiler membership change) refreshes the entity: the bus listener works on its own.
  - removing the zone entry gives `zones == []` after `advance(seconds=2)` (unregister notifies).
  - a patched `build_overview` that raises: the entity goes unavailable and the error is logged, the next good build recovers it.
  - D8 both branches: manager registered (its value), not registered (common settings, options before data, after an options change).
  - all earlier tests still pass (no lingering timers: the pending refresh handle is cancelled through `async_on_remove`).
- [ ] **Step 2: Run** `/tmp/claude-1000/-home-gabor-Development-2-HomeAssistant-SmartHeatZones/68c6a4fe-cf33-4fc8-a16f-dbf571faa616/scratchpad/venv/bin/pytest tests/test_overview.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** The `BoilerManager` is created in the common-entry branch of `async_setup_entry` (guarded by the existing `not in hass.data[DOMAIN]` check), before the `sensor` platform is forwarded; the zone path keeps its check. `OverviewSensor.async_added_to_hass`: build once and `async_write_ha_state()` immediately; `async_on_remove` for each of: `boiler.add_listener(self._schedule)`, `hass.bus.async_listen(EVENT_STATE_CHANGED, self._on_state, event_filter=...)` (a `@callback` filter taking `event_data`: `event_data["entity_id"] in {z.entity_id for z in boiler.get_zone_entities()}` evaluated at event time, D7), `async_track_time_interval(hass, self._refresh, OVERVIEW_REFRESH_INTERVAL)`. `_schedule()` sets a one-shot `async_call_later(hass, 1, self._refresh)` when none is pending, registers its cancel with `async_on_remove`, and clears the handle in `_refresh`; One guarded `_build()` serves the first build and `_refresh` (D11). `health.groups`: `group_overview` over the union of every zone's `_diagnostic_sensor_ids()` (all zones share the sensors; call it on any one zone, `{}` when there is no zone) with the largest `_sensor_stale_timeout` among the zones.
- [ ] **Step 4: Run** the new file and `pytest tests -q`. Expected: PASS (all earlier tests unchanged).

### Task 5: Integration docs (SmartHeatZones)

**Files:**
- Modify: `docs/advanced-features.md` (also `counters_since`, `failed_action`, and that the schedule control can apply a change up to 15 minutes after `next_change.at`; new "Overview entity" section: attributes, reason codes, counters and their restart reset, `next_change`), `docs/lovelace.md` (the new card, install via GlowStat >= 0.5.0), `docs/architecture.md` if it lists entities/files.

- [ ] **Step 1: Write the docs**: the contract table from the spec, the reason code list with one line each, "counters restart with Home Assistant".
- [ ] **Step 2: Run** `pytest tests -q`. Expected: PASS (no code change; guards against accidental edits).

### Task 6: Card core (GlowStat)

**Files:**
- Create: `src/heating-card.js`
- Modify: `build.sh` (`cat src/common.js src/thermometer-card.js src/climate-card.js src/heating-card.js`)
- Create: `tests/helpers.mjs` (move `boot`, `mkHass`, `tick`, `same` out of `tests/cards.test.mjs` and import them there too; no duplication)
- Test: `tests/heating-card.test.mjs`

**Interfaces:**
- Produces: custom elements `glowstat-heating-card` and `glowstat-heating-card-editor` registered with `customCards` like `src/common.js:196`; `GS_I18N` keys (hu + en) `h_title, h_boiler_on, h_boiler_off, h_since, h_held_by, h_starts, h_runtime, h_afterheat_joins, h_entity, h_next, h_now, h_src_primary, h_src_backup, h_src_limp, h_chip_afterheat, h_unavailable, h_schema_new, h_other` and reason texts `r_needs_heat, r_holding, r_afterheat, r_in_band, r_target_reached, r_door_open, r_hvac_off, r_no_reading, r_overheat, r_limp_heating, r_limp_waiting` with `{x}` style placeholders handled by one `h_reason(zone)` function; `setConfig` requires `entity`; `getCardSize()`; `getStubConfig(hass)` picks `sensor.smartheatzones_overview` when present.
- Renders from the overview state: header (boiler on/off with duration, starts/runtime/afterheat joins today, `held_by` with afterheat zones marked), zone rows (name, `current -> target`, distance bar with `on_below`/`off_above` ticks, source chip, translated reason, `next_change` line "-> 22° at 17:00"), a rows-with-fault marker (red marker also for `boiler.failed_action`; "since HH:MM" when `counters_since` is later than local midnight (`h_boiler_failed`, `h_counters_since`); red only for `relay_fault` non-empty; sensor source `backup`/`none` is a neutral/amber chip).

- [ ] **Step 1: Write failing tests**: header shows boiler on/off, counters and `held_by`; one row per zone with the translated reason for each of the 11 codes (parametrised, hu and en); the `in_band` row text contains the `on_below` value; `next_change` line; source chip texts for `primary` (no chip), `backup`, `none`; red class only with `relay_fault`; entity `unavailable`/missing -> a neutral hint, no exception; `schema: 2` -> hint plus rows still render known fields; `setConfig` without `entity` throws.
- [ ] **Step 2: Run** `./build.sh && npm test`. Expected: the new tests FAIL (element not defined).
- [ ] **Step 3: Implement** following `src/climate-card.js` structure (shadow DOM, render signature to skip identical renders, the editor with `ha-form` and `computeLabel` through `gsT`). Escape all strings with the shared helper from `src/common.js`.
- [ ] **Step 4: Run** `./build.sh && npm test`. Expected: all PASS (the 2 old test groups unchanged).

### Task 7: Timeline and time-to-target (GlowStat)

**Files:**
- Modify: `src/heating-card.js`, `tests/heating-card.test.mjs`

**Interfaces:**
- Produces: `gsHeatSegments(history: Array<{state, last_changed}>, from: number, to: number) -> Array<{start, end, on: boolean}>` (`on` is decided by the caller as above) and `gsEta(points: Array<{t: number(ms), v: number}>, target: number, now: number) -> number | null` (minutes, `null` unless: at least 6 points over at least 20 minutes, slope between 0.2 and 6 °C/h, current below `target`, result at most 480). Both are pure and tested through the rendered card output.
- Consumes: `hass.callApi('GET', 'history/period/<start>?filter_entity_id=...&end_time=...&significant_changes_only=0')`. Zones: with attributes (no `no_attributes`, no `minimal_response`), on = `attributes.hvac_action === 'heating'`. Boiler switch: on = state `on`. ETA: a separate numeric request for the sensor (`minimal_response&no_attributes`, like `src/thermometer-card.js`). No statistics path for the timeline, whatever `history_hours` is (1-72). Zone `entity_id`, `sensor_entity`, `boiler.entity` come from the overview.

- [ ] **Step 1: Write failing tests** (mock `callApi` with `extra.history`): a timeline bar per zone and one for the boiler, segments proportional to a known history; no history -> no bar, no error; ETA text `~25 min` for a clean linear rise only on a heating zone; no ETA when flat, falling, too few points, or not heating; `show_timeline: false` and `show_eta: false` hide them; history is requested once per `history_hours`, not on every render (count `api` calls across two `hass` updates).
- [ ] **Step 2: Run** `./build.sh && npm test`. Expected: the new tests FAIL.
- [ ] **Step 3: Implement** segments and ETA (least-squares slope over the last 60 min of the sensor history; cache per entity for 5 minutes).
- [ ] **Step 4: Run** `./build.sh && npm test`. Expected: all PASS.

### Task 8: Health line, quick actions, live flash, docs (GlowStat)

**Files:**
- Modify: `src/heating-card.js`, `tests/heating-card.test.mjs`, `README.md`, `CHANGELOG.md` is NOT touched (release step), `docs/` text in README only

**Interfaces:**
- Consumes: `health.groups` (key `"platform/entry-id"`), the zones' `entity_id`s, `hass.connection.subscribeEvents(cb, 'smartheatzones_failsafe')` (returns a Promise of the unsubscribe function).
- Produces: a health line per group `"<platform> N/M ok"` or `"<bad> of <total> silent"` (amber when `bad > 0`); buttons "All away" and "All eco" calling `climate.set_preset_mode` for every zone entity (`preset_mode: 'away'` / `'eco'`) with a visible failure message on error (reuse the climate card's `set_failed` text); the buttons are hidden with `show_actions: false`; on a `smartheatzones_failsafe` event the row whose `name` equals `event.data.zone` gets a flash class for 6 s; the subscription is created lazily when `hass.connection` is first available (from the `hass` setter, not only `connectedCallback`), at most once; `disconnectedCallback` unsubscribes, also when the Promise resolves after the disconnect (late unsubscribe). Health keys: split `"<platform>/<entry>"` at the first `/`; the key `"unregistered"` has no slash and is shown as "other sensors" (`h_other` text). A rejected `subscribeEvents` Promise gets a `.catch` with one `console.warn` (event subscription needs an admin user; documented in the README) and no flash. The quick actions fire all calls with `Promise.allSettled` and the failure text names the failed zones.

- [ ] **Step 1: Write failing tests**: health line text for 5/5 and 2/5 bad; the two buttons call `climate.set_preset_mode` once per zone with the right presets (assert `calls`); `show_actions: false` hides them; a failing service call shows the failure text; a fake `hass.connection.subscribeEvents` receives the callback, an event flashes the named row, removal unsubscribes (assert the returned unsubscribe function ran); a hass without `connection` does not throw, and a connection that appears later subscribes then; a Promise that resolves after `disconnectedCallback` is unsubscribed immediately; the health key `unregistered` renders; a rejecting `subscribeEvents` warns once and does not throw; one zone failing in the quick action still calls the others and names the failed one.
- [ ] **Step 2: Run** `./build.sh && npm test`. Expected: the new tests FAIL.
- [ ] **Step 3: Implement** the three features and the README section for the new card (options table like the other cards, requires SmartHeatZones >= 1.14.0, screenshot placeholder not added).
- [ ] **Step 4: Run** `./build.sh && npm test`; in SmartHeatZones `/tmp/claude-1000/-home-gabor-Development-2-HomeAssistant-SmartHeatZones/68c6a4fe-cf33-4fc8-a16f-dbf571faa616/scratchpad/venv/bin/pytest tests -q`. Expected: all PASS in both repos.
- [ ] **Step 5: Do not commit.** Report both repos' state to Gábor; version/changelog is a separate step; the browser check against a real Home Assistant is NOT done and must be stated as unverified.

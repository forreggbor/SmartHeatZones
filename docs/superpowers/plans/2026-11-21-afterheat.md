# Afterheat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A zone with the new `afterheat` option joins a running boiler as soon as it is below its target, and leaves by the normal hysteresis rule.

**Architecture:** The zone decides locally. `_evaluate_heating` gets one extra branch in the radiator hysteresis band; the one-minute watchdog re-evaluates idle afterheat zones while the boiler runs. The boiler manager is unchanged (its `get_active_zones()` is the "boiler running" signal).

**Tech Stack:** Home Assistant custom integration (Python 3.14 in CI), pytest-homeassistant-custom-component.

**Spec:** `docs/superpowers/specs/2026-11-21-afterheat-design.md` (issue #25). Work on `master`, no worktrees. No commit or push without Gábor's request.

## Decision Log

| # | Fork | Chosen | Deciding rung | Claim it rests on (verified) | Reverses if false |
|---|------|--------|---------------|------------------------------|-------------------|
| D1 | Who decides entry | Zone-local in `_evaluate_heating` plus the 1-minute watchdog (`WATCHDOG_INTERVAL`, `const.py:198`); not a boiler-manager sweep | 3 (fits the existing zone-driven pattern) and 5 | `_evaluate_heating` already runs on every reading; the manager has no zone-sweep hook other than the start-time piggyback | A sub-minute entry becomes a requirement |
| D2 | "Boiler running" | `has_real_demand()` (new, built on `_active_zones`, `boiler_manager.py:191`), not the relay state | 3 | `turn_on` calls the switch only when `was_off` (`boiler_manager.py:101-107`). Known limit: a zone removed while heating stays a member until restart (`climate.py:495-502`; issue #26); afterheat zones then see a permanently running boiler | #23 is fixed, or #26 stays unfixed |
| D3 | Who counts as a starter | Only a zone with real demand. A zone that joined by afterheat is marked at the boiler manager and does not count; the mark is cleared when the zone's own rule wants heat (`diff > hysteresis`). Decided by Gábor (replaces the earlier "any heating zone counts") | 1 (no zones holding the boiler for each other) | Chaining was possible: each episode ends at target + hysteresis (`climate.py:1303-1306`) but two afterheat zones could re-enter for each other | A real starter is never recognised (then no zone ever joins) |
| D4 | Watchdog re-evaluation scope | Only while `has_real_demand()`; full `_evaluate_heating` | 1 | Ungated, the normal rule would run every minute for every afterheat zone and revert a manual relay switch-off (`docs/advanced-features.md:123-124,145`). Gated, a manual switch-off of an afterheat zone below target is reverted within a minute while the boiler runs (same class as limp, `docs/advanced-features.md:165`). **Gábor confirms** | Gábor rejects the in-run revert |
| D5 | Explicit limp / underfloor guard | None | 5 | Limp sets `_current_temp = None` (`climate.py:946-948`), so `_evaluate_heating` returns early; underfloor hysteresis is 0 (`climate.py:1132-1133`) and its branch already heats below target | Limp keeps a temperature, or underfloor gets a hysteresis |

## Global Constraints

- Option key `afterheat`, boolean, default `False`; per zone only.
- Entry: current < adjusted target (no hysteresis). Exit: the unchanged normal rule (target + effective hysteresis; underfloor: target).
- Entry/watchdog condition is "real demand": `self._boiler.has_real_demand()`, i.e. at least one active zone that did not join by afterheat. The relay's physical state is not read. A zone that entered by the existing piggyback counts as real demand (unchanged behaviour).
- A joined zone keeps heating to its own target even after the starter stopped; the boiler then runs for it alone.
- Existing piggyback (`check_piggyback_heating`, `_trigger_piggyback_heating`) stays unchanged.
- Limp mode never joins (a zone in limp has `_current_temp is None`, so `_evaluate_heating` already returns early).
- Underfloor: no different threshold, only the gated one-minute re-check (D4, D5). State this in the docs.
- The new `afterheat` keys must exist in `strings.json`, `translations/en.json`, `translations/hu.json`, in the same four places each (config step `data` and `data_description`, options step `data` and `data_description`, next to `sensor_stale_hours`). `strings.json` carries the Hungarian text like today. The files already differ by `config.abort.unknown` and `config.abort.zones_exist` (only in `strings.json`): leave that. New texts have no leading/trailing spaces (hassfest).
- Code and comments in English. Error visibility: log the join with `_LOGGER.info` (zone, current, adjusted target, active zones).

## Review Focus

- Target reached while the starter still runs: zone leaves at target + hysteresis, boiler stays for the starter (test in Task 1).
- Starter stops first: afterheat zone keeps heating and keeps the boiler on (test in Task 1).
- Door/window open, HVAC off, no reading, limp: no join (tests in Task 1).
- Boiler running only because of another afterheat zone: joins too (accepted in spec; test in Task 1).
- Join never starts the boiler: no `switch.turn_on` on BOILER (test in Task 1).
- Boiler idle: the watchdog does not re-evaluate, a manual switch-off stays (test in Task 1).
- Option saved as `False` or absent on an existing zone: unchanged behaviour (test in Task 1).

---

### Task 1: Zone logic

**Files:**
- Modify: `custom_components/smartheatzones/const.py` (add `CONF_AFTERHEAT = "afterheat"`, `DEFAULT_AFTERHEAT = False`, next to `CONF_SENSOR_STALE_HOURS`)
- Modify: `custom_components/smartheatzones/climate.py` (`async_setup_entry` reads the option; `__init__` stores `self._afterheat`; `_evaluate_heating` radiator branch ~line 1295; `_watchdog` ~line 1020; `extra_state_attributes` gets `"afterheat": self._afterheat`)
- Modify: `custom_components/smartheatzones/boiler_manager.py` (`turn_on(self, entity_id, zone, afterheat: bool = False)` adds the zone to a new `self._afterheat_zones` set when `afterheat`, discards it otherwise; `turn_off` discards it; new `has_real_demand(self) -> bool` returns `bool(self._active_zones - self._afterheat_zones)`)
- Test: `tests/test_afterheat.py`

**Step 0 (once): test environment.** HA is not installed locally. Create a venv outside the repo: `python3.14 -m venv $SCRATCH/venv && $SCRATCH/venv/bin/pip install -r requirements_test.txt` (`$SCRATCH` = the session scratchpad). All red/green steps use `$SCRATCH/venv/bin/pytest`. Without it the steps are unverified; say so, never imply green.

**Interfaces:**
- Consumes: `setup_zone(hass, temp, relay, zone_extra, common_extra)` and `commands`, `advance`, `LIMP_OFF` from `tests/test_failsafe.py`; `hass.data[DOMAIN][DATA_BOILER_MAIN]` (the boiler manager; tests mark it running with `boiler._active_zones.add("Other")` and release with `await boiler.turn_off(BOILER, "Other")`).
- Produces: `SmartHeatZoneClimate._afterheat: bool`, `_afterheat_joined: bool`; `BoilerManager.has_real_demand() -> bool`; `BoilerManager.turn_on(..., afterheat: bool = False)`; `_set_heating(enable, reason=None, afterheat=False)`.

- [ ] **Step 1: Write failing tests in `tests/test_afterheat.py`** (zone: target 21 °C, hysteresis 0.5, `zone_extra={CONF_AFTERHEAT: True}`):
  - `test_joins_running_boiler_below_target_inside_the_band`: temp "20.8", boiler marked running, then `hass.states.async_set(SENSOR, "20.8")` re-set to "20.7" (a new reading) → `hvac_action == "heating"`, relay `turn_on` recorded once, no `switch.turn_on` on BOILER.
  - `test_flag_off_does_not_join`: same with `zone_extra={}` → `idle`, no relay command.
  - `test_does_not_join_when_boiler_is_idle`: no active zones → `idle`.
  - `test_does_not_join_at_or_above_target`: temp "21.0" and "21.2" with boiler running → `idle`.
  - `test_leaves_at_target_plus_hysteresis`: joined at 20.8; reading 21.4 → still `heating`; reading 21.6 → `idle`, relay `turn_off` recorded, `"Living" not in boiler.get_active_zones()`, and no `switch.turn_off` on BOILER ("Other" still holds the boiler).
  - `test_keeps_heating_when_the_starter_stops_first`: joined; `await boiler.turn_off(BOILER, "Other")` → zone still `heating`, `"Living" in boiler.get_active_zones()`, no `switch.turn_off` on BOILER.
  - `test_watchdog_joins_without_a_new_reading`: temp 20.8 reading first (boiler idle → `idle`), then mark boiler running, `await advance(hass, freezer, minutes=1)` → `heating`.
  - `test_watchdog_does_not_reevaluate_while_boiler_idle`: temp "20.0" → `heating` (zone alone holds the boiler); manual relay switch-off (relay "on" then "off") → `idle`, boiler released; `advance(minutes=1)` → still `idle`, no new relay `turn_on`.
  - `test_two_afterheat_zones_do_not_hold_the_boiler_for_each_other`: one joined zone (via `boiler.turn_on(BOILER, "Joined", afterheat=True)`) plus no other active zone → `has_real_demand()` is False and a zone below target does not join.
  - `test_joined_zone_becomes_real_demand_when_it_gets_cold_enough`: joined at 20.8, then reading 20.4 (diff > 0.5) → `"Living"` no longer in the afterheat set, `has_real_demand()` True.
  - `test_no_join_with_door_open_hvac_off_no_reading_or_limp`: four parametrised cases (open door sensor in `CONF_DOOR_SENSORS`, `climate.set_hvac_mode off`, temp `"unavailable"`, sensor lost with `LIMP_OFF` after the grace/stale time) → never `heating`.
  - `test_attribute_exposes_the_option`: `attrs["afterheat"] is True`.
- [ ] **Step 2: Run** `$SCRATCH/venv/bin/pytest tests/test_afterheat.py -v`. Expected: FAIL (the new tests; `afterheat` is not read yet).
- [ ] **Step 3: Implement.**
  - `const.py`: the two constants.
  - `climate.py` setup: `afterheat = zone_data.get(CONF_AFTERHEAT, DEFAULT_AFTERHEAT)` passed to the entity; `self._afterheat = bool(afterheat)`.
  - `_evaluate_heating`, radiator branch: after the `elif diff < -effective_hysteresis` branch add `elif self._afterheat and not self._is_heating and diff > 0 and self._boiler.has_real_demand(): await self._set_heating(True, reason=..., afterheat=True)`, set `self._afterheat_joined = True`, and log the join at info level (zone, current, adjusted target, active zones).
  - `_watchdog`: before `_check_relay_notice`, inside its own `try/except Exception` with `_LOGGER.exception(...)`: `if self._afterheat and not self._is_heating and self._boiler.has_real_demand(): await self._evaluate_heating()`.
  - `_set_heating` passes `afterheat` to `self._boiler.turn_on`. In the radiator branch, when `diff > effective_hysteresis` and the zone is already heating with `_afterheat_joined`, clear the flag and call `self._boiler.turn_on(self._boiler_entity, zone=self.name, afterheat=False)` (the zone now has real demand). `_afterheat_joined` is also reset when the zone stops heating.
  - `extra_state_attributes`: add `"afterheat"`.
- [ ] **Step 4: Run** `pytest tests/test_afterheat.py tests/test_failsafe.py tests/test_limp.py -v`. Expected: all PASS.
- [ ] **Step 5: Run the whole suite** `pytest tests -q`. Expected: all PASS.

### Task 2: Options UI, translations, docs

**Files:**
- Modify: `custom_components/smartheatzones/config_flow.py` (zone schema near `CONF_SENSOR_STALE_HOURS` ~line 253: `vol.Optional(CONF_AFTERHEAT, default=DEFAULT_AFTERHEAT): selector.BooleanSelector()`)
- Modify: `custom_components/smartheatzones/options_flow.py` (zone schema near line 305: same field, `default=self._data.get(CONF_AFTERHEAT, DEFAULT_AFTERHEAT)`)
- Modify: `custom_components/smartheatzones/strings.json`, `custom_components/smartheatzones/translations/en.json`, `custom_components/smartheatzones/translations/hu.json` (label + description for `afterheat` in both the config step and the options step, like `sensor_stale_hours`)
- Modify: `docs/configuration.md` (zone setting), `docs/advanced-features.md` ("Afterheat" section: entry, exit, stays on when the starter stops, underfloor only gets the one-minute re-check, a manual relay switch-off is reverted within a minute while the boiler runs (D4), two afterheat zones can keep the boiler running for each other (D3))
- Test: `tests/test_afterheat.py` (extend)

**Interfaces:**
- Consumes: `CONF_AFTERHEAT`, `DEFAULT_AFTERHEAT` from Task 1.
- Produces: the stored zone data key `afterheat`.

- [ ] **Step 1: Write failing test** `test_options_flow_saves_the_afterheat_flag`: run the zone options flow (pattern from `tests/test_limp_settings.py`, which passes the outdoor sensor value too) with `afterheat: True` and assert the entry data holds `afterheat is True`; a second run with `False` stores `False`.
- [ ] **Step 2: Run** `pytest tests/test_afterheat.py::test_options_flow_saves_the_afterheat_flag -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the two schema fields, the translation keys (en and hu text: label "Afterheat" / "Utánfűtés"; description: joins a running boiler when below target, leaves by hysteresis / "Ha a kazán már megy, a zóna a célérték alatt is bekapcsol, és a hiszterézis szerint áll le"), and the docs.
- [ ] **Step 4: Run** `pytest tests -q`. Expected: all PASS. Verify the three JSON files parse, the `afterheat` keys are present in all three in the four places, and the new strings have no leading/trailing spaces.
- [ ] **Step 5: Do not commit.** Report to Gábor, including the open confirmations (D3, D4) and issue #26; the version/changelog step is a separate `/update-version-changelog`.

# Afterheat (zone option) - design

Issue: #25. Status: awaiting approval.

## Intent
Fewer boiler starts. While the boiler already runs for one zone, zones that opted in also heat when they are below target, instead of starting the boiler on their own later.

## Behaviour
- New per-zone boolean `afterheat`, default off, set in the zone options.
- Entry: afterheat on, HVAC heat, a valid reading, no open door/window, no limp mode, boiler running (the boiler manager has at least one active zone), and current temperature < adjusted target. No hysteresis on entry (this uses the hysteresis band below the target).
- Exit: the normal evaluation, unchanged. Radiator: target + effective hysteresis (adaptive included). Underfloor: the target (no hysteresis). Hysteresis is always respected.
- Once the zone joined, it keeps heating to its own target even if the starter zone has stopped (the boiler then runs for it alone).
- Any heating zone counts as a starter, including another afterheat zone that joined.
- Existing piggyback at boiler start stays as is (all zones). The option only adds the "boiler already running" entry.
- "Boiler running" means active zones in the boiler manager. The relay's physical state is not read (#23).

## Approaches
- A (chosen): the zone decides in `_evaluate_heating`; runs on every own reading and on the one-minute watchdog. Entry can lag by at most about one minute behind the sensor report. Small, follows the existing pattern.
- B (rejected): the boiler manager sweeps afterheat zones. Immediate, but splits the decision across two classes and leans on the live zone dict (#24).

## Non-goals
Changing piggyback for all zones; reading the boiler's physical state; limp-mode afterheat.

## Left to the builder
Option key name and form placement, translations (hu/en), docs, tests (entry, no entry when boiler off, exit at hysteresis, starter stops first, door open, limp, flag off).

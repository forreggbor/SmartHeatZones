"""Afterheat: a zone joins a boiler that already runs for another zone, and leaves by its normal rule."""
import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.smartheatzones.const import (
    CONF_AFTERHEAT,
    CONF_DOOR_SENSORS,
    CONF_SENSOR,
    CONF_ZONE_RELAYS,
    DATA_BOILER_MAIN,
    DOMAIN,
)

from .test_failsafe import BOILER, CLIMATE, LIMP_OFF, RELAY, SENSOR, advance, commands, setup_zone

AFTERHEAT = {CONF_AFTERHEAT: True}
DOOR = "binary_sensor.door"


def attrs(hass) -> dict:
    """Attributes of the zone's climate entity."""
    return hass.states.get(CLIMATE).attributes


def boiler_of(hass):
    """The shared boiler manager."""
    return hass.data[DOMAIN][DATA_BOILER_MAIN]


async def reading(hass, value: str) -> None:
    """Send a new temperature reading."""
    hass.states.async_set(SENSOR, value)
    await hass.async_block_till_done()


@pytest.fixture
def switches(hass):
    """Recorded switch.turn_on / switch.turn_off calls."""
    return async_mock_service(hass, "switch", "turn_on"), async_mock_service(hass, "switch", "turn_off")


async def joined_zone(hass, switches):
    """A zone with afterheat that joined a boiler held by another zone ("Other"), at 20.8 °C (target 21, hysteresis 0.5)."""
    zone = await setup_zone(hass, temp="20.9", zone_extra=AFTERHEAT)
    assert attrs(hass)["hvac_action"] == "idle"
    boiler_of(hass)._active_zones.add("Other")
    await reading(hass, "20.8")
    assert attrs(hass)["hvac_action"] == "heating"
    return zone


async def test_joins_running_boiler_below_target_inside_the_band(hass, switches):
    on, _off = switches
    await setup_zone(hass, temp="20.9", zone_extra=AFTERHEAT)
    boiler_of(hass)._active_zones.add("Other")

    await reading(hass, "20.7")

    assert attrs(hass)["hvac_action"] == "heating"
    assert len(commands(on, RELAY)) == 1
    assert commands(on, BOILER) == []  # the boiler was already running, it is not started again


async def test_flag_off_does_not_join(hass, switches):
    on, _off = switches
    await setup_zone(hass, temp="20.9")
    boiler_of(hass)._active_zones.add("Other")

    await reading(hass, "20.7")

    assert attrs(hass)["hvac_action"] == "idle"
    assert commands(on, RELAY) == []


async def test_does_not_join_when_boiler_is_idle(hass, switches):
    await setup_zone(hass, temp="20.9", zone_extra=AFTERHEAT)

    await reading(hass, "20.7")

    assert attrs(hass)["hvac_action"] == "idle"


@pytest.mark.parametrize("value", ["21.0", "21.2"])
async def test_does_not_join_at_or_above_target(hass, switches, value):
    await setup_zone(hass, temp="21.3", zone_extra=AFTERHEAT)
    boiler_of(hass)._active_zones.add("Other")

    await reading(hass, value)

    assert attrs(hass)["hvac_action"] == "idle"


async def test_leaves_at_target_plus_hysteresis(hass, switches):
    _on, off = switches
    await joined_zone(hass, switches)

    await reading(hass, "21.4")  # above target, still inside the hysteresis band
    assert attrs(hass)["hvac_action"] == "heating"

    await reading(hass, "21.6")  # target + hysteresis passed
    assert attrs(hass)["hvac_action"] == "idle"
    assert len(commands(off, RELAY)) == 1
    assert "Living" not in boiler_of(hass).get_active_zones()
    assert commands(off, BOILER) == []  # "Other" still holds the boiler


async def test_keeps_heating_when_the_starter_stops_first(hass, switches):
    _on, off = switches
    await joined_zone(hass, switches)

    await boiler_of(hass).turn_off(BOILER, "Other")
    await hass.async_block_till_done()

    assert attrs(hass)["hvac_action"] == "heating"
    assert "Living" in boiler_of(hass).get_active_zones()
    assert commands(off, BOILER) == []


async def test_watchdog_joins_without_a_new_reading(hass, freezer, switches):
    on, _off = switches
    await setup_zone(hass, temp="20.8", zone_extra=AFTERHEAT)
    assert attrs(hass)["hvac_action"] == "idle"

    boiler_of(hass)._active_zones.add("Other")
    await advance(hass, freezer, minutes=1)

    assert attrs(hass)["hvac_action"] == "heating"
    assert commands(on, BOILER) == []


async def test_watchdog_does_not_reevaluate_while_there_is_no_real_demand(hass, freezer, switches):
    on, _off = switches
    await setup_zone(hass, temp="20.0", zone_extra=AFTERHEAT)  # cold: the zone heats on its own demand
    assert attrs(hass)["hvac_action"] == "heating"

    hass.states.async_set(RELAY, "on")
    await hass.async_block_till_done()
    hass.states.async_set(RELAY, "off")  # switched off by hand
    await hass.async_block_till_done()
    assert attrs(hass)["hvac_action"] == "idle"
    on_before = len(commands(on, RELAY))

    await advance(hass, freezer, minutes=1)

    assert attrs(hass)["hvac_action"] == "idle"
    assert len(commands(on, RELAY)) == on_before


async def test_afterheat_zones_do_not_hold_the_boiler_for_each_other(hass, switches):
    await setup_zone(hass, temp="20.9", zone_extra=AFTERHEAT)
    boiler = boiler_of(hass)
    boiler._active_zones.add("Joined")
    boiler._afterheat_zones.add("Joined")  # another zone that only joined by afterheat
    assert boiler.has_real_demand() is False

    await reading(hass, "20.7")

    assert attrs(hass)["hvac_action"] == "idle"


async def test_a_joined_zone_becomes_real_demand_when_it_gets_cold_enough(hass, switches):
    await joined_zone(hass, switches)
    boiler = boiler_of(hass)
    assert "Living" in boiler._afterheat_zones

    await reading(hass, "20.4")  # more than the hysteresis below target: the zone itself wants heat
    await boiler.turn_off(BOILER, "Other")

    assert "Living" not in boiler._afterheat_zones
    assert boiler.has_real_demand() is True


async def test_a_zone_that_stops_heating_is_no_longer_marked(hass, switches):
    await joined_zone(hass, switches)

    await reading(hass, "21.6")

    assert "Living" not in boiler_of(hass)._afterheat_zones


@pytest.mark.parametrize("case", ["door", "hvac_off", "no_reading", "limp"])
async def test_no_join_when_the_zone_must_not_heat(hass, freezer, switches, case):
    if case == "door":
        hass.states.async_set(DOOR, "on")
        await setup_zone(hass, temp="20.9", zone_extra={**AFTERHEAT, CONF_DOOR_SENSORS: [DOOR]})
    elif case == "no_reading":
        await setup_zone(hass, temp="unknown", zone_extra=AFTERHEAT)
    elif case == "limp":
        await setup_zone(hass, temp="20.9", zone_extra={**AFTERHEAT, **LIMP_OFF})
    else:
        await setup_zone(hass, temp="20.9", zone_extra=AFTERHEAT)
        await hass.services.async_call(
            "climate", "set_hvac_mode", {"entity_id": CLIMATE, "hvac_mode": "off"}, blocking=True
        )
    boiler_of(hass)._active_zones.add("Other")

    if case == "limp":
        hass.states.async_set(SENSOR, "unavailable")
        await advance(hass, freezer, minutes=11)
        assert attrs(hass)["limp_active"] is True
    elif case != "no_reading":  # without a reading the zone has nothing to decide on
        await reading(hass, "20.7")
    await advance(hass, freezer, minutes=1)

    assert attrs(hass)["hvac_action"] != "heating"


async def test_attribute_exposes_the_option(hass, switches):
    await setup_zone(hass, temp="20.9", zone_extra=AFTERHEAT)
    assert attrs(hass)["afterheat"] is True


async def test_options_flow_saves_the_afterheat_flag(hass, switches):
    zone = await setup_zone(hass, temp="21.0")
    base = {CONF_SENSOR: SENSOR, CONF_ZONE_RELAYS: [RELAY]}

    result = await hass.config_entries.options.async_init(zone.entry_id)
    assert result["step_id"] == "zone"
    field = next(k for k in result["data_schema"].schema if str(k) == CONF_AFTERHEAT)
    assert field.default() is False

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={**base, CONF_AFTERHEAT: True}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert zone.options[CONF_AFTERHEAT] is True


async def test_a_reload_keeps_the_afterheat_mark_of_a_joined_zone(hass, switches):
    zone = await joined_zone(hass, switches)
    boiler = boiler_of(hass)
    hass.states.async_set(RELAY, "on")  # the relay really is on
    await hass.async_block_till_done()
    assert "Living" in boiler._afterheat_zones

    assert await hass.config_entries.async_reload(zone.entry_id)
    await hass.async_block_till_done()

    assert "Living" in boiler._afterheat_zones
    await boiler.turn_off(BOILER, "Other")
    assert boiler.has_real_demand() is False


async def test_a_zone_with_real_demand_gets_piggyback_when_the_boiler_only_ran_for_afterheat(hass, switches):
    on, _off = switches
    await setup_zone(hass, temp="20.9")  # no afterheat option, inside the band: normal rule does not heat
    boiler = boiler_of(hass)
    boiler._active_zones.add("Joined")
    boiler._afterheat_zones.add("Joined")  # the boiler runs only for a zone that joined by afterheat

    await boiler.turn_on(BOILER, "Starter")  # a zone with real demand starts
    await hass.async_block_till_done()

    assert attrs(hass)["hvac_action"] == "heating"  # the boiler "restarts" for real demand: piggyback runs
    assert commands(on, BOILER) == []  # the boiler itself was never switched off in between


async def test_no_extra_piggyback_while_real_demand_already_runs(hass, switches):
    await setup_zone(hass, temp="20.9")
    boiler = boiler_of(hass)
    boiler._active_zones.add("Other")  # real demand already running

    await boiler.turn_on(BOILER, "Starter")
    await hass.async_block_till_done()

    assert attrs(hass)["hvac_action"] == "idle"  # unchanged behaviour: piggyback only at the boiler start

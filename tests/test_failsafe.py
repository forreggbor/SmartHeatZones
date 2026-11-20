"""Safety behavior of a zone: sensor fail-safe, failed relay commands and startup state."""
from datetime import timedelta

from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
    mock_restore_cache,
)

from custom_components.smartheatzones import async_remove_entry
from custom_components.smartheatzones.const import (
    CONF_BOILER_MAIN,
    CONF_HYSTERESIS,
    CONF_IS_COMMON_SETTINGS,
    CONF_OVERHEAT_PROTECTION,
    CONF_SCHEDULE,
    CONF_SENSOR,
    CONF_ZONE_RELAYS,
    DATA_ACTIVE_ZONES,
    DATA_BOILER_MAIN,
    DOMAIN,
)

SENSOR = "sensor.living_temp"
RELAY = "switch.living_relay"
BOILER = "switch.boiler"
CLIMATE = "climate.living"


async def setup_zone(hass: HomeAssistant, temp: str = "19.0", relay: str = "off"):
    """Create the common settings entry and one zone (target 21 °C, wall thermostat, 0.5 hysteresis)."""
    hass.states.async_set(SENSOR, temp)
    hass.states.async_set(RELAY, relay)
    hass.states.async_set(BOILER, "off")

    common = MockConfigEntry(
        domain=DOMAIN,
        title="Common",
        version=2,
        data={
            CONF_IS_COMMON_SETTINGS: True,
            CONF_BOILER_MAIN: BOILER,
            CONF_HYSTERESIS: 0.5,
            CONF_OVERHEAT_PROTECTION: 26.0,
        },
    )
    common.add_to_hass(hass)
    assert await hass.config_entries.async_setup(common.entry_id)

    zone = MockConfigEntry(
        domain=DOMAIN,
        title="Living",
        version=2,
        data={CONF_SENSOR: SENSOR, CONF_ZONE_RELAYS: [RELAY], CONF_SCHEDULE: []},
    )
    zone.add_to_hass(hass)
    assert await hass.config_entries.async_setup(zone.entry_id)
    await hass.async_block_till_done()
    return zone


def commands(calls, entity_id):
    """Entity ids targeted by the recorded service calls."""
    return [c for c in calls if c.data.get("entity_id") == entity_id]


async def advance(hass, freezer, **delta):
    """Move the clock forward and let the interval listeners run."""
    freezer.tick(timedelta(**delta))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_normal_control_still_works(hass, freezer):
    """Too cold -> relay on, warm enough -> relay off, no fault is reported."""
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="19.0")
    assert len(commands(on, RELAY)) == 1

    hass.states.async_set(SENSOR, "23.0")
    await hass.async_block_till_done()
    assert len(commands(off, RELAY)) == 1
    assert hass.states.get(CLIMATE).attributes["sensor_fault"] is None


async def test_unavailable_sensor_switches_heating_off_after_the_grace_period(hass, freezer):
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="19.0")
    assert len(commands(on, RELAY)) == 1

    hass.states.async_set(SENSOR, "unavailable")
    await hass.async_block_till_done()
    await advance(hass, freezer, minutes=5)
    assert commands(off, RELAY) == []  # still inside the grace period
    assert hass.states.get(CLIMATE).attributes["sensor_fault"] is None

    await advance(hass, freezer, minutes=6)
    assert len(commands(off, RELAY)) == 1
    attrs = hass.states.get(CLIMATE).attributes
    assert attrs["sensor_fault"] == "sensor_unavailable"
    assert attrs["current_temperature"] is None


async def test_silent_sensor_switches_heating_off(hass, freezer):
    """A dead battery leaves the last value in place; no report for 2 hours is a fault."""
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="19.0")

    await advance(hass, freezer, hours=1, minutes=59)
    assert commands(off, RELAY) == []

    await advance(hass, freezer, minutes=2)
    assert len(commands(off, RELAY)) == 1
    assert hass.states.get(CLIMATE).attributes["sensor_fault"] == "sensor_stale"


async def test_sensor_recovery_resumes_control(hass, freezer):
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="19.0")
    hass.states.async_set(SENSOR, "unavailable")
    await hass.async_block_till_done()
    await advance(hass, freezer, minutes=11)
    assert hass.states.get(CLIMATE).attributes["sensor_fault"] == "sensor_unavailable"
    heating_commands = len(commands(on, RELAY))

    hass.states.async_set(SENSOR, "18.0")
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE).attributes["sensor_fault"] is None
    assert len(commands(on, RELAY)) == heating_commands + 1  # cold again -> heating resumes


async def test_failed_relay_off_is_retried(hass, freezer):
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="19.0")

    async def failing(call):
        raise HomeAssistantError("relay unreachable")

    hass.services.async_register("switch", "turn_off", failing)
    hass.states.async_set(SENSOR, "23.0")  # warm enough -> off command, which fails
    await hass.async_block_till_done()
    attrs = hass.states.get(CLIMATE).attributes
    assert attrs["relay_fault"] == [RELAY]
    boiler = hass.data[DOMAIN][DATA_BOILER_MAIN]
    assert boiler.get_boiler_state()["failed_action"] == "turn_off"

    off = async_mock_service(hass, "switch", "turn_off")  # the relay works again
    await advance(hass, freezer, minutes=1)
    assert len(commands(off, RELAY)) == 1
    assert len(commands(off, BOILER)) == 1
    assert hass.states.get(CLIMATE).attributes["relay_fault"] == []
    assert boiler.get_boiler_state()["failed_action"] is None


async def test_a_newer_decision_cancels_the_retry(hass, freezer):
    """The retry must never fight a newer decision (or a manual switch)."""
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="19.0")

    async def failing(call):
        raise HomeAssistantError("relay unreachable")

    hass.services.async_register("switch", "turn_off", failing)
    hass.states.async_set(SENSOR, "23.0")
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE).attributes["relay_fault"] == [RELAY]

    off = async_mock_service(hass, "switch", "turn_off")
    hass.states.async_set(SENSOR, "18.0")  # cold again: heating is wanted, the old off is obsolete
    await hass.async_block_till_done()
    await advance(hass, freezer, minutes=1)
    assert commands(off, RELAY) == []
    assert hass.states.get(CLIMATE).attributes["relay_fault"] == []


async def test_a_relay_left_on_before_startup_is_taken_over(hass, freezer):
    """After a restart a running relay must still be switched off when the room is warm."""
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="25.0", relay="on")
    assert len(commands(off, RELAY)) == 1


async def test_invalid_stored_values_do_not_break_the_entity(hass):
    async_mock_service(hass, "switch", "turn_on")
    async_mock_service(hass, "switch", "turn_off")
    mock_restore_cache(hass, [State(CLIMATE, "heat", {"temperature": "abc", "preset_mode": "bogus"})])
    await setup_zone(hass, temp="21.0")
    attrs = hass.states.get(CLIMATE).attributes
    assert attrs["preset_mode"] == "auto"
    assert attrs["temperature"] == 21.0


async def test_removing_a_zone_does_not_touch_a_zone_with_a_similar_name(hass):
    hass.data.setdefault(DOMAIN, {})[DATA_ACTIVE_ZONES] = {"Bath", "Bathroom"}
    entry = MockConfigEntry(domain=DOMAIN, title="Bath", data={})
    await async_remove_entry(hass, entry)
    assert hass.data[DOMAIN][DATA_ACTIVE_ZONES] == {"Bathroom"}

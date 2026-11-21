"""Limp mode: open-loop heating cycle while neither the zone sensor nor a backup can be trusted."""
import logging
from datetime import timedelta

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.smartheatzones.const import (
    CONF_BACKUP_SENSOR,
    CONF_DOOR_SENSORS,
    CONF_HEATING_MODE,
    CONF_LIMP_ON,
    CONF_LIMP_OUTDOOR_CUTOFF,
    CONF_LIMP_PERIOD,
    CONF_OUTDOOR_BACKUP_SENSOR,
    CONF_OUTDOOR_SENSOR,
    CONF_SENSOR,
    CONF_SENSOR_STALE_HOURS,
    CONF_ZONE_RELAYS,
    DOMAIN,
)

from .test_failsafe import BOILER, CLIMATE, LIMP_OFF, RELAY, SENSOR, advance, commands, setup_zone

OUTDOOR = "sensor.outdoor"
WEATHER = "weather.home"


def attrs(hass) -> dict:
    """Attributes of the zone's climate entity."""
    return hass.states.get(CLIMATE).attributes


def pin(freezer, hours: int, minutes: int = 0) -> None:
    """
    Freeze the clock at a known local time of one fixed day, so the limp phase is deterministic.

    The day is chosen on the first call of a test and kept (moving the clock must not move "today").
    """
    if not hasattr(freezer, "limp_base"):
        freezer.limp_base = dt_util.start_of_local_day() + timedelta(days=1)
    freezer.move_to(freezer.limp_base + timedelta(hours=hours, minutes=minutes))


async def limp_zone(hass, freezer, start_minute: int, zone_extra=None, common_extra=None, states=()):
    """
    A zone whose only sensor is unavailable from the start.

    The fault is declared 10 minutes after setup, i.e. at local minute-of-day `start_minute + 10`; pass
    start_minute so that this lands where the test wants it in the cycle.
    """
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    pin(freezer, 0, start_minute)
    for entity_id, state, *state_attrs in states:  # set after the pin: entity ages are measured on the frozen clock
        hass.states.async_set(entity_id, state, *state_attrs)
    zone = await setup_zone(hass, temp="unavailable", zone_extra=zone_extra, common_extra=common_extra)
    await advance(hass, freezer, minutes=10)
    return zone, on, off


async def run_minutes(hass, freezer, count: int):
    """Advance the clock minute by minute (one watchdog tick per minute)."""
    for _ in range(count):
        await advance(hass, freezer, minutes=1)


async def test_radiator_cycle_on_then_off(hass, freezer):
    zone, on, off = await limp_zone(hass, freezer, start_minute=50)  # declared at minute 60 -> phase 0
    assert attrs(hass)["limp_active"] is True and attrs(hass)["sensor_source"] == "none"
    assert len(commands(on, RELAY)) == 1  # on phase starts: 10 min on per 60

    await run_minutes(hass, freezer, 9)  # minute 69, phase 9
    assert commands(off, RELAY) == []
    await run_minutes(hass, freezer, 1)  # minute 70, phase 10
    assert len(commands(off, RELAY)) == 1
    await run_minutes(hass, freezer, 49)  # minute 119, phase 59
    assert len(commands(on, RELAY)) == 1
    await run_minutes(hass, freezer, 1)  # minute 120, phase 0 -> next cycle
    assert len(commands(on, RELAY)) == 2


async def test_zone_override_beats_the_mode_profile(hass, freezer):
    zone, on, off = await limp_zone(
        hass, freezer, start_minute=20, zone_extra={CONF_LIMP_ON: 5, CONF_LIMP_PERIOD: 30}
    )  # declared at minute 30 -> phase 0 of a 30 min period
    assert len(commands(on, RELAY)) == 1
    await run_minutes(hass, freezer, 4)
    assert commands(off, RELAY) == []
    await run_minutes(hass, freezer, 1)
    assert len(commands(off, RELAY)) == 1


async def test_zero_duty_never_heats(hass, freezer):
    zone, on, off = await limp_zone(hass, freezer, start_minute=50, zone_extra=LIMP_OFF)
    await run_minutes(hass, freezer, 130)
    assert commands(on, RELAY) == []


async def test_underfloor_zone_uses_its_own_profile(hass, freezer):
    zone, on, off = await limp_zone(
        hass, freezer, start_minute=170, zone_extra={CONF_HEATING_MODE: "underfloor"}
    )  # declared at minute 180 -> phase 0 of 40/180
    assert len(commands(on, RELAY)) == 1
    await run_minutes(hass, freezer, 39)
    assert commands(off, RELAY) == []
    await run_minutes(hass, freezer, 1)
    assert len(commands(off, RELAY)) == 1


@pytest.mark.parametrize(
    ("outdoor", "on_minutes"),
    [(-12.0, 20), (-5.0, 15), (5.0, 12), (12.0, 10)],  # multipliers x2.0, x1.5, x1.2, x1.0 of 10 minutes
)
async def test_outdoor_temperature_scales_the_on_time(hass, freezer, outdoor, on_minutes):
    zone, on, off = await limp_zone(
        hass, freezer, start_minute=50, common_extra={CONF_OUTDOOR_SENSOR: OUTDOOR},
        states=[(OUTDOOR, str(outdoor))],
    )
    assert attrs(hass)["outdoor_source"] == "live"
    assert len(commands(on, RELAY)) == 1
    await run_minutes(hass, freezer, on_minutes - 1)
    assert commands(off, RELAY) == []
    await run_minutes(hass, freezer, 1)
    assert len(commands(off, RELAY)) == 1


async def test_warm_outdoor_stops_the_cycle(hass, freezer):
    zone, on, off = await limp_zone(  # default cut-off 15 °C
        hass, freezer, start_minute=50, common_extra={CONF_OUTDOOR_SENSOR: OUTDOOR}, states=[(OUTDOOR, "16.0")],
    )
    await run_minutes(hass, freezer, 70)
    assert commands(on, RELAY) == []


async def test_a_disabled_cutoff_keeps_the_cycle_running_in_warm_weather(hass, freezer):
    zone, on, off = await limp_zone(
        hass, freezer, start_minute=50,
        common_extra={CONF_OUTDOOR_SENSOR: OUTDOOR, CONF_LIMP_OUTDOOR_CUTOFF: None},
        states=[(OUTDOOR, "25.0")],
    )
    assert len(commands(on, RELAY)) == 1


async def test_backup_weather_entity_replaces_a_lost_outdoor_sensor(hass, freezer):
    zone, on, off = await limp_zone(
        hass, freezer, start_minute=50,
        common_extra={CONF_OUTDOOR_SENSOR: OUTDOOR, CONF_OUTDOOR_BACKUP_SENSOR: WEATHER},
        states=[(OUTDOOR, "unavailable"), (WEATHER, "snowy", {"temperature": -12.0, "temperature_unit": "°C"})],
    )
    assert attrs(hass)["outdoor_source"] == "backup"
    await run_minutes(hass, freezer, 19)  # x2.0 -> 20 minutes on
    assert commands(off, RELAY) == []
    await run_minutes(hass, freezer, 1)
    assert len(commands(off, RELAY)) == 1


async def test_a_fahrenheit_weather_entity_is_ignored_loudly(hass, freezer, caplog):
    with caplog.at_level(logging.WARNING):
        zone, on, off = await limp_zone(
            hass, freezer, start_minute=50, common_extra={CONF_OUTDOOR_BACKUP_SENSOR: WEATHER},
            states=[(WEATHER, "snowy", {"temperature": 10.0, "temperature_unit": "°F"})],
        )
    assert attrs(hass)["outdoor_source"] == "none"
    assert "only °C is supported" in caplog.text
    await run_minutes(hass, freezer, 9)  # no outdoor data -> nominal x1.0 -> 10 minutes on
    assert commands(off, RELAY) == []
    await run_minutes(hass, freezer, 1)
    assert len(commands(off, RELAY)) == 1


async def test_a_lost_outdoor_sensor_falls_back_to_the_cautious_estimate(hass, freezer):
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    pin(freezer, 0, 30)
    hass.states.async_set(OUTDOOR, "5.0")
    await setup_zone(
        hass, temp="21.0",
        zone_extra={CONF_SENSOR_STALE_HOURS: 24},
        common_extra={CONF_OUTDOOR_SENSOR: OUTDOOR},
    )
    for hours, value in ((4, "-12.0"), (8, "2.0"), (13, "6.0")):  # the day's night low is -12
        pin(freezer, hours, 30)
        hass.states.async_set(OUTDOOR, value)
        await hass.async_block_till_done()

    pin(freezer, 14, 50)
    hass.states.async_set(OUTDOOR, "unavailable")
    hass.states.async_set(SENSOR, "unavailable")
    await hass.async_block_till_done()
    await advance(hass, freezer, minutes=10)  # declared at 15:00 -> phase 0
    assert attrs(hass)["outdoor_source"] == "estimate"
    assert len(commands(on, RELAY)) == 1
    await run_minutes(hass, freezer, 19)  # -12 °C -> x2.0 -> 20 minutes on
    assert commands(off, RELAY) == []
    await run_minutes(hass, freezer, 1)
    assert len(commands(off, RELAY)) == 1


async def test_hvac_off_and_open_doors_stop_the_cycle(hass, freezer):
    door = "binary_sensor.door"
    zone, on, off = await limp_zone(
        hass, freezer, start_minute=50, zone_extra={CONF_DOOR_SENSORS: [door]}, states=[(door, "on")]
    )
    assert commands(on, RELAY) == []  # door open: no heating in the on phase
    hass.states.async_set(door, "off")
    await hass.async_block_till_done()
    await run_minutes(hass, freezer, 1)
    assert len(commands(on, RELAY)) == 1  # closed: the cycle resumes (still inside the on phase)

    await hass.services.async_call("climate", "set_hvac_mode", {"entity_id": CLIMATE, "hvac_mode": "off"}, blocking=True)
    await hass.async_block_till_done()
    assert attrs(hass)["hvac_action"] == "off"
    await run_minutes(hass, freezer, 70)
    assert len(commands(on, RELAY)) == 1  # never again while HVAC is off


async def test_limp_starts_only_after_the_fault_is_declared_even_across_a_reload(hass, freezer):
    zone, on, off = await limp_zone(hass, freezer, start_minute=50)
    assert attrs(hass)["limp_active"] is True
    assert await hass.config_entries.async_reload(zone.entry_id)
    await hass.async_block_till_done()
    assert attrs(hass)["limp_active"] is False  # the clock restarted with the reload
    await advance(hass, freezer, minutes=9)
    assert attrs(hass)["limp_active"] is False
    await advance(hass, freezer, minutes=2)
    assert attrs(hass)["limp_active"] is True


async def test_limp_backup_and_primary_hand_over_both_ways(hass, freezer):
    backup = "sensor.backup_temp"
    zone, on, off = await limp_zone(
        hass, freezer, start_minute=50, zone_extra={CONF_BACKUP_SENSOR: backup}, states=[(backup, "unavailable")]
    )
    assert attrs(hass)["sensor_source"] == "none" and attrs(hass)["limp_active"] is True

    hass.states.async_set(backup, "23.0")  # backup back: normal control, warm -> off
    await hass.async_block_till_done()
    assert attrs(hass)["sensor_source"] == "backup" and attrs(hass)["limp_active"] is False
    assert attrs(hass)["current_temperature"] == 23.0

    hass.states.async_set(backup, "unavailable")
    await hass.async_block_till_done()
    await advance(hass, freezer, minutes=11)
    assert attrs(hass)["sensor_source"] == "none" and attrs(hass)["limp_active"] is True

    hass.states.async_set(SENSOR, "20.0")  # primary back
    await hass.async_block_till_done()
    assert attrs(hass)["sensor_source"] == "primary" and attrs(hass)["limp_active"] is False
    assert attrs(hass)["sensor_fault"] is None


async def test_a_failed_relay_command_in_limp_is_retried(hass, freezer):
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")

    async def failing(call):
        raise HomeAssistantError("relay unreachable")

    pin(freezer, 0, 50)
    await setup_zone(hass, temp="unavailable")
    hass.services.async_register("switch", "turn_on", failing)
    await advance(hass, freezer, minutes=10)  # limp on phase: the turn_on fails
    assert attrs(hass)["relay_fault"] == [RELAY]

    on = async_mock_service(hass, "switch", "turn_on")  # the relay works again
    await advance(hass, freezer, minutes=1)
    assert len(commands(on, RELAY)) == 1
    assert attrs(hass)["relay_fault"] == []


async def test_two_zones_in_the_same_phase_start_the_boiler_once(hass, freezer):
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    pin(freezer, 0, 50)
    await setup_zone(hass, temp="unavailable")
    hass.states.async_set("sensor.bath_temp", "unavailable")
    hass.states.async_set("switch.bath_relay", "off")
    second = MockConfigEntry(
        domain=DOMAIN, title="Bath", version=2,
        data={CONF_SENSOR: "sensor.bath_temp", CONF_ZONE_RELAYS: ["switch.bath_relay"]},
    )
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()
    await advance(hass, freezer, minutes=11)
    assert len(commands(on, RELAY)) == 1 and len(commands(on, "switch.bath_relay")) == 1
    assert len(commands(on, BOILER)) == 1

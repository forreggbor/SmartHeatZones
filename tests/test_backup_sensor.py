"""Backup temperature sensor: the zone keeps normal control while the primary sensor is lost."""
import logging
from unittest.mock import AsyncMock, patch

from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.smartheatzones.climate import SmartHeatZoneClimate
from custom_components.smartheatzones.const import CONF_BACKUP_SENSOR, CONF_BACKUP_SENSOR_OFFSET

from .test_failsafe import CLIMATE, LIMP_OFF, RELAY, SENSOR, advance, commands, setup_zone

BACKUP = "sensor.backup_temp"


def attrs(hass) -> dict:
    """Attributes of the zone's climate entity."""
    return hass.states.get(CLIMATE).attributes


async def zone_on_backup(hass, freezer, backup="20.0", offset=0.0, primary="21.0"):
    """A zone whose primary sensor has just been declared lost, with a healthy backup sensor."""
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    hass.states.async_set(BACKUP, backup)
    await setup_zone(
        hass, temp=primary,
        zone_extra={CONF_BACKUP_SENSOR: BACKUP, CONF_BACKUP_SENSOR_OFFSET: offset, **LIMP_OFF},
    )
    hass.states.async_set(SENSOR, "unavailable")
    await hass.async_block_till_done()
    await advance(hass, freezer, minutes=11)
    return on, off


async def test_backup_takes_over_and_keeps_controlling(hass, freezer):
    on, off = await zone_on_backup(hass, freezer, backup="20.0")
    assert attrs(hass)["sensor_fault"] == "sensor_unavailable"
    assert attrs(hass)["sensor_source"] == "backup"
    assert attrs(hass)["current_temperature"] == 20.0
    assert len(commands(on, RELAY)) == 1  # cold on the backup reading -> heating, not switched off
    assert commands(off, RELAY) == []

    hass.states.async_set(BACKUP, "23.0")  # warm
    await hass.async_block_till_done()
    assert len(commands(off, RELAY)) == 1


async def test_backup_correction_is_added_to_the_reading(hass, freezer):
    await zone_on_backup(hass, freezer, backup="19.0", offset=1.5)
    assert attrs(hass)["current_temperature"] == 20.5


async def test_primary_returning_ends_the_episode(hass, freezer):
    on, off = await zone_on_backup(hass, freezer)
    hass.states.async_set(SENSOR, "22.5")
    await hass.async_block_till_done()
    assert attrs(hass)["sensor_fault"] is None
    assert attrs(hass)["sensor_source"] == "primary"
    assert attrs(hass)["current_temperature"] == 22.5


async def test_backup_lost_too_switches_off_and_recovers_with_the_backup(hass, freezer):
    on, off = await zone_on_backup(hass, freezer, backup="20.0")
    assert len(commands(on, RELAY)) == 1

    hass.states.async_set(BACKUP, "unavailable")
    await hass.async_block_till_done()
    await advance(hass, freezer, minutes=11)
    assert attrs(hass)["sensor_source"] == "none"
    assert attrs(hass)["current_temperature"] is None
    assert len(commands(off, RELAY)) == 1

    hass.states.async_set(BACKUP, "19.0")  # backup is back while the primary is still lost
    await hass.async_block_till_done()
    assert attrs(hass)["sensor_source"] == "backup"
    assert attrs(hass)["current_temperature"] == 19.0
    assert len(commands(on, RELAY)) == 2


async def test_a_flapping_backup_reading_does_not_chatter_the_relay(hass, freezer):
    on, off = await zone_on_backup(hass, freezer, backup="20.0")
    baseline_on, baseline_off = len(commands(on, RELAY)), len(commands(off, RELAY))
    for value in ("20.8", "21.2", "20.7", "21.3", "20.6"):  # inside the 0.5 hysteresis band around 21
        hass.states.async_set(BACKUP, value)
        await hass.async_block_till_done()
    assert len(commands(on, RELAY)) == baseline_on
    assert len(commands(off, RELAY)) == baseline_off


async def test_recovery_is_also_detected_by_the_watchdog(hass, freezer):
    """A silent primary that reports the same value again raises no state change event."""
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="19.0", zone_extra=LIMP_OFF)
    await advance(hass, freezer, hours=2, minutes=1)
    assert attrs(hass)["sensor_fault"] == "sensor_stale"
    assert len(commands(off, RELAY)) == 1

    hass.states.async_set(SENSOR, "19.0")  # identical: only last_reported moves
    await hass.async_block_till_done()
    await advance(hass, freezer, minutes=1)
    assert attrs(hass)["sensor_fault"] is None
    assert len(commands(on, RELAY)) == 2  # cold again -> heating resumes


async def test_an_error_in_the_sensor_chain_is_logged_and_does_not_stop_the_retry(hass, freezer, caplog):
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="19.0")

    async def failing(call):
        raise HomeAssistantError("relay unreachable")

    hass.services.async_register("switch", "turn_off", failing)
    hass.states.async_set(SENSOR, "23.0")  # off command fails -> pending retry
    await hass.async_block_till_done()
    assert attrs(hass)["relay_fault"] == [RELAY]

    off = async_mock_service(hass, "switch", "turn_off")  # the relay works again
    with patch.object(SmartHeatZoneClimate, "_run_sensor_chain", AsyncMock(side_effect=RuntimeError("boom"))):
        with caplog.at_level(logging.ERROR):
            await advance(hass, freezer, minutes=1)
    assert "sensor chain evaluation FAILED" in caplog.text
    assert len(commands(off, RELAY)) == 1  # the retry still ran
    assert attrs(hass)["relay_fault"] == []


async def test_after_a_reload_a_backup_event_is_handled_once(hass, freezer):
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    hass.states.async_set(BACKUP, "21.0")
    zone = await setup_zone(hass, temp="21.0", zone_extra={CONF_BACKUP_SENSOR: BACKUP})

    calls = []
    original = SmartHeatZoneClimate._backup_sensor_changed

    async def counting(self, event):
        calls.append(event)
        await original(self, event)

    with patch.object(SmartHeatZoneClimate, "_backup_sensor_changed", counting):
        assert await hass.config_entries.async_reload(zone.entry_id)
        await hass.async_block_till_done()
        hass.states.async_set(SENSOR, "unavailable")
        await hass.async_block_till_done()
        await advance(hass, freezer, minutes=11)
        assert attrs(hass)["sensor_source"] == "backup"
        before = len(calls)
        hass.states.async_set(BACKUP, "18.0")
        await hass.async_block_till_done()
    assert len(calls) - before == 1
    assert len(commands(on, RELAY)) == 1

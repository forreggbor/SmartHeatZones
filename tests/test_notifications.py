"""Fail-safe events, translated notifications and the diagnosis of sensor groups."""
import logging
from unittest.mock import AsyncMock, patch

from homeassistant.components import persistent_notification
from homeassistant.components.persistent_notification import _async_get_or_create_notifications
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_mock_service,
)

from custom_components.smartheatzones.const import CONF_BACKUP_SENSOR, EVENT_FAILSAFE

from .test_backup_sensor import BACKUP, zone_on_backup
from .test_failsafe import LIMP_OFF, RELAY, SENSOR, advance, setup_zone
from .test_limp import limp_zone

SENSOR_NOTICE = "smartheatzones_living_sensor"
RELAY_NOTICE = "smartheatzones_living_relay"


def notices(hass) -> dict:
    """The persistent notifications currently showing."""
    return _async_get_or_create_notifications(hass)


def states_of(events) -> list[str]:
    """The fail-safe states of the captured events, in order."""
    return [event.data["state"] for event in events]


async def test_backup_then_limp_then_recovery_each_report_once(hass, freezer):
    events = async_capture_events(hass, EVENT_FAILSAFE)
    await zone_on_backup(hass, freezer, backup="20.0")
    assert states_of(events) == ["backup"]
    assert events[0].data["zone"] == "Living" and events[0].data["cause"] == "sensor_unavailable"
    assert BACKUP in notices(hass)[SENSOR_NOTICE]["message"]

    await advance(hass, freezer, minutes=3)  # nothing changed: no new report
    assert states_of(events) == ["backup"]

    hass.states.async_set(BACKUP, "unavailable")
    await hass.async_block_till_done()
    await advance(hass, freezer, minutes=11)
    assert states_of(events) == ["backup", "limp"]
    assert "Limp mode" in notices(hass)[SENSOR_NOTICE]["message"]  # replaced, not duplicated

    hass.states.async_set(SENSOR, "22.0")
    await hass.async_block_till_done()
    assert states_of(events) == ["backup", "limp", "recovered"]
    assert events[-1].data["cause"] == "sensor_unavailable"
    assert SENSOR_NOTICE not in notices(hass)


async def test_notifications_of_a_previous_run_are_dismissed_at_setup(hass):
    persistent_notification.async_create(hass, "old", notification_id=SENSOR_NOTICE)
    persistent_notification.async_create(hass, "old", notification_id=RELAY_NOTICE)
    async_mock_service(hass, "switch", "turn_on")
    async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="21.0")
    assert SENSOR_NOTICE not in notices(hass) and RELAY_NOTICE not in notices(hass)


async def test_unreachable_relay_is_reported_and_a_sensor_recovery_leaves_that_notice(hass, freezer):
    events = async_capture_events(hass, EVENT_FAILSAFE)
    await zone_on_backup(hass, freezer, backup="20.0")  # cold on the backup: heating is wanted
    hass.states.async_set(RELAY, "unavailable")
    await hass.async_block_till_done()
    await advance(hass, freezer, minutes=16)
    assert RELAY_NOTICE in notices(hass) and SENSOR_NOTICE in notices(hass)
    assert "relay_unavailable" in states_of(events)
    assert RELAY in notices(hass)[RELAY_NOTICE]["message"]

    hass.states.async_set(SENSOR, "20.0")  # primary sensor back: only the sensor notice goes away
    await hass.async_block_till_done()
    assert SENSOR_NOTICE not in notices(hass) and RELAY_NOTICE in notices(hass)

    hass.states.async_set(RELAY, "on")
    await hass.async_block_till_done()
    await advance(hass, freezer, minutes=1)
    assert RELAY_NOTICE not in notices(hass)
    assert states_of(events)[-1] == "relay_recovered"


async def test_a_broken_notifier_does_not_disturb_the_control(hass, freezer, caplog):
    with patch(
        "custom_components.smartheatzones.notifications.async_text", AsyncMock(side_effect=RuntimeError("boom"))
    ), caplog.at_level(logging.ERROR):
        zone, on, off = await limp_zone(hass, freezer, start_minute=50)
    assert "Reporting the fail-safe state" in caplog.text
    assert len([c for c in on if c.data.get("entity_id") == RELAY]) == 1  # the limp cycle still started


async def test_notification_text_follows_the_language(hass, freezer):
    hass.config.language = "hu"
    await limp_zone(hass, freezer, start_minute=50)
    message = notices(hass)[SENSOR_NOTICE]["message"]
    assert "Korlátozott üzem" in message and "Living" in message


async def test_the_diagnosis_names_the_integration_when_several_sensors_are_lost(hass, freezer):
    zha = MockConfigEntry(domain="zha")
    zha.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create("sensor", "zha", "t1", config_entry=zha, suggested_object_id="living_temp")
    registry.async_get_or_create("sensor", "zha", "t2", config_entry=zha, suggested_object_id="backup_temp")
    await limp_zone(
        hass, freezer, start_minute=50,
        zone_extra={CONF_BACKUP_SENSOR: BACKUP}, states=[(BACKUP, "unavailable")],
    )
    message = notices(hass)[SENSOR_NOTICE]["message"]
    assert "zha: 2/2 sensors silent" in message and "network or coordinator problem" in message

"""Zone snapshot for the overview, the decision reason and the next scheduled change."""
import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.smartheatzones.const import (
    CONF_AFTERHEAT,
    CONF_DOOR_SENSORS,
    CONF_LIMP_ON,
    CONF_LIMP_OUTDOOR_CUTOFF,
    CONF_LIMP_PERIOD,
    CONF_OUTDOOR_SENSOR,
    CONF_SCHEDULE,
    CONF_TEMP_OFFSET,
    CONF_THERMOSTAT_TYPE,
    DATA_BOILER_MAIN,
    DOMAIN,
)

from .test_failsafe import CLIMATE, LIMP_OFF, SENSOR, advance, setup_zone

ZONE_KEYS = {
    "name", "entity_id", "sensor_entity", "heating_mode", "hvac_mode", "hvac_action", "preset", "current",
    "target", "adjusted_target", "hysteresis", "on_below", "off_above", "sensor_source", "sensor_fault",
    "limp", "next_change", "afterheat", "joined", "relay_unavailable", "relay_fault", "reason",
}
LIMP_KEYS = {"active", "on_min", "effective_on_min", "period_min", "next_in_min"}
SCHEDULE = [
    {"start": "06:00", "end": "08:00", "temp": 21, "label": "Morning"},
    {"start": "17:00", "end": "22:00", "temp": 22.5, "label": "Evening"},
]


@pytest.fixture(autouse=True)
def switches(hass):
    """Recorded switch calls."""
    return async_mock_service(hass, "switch", "turn_on"), async_mock_service(hass, "switch", "turn_off")


def zone_of(hass):
    """The zone entity object."""
    entity = next(e for e in hass.data[DOMAIN][DATA_BOILER_MAIN].get_zone_entities())
    return entity


def snap(hass) -> dict:
    """The zone's overview snapshot."""
    return zone_of(hass).overview_snapshot()


async def test_snapshot_has_every_key_for_a_zone_without_reading(hass):
    await setup_zone(hass, temp="unknown")

    snapshot = snap(hass)

    assert set(snapshot) == ZONE_KEYS
    assert set(snapshot["limp"]) == LIMP_KEYS
    assert snapshot["current"] is None
    assert snapshot["reason"] == {"code": "no_reading"}
    assert snapshot["name"] == "Living" and snapshot["entity_id"] == CLIMATE


async def test_in_band_reason_in_attributes_and_snapshot(hass):
    await setup_zone(hass, temp="20.7")

    expected = {"code": "in_band", "on_below": 20.5, "target": 21.0}
    assert hass.states.get(CLIMATE).attributes["reason"] == expected
    assert snap(hass)["reason"] == expected


async def test_cold_zone_needs_heat_then_holds(hass):
    await setup_zone(hass, temp="19.0")
    assert snap(hass)["reason"] == {"code": "needs_heat"}

    hass.states.async_set(SENSOR, "21.2")
    await hass.async_block_till_done()
    assert snap(hass)["reason"] == {"code": "holding", "off_above": 21.5}


async def test_afterheat_joined_zone(hass):
    await setup_zone(hass, temp="20.9", zone_extra={CONF_AFTERHEAT: True})
    hass.data[DOMAIN][DATA_BOILER_MAIN]._active_zones.add("Other")
    hass.states.async_set(SENSOR, "20.8")
    await hass.async_block_till_done()

    snapshot = snap(hass)

    assert snapshot["reason"] == {"code": "afterheat"}
    assert snapshot["joined"] is True and snapshot["afterheat"] is True


async def test_door_open_reason(hass):
    hass.states.async_set("binary_sensor.door", "on")
    await setup_zone(hass, temp="19.0", zone_extra={CONF_DOOR_SENSORS: ["binary_sensor.door"]})

    assert snap(hass)["reason"] == {"code": "door_open"}


async def test_hvac_off_reason(hass):
    await setup_zone(hass, temp="19.0")
    await hass.services.async_call("climate", "set_hvac_mode", {"entity_id": CLIMATE, "hvac_mode": "off"}, blocking=True)

    assert snap(hass)["reason"] == {"code": "hvac_off"}


async def test_limp_waiting_has_a_countdown(hass, freezer):
    freezer.move_to("2026-11-23 12:00:00")
    await setup_zone(hass, temp="20.9", zone_extra=LIMP_OFF)
    hass.states.async_set(SENSOR, "unavailable")
    await advance(hass, freezer, minutes=11)

    snapshot = snap(hass)
    local = dt_util.now()
    phase = (local.hour * 60 + local.minute) % 60

    assert snapshot["limp"]["active"] is True
    assert snapshot["limp"]["effective_on_min"] == 0
    assert snapshot["reason"] == {"code": "limp_waiting", "next_in_min": 60 - phase}
    assert snapshot["limp"]["next_in_min"] == 60 - phase
    assert "next_in_min" not in hass.states.get(CLIMATE).attributes["reason"]


async def test_limp_heating_reason(hass, freezer):
    await setup_zone(hass, temp="20.9", zone_extra={CONF_LIMP_ON: 60, CONF_LIMP_PERIOD: 60})
    hass.states.async_set(SENSOR, "unavailable")
    await advance(hass, freezer, minutes=11)

    snapshot = snap(hass)

    assert snapshot["reason"] == {"code": "limp_heating"}
    assert snapshot["limp"]["next_in_min"] == 0


async def test_limp_with_outdoor_cutoff_has_no_countdown(hass, freezer):
    hass.states.async_set("sensor.outdoor", "20")
    await setup_zone(
        hass, temp="20.9", zone_extra=LIMP_OFF,
        common_extra={CONF_OUTDOOR_SENSOR: "sensor.outdoor", CONF_LIMP_OUTDOOR_CUTOFF: 15.0},
    )
    hass.states.async_set(SENSOR, "unavailable")
    await advance(hass, freezer, minutes=11)

    snapshot = snap(hass)

    assert snapshot["limp"]["active"] is True
    assert snapshot["limp"]["effective_on_min"] is None
    assert snapshot["limp"]["next_in_min"] is None


async def test_next_change_in_preset_auto_only_in_the_snapshot(hass, freezer):
    freezer.move_to("2026-11-23 12:00:00")
    await setup_zone(hass, temp="20.9", zone_extra={CONF_SCHEDULE: SCHEDULE})

    assert snap(hass)["next_change"] == {"at": "17:00", "in_min": 300, "temp": 22.5, "label": "Evening"}
    assert "next_change" not in hass.states.get(CLIMATE).attributes


async def test_no_next_change_in_preset_manual(hass, freezer):
    freezer.move_to("2026-11-23 12:00:00")
    await setup_zone(hass, temp="20.9", zone_extra={CONF_SCHEDULE: SCHEDULE})
    await hass.services.async_call("climate", "set_preset_mode", {"entity_id": CLIMATE, "preset_mode": "manual"}, blocking=True)

    assert snap(hass)["next_change"] is None


async def test_radiator_zone_reason_uses_the_adjusted_target(hass):
    await setup_zone(hass, temp="23.8", zone_extra={CONF_THERMOSTAT_TYPE: "radiator", CONF_TEMP_OFFSET: 3.0})

    snapshot = snap(hass)

    assert snapshot["adjusted_target"] == 24.0
    assert snapshot["on_below"] == 23.5 and snapshot["off_above"] == 24.5
    assert snapshot["reason"] == {"code": "in_band", "on_below": 23.5, "target": 24.0}


async def test_a_failing_reason_does_not_break_the_state(hass, monkeypatch, caplog):
    monkeypatch.setattr(
        "custom_components.smartheatzones.climate.decision_reason", lambda **kw: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    await setup_zone(hass, temp="20.7")
    hass.states.async_set(SENSOR, "20.8")
    await hass.async_block_till_done()

    assert hass.states.get(CLIMATE).attributes["reason"] is None
    assert "boom" in caplog.text

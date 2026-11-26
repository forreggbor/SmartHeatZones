"""Overview entity: one sensor with the state of the whole heating system."""
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.smartheatzones import overview as overview_module
from custom_components.smartheatzones.const import (
    CONF_BOILER_MAIN,
    CONF_IS_COMMON_SETTINGS,
    DATA_BOILER_MAIN,
    DOMAIN,
)

from .test_failsafe import BOILER, CLIMATE, SENSOR, advance, setup_zone
from .test_zone_snapshot import ZONE_KEYS

OVERVIEW = "sensor.smartheatzones_overview"


@pytest.fixture(autouse=True)
def switches(hass):
    """Recorded switch calls."""
    return async_mock_service(hass, "switch", "turn_on"), async_mock_service(hass, "switch", "turn_off")


def common_entry(hass):
    """The common settings config entry."""
    return next(e for e in hass.config_entries.async_entries(DOMAIN) if e.data.get(CONF_IS_COMMON_SETTINGS))


def boiler_of(hass):
    """The shared boiler manager."""
    return hass.data[DOMAIN][DATA_BOILER_MAIN]


def data(hass) -> dict:
    """Attributes of the overview entity."""
    return hass.states.get(OVERVIEW).attributes


async def test_entity_exists_with_the_full_contract(hass, freezer):
    await setup_zone(hass, temp="23.0")
    assert hass.states.get(OVERVIEW) is not None  # the entity exists as soon as the common entry is loaded
    await advance(hass, freezer, seconds=2)  # the zone registering schedules one coalesced refresh

    state = hass.states.get(OVERVIEW)

    assert state.state == "off"
    assert state.attributes["schema"] == 1
    assert state.attributes["boiler"]["entity"] == BOILER  # before any zone asked for heat
    assert [z["name"] for z in state.attributes["zones"]] == ["Living"]
    assert set(state.attributes["zones"][0]) == ZONE_KEYS


async def test_state_is_on_while_the_boiler_runs(hass, freezer):
    await setup_zone(hass, temp="19.0")  # cold: the zone heats
    await advance(hass, freezer, seconds=2)

    assert hass.states.get(OVERVIEW).state == "on"
    assert data(hass)["boiler"]["held_by"] == ["Living"]
    assert data(hass)["boiler"]["running"] is True


async def test_a_zone_state_change_refreshes_within_the_coalescing_time(hass, freezer):
    await setup_zone(hass, temp="23.0")
    await advance(hass, freezer, seconds=2)
    assert data(hass)["zones"][0]["hvac_action"] == "idle"

    hass.states.async_set(SENSOR, "19.0")  # cold: the zone starts heating and writes its state
    await hass.async_block_till_done()
    await advance(hass, freezer, seconds=2)

    assert data(hass)["zones"][0]["hvac_action"] == "heating"
    assert data(hass)["zones"][0]["current"] == 19.0


async def test_the_interval_refreshes_without_any_event(hass, freezer):
    await setup_zone(hass, temp="23.0")
    updated = data(hass)["updated"]

    await advance(hass, freezer, seconds=61)

    assert data(hass)["updated"] != updated


async def test_a_preset_change_refreshes_without_a_boiler_change(hass, freezer):
    await setup_zone(hass, temp="23.0")
    await hass.services.async_call("climate", "set_preset_mode", {"entity_id": CLIMATE, "preset_mode": "eco"}, blocking=True)
    await advance(hass, freezer, seconds=2)

    assert data(hass)["zones"][0]["preset"] == "eco"


async def test_zero_zones(hass):
    from .test_failsafe import MockConfigEntry
    from custom_components.smartheatzones.const import CONF_HYSTERESIS, CONF_OVERHEAT_PROTECTION

    common = MockConfigEntry(
        domain=DOMAIN, title="Common", version=2,
        data={CONF_IS_COMMON_SETTINGS: True, CONF_BOILER_MAIN: BOILER, CONF_HYSTERESIS: 0.5, CONF_OVERHEAT_PROTECTION: 26.0},
    )
    common.add_to_hass(hass)
    assert await hass.config_entries.async_setup(common.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(OVERVIEW).state == "off"
    assert data(hass)["zones"] == []
    assert data(hass)["health"]["groups"] == {}


async def test_removing_the_zone_empties_the_zones(hass, freezer):
    zone = await setup_zone(hass, temp="23.0")

    await hass.config_entries.async_remove(zone.entry_id)
    await advance(hass, freezer, seconds=2)

    assert hass.states.get(OVERVIEW) is not None
    assert hass.states.get(OVERVIEW).state != "unavailable"
    assert data(hass)["zones"] == []


async def test_health_groups_have_totals_and_no_entity_lists(hass, freezer):
    await setup_zone(hass, temp="23.0")
    await advance(hass, freezer, seconds=2)

    groups = data(hass)["health"]["groups"]

    assert groups == {"unregistered": {"total": 1, "bad": 0}}


async def test_unloading_the_common_entry_removes_the_entity_and_a_reload_keeps_one(hass):
    await setup_zone(hass, temp="23.0")
    common = common_entry(hass)
    assert len(boiler_of(hass)._listeners) == 1

    assert await hass.config_entries.async_reload(common.entry_id)
    await hass.async_block_till_done()
    assert len(boiler_of(hass)._listeners) == 1
    assert len([s for s in hass.states.async_all("sensor") if s.entity_id == OVERVIEW]) == 1

    assert await hass.config_entries.async_unload(common.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(OVERVIEW).state == "unavailable"  # removed entities report unavailable until the registry drops them
    assert len(boiler_of(hass)._listeners) == 0


async def test_a_failing_build_makes_the_entity_unavailable_and_recovers(hass, freezer, monkeypatch, caplog):
    await setup_zone(hass, temp="23.0")
    real = overview_module.build_overview

    def broken(*args, **kwargs):
        raise RuntimeError("build broke")

    monkeypatch.setattr("custom_components.smartheatzones.sensor.build_overview", broken)
    await advance(hass, freezer, seconds=61)
    assert hass.states.get(OVERVIEW).state == "unavailable"
    assert "build broke" in caplog.text

    monkeypatch.setattr("custom_components.smartheatzones.sensor.build_overview", real)
    await advance(hass, freezer, seconds=61)
    assert hass.states.get(OVERVIEW).state == "off"


async def test_boiler_entity_comes_from_the_manager_when_registered(hass):
    await setup_zone(hass, temp="23.0")
    boiler_of(hass)._boiler_entity_id = None  # the zone registered the configured boiler at setup
    await boiler_of(hass).register_boiler("switch.other_boiler")

    built = overview_module.build_overview(hass, boiler_of(hass), __import__("homeassistant.util.dt", fromlist=["x"]).utcnow())

    assert built["boiler"]["entity"] == "switch.other_boiler"


async def test_boiler_entity_falls_back_to_the_options_before_the_data(hass):
    await setup_zone(hass, temp="23.0")
    boiler = boiler_of(hass)
    boiler._boiler_entity_id = None
    hass.config_entries.async_update_entry(common_entry(hass), options={CONF_BOILER_MAIN: "switch.from_options"})

    built = overview_module.build_overview(hass, boiler, __import__("homeassistant.util.dt", fromlist=["x"]).utcnow())

    assert built["boiler"]["entity"] == "switch.from_options"

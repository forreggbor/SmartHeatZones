"""Limp / backup settings: validation, inheritance, cleared fields, applying common changes to zones."""
import logging
from unittest.mock import AsyncMock, patch

from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.smartheatzones.const import (
    CONF_BACKUP_SENSOR,
    CONF_BACKUP_SENSOR_OFFSET,
    CONF_HEATING_MODE,
    CONF_IS_COMMON_SETTINGS,
    CONF_LIMP_ON,
    CONF_LIMP_OUTDOOR_CUTOFF,
    CONF_LIMP_PERIOD,
    CONF_LIMP_RADIATOR_ON,
    CONF_LIMP_RADIATOR_PERIOD,
    CONF_LIMP_UNDERFLOOR_ON,
    CONF_LIMP_UNDERFLOOR_PERIOD,
    CONF_OUTDOOR_BACKUP_SENSOR,
    CONF_SENSOR,
    CONF_ZONE_RELAYS,
    DATA_BOILER_MAIN,
    DOMAIN,
    HEATING_MODE_UNDERFLOOR,
)
from custom_components.smartheatzones.limp import (
    ERR_LIMP_ON_EXCEEDS_PERIOD,
    ERR_LIMP_PAIR_REQUIRED,
    ERR_LIMP_PERIOD_RANGE,
    apply_optional_fields,
    resolve_limp,
    validate_common_limp,
    validate_limp_pair,
    validate_zone_limp,
)

from .test_failsafe import BOILER, CLIMATE, RELAY, SENSOR, setup_zone


def common_entry(hass) -> MockConfigEntry:
    """The common settings config entry of the running integration."""
    return next(e for e in hass.config_entries.async_entries(DOMAIN) if e.data.get(CONF_IS_COMMON_SETTINGS))


def test_validate_limp_pair():
    assert validate_limp_pair(10, 60) is None
    assert validate_limp_pair(0, 60) is None  # 0 = no heating
    assert validate_limp_pair(60, 60) is None
    assert validate_limp_pair(61, 60) == ERR_LIMP_ON_EXCEEDS_PERIOD
    assert validate_limp_pair(-1, 60) == ERR_LIMP_ON_EXCEEDS_PERIOD
    assert validate_limp_pair(5, 9) == ERR_LIMP_PERIOD_RANGE
    assert validate_limp_pair(5, 721) == ERR_LIMP_PERIOD_RANGE
    assert validate_limp_pair(5.5, 60) == ERR_LIMP_PERIOD_RANGE
    assert validate_limp_pair("x", 60) == ERR_LIMP_PERIOD_RANGE


def test_validate_form_inputs():
    assert validate_common_limp({}) == {}
    assert validate_common_limp({CONF_LIMP_RADIATOR_ON: 90}) == {CONF_LIMP_RADIATOR_PERIOD: ERR_LIMP_ON_EXCEEDS_PERIOD}
    assert validate_common_limp({CONF_LIMP_UNDERFLOOR_PERIOD: 5}) == {CONF_LIMP_UNDERFLOOR_PERIOD: ERR_LIMP_PERIOD_RANGE}
    assert validate_zone_limp({}) == {}
    assert validate_zone_limp({CONF_LIMP_ON: 0, CONF_LIMP_PERIOD: 60}) == {}
    assert validate_zone_limp({CONF_LIMP_ON: 5}) == {CONF_LIMP_PERIOD: ERR_LIMP_PAIR_REQUIRED}
    assert validate_zone_limp({CONF_LIMP_ON: 70, CONF_LIMP_PERIOD: 60}) == {CONF_LIMP_PERIOD: ERR_LIMP_ON_EXCEEDS_PERIOD}


def test_resolve_limp_order_override_then_mode_profile_then_defaults():
    common = {CONF_LIMP_RADIATOR_ON: 12, CONF_LIMP_RADIATOR_PERIOD: 90, CONF_LIMP_UNDERFLOOR_ON: 30, CONF_LIMP_UNDERFLOOR_PERIOD: 120}
    assert resolve_limp({}, {}, "radiator", "Z") == (10, 60)  # defaults
    assert resolve_limp({}, {}, HEATING_MODE_UNDERFLOOR, "Z") == (40, 180)
    assert resolve_limp(common, {}, "radiator", "Z") == (12, 90)  # mode profile
    assert resolve_limp(common, {}, HEATING_MODE_UNDERFLOOR, "Z") == (30, 120)
    assert resolve_limp(common, {CONF_LIMP_ON: 5, CONF_LIMP_PERIOD: 30}, "radiator", "Z") == (5, 30)  # zone override
    assert resolve_limp(common, {CONF_LIMP_ON: 0, CONF_LIMP_PERIOD: 30}, "radiator", "Z") == (0, 30)  # override to "off"


def test_resolve_limp_invalid_stored_values_fall_back_loudly(caplog):
    with caplog.at_level(logging.WARNING):
        assert resolve_limp({CONF_LIMP_RADIATOR_ON: 999}, {}, "radiator", "Z") == (10, 60)
        assert resolve_limp({}, {CONF_LIMP_ON: 80, CONF_LIMP_PERIOD: 60}, "radiator", "Z") == (10, 60)
    assert "Invalid limp profile" in caplog.text and "Invalid limp override" in caplog.text


def test_apply_optional_fields_removes_cleared_keys_and_nulls_the_marked_ones():
    data = {"a": 1, "b": 2, "c": 3, "d": 0}
    apply_optional_fields(data, {"a": 5, "d": 0.0}, ["a", "b", "c", "d"], null_keys=["c"])
    assert data == {"a": 5, "c": None, "d": 0.0}  # b removed, c explicit None, 0 is a real value


async def test_zone_gets_the_inherited_and_overridden_profile(hass):
    async_mock_service(hass, "switch", "turn_on")
    async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="21.0")
    attrs = hass.states.get(CLIMATE).attributes
    assert (attrs["limp_on_minutes"], attrs["limp_period_minutes"]) == (10, 60)


async def test_zone_override_wins_over_the_common_profile(hass):
    async_mock_service(hass, "switch", "turn_on")
    async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="21.0", zone_extra={CONF_LIMP_ON: 7, CONF_LIMP_PERIOD: 45})
    attrs = hass.states.get(CLIMATE).attributes
    assert (attrs["limp_on_minutes"], attrs["limp_period_minutes"]) == (7, 45)


async def test_a_common_settings_change_reaches_a_running_zone(hass):
    async_mock_service(hass, "switch", "turn_on")
    async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="21.0")
    common = common_entry(hass)
    hass.config_entries.async_update_entry(common, options={**common.data, CONF_LIMP_RADIATOR_ON: 20})
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE).attributes["limp_on_minutes"] == 20
    assert hass.data[DOMAIN]  # the common entry itself was not reloaded away


async def test_a_zone_that_fails_to_reload_does_not_stop_the_others(hass, caplog):
    async_mock_service(hass, "switch", "turn_on")
    async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="21.0")
    second = MockConfigEntry(
        domain=DOMAIN, title="Bath", version=2,
        data={CONF_SENSOR: "sensor.bath_temp", CONF_ZONE_RELAYS: ["switch.bath_relay"]},
    )
    hass.states.async_set("sensor.bath_temp", "21.0")
    hass.states.async_set("switch.bath_relay", "off")
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()

    common = common_entry(hass)
    reload_mock = AsyncMock(side_effect=[RuntimeError("boom"), True])
    with patch.object(hass.config_entries, "async_reload", reload_mock), caplog.at_level(logging.INFO):
        hass.config_entries.async_update_entry(common, options={**common.data, CONF_LIMP_RADIATOR_ON: 15})
        await hass.async_block_till_done()
    assert reload_mock.await_count == 2
    assert "FAILED" in caplog.text and "reloaded 1 of 2 zones" in caplog.text


async def test_common_options_flow_clears_removed_fields_and_stores_a_disabled_cutoff(hass):
    async_mock_service(hass, "switch", "turn_on")
    async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="21.0")
    common = common_entry(hass)
    hass.config_entries.async_update_entry(
        common, options={**common.data, CONF_OUTDOOR_BACKUP_SENSOR: "weather.home", CONF_LIMP_OUTDOOR_CUTOFF: 12.0}
    )
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(common.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"boiler_main": BOILER, "outdoor_temp_sensor": "sensor.outdoor", "hysteresis": 0.5, "overheat_temp": 26.0}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert CONF_OUTDOOR_BACKUP_SENSOR not in common.options  # cleared field really disappeared
    assert common.options[CONF_LIMP_OUTDOOR_CUTOFF] is None  # explicit "disabled"


async def test_common_options_flow_rejects_an_invalid_profile(hass):
    async_mock_service(hass, "switch", "turn_on")
    async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="21.0")
    common = common_entry(hass)
    result = await hass.config_entries.options.async_init(common.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"boiler_main": BOILER, "outdoor_temp_sensor": "sensor.outdoor", CONF_LIMP_UNDERFLOOR_ON: 200, CONF_LIMP_UNDERFLOOR_PERIOD: 100},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_LIMP_UNDERFLOOR_PERIOD: ERR_LIMP_ON_EXCEEDS_PERIOD}


async def test_zone_options_flow_clears_backup_and_override_and_validates_the_pair(hass):
    async_mock_service(hass, "switch", "turn_on")
    async_mock_service(hass, "switch", "turn_off")
    zone = await setup_zone(
        hass, temp="21.0",
        zone_extra={CONF_BACKUP_SENSOR: "sensor.other", CONF_BACKUP_SENSOR_OFFSET: -2.0, CONF_LIMP_ON: 7, CONF_LIMP_PERIOD: 45},
    )
    base = {CONF_HEATING_MODE: "radiator", "thermostat_type": "wall", "sensor_entity_id": SENSOR, "relay_entities": [RELAY]}

    result = await hass.config_entries.options.async_init(zone.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input={**base, CONF_LIMP_ON: 7})
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_LIMP_PERIOD: ERR_LIMP_PAIR_REQUIRED}

    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input=base)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    for key in (CONF_BACKUP_SENSOR, CONF_BACKUP_SENSOR_OFFSET, CONF_LIMP_ON, CONF_LIMP_PERIOD):
        assert key not in zone.options
    attrs = hass.states.get(CLIMATE).attributes
    assert (attrs["limp_on_minutes"], attrs["limp_period_minutes"]) == (10, 60)  # inherited again


async def test_boiler_mismatch_is_logged_once(hass, caplog):
    async_mock_service(hass, "switch", "turn_on")
    async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="19.0")  # registers switch.boiler
    boiler = hass.data[DOMAIN][DATA_BOILER_MAIN]
    with caplog.at_level(logging.WARNING):
        await boiler.turn_on("switch.other_boiler", zone="Bath")
        await boiler.turn_on("switch.other_boiler", zone="Bath")
    assert caplog.text.count("needs a Home Assistant restart") == 1

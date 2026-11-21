"""A relay that drops off the network (wifi outage) is not a manual override (issue #22)."""
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.smartheatzones.const import DATA_BOILER_MAIN, DOMAIN

from .test_failsafe import BOILER, CLIMATE, RELAY, SENSOR, commands, setup_zone


def attrs(hass: HomeAssistant) -> dict:
    """Attributes of the zone's climate entity."""
    return hass.states.get(CLIMATE).attributes


async def test_relay_going_unavailable_is_not_a_manual_override(hass):
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="19.0")
    assert attrs(hass)["hvac_action"] == "heating"
    boiler_off_before = len(commands(off, BOILER))

    hass.states.async_set(RELAY, "on")
    await hass.async_block_till_done()
    hass.states.async_set(RELAY, "unavailable")
    await hass.async_block_till_done()

    assert attrs(hass)["hvac_action"] == "heating"  # still the zone's own decision
    assert len(commands(off, BOILER)) == boiler_off_before  # boiler not released
    assert attrs(hass)["relay_unavailable"] == [RELAY]


async def test_relay_back_on_while_the_zone_wants_off_is_switched_off(hass):
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="19.0")
    hass.states.async_set(RELAY, "on")
    await hass.async_block_till_done()

    hass.states.async_set(RELAY, "unavailable")
    await hass.async_block_till_done()
    hass.states.async_set(SENSOR, "23.0")  # warm -> the zone wants heating off
    await hass.async_block_till_done()
    assert attrs(hass)["hvac_action"] == "idle"
    off_before = len(commands(off, RELAY))

    hass.states.async_set(RELAY, "on")  # the relay kept its old state during the outage
    await hass.async_block_till_done()
    assert len(commands(off, RELAY)) == off_before + 1
    assert attrs(hass)["hvac_action"] == "idle"
    assert attrs(hass)["relay_unavailable"] == []


async def test_relay_back_off_while_the_zone_wants_heat_is_switched_on(hass):
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="19.0")
    hass.states.async_set(RELAY, "on")
    await hass.async_block_till_done()

    hass.states.async_set(RELAY, "unavailable")
    await hass.async_block_till_done()
    on_before = len(commands(on, RELAY))

    hass.states.async_set(RELAY, "off")  # came back off, but the room is still cold
    await hass.async_block_till_done()
    assert len(commands(on, RELAY)) == on_before + 1
    assert attrs(hass)["hvac_action"] == "heating"


async def test_relay_unavailable_at_startup_is_listed_and_taken_over_without_a_reading(hass):
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="unknown", relay="unavailable")
    assert attrs(hass)["relay_unavailable"] == [RELAY]
    assert attrs(hass)["hvac_action"] == "idle"

    hass.states.async_set(RELAY, "on")  # it was running before the restart
    await hass.async_block_till_done()
    assert attrs(hass)["hvac_action"] == "heating"  # taken over, not switched off
    assert commands(off, RELAY) == []
    assert attrs(hass)["relay_unavailable"] == []


async def test_a_genuine_manual_switch_is_still_detected(hass):
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    await setup_zone(hass, temp="19.0")
    hass.states.async_set(RELAY, "on")
    await hass.async_block_till_done()
    assert attrs(hass)["hvac_action"] == "heating"

    hass.states.async_set(RELAY, "off")  # someone switches the relay off by hand
    await hass.async_block_till_done()
    assert attrs(hass)["hvac_action"] == "idle"
    assert len(commands(off, BOILER)) == 1


async def test_stale_boiler_membership_is_released_at_setup(hass):
    """A reload leaves the zone registered at the boiler manager; a zone that is not heating must let go."""
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    zone = await setup_zone(hass, temp="23.0")  # warm, not heating
    boiler = hass.data[DOMAIN][DATA_BOILER_MAIN]
    await boiler.register_boiler(BOILER)  # registered by the zone's earlier heating
    boiler._active_zones.add("Living")  # left behind by the previous (unloaded) entity
    boiler_off_before = len(commands(off, BOILER))

    assert await hass.config_entries.async_reload(zone.entry_id)
    await hass.async_block_till_done()

    assert boiler.get_active_zones() == []
    assert len(commands(off, BOILER)) == boiler_off_before + 1

"""Documents what Home Assistant does when switch.turn_off targets an unavailable switch."""
from homeassistant.components import switch
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockEntityPlatform, MockToggleEntity


async def test_service_call_to_an_unavailable_switch(hass):
    assert await async_setup_component(hass, "switch", {})
    entity = MockToggleEntity("relay", "on")
    entity._attr_available = False
    platform = MockEntityPlatform(hass, domain="switch")
    await platform.async_add_entities([entity])
    entity.entity_id = "switch.relay"
    await hass.async_block_till_done()
    assert hass.states.get("switch.relay").state == "unavailable"

    # No exception and no effect: the command is silently dropped, so the zone's retry list never fills.
    # This is why a relay that comes back is sent the zone's wanted state (see climate._relay_recovered).
    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.relay"}, blocking=True)
    assert entity.state == "on"

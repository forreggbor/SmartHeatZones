"""Shared sensor-health helpers: sensor problems, outdoor chain, outdoor estimate, groups."""
from datetime import timedelta

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartheatzones.const import (
    LIMP_OUTDOOR_MAX_AGE,
    OUTDOOR_ESTIMATE_MAX_AGE,
    SENSOR_UNAVAILABLE_GRACE,
)
from custom_components.smartheatzones.sensor_health import (
    OutdoorWindow,
    effective_outdoor,
    group_overview,
    outdoor_multiplier,
    read_outdoor,
    sensor_problem,
)

SENSOR = "sensor.t"
OUT = "sensor.outdoor"
WEATHER = "weather.home"
STALE = timedelta(hours=2)


def test_outdoor_multiplier_bands():
    assert outdoor_multiplier(-15) == 2.0
    assert outdoor_multiplier(-10) == 1.5  # boundary belongs to the warmer band
    assert outdoor_multiplier(-1) == 1.5
    assert outdoor_multiplier(0) == 1.2
    assert outdoor_multiplier(9.9) == 1.2
    assert outdoor_multiplier(10) == 1.0
    assert outdoor_multiplier(30) == 1.0


async def test_sensor_problem_unavailable_needs_the_grace_period(hass):
    now = dt_util.utcnow()
    hass.states.async_set(SENSOR, "unavailable")
    problem, since = sensor_problem(hass, SENSOR, STALE, None, now)
    assert problem is None and since == now  # clock starts

    problem, since = sensor_problem(hass, SENSOR, STALE, since, now + SENSOR_UNAVAILABLE_GRACE)
    assert problem == "sensor_unavailable" and since == now

    hass.states.async_set(SENSOR, "20.0")
    problem, since = sensor_problem(hass, SENSOR, STALE, since, now + SENSOR_UNAVAILABLE_GRACE)
    assert problem is None and since is None  # readable again resets the clock


async def test_sensor_problem_stale_uses_last_reported(hass):
    hass.states.async_set(SENSOR, "20.0")
    state = hass.states.get(SENSOR)
    now = state.last_updated + STALE - timedelta(seconds=1)
    assert sensor_problem(hass, SENSOR, STALE, None, now) == (None, None)
    assert sensor_problem(hass, SENSOR, STALE, None, now + timedelta(seconds=1)) == ("sensor_stale", None)

    # a repeated identical value only updates last_reported and still counts as alive
    hass.states.async_set(SENSOR, "20.0")
    later = state.last_updated + STALE + timedelta(minutes=5)
    hass.states.async_set(SENSOR, "20.0")
    fresh = hass.states.get(SENSOR)
    assert sensor_problem(hass, SENSOR, STALE, None, fresh.last_reported + timedelta(minutes=30)) == (None, None)
    assert later > state.last_updated


def _register_device_sensors(hass, *object_ids):
    """Register sensors that belong to one device (as an MQTT/Zigbee2MQTT device would expose them)."""
    entry = MockConfigEntry(domain="mqtt")
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("mqtt", "zigbee2mqtt_0x1234")}
    )
    registry = er.async_get(hass)
    return [
        registry.async_get_or_create(
            "sensor", "mqtt", object_id, config_entry=entry, device_id=device.id, suggested_object_id=object_id
        ).entity_id
        for object_id in object_ids
    ]


async def test_sensor_problem_unchanged_value_with_a_reporting_device_is_not_stale(hass, freezer):
    """Regression #28: MQTT does not rewrite an unchanged temperature, but the device's other sensors report."""
    temp, humidity = _register_device_sensors(hass, "room_temperature", "room_humidity")
    hass.states.async_set(temp, "23.3")
    hass.states.async_set(humidity, "54")
    freezer.tick(STALE - timedelta(minutes=5))
    hass.states.async_set(humidity, "55")  # the device is alive, the temperature did not change
    freezer.tick(timedelta(minutes=10))
    assert sensor_problem(hass, temp, STALE, None, dt_util.utcnow()) == (None, None)
    groups = group_overview(hass, [temp], STALE, dt_util.utcnow())
    assert [group["bad"] for group in groups.values()] == [0]


async def test_sensor_problem_silent_device_is_stale(hass, freezer):
    """A dead battery silences every sensor of the device: still detected."""
    temp, humidity = _register_device_sensors(hass, "room_temperature", "room_humidity")
    hass.states.async_set(temp, "23.3")
    hass.states.async_set(humidity, "54")
    freezer.tick(STALE)
    assert sensor_problem(hass, temp, STALE, None, dt_util.utcnow()) == ("sensor_stale", None)


async def test_sensor_problem_unavailable_sibling_does_not_keep_the_sensor_alive(hass, freezer):
    temp, humidity = _register_device_sensors(hass, "room_temperature", "room_humidity")
    hass.states.async_set(temp, "23.3")
    freezer.tick(STALE)
    hass.states.async_set(humidity, "unavailable")
    assert sensor_problem(hass, temp, STALE, None, dt_util.utcnow()) == ("sensor_stale", None)


async def test_sensor_problem_without_an_entity_is_fine(hass):
    assert sensor_problem(hass, None, STALE, None, dt_util.utcnow()) == (None, None)


async def test_read_outdoor_sensor_and_weather(hass):
    now = dt_util.utcnow()
    hass.states.async_set(OUT, "-3.5")
    assert read_outdoor(hass, OUT, now) == -3.5
    hass.states.async_set(OUT, "unavailable")
    assert read_outdoor(hass, OUT, now) is None
    hass.states.async_set(OUT, "oops")
    assert read_outdoor(hass, OUT, now) is None
    assert read_outdoor(hass, "sensor.missing", now) is None
    assert read_outdoor(hass, None, now) is None

    hass.states.async_set(WEATHER, "cloudy", {"temperature": 4.0, "temperature_unit": "°C"})
    assert read_outdoor(hass, WEATHER, now) == 4.0
    hass.states.async_set(WEATHER, "cloudy", {"temperature": 39.0, "temperature_unit": "°F"})
    assert read_outdoor(hass, WEATHER, now) is None  # only °C is supported
    hass.states.async_set(WEATHER, "cloudy", {})
    assert read_outdoor(hass, WEATHER, now) is None


async def test_read_outdoor_rejects_an_old_value(hass):
    hass.states.async_set(OUT, "5.0")
    state = hass.states.get(OUT)
    assert read_outdoor(hass, OUT, state.last_updated + LIMP_OUTDOOR_MAX_AGE) == 5.0
    assert read_outdoor(hass, OUT, state.last_updated + LIMP_OUTDOOR_MAX_AGE + timedelta(seconds=1)) is None


def test_outdoor_window_needs_samples_and_span():
    base = dt_util.utcnow()
    window = OutdoorWindow()
    window.add(base, 5.0)
    window.add(base + timedelta(hours=1), 3.0)
    assert window.estimate(base + timedelta(hours=1)) is None  # fewer than 3 samples
    window.add(base + timedelta(hours=2), 8.0)
    assert window.estimate(base + timedelta(hours=2)) is None  # span under 12 h
    window.add(base + timedelta(hours=13), 9.0)
    assert window.estimate(base + timedelta(hours=13)) == 3.0  # minimum of the day


def test_outdoor_window_keeps_the_last_day_during_a_long_outage():
    base = dt_util.utcnow()
    window = OutdoorWindow()
    for hours, value in ((0, 8.0), (6, -9.0), (12, 2.0), (20, 6.0)):
        window.add(base + timedelta(hours=hours), value)
    last = base + timedelta(hours=20)
    assert window.estimate(last + timedelta(days=3)) == -9.0  # window did not drain
    assert window.estimate(last + OUTDOOR_ESTIMATE_MAX_AGE) == -9.0
    assert window.estimate(last + OUTDOOR_ESTIMATE_MAX_AGE + timedelta(seconds=1)) is None


def test_outdoor_window_drops_samples_older_than_24_hours():
    base = dt_util.utcnow()
    window = OutdoorWindow()
    window.add(base, -20.0)  # will fall out of the window
    for hours, value in ((10, 4.0), (20, 6.0), (30, 5.0)):
        window.add(base + timedelta(hours=hours), value)
    assert window.estimate(base + timedelta(hours=30)) == 4.0


async def test_effective_outdoor_chain(hass):
    now = dt_util.utcnow()
    window = OutdoorWindow()
    for hours, value in ((-20, -8.0), (-10, 1.0), (-1, 3.0)):
        window.add(now + timedelta(hours=hours), value)

    hass.states.async_set(OUT, "2.0")
    hass.states.async_set(WEATHER, "sunny", {"temperature": 7.0, "temperature_unit": "°C"})
    assert effective_outdoor(hass, OUT, WEATHER, window, now) == (2.0, "live")

    hass.states.async_set(OUT, "unavailable")
    assert effective_outdoor(hass, OUT, WEATHER, window, now) == (7.0, "backup")

    hass.states.async_set(WEATHER, "unavailable")
    assert effective_outdoor(hass, OUT, WEATHER, window, now) == (-8.0, "estimate")

    assert effective_outdoor(hass, OUT, WEATHER, OutdoorWindow(), now) == (None, "none")


async def test_group_overview_groups_by_integration_and_counts_bad_sensors(hass):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    now = dt_util.utcnow()
    entry_a = MockConfigEntry(domain="zha")
    entry_b = MockConfigEntry(domain="shelly")
    entry_a.add_to_hass(hass)
    entry_b.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create("sensor", "zha", "a1", config_entry=entry_a, suggested_object_id="a1")
    registry.async_get_or_create("sensor", "zha", "a2", config_entry=entry_a, suggested_object_id="a2")
    registry.async_get_or_create("sensor", "shelly", "b1", config_entry=entry_b, suggested_object_id="b1")
    hass.states.async_set("sensor.a1", "unavailable")
    hass.states.async_set("sensor.a2", "unknown")
    hass.states.async_set("sensor.b1", "21.0")
    hass.states.async_set("sensor.loose", "20.0")

    groups = group_overview(hass, ["sensor.a1", "sensor.a2", "sensor.b1", "sensor.loose", "sensor.a1", ""], STALE, now)
    zha = groups[f"zha/{entry_a.entry_id}"]
    assert zha["total"] == 2 and zha["bad"] == 2 and sorted(zha["bad_entities"]) == ["sensor.a1", "sensor.a2"]
    assert groups[f"shelly/{entry_b.entry_id}"]["bad"] == 0
    assert groups["unregistered"]["total"] == 1

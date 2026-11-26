"""
SmartHeatZones - Sensor health helpers


Stateless helpers shared by the zone thermostat (primary and backup sensor), the limp mode and the
fault diagnostics:
- sensor_problem(): is a temperature sensor trustworthy (unavailable / silent)?
- outdoor_multiplier(): outdoor-temperature band multiplier (adaptive hysteresis and limp duty)
- effective_outdoor() + OutdoorWindow: outdoor temperature when the outdoor sensor may be gone
- group_overview(): which sensors share an integration, and how many of them are silent
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Optional

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er

from .const import (
    ADAPTIVE_HYSTERESIS_MULTIPLIERS,
    LIMP_OUTDOOR_MAX_AGE,
    LOG_PREFIX,
    OUTDOOR_ESTIMATE_MAX_AGE,
    OUTDOOR_ESTIMATE_MIN_SAMPLES,
    OUTDOOR_ESTIMATE_MIN_SPAN,
    OUTDOOR_SOURCE_BACKUP,
    OUTDOOR_SOURCE_ESTIMATE,
    OUTDOOR_SOURCE_LIVE,
    OUTDOOR_SAMPLE_BUCKET,
    OUTDOOR_SOURCE_NONE,
    OUTDOOR_WINDOW,
    SENSOR_BAD_STATES,
    SENSOR_UNAVAILABLE_GRACE,
)

_LOGGER = logging.getLogger(__name__)

_WARNED_UNITS: set[str] = set()  # weather entities already reported for a non-Celsius unit


def _last_seen(state: State) -> datetime:
    """When the entity last reported anything (a repeated identical value counts as a report)."""
    return max(state.last_updated, getattr(state, "last_reported", state.last_updated))


def _device_last_seen(hass: HomeAssistant, entity_id: str, state: State) -> datetime:
    """
    When the sensor or any other readable sensor of the same device last reported anything.

    An MQTT entity (e.g. Zigbee2MQTT) does not rewrite an unchanged value, so a stable temperature
    never advances last_reported although the device keeps reporting (humidity, link quality, ...).
    A dead battery or a lost device silences all of its sensors, so that is still detected.
    """
    seen = _last_seen(state)
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry is None or entry.device_id is None:
        return seen
    for sibling in er.async_entries_for_device(registry, entry.device_id):
        if sibling.domain != "sensor" or sibling.entity_id == entity_id:
            continue
        sibling_state = hass.states.get(sibling.entity_id)
        if sibling_state is not None and sibling_state.state not in SENSOR_BAD_STATES:
            seen = max(seen, _last_seen(sibling_state))
    return seen


def _readable_number(state: Optional[State]) -> Optional[float]:
    """The numeric value of a sensor state, or None when it is missing, unavailable or not a number."""
    if state is None or state.state in SENSOR_BAD_STATES:
        return None
    try:
        return float(state.state)
    except (ValueError, TypeError):
        return None


def sensor_problem(
    hass: HomeAssistant,
    entity_id: Optional[str],
    stale_timeout: timedelta,
    bad_since: Optional[datetime],
    now: datetime,
) -> tuple[Optional[str], Optional[datetime]]:
    """
    Why a temperature sensor cannot be trusted right now, or None when it is fine.

    - "sensor_unavailable": no readable value for longer than SENSOR_UNAVAILABLE_GRACE
    - "sensor_stale": neither the sensor nor any other sensor of its device has reported anything for
      the silence limit (a dead battery usually leaves the last value in place instead of going
      unavailable)

    Returns (problem, new_bad_since). The caller stores bad_since: it is the start of the current
    "not readable" period and is reset as soon as a readable value is seen.
    """
    if not entity_id:
        return None, bad_since

    state = hass.states.get(entity_id)
    if _readable_number(state) is None:
        if bad_since is None:
            bad_since = now
        if now - bad_since >= SENSOR_UNAVAILABLE_GRACE:
            return "sensor_unavailable", bad_since
        return None, bad_since

    if now - _device_last_seen(hass, entity_id, state) >= stale_timeout:
        return "sensor_stale", None
    return None, None


def outdoor_multiplier(outdoor_temp: float) -> float:
    """Multiplier for an outdoor temperature (1.0 when it is mild)."""
    for temp_threshold, mult in sorted(ADAPTIVE_HYSTERESIS_MULTIPLIERS.items()):
        if outdoor_temp < temp_threshold:
            return mult
    return 1.0


class OutdoorWindow:
    """
    Cautious outdoor estimate: the minimum of the samples in the 24 h ending at the last valid sample.

    The window does not move while no data arrives, so a multi-day outage keeps using the last day's
    night low (which errs to the cold side). In memory only.
    """

    def __init__(self) -> None:
        self._samples: deque[tuple[datetime, float]] = deque()

    def add(self, when: datetime, value: float) -> None:
        """
        Record a valid outdoor reading and drop samples older than the window.

        Readings within OUTDOOR_SAMPLE_BUCKET of the previous sample are merged into it (keeping the
        minimum), so a chatty sensor cannot grow the window without bound.
        """
        if self._samples and when - self._samples[-1][0] < OUTDOOR_SAMPLE_BUCKET:
            start, lowest = self._samples[-1]
            self._samples[-1] = (start, min(lowest, value))
            return
        self._samples.append((when, value))
        while self._samples and self._samples[0][0] < when - OUTDOOR_WINDOW:
            self._samples.popleft()

    def estimate(self, now: datetime) -> Optional[float]:
        """The cautious estimate, or None when there is not enough (or too old) data."""
        if len(self._samples) < OUTDOOR_ESTIMATE_MIN_SAMPLES:
            return None
        first, last = self._samples[0][0], self._samples[-1][0]
        if last - first < OUTDOOR_ESTIMATE_MIN_SPAN or now - last > OUTDOOR_ESTIMATE_MAX_AGE:
            return None
        return min(value for _, value in self._samples)


def read_outdoor(hass: HomeAssistant, entity_id: Optional[str], now: datetime) -> Optional[float]:
    """
    A current outdoor temperature in °C from a sensor or a weather entity, or None.

    None when the entity is missing, unavailable, not a number, older than LIMP_OUTDOOR_MAX_AGE, or
    (weather entity) reports a unit other than °C.
    """
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None or state.state in SENSOR_BAD_STATES:
        return None
    if now - _device_last_seen(hass, entity_id, state) > LIMP_OUTDOOR_MAX_AGE:
        return None

    if entity_id.split(".", 1)[0] == "weather":
        unit = state.attributes.get("temperature_unit")
        if unit not in (None, "°C"):
            if entity_id not in _WARNED_UNITS:
                _WARNED_UNITS.add(entity_id)
                _LOGGER.warning(
                    "%s Outdoor backup %s reports %r, only °C is supported - ignoring it",
                    LOG_PREFIX, entity_id, unit
                )
            return None
        try:
            return float(state.attributes.get("temperature"))
        except (ValueError, TypeError):
            return None

    return _readable_number(state)


def effective_outdoor(
    hass: HomeAssistant,
    live_id: Optional[str],
    backup_id: Optional[str],
    window: OutdoorWindow,
    now: datetime,
) -> tuple[Optional[float], str]:
    """
    Best available outdoor temperature and where it came from.

    live sensor -> backup source -> cautious estimate -> none (the caller then uses its neutral default).
    """
    for source, entity_id in ((OUTDOOR_SOURCE_LIVE, live_id), (OUTDOOR_SOURCE_BACKUP, backup_id)):
        value = read_outdoor(hass, entity_id, now)
        if value is not None:
            return value, source
    estimate = window.estimate(now)
    if estimate is not None:
        return estimate, OUTDOOR_SOURCE_ESTIMATE
    return None, OUTDOOR_SOURCE_NONE


def group_overview(
    hass: HomeAssistant,
    entity_ids: list[str],
    stale_timeout: timedelta,
    now: datetime,
) -> dict[str, dict]:
    """
    Sensors grouped by integration (entity registry platform + config entry).

    Returns {group: {"total": n, "bad": n, "bad_entities": [...]}}. A sensor is bad when it is
    unavailable/unknown/not a number or silent for longer than stale_timeout. Used only to word the
    fault notification (many bad sensors in one group point at a network or coordinator problem).
    """
    registry = er.async_get(hass)
    groups: dict[str, dict] = {}
    for entity_id in dict.fromkeys(e for e in entity_ids if e):
        entry = registry.async_get(entity_id)
        key = f"{entry.platform}/{entry.config_entry_id}" if entry else "unregistered"
        group = groups.setdefault(key, {"total": 0, "bad": 0, "bad_entities": []})
        group["total"] += 1
        state = hass.states.get(entity_id)
        if _readable_number(state) is None or now - _device_last_seen(hass, entity_id, state) >= stale_timeout:
            group["bad"] += 1
            group["bad_entities"].append(entity_id)
    return groups

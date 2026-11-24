"""
SmartHeatZones - overview sensor.

One entity for the whole heating system: state "on" while the boiler runs, all data in the
attributes (contract: see overview.build_overview). Refreshed when a zone or the boiler changes
(coalesced to one refresh per second) and once a minute.
"""

import logging
from typing import Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.util import dt as dt_util

from .boiler_manager import BoilerManager
from .const import DATA_BOILER_MAIN, DOMAIN, LOG_PREFIX, OVERVIEW_REFRESH_INTERVAL
from .overview import build_overview

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Create the overview entity (common settings entry only)."""
    async_add_entities([OverviewSensor(hass, hass.data[DOMAIN][DATA_BOILER_MAIN])])


class OverviewSensor(SensorEntity):
    """Aggregated state of the boiler and all zones."""

    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_name = "SmartHeatZones overview"
    _attr_unique_id = "smartheatzones_overview"
    _attr_icon = "mdi:radiator"
    # The data is rebuilt every minute and is large: keep it out of the recorder (the card does not read its history)
    _unrecorded_attributes = frozenset({"schema", "updated", "boiler", "zones", "health"})

    def __init__(self, hass: HomeAssistant, boiler: BoilerManager):
        self.hass = hass
        self.entity_id = "sensor.smartheatzones_overview"
        self._boiler = boiler
        self._data: dict = {}
        self._pending: Optional[CALLBACK_TYPE] = None

    async def async_added_to_hass(self) -> None:
        """Build once, then follow the boiler, the zones and the clock."""
        self._build()
        self.async_write_ha_state()
        self.async_on_remove(self._boiler.add_listener(self._schedule))
        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._on_state, event_filter=self._is_zone_event)
        )
        self.async_on_remove(async_track_time_interval(self.hass, self._refresh, OVERVIEW_REFRESH_INTERVAL))
        self.async_on_remove(self._cancel_pending)

    @callback
    def _is_zone_event(self, event_data: dict) -> bool:
        """Event filter: only state changes of the zones' climate entities (looked up at event time)."""
        return event_data.get("entity_id") in {zone.entity_id for zone in self._boiler.get_zone_entities()}

    @callback
    def _on_state(self, _event) -> None:
        """A zone changed."""
        self._schedule()

    @callback
    def _schedule(self) -> None:
        """Refresh once, one second from now, however many changes arrive meanwhile."""
        if self._pending is None:
            self._pending = async_call_later(self.hass, 1, self._refresh)

    @callback
    def _cancel_pending(self) -> None:
        """Drop a pending refresh (entity removal)."""
        if self._pending is not None:
            self._pending()
            self._pending = None

    @callback
    def _refresh(self, _now=None) -> None:
        """Rebuild the data and publish it (a pending one-shot refresh is covered by this one)."""
        self._cancel_pending()
        self._build()
        self.async_write_ha_state()

    def _build(self) -> None:
        """Build the data; a failure is logged and the entity reports unavailable until the next good build."""
        try:
            self._data = build_overview(self.hass, self._boiler, dt_util.utcnow())
            self._attr_available = True
        except Exception:
            _LOGGER.exception("%s Building the overview FAILED", LOG_PREFIX)
            self._attr_available = False

    @property
    def native_value(self) -> str:
        """on while the boiler runs."""
        return "on" if self._data.get("boiler", {}).get("running") else "off"

    @property
    def extra_state_attributes(self) -> dict:
        """The overview contract."""
        return self._data

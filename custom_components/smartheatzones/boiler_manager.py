"""
SmartHeatZones - Boiler Manager
Version: 1.12.0

CHANGELOG v1.12.0 (FEATURE)
- Added: warning when a zone uses a different boiler switch than the registered one; zone entity snapshot for diagnostics
CHANGELOG v1.10.1 (SAFETY FIX)
- Fixed: a failed boiler command is retried (only while it is still the wanted one)

CHANGELOG v1.9.1 (BUGFIX)
- Fixed: Removing the outdoor temperature sensor is not removed from settings

Central boiler relay coordinator - manages shared boiler switch across all zones.

NEW in v1.9.0:
- Lovelace Dashboard Phase 1 (no changes to boiler manager)

NEW in v1.8.1:
- Piggyback heating: When boiler turns on, all zones with temp < target turn on immediately
"""

import logging
from datetime import datetime, time
from typing import Callable, Optional, TYPE_CHECKING
from homeassistant.core import Event, HassJob, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    DATA_BOILER_MAIN,
    LOG_PREFIX,
    ORPHAN_ZONE_RELEASE_DELAY,
    SENSOR_BAD_STATES,
)

if TYPE_CHECKING:
    from .climate import SmartHeatZoneClimate

_LOGGER = logging.getLogger(__name__)


class BoilerManager:
    """
    Központi kazánvezérlő osztály.

    Feladata:
      - közös kazán relé kezelése (pl. switch.shelly_2pm_relay_1)
      - aktív zónák számlálása
      - redundáns kapcsolások elkerülése
      - piggyback heating: más zónák bekapcsolása amikor a kazán már megy
    """

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._boiler_entity_id: Optional[str] = None
        self._boiler_unsub: Optional[Callable[[], None]] = None  # boiler switch state listener
        self._active_zones: set[str] = set()
        self._afterheat_zones: set[str] = set()  # active zones that only joined by afterheat (no real demand)
        self._zone_entities: dict[str, "SmartHeatZoneClimate"] = {}
        self._orphan_checks: dict[str, Callable[[], None]] = {}  # zone name -> cancel of its pending release
        self._failed_action: Optional[str] = None  # boiler command that failed and is retried
        self._mismatch_warned = False  # a differing boiler entity was already reported
        # Daily counters (in memory only): reset at local midnight, see stats()
        self._created = dt_util.now()
        self._counter_day = self._created.date()
        self._since: Optional[datetime] = None  # start of the current running period
        self._period_start: Optional[datetime] = None  # start of the running period inside the counter day
        self._runtime_s = 0.0
        self._starts = 0
        self._afterheat_joins = 0
        self._listeners: list[Callable[[], None]] = []
        _LOGGER.info("%s BoilerManager initialized", LOG_PREFIX)

    # --------------------------------------------------------------------------
    # Alapműveletek
    # --------------------------------------------------------------------------

    def register_zone_entity(self, zone_name: str, entity: "SmartHeatZoneClimate"):
        """Register a zone climate entity for piggyback heating (a reloaded zone cancels its pending release)."""
        cancel = self._orphan_checks.pop(zone_name, None)
        if cancel:
            cancel()
        self._zone_entities[zone_name] = entity
        _LOGGER.debug("%s Zone entity registered: %s", LOG_PREFIX, zone_name)
        self._notify()

    def get_zone_entities(self) -> list["SmartHeatZoneClimate"]:
        """All registered zone entities (a snapshot, safe to iterate across awaits)."""
        return list(self._zone_entities.values())

    def unregister_zone_entity(self, zone_name: str):
        """
        Unregister a zone climate entity.

        A zone that still holds the boiler keeps it for ORPHAN_ZONE_RELEASE_DELAY: a reload registers it
        again (the boiler keeps running), a deleted or renamed zone never does and then releases it.
        """
        if zone_name in self._zone_entities:
            del self._zone_entities[zone_name]
            _LOGGER.debug("%s Zone entity unregistered: %s", LOG_PREFIX, zone_name)
            self._notify()
        if zone_name in self._active_zones and zone_name not in self._orphan_checks:
            self._orphan_checks[zone_name] = async_call_later(
                self.hass, ORPHAN_ZONE_RELEASE_DELAY,
                HassJob(self._make_orphan_release(zone_name), cancel_on_shutdown=True),
            )

    def _make_orphan_release(self, zone_name: str) -> Callable:
        """The delayed release of a zone that was removed while it held the boiler."""

        @callback
        def release(_now) -> None:
            self._orphan_checks.pop(zone_name, None)
            if zone_name in self._zone_entities or zone_name not in self._active_zones:
                return
            _LOGGER.warning(
                "%s Zone '%s' was removed while heating - releasing its boiler demand", LOG_PREFIX, zone_name
            )
            self.hass.async_create_task(self._release_orphan(zone_name))

        return release

    async def _release_orphan(self, zone_name: str) -> None:
        """Release the boiler demand of a removed zone; never raises."""
        try:
            await self.turn_off(None, zone_name)
        except Exception:
            _LOGGER.exception("%s Releasing the boiler demand of removed zone '%s' FAILED", LOG_PREFIX, zone_name)

    async def register_boiler(self, entity_id: str):
        """
        Register the boiler switch and watch its state; the first registration of a run wins.

        A different switch later is only warned about in turn_on() (a changed boiler needs a restart).
        """
        if self._boiler_entity_id:
            return
        self._boiler_entity_id = entity_id
        self._boiler_unsub = async_track_state_change_event(self.hass, [entity_id], self._boiler_state_changed)
        _LOGGER.info("%s Boiler entity registered: %s", LOG_PREFIX, entity_id)

    async def _boiler_state_changed(self, event: Event) -> None:
        """
        The boiler switch changed state.

        A switch that goes unavailable cannot be commanded (Home Assistant skips it without an error),
        so when it is back (e.g. after a reboot) it is set to the wanted state: on while any zone holds
        the boiler, off otherwise. A change between two readable states (ours, or a manual switch) is
        left alone, like before.
        """
        try:
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")
            if new_state is None:
                return
            if new_state.state in SENSOR_BAD_STATES:
                if old_state is None or old_state.state not in SENSOR_BAD_STATES:
                    _LOGGER.warning(
                        "%s Boiler switch %s is %s - it is set to the wanted state when it is back",
                        LOG_PREFIX, self._boiler_entity_id, new_state.state
                    )
                return
            if old_state is not None and old_state.state not in SENSOR_BAD_STATES:
                return

            wanted_on = bool(self._active_zones)
            _LOGGER.warning(
                "%s Boiler switch %s is back (%s) | wanted %s | active zones: %s",
                LOG_PREFIX, self._boiler_entity_id, new_state.state, "ON" if wanted_on else "OFF",
                sorted(self._active_zones)
            )
            if (new_state.state == "on") != wanted_on:
                await self._call_boiler_service("turn_on" if wanted_on else "turn_off")
        except Exception:
            _LOGGER.exception("%s Handling a boiler switch state change FAILED", LOG_PREFIX)

    async def turn_on(self, entity_id: Optional[str], zone: str, afterheat: bool = False):
        """Kazán bekapcsolása zónából. Afterheat: the zone only joined a running boiler, it is not real demand."""
        if entity_id and self._boiler_entity_id is None:
            await self.register_boiler(entity_id)
        elif entity_id and entity_id != self._boiler_entity_id and not self._mismatch_warned:
            self._mismatch_warned = True
            _LOGGER.warning(
                "%s Zone '%s' uses boiler %s but %s is registered - a changed boiler switch needs a Home Assistant restart",
                LOG_PREFIX, zone, entity_id, self._boiler_entity_id
            )

        was_off = len(self._active_zones) == 0
        had_real_demand = self.has_real_demand()
        before = self._membership()
        newly_joined = zone not in self._active_zones
        self._active_zones.add(zone)
        if afterheat:
            self._afterheat_zones.add(zone)
        else:
            self._afterheat_zones.discard(zone)
        try:
            self._count_change(zone, was_off, afterheat and newly_joined)
        except Exception:
            _LOGGER.exception("%s Boiler counter bookkeeping failed (turn_on %s)", LOG_PREFIX, zone)
        self._notify_if_changed(before)
        _LOGGER.debug("%s Zone '%s' requested boiler ON (active_zones=%d)", LOG_PREFIX, zone, len(self._active_zones))

        if was_off:
            # Boiler is turning on - physically turn it on
            await self._call_boiler_service("turn_on")
        if was_off or (not afterheat and not had_real_demand):
            # The boiler starts, or real demand starts on a boiler that only ran for afterheat zones
            await self._trigger_piggyback_heating(initiating_zone=zone)

    async def turn_off(self, entity_id: Optional[str], zone: str):
        """Kazán kikapcsolása zónából."""
        before = self._membership()
        self._afterheat_zones.discard(zone)
        if zone in self._active_zones:
            self._active_zones.remove(zone)
        try:
            self._count_release()
        except Exception:
            _LOGGER.exception("%s Boiler counter bookkeeping failed (turn_off %s)", LOG_PREFIX, zone)
        self._notify_if_changed(before)

        _LOGGER.debug("%s Zone '%s' released boiler (active_zones=%d)", LOG_PREFIX, zone, len(self._active_zones))

        # Ha nincs több aktív zóna, akkor kapcsoljuk ki a kazánt
        if not self._active_zones:
            await self._call_boiler_service("turn_off")

    # --------------------------------------------------------------------------
    # Piggyback heating
    # --------------------------------------------------------------------------

    async def _trigger_piggyback_heating(self, initiating_zone: str):
        """
        Trigger piggyback heating check in all zones.

        When boiler turns on, all zones should check if current_temp < target_temp
        and turn on immediately without hysteresis or waiting for sensor update.
        """
        _LOGGER.info(
            "%s Piggyback heating triggered by zone '%s' - checking all zones",
            LOG_PREFIX, initiating_zone
        )

        # A snapshot: zones may be set up or removed while a check awaits
        for zone_name, zone_entity in list(self._zone_entities.items()):
            if zone_name == initiating_zone or self._zone_entities.get(zone_name) is not zone_entity:
                continue  # the initiator itself, or a zone removed/reloaded meanwhile
            await zone_entity.check_piggyback_heating()

    # --------------------------------------------------------------------------
    # Segédfüggvények
    # --------------------------------------------------------------------------

    async def _call_boiler_service(self, action: str) -> bool:
        """Service hívás a kazán kapcsolóhoz. A sikertelen parancsot megjegyzi és újrapróbálja."""
        if not self._boiler_entity_id:
            _LOGGER.warning("%s No boiler entity configured", LOG_PREFIX)
            return False

        try:
            await self.hass.services.async_call(
                "switch",
                action,
                {"entity_id": self._boiler_entity_id},
                blocking=True,
            )
            _LOGGER.info("%s Boiler relay %s → %s", LOG_PREFIX, self._boiler_entity_id, action.upper())
            failed_before, self._failed_action = self._failed_action, None
            if failed_before:
                self._notify()
            return True
        except Exception as e:
            failed_before, self._failed_action = self._failed_action, action
            if failed_before != action:
                self._notify()
            _LOGGER.error(
                "%s Boiler relay command FAILED %s → %s: %s (will retry)",
                LOG_PREFIX, self._boiler_entity_id, action, e
            )
            return False

    async def retry_failed(self):
        """
        Retry a failed boiler command, if it is still the wanted one.

        The wanted state follows the active zones, so a newer decision cancels the retry and a
        manual switch by the user is never overridden.
        """
        if not self._failed_action:
            return
        wanted = "turn_on" if self._active_zones else "turn_off"
        if wanted != self._failed_action:
            self._failed_action = None
            return
        _LOGGER.warning("%s Retrying failed boiler command: %s", LOG_PREFIX, self._failed_action)
        await self._call_boiler_service(self._failed_action)

    # --------------------------------------------------------------------------
    # Állapot lekérdezés és debug
    # --------------------------------------------------------------------------

    def add_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Call callback (sync) when the boiler state changes; returns the remover."""
        self._listeners.append(callback)

        def remove() -> None:
            if callback in self._listeners:
                self._listeners.remove(callback)

        return remove

    def _membership(self) -> tuple[frozenset, frozenset]:
        """Active and afterheat zones, to detect a change."""
        return frozenset(self._active_zones), frozenset(self._afterheat_zones)

    def _notify_if_changed(self, before: tuple[frozenset, frozenset]) -> None:
        """Notify the listeners when membership or the afterheat marks changed."""
        if self._membership() != before:
            self._notify()

    def _notify(self) -> None:
        """Call every listener; a failing one is logged and does not stop the others."""
        for callback in list(self._listeners):
            try:
                callback()
            except Exception:
                _LOGGER.exception("%s Boiler listener failed", LOG_PREFIX)

    def _roll_day(self, now: datetime) -> None:
        """Reset the daily counters when the local date changed; a running period restarts at midnight."""
        if now.date() == self._counter_day:
            return
        self._counter_day = now.date()
        self._runtime_s = 0.0
        self._starts = 0
        self._afterheat_joins = 0
        if self._period_start is not None:
            self._period_start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)

    @staticmethod
    def _elapsed(later: datetime, earlier: datetime) -> float:
        """Real seconds between two local times (UTC difference, so a DST change does not skew it)."""
        return (dt_util.as_utc(later) - dt_util.as_utc(earlier)).total_seconds()

    def _count_change(self, zone: str, was_off: bool, afterheat_join: bool) -> None:
        """Counter bookkeeping for a zone that requested the boiler."""
        now = dt_util.now()
        self._roll_day(now)
        if was_off:
            self._starts += 1
            self._since = self._period_start = now
        if afterheat_join:
            self._afterheat_joins += 1

    def _count_release(self) -> None:
        """Counter bookkeeping after a zone released the boiler: close the running period when none is left."""
        now = dt_util.now()
        self._roll_day(now)
        if not self._active_zones and self._period_start is not None:
            self._runtime_s += self._elapsed(now, self._period_start)
            self._since = self._period_start = None

    def stats(self, now: Optional[datetime] = None) -> dict:
        """Boiler snapshot for the overview: state, holders, today's counters."""
        now = now or dt_util.now()
        self._roll_day(now)
        runtime = self._runtime_s
        if self._period_start is not None:
            runtime += self._elapsed(now, self._period_start)
        midnight = datetime.combine(self._counter_day, time.min, tzinfo=now.tzinfo)
        return {
            "running": bool(self._active_zones),
            "since": self._since.isoformat() if self._since else None,
            "held_by": sorted(self._active_zones - self._afterheat_zones),
            "afterheat_zones": sorted(self._afterheat_zones),
            "starts_today": self._starts,
            "runtime_today_s": int(runtime),
            "afterheat_joins_today": self._afterheat_joins,
            "failed_action": self._failed_action,
            "counters_since": max(self._created, midnight).isoformat(),
        }

    def is_afterheat_member(self, zone: str) -> bool:
        """True if the zone is active only because it joined by afterheat (kept across a zone reload)."""
        return zone in self._afterheat_zones

    def has_real_demand(self) -> bool:
        """True if at least one active zone heats on its own demand (not only by afterheat)."""
        return bool(self._active_zones - self._afterheat_zones)

    def get_active_zones(self) -> list[str]:
        """Aktív fűtési zónák listája."""
        return list(self._active_zones)

    def get_boiler_state(self) -> dict:
        """Kazán státusz JSON formátumban."""
        return {
            "boiler_entity": self._boiler_entity_id,
            "active_zones": list(self._active_zones),
            "active_count": len(self._active_zones),
            "failed_action": self._failed_action,
        }

    def __repr__(self):
        return f"<BoilerManager entity={self._boiler_entity_id} active_zones={len(self._active_zones)}>"

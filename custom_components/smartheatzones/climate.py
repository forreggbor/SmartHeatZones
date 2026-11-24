"""
SmartHeatZones - Climate Platform
Version: 1.12.0 (HA 2025.10+ compatible)
Author: forreggbor

CHANGELOG v1.12.0 (FEATURE)
- Added: backup temperature sensor, limp mode (open-loop heating cycle) when no sensor is usable, outdoor source chain
- Added: fail-safe event, translated notifications, attributes sensor_source / limp_active / outdoor_source / relay_unavailable
- Changed: a lost zone sensor no longer switches the heating off; the watchdog evaluates the sensor chain every minute and is error-isolated
- Fixed: a relay that becomes unavailable is no longer taken for a manual switch-off; a returning relay gets the wanted state
- Fixed: relay_fault is published right after a retry; stale boiler membership is released at setup
CHANGELOG v1.11.0 (FEATURE)
- Added: the sensor silence limit is a per-zone setting (default 2 h) and shown as sensor_stale_hours
- Fixed: schedule timer and state listeners are removed with the entity (no duplicate commands after a reload)

CHANGELOG v1.10.1 (SAFETY FIX)
- Fixed: heating is switched off when the temperature sensor is lost (unavailable 10 min / silent 2 h)
- Fixed: failed relay commands are retried; a relay left on over a restart is taken over
- Fixed: invalid stored target temperature or preset no longer stops the zone from loading
- Added: sensor_fault and relay_fault state attributes

CHANGELOG v1.10.0 (FEATURE)
- Added: preset_temperatures state attribute (comfort/eco/away targets) for dashboard cards

CHANGELOG v1.9.1 (BUGFIX)
- Fixed: Removing the outdoor temperature sensor is not removed from settings

NEW in v1.9.0:
- Lovelace Dashboard Phase 1 with comprehensive monitoring
- Template sensors for statistics and tracking
- No code changes to climate platform (dashboard is add-on)

NEW in v1.8.1:
- Piggyback heating: When boiler turns on, all zones with temp < target turn on immediately
- Zone entity registration with boiler manager for piggyback coordination
- No hysteresis applied during piggyback heating - simple temp < target check

NEW in v1.7.0:
- Thermostat type selection (Wall vs Radiator)
- Temperature offset for radiator thermostats (compensates for TRV placement)
- Adjusted target temperature calculation (_get_adjusted_target_temp method)
- Updated heating evaluation to use adjusted targets
- Auto heat restart uses adjusted targets
- New entity attributes: thermostat_type, temp_offset, adjusted_target_temp

NEW in v1.6.1:
- No functional changes (bugfix release for config flow)

NEW in v1.6.0:
- Common settings integration (read shared config)
- Underfloor heating mode (no hysteresis)
- HVAC OFF vs Idle logic fix (always HEAT when adjusting)
- Zone-specific configuration only

FIXES in 1.5.1:
- Schedule reload on options update
- Auto HEAT restart when temp drops below target
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from . import notifications
from .limp import resolve_limp
from .sensor_health import (
    OutdoorWindow,
    effective_outdoor,
    group_overview,
    outdoor_multiplier,
    read_outdoor,
    sensor_problem,
)
from .decision import decision_reason, next_schedule_change
from .const import (
    DOMAIN,
    DATA_BOILER_MAIN,
    DATA_ACTIVE_ZONES,
    DATA_COMMON_SETTINGS,
    CONF_SENSOR,
    CONF_ZONE_RELAYS,
    CONF_DOOR_SENSORS,
    CONF_SCHEDULE,
    CONF_HEATING_MODE,
    CONF_THERMOSTAT_TYPE,
    CONF_TEMP_OFFSET,
    CONF_BOILER_MAIN,
    CONF_HYSTERESIS,
    CONF_OVERHEAT_PROTECTION,
    CONF_OUTDOOR_SENSOR,
    CONF_ADAPTIVE_HYSTERESIS,
    DEFAULT_HYSTERESIS,
    DEFAULT_OVERHEAT_TEMP,
    DEFAULT_ADAPTIVE_HYSTERESIS,
    DEFAULT_HEATING_MODE,
    DEFAULT_THERMOSTAT_TYPE,
    DEFAULT_TEMP_OFFSET,
    HEATING_MODE_RADIATOR,
    HEATING_MODE_UNDERFLOOR,
    THERMOSTAT_TYPE_WALL,
    THERMOSTAT_TYPE_RADIATOR,
    PRESET_AUTO,
    PRESET_MANUAL,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_AWAY,
    PRESET_MODES,
    PRESET_TEMPERATURES,
    LOG_PREFIX,
    ERR_OVERHEAT,
    EVENT_FAILSAFE,
    RELAY_UNAVAILABLE_NOTICE_AFTER,
    SENSOR_BAD_STATES,
    SENSOR_SOURCE_BACKUP,
    SENSOR_SOURCE_NONE,
    SENSOR_SOURCE_PRIMARY,
    SENSOR_UNAVAILABLE_GRACE,
    CONF_SENSOR_STALE_HOURS,
    CONF_AFTERHEAT,
    DEFAULT_AFTERHEAT,
    CONF_BACKUP_SENSOR,
    CONF_BACKUP_SENSOR_OFFSET,
    CONF_LIMP_OUTDOOR_CUTOFF,
    CONF_OUTDOOR_BACKUP_SENSOR,
    DEFAULT_BACKUP_SENSOR_OFFSET,
    DEFAULT_LIMP_OUTDOOR_CUTOFF,
    DEFAULT_SENSOR_STALE_HOURS,
    MIN_SENSOR_STALE_HOURS,
    MAX_SENSOR_STALE_HOURS,
    WATCHDOG_INTERVAL,
)


_LOGGER = logging.getLogger(__name__)


def _get_common_settings(hass: HomeAssistant) -> dict:
    """Get common settings from DATA_COMMON_SETTINGS entry."""
    common_entry = hass.data.get(DOMAIN, {}).get(DATA_COMMON_SETTINGS)
    if common_entry:
        # Return options if available, otherwise data
        return common_entry.options if common_entry.options else common_entry.data
    return {}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Platform setup - zone creation with common settings."""
    name = entry.title
    zone_data = entry.options if entry.options else entry.data
    
    # NEW v1.6.0: Load common settings
    common_settings = _get_common_settings(hass)
    
    if not common_settings:
        _LOGGER.error(
            "%s [%s] Cannot create zone - common settings not found!",
            LOG_PREFIX, name
        )
        return

    # Zone-specific config
    sensor = zone_data.get(CONF_SENSOR)
    relays = zone_data.get(CONF_ZONE_RELAYS, [])
    doors = zone_data.get(CONF_DOOR_SENSORS, [])
    heating_mode = zone_data.get(CONF_HEATING_MODE, DEFAULT_HEATING_MODE)
    thermostat_type = zone_data.get(CONF_THERMOSTAT_TYPE, DEFAULT_THERMOSTAT_TYPE)
    temp_offset = zone_data.get(CONF_TEMP_OFFSET, DEFAULT_TEMP_OFFSET)
    schedule = zone_data.get(CONF_SCHEDULE, [])
    sensor_stale_hours = zone_data.get(CONF_SENSOR_STALE_HOURS, DEFAULT_SENSOR_STALE_HOURS)
    afterheat = zone_data.get(CONF_AFTERHEAT, DEFAULT_AFTERHEAT)
    backup_sensor = zone_data.get(CONF_BACKUP_SENSOR)
    backup_offset = zone_data.get(CONF_BACKUP_SENSOR_OFFSET, DEFAULT_BACKUP_SENSOR_OFFSET)
    limp_on, limp_period = resolve_limp(common_settings, zone_data, heating_mode, name)
    
    if not schedule:
        _LOGGER.warning(
            "%s [%s] No schedule configured! Auto preset will not work.",
            LOG_PREFIX, name
        )

    # Common settings (shared across zones)
    boiler_entity = common_settings.get(CONF_BOILER_MAIN)
    hysteresis = common_settings.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)
    overheat_temp = common_settings.get(CONF_OVERHEAT_PROTECTION, DEFAULT_OVERHEAT_TEMP)
    outdoor_sensor = common_settings.get(CONF_OUTDOOR_SENSOR)
    adaptive_hyst = common_settings.get(CONF_ADAPTIVE_HYSTERESIS, DEFAULT_ADAPTIVE_HYSTERESIS)
    limp_cutoff = common_settings.get(CONF_LIMP_OUTDOOR_CUTOFF, DEFAULT_LIMP_OUTDOOR_CUTOFF)  # None = disabled
    outdoor_backup = common_settings.get(CONF_OUTDOOR_BACKUP_SENSOR)

    _LOGGER.info(
        "%s Creating climate entity: %s | Mode=%s | ThermostatType=%s | Offset=%.1f°C | Sensor=%s | Relays=%s | Schedule=%d blocks",
        LOG_PREFIX, name, heating_mode, thermostat_type, temp_offset, sensor, relays, len(schedule)
    )
    _LOGGER.info(
        "%s [%s] Common settings: Boiler=%s | Hyst=%.2f°C | Overheat=%.1f°C | Adaptive=%s",
        LOG_PREFIX, name, boiler_entity, hysteresis, overheat_temp, adaptive_hyst
    )

    entity = SmartHeatZoneClimate(
        hass=hass,
        name=name,
        heating_mode=heating_mode,
        thermostat_type=thermostat_type,
        temp_offset=temp_offset,
        sensor_entity_id=sensor,
        relay_entities=relays,
        door_sensors=doors,
        schedule=schedule,
        sensor_stale_hours=sensor_stale_hours,
        boiler_entity=boiler_entity,
        hysteresis=hysteresis,
        overheat_temp=overheat_temp,
        outdoor_sensor=outdoor_sensor,
        adaptive_hysteresis_enabled=adaptive_hyst,
        backup_sensor_entity_id=backup_sensor,
        backup_sensor_offset=backup_offset,
        limp_on_minutes=limp_on,
        limp_period_minutes=limp_period,
        limp_outdoor_cutoff=limp_cutoff,
        outdoor_backup_entity_id=outdoor_backup,
        afterheat=afterheat,
    )
    async_add_entities([entity])
    _LOGGER.info("%s Climate entity created for %s", LOG_PREFIX, name)


class SmartHeatZoneClimate(ClimateEntity, RestoreEntity):
    """Zone thermostat entity v1.6.0."""

    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE |
        ClimateEntityFeature.PRESET_MODE
    )
    _attr_min_temp = 5.0
    _attr_max_temp = 28.0
    _attr_preset_modes = PRESET_MODES

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        heating_mode: str,
        thermostat_type: str,
        temp_offset: float,
        sensor_entity_id: str,
        relay_entities: list[str],
        door_sensors: list[str],
        schedule: list,
        sensor_stale_hours: float,
        boiler_entity: Optional[str],
        hysteresis: float,
        overheat_temp: float,
        outdoor_sensor: Optional[str],
        adaptive_hysteresis_enabled: bool,
        backup_sensor_entity_id: Optional[str],
        backup_sensor_offset: float,
        limp_on_minutes: int,
        limp_period_minutes: int,
        limp_outdoor_cutoff: Optional[float],
        outdoor_backup_entity_id: Optional[str],
        afterheat: bool = False,
    ):
        """Initialize zone thermostat."""
        self.hass = hass
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{name.lower().replace(' ', '_')}"

        # Zone-specific
        self._heating_mode = heating_mode
        self._thermostat_type = thermostat_type
        self._temp_offset = temp_offset
        self._sensor_entity_id = sensor_entity_id
        self._relay_entities = relay_entities or []
        self._door_sensors = door_sensors or []
        self._schedule = schedule or []
        self._sensor_stale_timeout = self._stale_timeout_from(sensor_stale_hours)

        # Common settings (from common entry)
        self._boiler_entity = boiler_entity
        self._base_hysteresis = hysteresis
        self._overheat_temp = overheat_temp
        self._outdoor_sensor = outdoor_sensor
        self._adaptive_hysteresis_enabled = adaptive_hysteresis_enabled
        self._limp_outdoor_cutoff = limp_outdoor_cutoff
        self._outdoor_backup_entity_id = outdoor_backup_entity_id
        self._afterheat = bool(afterheat)
        self._afterheat_joined = False  # heating only because the boiler runs for another zone

        # Backup sensor and limp mode (zone settings, inherited from the common settings)
        self._backup_sensor_entity_id = backup_sensor_entity_id
        self._backup_sensor_offset = float(backup_sensor_offset or 0.0)
        self._limp_on_minutes = limp_on_minutes
        self._limp_period_minutes = limp_period_minutes

        # Runtime state
        self._current_temp = None
        self._target_temp = 21.0
        self._hvac_mode = HVACMode.HEAT
        self._is_heating = False
        self._preset_mode = PRESET_AUTO
        self._schedule_tracker = None
        self._outdoor_temp = None
        self._boiler = hass.data[DOMAIN][DATA_BOILER_MAIN]

        # Fail-safe state (v1.10.1)
        self._sensor_fault: Optional[str] = None  # why the sensor is not trusted, None when fine
        self._sensor_bad_since: Optional[datetime] = None
        self._backup_bad_since: Optional[datetime] = None  # "not readable since" clock of the backup sensor
        self._sensor_source = SENSOR_SOURCE_PRIMARY  # which sensor the control currently runs on
        self._outdoor_window = OutdoorWindow()  # cautious outdoor estimate for the limp mode
        self._announced_state: Optional[str] = None  # last fail-safe state reported by event/notification
        self._relay_notice_active = False  # an "unreachable relay" notification is showing
        self._limp_state: Optional[tuple] = None  # last limp decision (wanted, detail), to log changes only
        self._limp_outdoor_source: Optional[str] = None  # where the outdoor value of the last limp decision came from
        self._limp_effective_on: Optional[int] = None  # scaled "on minutes" of the last limp decision, None when none applies
        self._failed_relay_actions: dict[str, str] = {}  # relay entity -> command that failed
        self._relay_unavailable_since: dict[str, datetime] = {}  # relay entity -> when it became unreachable

        _LOGGER.info(
            "%s [%s] Initialized | Mode=%s | Preset=%s | Overheat=%.1f°C",
            LOG_PREFIX, self.name, self._heating_mode, self._preset_mode, self._overheat_temp
        )

        if self._schedule and self._preset_mode == PRESET_AUTO:
            self._apply_current_schedule_block()

    async def async_added_to_hass(self):
        """Entity added to Home Assistant."""
        await super().async_added_to_hass()

        # Register with boiler manager for piggyback heating
        self._boiler.register_zone_entity(self.name, self)
        _LOGGER.debug("%s [%s] Registered with boiler manager", LOG_PREFIX, self.name)

        # State restoration
        last_state = await self.async_get_last_state()
        if last_state:
            if last_state.attributes.get(ATTR_TEMPERATURE):
                try:
                    restored = float(last_state.attributes[ATTR_TEMPERATURE])
                    self._target_temp = min(max(restored, self._attr_min_temp), self._attr_max_temp)
                    _LOGGER.info("%s [%s] Restored target: %.1f°C", LOG_PREFIX, self.name, self._target_temp)
                except (ValueError, TypeError):
                    _LOGGER.warning(
                        "%s [%s] Ignoring invalid stored target temperature: %r",
                        LOG_PREFIX, self.name, last_state.attributes[ATTR_TEMPERATURE]
                    )

            if last_state.state in [HVACMode.HEAT, HVACMode.OFF]:
                self._hvac_mode = last_state.state
                _LOGGER.info("%s [%s] Restored HVAC: %s", LOG_PREFIX, self.name, self._hvac_mode)

            restored_preset = last_state.attributes.get("preset_mode")
            if restored_preset in PRESET_MODES:
                self._preset_mode = restored_preset
                _LOGGER.info("%s [%s] Restored preset: %s", LOG_PREFIX, self.name, self._preset_mode)
            elif restored_preset:
                _LOGGER.warning("%s [%s] Ignoring invalid stored preset: %r", LOG_PREFIX, self.name, restored_preset)

        # Temperature sensor tracking
        if self._sensor_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._sensor_entity_id],
                    self._sensor_changed,
                )
            )

            sensor_state = self.hass.states.get(self._sensor_entity_id)
            if sensor_state and sensor_state.state not in SENSOR_BAD_STATES:
                try:
                    self._current_temp = float(sensor_state.state)
                    _LOGGER.info("%s [%s] Initial temp: %.2f°C", LOG_PREFIX, self.name, self._current_temp)
                except (ValueError, TypeError):
                    pass

        # Backup temperature sensor (used only while the primary sensor is lost)
        if self._backup_sensor_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._backup_sensor_entity_id],
                    self._backup_sensor_changed,
                )
            )

        # Outdoor samples for the limp mode's cautious estimate (live sensor and backup source)
        for outdoor_id in (self._outdoor_sensor, self._outdoor_backup_entity_id):
            if outdoor_id:
                self._record_outdoor_sample(outdoor_id)
                self.async_on_remove(
                    async_track_state_change_event(
                        self.hass,
                        [outdoor_id],
                        self._outdoor_sample_changed,
                    )
                )

        # Event-based relay monitoring
        if self._relay_entities:
            for relay_id in self._relay_entities:
                self.async_on_remove(
                    async_track_state_change_event(
                        self.hass,
                        [relay_id],
                        self._relay_state_changed,
                    )
                )
            _LOGGER.info(
                "%s [%s] Event-based relay monitoring enabled for %d relays",
                LOG_PREFIX, self.name, len(self._relay_entities)
            )

        # Outdoor sensor tracking
        if self._outdoor_sensor and self._adaptive_hysteresis_enabled:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._outdoor_sensor],
                    self._outdoor_sensor_changed,
                )
            )

            outdoor_state = self.hass.states.get(self._outdoor_sensor)
            if outdoor_state and outdoor_state.state not in ["unavailable", "unknown", "none"]:
                try:
                    self._outdoor_temp = float(outdoor_state.state)
                    _LOGGER.info("%s [%s] Outdoor temp: %.2f°C", LOG_PREFIX, self.name, self._outdoor_temp)
                except (ValueError, TypeError):
                    pass

        # Door/window sensors
        for door in self._door_sensors:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [door],
                    self._door_changed,
                )
            )

        # Schedule tracker
        if self._schedule and self._preset_mode == PRESET_AUTO:
            self._schedule_tracker = async_track_time_interval(
                self.hass,
                self._check_schedule,
                timedelta(minutes=15)
            )
            _LOGGER.debug("%s [%s] Schedule tracker enabled", LOG_PREFIX, self.name)

        # Take over the real relay state: after a restart a relay may still be on while this entity
        # starts as "not heating", and it could then never be switched off again.
        if any((r := self.hass.states.get(rid)) is not None and r.state == "on" for rid in self._relay_entities):
            _LOGGER.warning(
                "%s [%s] Relay is already ON at startup - taking over the heating state",
                LOG_PREFIX, self.name
            )
            self._is_heating = True
            # A reload keeps the manager: a zone that had only joined by afterheat stays marked as such
            self._afterheat_joined = self._boiler.is_afterheat_member(self.name)
            if self._boiler_entity:
                await self._boiler.turn_on(self._boiler_entity, zone=self.name, afterheat=self._afterheat_joined)

        # A notification of a previous run (or reload) may still be showing; the watchdog re-creates what is true
        notifications.dismiss(self.hass, self.name, notifications.CAUSE_SENSOR)
        notifications.dismiss(self.hass, self.name, notifications.CAUSE_RELAY)

        # Relays that are already unreachable now (restart during a wifi outage)
        for relay_id in self._relay_entities:
            relay_state = self.hass.states.get(relay_id)
            if relay_state is None or relay_state.state in SENSOR_BAD_STATES:
                self._relay_unavailable_since[relay_id] = dt_util.utcnow()
                _LOGGER.warning("%s [%s] Relay %s is not available at startup", LOG_PREFIX, self.name, relay_id)

        # A reload leaves this zone registered at the boiler manager; release it when the zone is not heating
        if self._boiler_entity and not self._is_heating and self.name in self._boiler.get_active_zones():
            _LOGGER.warning("%s [%s] Releasing stale boiler membership left by a reload", LOG_PREFIX, self.name)
            await self._boiler.turn_off(self._boiler_entity, zone=self.name)

        # Fail-safe watchdog (sensor health and retry of failed relay commands)
        self._sensor_problem()  # starts the "unavailable" clock if the sensor is not readable now
        self._backup_reading()  # same for the backup sensor
        self.async_on_remove(
            async_track_time_interval(self.hass, self._watchdog, WATCHDOG_INTERVAL)
        )

        await self._evaluate_heating()

    async def async_will_remove_from_hass(self):
        """Entity removal - stop the schedule timer and unregister from boiler manager."""
        if self._schedule_tracker:
            self._schedule_tracker()
            self._schedule_tracker = None
        self._boiler.unregister_zone_entity(self.name)
        _LOGGER.debug("%s [%s] Unregistered from boiler manager", LOG_PREFIX, self.name)
        await super().async_will_remove_from_hass()

    # ==================================================================================
    # PIGGYBACK HEATING (v1.8.1)
    # ==================================================================================

    async def check_piggyback_heating(self):
        """
        Check if this zone should turn on due to piggyback heating.

        Called when boiler turns on by another zone. This zone should turn on
        immediately if current_temp < target_temp, without hysteresis and without
        waiting for sensor update.
        """
        # Only piggyback if HVAC is in HEAT mode
        if self._hvac_mode != HVACMode.HEAT:
            _LOGGER.debug(
                "%s [%s] Piggyback skipped - HVAC mode is %s",
                LOG_PREFIX, self.name, self._hvac_mode
            )
            return

        # Already heating - no action needed
        if self._is_heating:
            _LOGGER.debug(
                "%s [%s] Piggyback skipped - already heating",
                LOG_PREFIX, self.name
            )
            return

        # No temperature reading yet
        if self._current_temp is None:
            _LOGGER.debug(
                "%s [%s] Piggyback skipped - no temperature reading",
                LOG_PREFIX, self.name
            )
            return

        # Check door/window sensors
        for door in self._door_sensors:
            state = self.hass.states.get(door)
            if state and state.state == "on":
                _LOGGER.debug(
                    "%s [%s] Piggyback skipped - door/window open",
                    LOG_PREFIX, self.name
                )
                return

        # Simple check: current < target (NO hysteresis)
        adjusted_target = self._get_adjusted_target_temp()

        if self._current_temp < adjusted_target:
            _LOGGER.info(
                "%s [%s] PIGGYBACK HEATING! Current=%.2f°C < Adjusted Target=%.2f°C → Turning ON",
                LOG_PREFIX, self.name, self._current_temp, adjusted_target
            )
            await self._set_heating(True, reason="Piggyback heating (boiler already running)")
        else:
            _LOGGER.debug(
                "%s [%s] Piggyback not needed - current=%.2f°C >= target=%.2f°C",
                LOG_PREFIX, self.name, self._current_temp, adjusted_target
            )

    # ==================================================================================
    # EVENT-BASED RELAY MONITORING
    # ==================================================================================

    @callback
    async def _relay_state_changed(self, event):
        """
        Instant relay state change detection (event-based).

        A relay that becomes unreachable (wifi outage) is never read as "switched off by hand".
        When it comes back, the zone's wanted state is pushed to it instead of adopting its old state.
        """
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")

        if not new_state:
            return

        relay_id = new_state.entity_id
        now = dt_util.utcnow()

        if new_state.state in SENSOR_BAD_STATES:
            if relay_id not in self._relay_unavailable_since:
                self._relay_unavailable_since[relay_id] = now
                _LOGGER.warning(
                    "%s [%s] Relay %s is %s - cannot be controlled until it is back",
                    LOG_PREFIX, self.name, relay_id, new_state.state
                )
                self.async_write_ha_state()
            return

        was_unreachable = (
            relay_id in self._relay_unavailable_since
            or old_state is None
            or old_state.state in SENSOR_BAD_STATES
        )
        if was_unreachable:
            self._relay_unavailable_since.pop(relay_id, None)
            await self._relay_recovered(relay_id, new_state.state)
            return

        if new_state.state != old_state.state:
            _LOGGER.info(
                "%s [%s] Relay state changed: %s → %s (event-based detection)",
                LOG_PREFIX, self.name, relay_id, new_state.state.upper()
            )

            # Check all relay states
            relay_states = []
            for r_id in self._relay_entities:
                r_state = self.hass.states.get(r_id)
                if r_state and r_state.state not in SENSOR_BAD_STATES:
                    relay_states.append(r_state.state == "on")

            actual_heating = any(relay_states) if relay_states else False

            if actual_heating != self._is_heating:
                _LOGGER.warning(
                    "%s [%s] MANUAL OVERRIDE DETECTED! Expected=%s, Actual=%s → Synchronizing",
                    LOG_PREFIX, self.name, self._is_heating, actual_heating
                )

                self._is_heating = actual_heating

                # Boiler coordination
                if actual_heating and self._boiler_entity:
                    await self._boiler.turn_on(self._boiler_entity, zone=self.name)
                elif not actual_heating and self._boiler_entity:
                    await self._boiler.turn_off(self._boiler_entity, zone=self.name)

                self.async_write_ha_state()

    async def _relay_recovered(self, relay_id: str, state: str) -> None:
        """
        A relay is reachable again after being unavailable.

        With a temperature basis (a reading or a declared sensor fault) the zone's wanted state is
        pushed to the relay. Without any basis (the zone has not decided anything yet) a relay that is
        on is taken over, like at startup, so the zone can still switch it off later.
        """
        has_basis = self._current_temp is not None or self._sensor_fault is not None
        _LOGGER.warning(
            "%s [%s] Relay %s is back (%s) | wanted heating=%s | decision basis=%s",
            LOG_PREFIX, self.name, relay_id, state, self._is_heating, has_basis
        )

        if has_basis:
            if (state == "on") != self._is_heating:
                await self._call_switch_service("turn_on" if self._is_heating else "turn_off", relay_id)
        elif state == "on" and not self._is_heating:
            self._is_heating = True
            if self._boiler_entity:
                await self._boiler.turn_on(self._boiler_entity, zone=self.name)

        self.async_write_ha_state()

    # ==================================================================================
    # SENSOR CALLBACKS
    # ==================================================================================

    @callback
    async def _sensor_changed(self, event):
        """Temperature sensor change."""
        new_state = event.data.get("new_state")
        if not new_state:
            return

        try:
            if new_state.state in SENSOR_BAD_STATES:
                _LOGGER.warning("%s [%s] Sensor unavailable (fail-safe after %s)", LOG_PREFIX, self.name, SENSOR_UNAVAILABLE_GRACE)
                self._sensor_problem()  # starts the grace period
                return

            try:
                value = float(new_state.state)
            except (ValueError, TypeError):
                _LOGGER.error("%s [%s] Invalid sensor value: %s", LOG_PREFIX, self.name, new_state.state)
                self._sensor_problem()  # an unreadable value counts like "unavailable"
                return

            self._current_temp = value
            self._sensor_bad_since = None
            if self._sensor_fault:
                await self._end_fault_episode()
            _LOGGER.debug("%s [%s] Sensor: %.2f°C", LOG_PREFIX, self.name, self._current_temp)
            await self._apply_reading()
        except Exception:
            _LOGGER.exception("%s [%s] Handling a sensor update FAILED", LOG_PREFIX, self.name)

    @callback
    async def _backup_sensor_changed(self, event):
        """Backup sensor change: it only matters while the primary sensor is lost."""
        try:
            if self._sensor_fault is None:
                return
            await self._run_sensor_chain()
        except Exception:
            _LOGGER.exception("%s [%s] Handling a backup sensor update FAILED", LOG_PREFIX, self.name)

    async def _apply_reading(self):
        """Run the control logic on the current reading (primary or backup)."""
        await self._check_overheat_protection()
        await self._auto_heat_restart()
        await self._evaluate_heating()

    @callback
    async def _outdoor_sensor_changed(self, event):
        """Outdoor temperature change."""
        new_state = event.data.get("new_state")
        if not new_state or new_state.state in ["unavailable", "unknown", "none"]:
            return

        try:
            old_outdoor = self._outdoor_temp
            self._outdoor_temp = float(new_state.state)
            _LOGGER.debug("%s [%s] Outdoor: %.2f°C", LOG_PREFIX, self.name, self._outdoor_temp)

            if old_outdoor is not None and abs(self._outdoor_temp - old_outdoor) > 5.0:
                _LOGGER.info(
                    "%s [%s] Significant outdoor change: %.1f → %.1f°C, re-evaluating",
                    LOG_PREFIX, self.name, old_outdoor, self._outdoor_temp
                )
                await self._evaluate_heating()

        except (ValueError, TypeError):
            pass

    @callback
    async def _door_changed(self, event):
        """Door/window sensor change."""
        new_state = event.data.get("new_state")
        if new_state and new_state.state == "on":
            _LOGGER.warning("%s [%s] Door/window open – heating paused", LOG_PREFIX, self.name)
            await self._set_heating(False, reason="Door/window open")
        elif new_state and new_state.state == "off":
            _LOGGER.info("%s [%s] Door/window closed – re-evaluating", LOG_PREFIX, self.name)
            await self._evaluate_heating()

    # ==================================================================================
    # SENSOR FAIL-SAFE (v1.10.1)
    # ==================================================================================

    def _stale_timeout_from(self, hours) -> timedelta:
        """Silence limit of the zone sensor from the zone setting; an invalid value falls back to the default."""
        try:
            value = float(hours)
            if not MIN_SENSOR_STALE_HOURS <= value <= MAX_SENSOR_STALE_HOURS:
                raise ValueError("out of range")
        except (ValueError, TypeError):
            _LOGGER.warning(
                "%s [%s] Invalid sensor silence limit %r - using %.1f h",
                LOG_PREFIX, self.name, hours, DEFAULT_SENSOR_STALE_HOURS
            )
            value = DEFAULT_SENSOR_STALE_HOURS
        return timedelta(hours=value)

    def _sensor_problem(self) -> Optional[str]:
        """
        Why the temperature sensor cannot be trusted right now, or None when it is fine.

        Thin wrapper around sensor_health.sensor_problem() that keeps the "not readable since" clock.
        """
        problem, self._sensor_bad_since = sensor_problem(
            self.hass, self._sensor_entity_id, self._sensor_stale_timeout,
            self._sensor_bad_since, dt_util.utcnow()
        )
        return problem

    def _backup_reading(self) -> Optional[float]:
        """
        The backup sensor value (with its correction) when the backup sensor is trustworthy, else None.

        Trustworthy = readable now, not silent for longer than the zone's silence limit.
        """
        if not self._backup_sensor_entity_id:
            return None
        problem, self._backup_bad_since = sensor_problem(
            self.hass, self._backup_sensor_entity_id, self._sensor_stale_timeout,
            self._backup_bad_since, dt_util.utcnow()
        )
        if problem:
            return None
        state = self.hass.states.get(self._backup_sensor_entity_id)
        try:
            return float(state.state) + self._backup_sensor_offset
        except (AttributeError, ValueError, TypeError):
            return None

    def _enter_fault_episode(self, problem: str):
        """The primary sensor is declared lost."""
        self._sensor_fault = problem
        _LOGGER.error("%s [%s] FAIL-SAFE: primary sensor lost (%s)", LOG_PREFIX, self.name, problem)

    async def _end_fault_episode(self):
        """The primary sensor is back: normal control on the primary sensor resumes."""
        cause = self._sensor_fault
        _LOGGER.warning("%s [%s] Sensor recovered (%s) - normal control resumes", LOG_PREFIX, self.name, cause)
        self._sensor_fault = None
        self._sensor_source = SENSOR_SOURCE_PRIMARY
        self._limp_state = None
        self._limp_outdoor_source = None
        await self._announce_sensor_state("recovered", cause)

    def _diagnostic_sensor_ids(self) -> list[str]:
        """Every temperature sensor the integration depends on (all zones, outdoor sources included)."""
        ids: list[str] = []
        for zone in self._boiler.get_zone_entities():
            ids += [zone._sensor_entity_id, zone._backup_sensor_entity_id, zone._outdoor_sensor, zone._outdoor_backup_entity_id]
        return [i for i in ids if i and i.split(".", 1)[0] == "sensor"]

    async def _announce_sensor_state(self, state: str, cause: Optional[str]) -> None:
        """
        Report a sensor fail-safe state change ("backup", "limp" or "recovered") once.

        Fires the smartheatzones_failsafe event and creates/replaces (or, on recovery, dismisses) the
        zone's sensor notification. Never raises: a broken notifier must not disturb the control.
        """
        if state == "recovered":
            if self._announced_state is None:
                return
            self._announced_state = None
        elif self._announced_state == state:
            return
        else:
            self._announced_state = state

        try:
            groups = group_overview(
                self.hass, self._diagnostic_sensor_ids(), self._sensor_stale_timeout, dt_util.utcnow()
            )
            self.hass.bus.async_fire(EVENT_FAILSAFE, {
                "zone": self.name,
                "state": state,
                "cause": cause,
                "sensor_source": self._sensor_source,
                "groups": groups,
                "relays_unavailable": sorted(self._relay_unavailable_since),
            })
            if state == "recovered":
                notifications.dismiss(self.hass, self.name, notifications.CAUSE_SENSOR)
                return

            diagnosis = ""
            for group, info in groups.items():
                if info["bad"]:
                    diagnosis += " " + await notifications.async_text(
                        self.hass, "failsafe_diagnosis_group",
                        platform=group.split("/", 1)[0], bad=info["bad"], total=info["total"],
                    )
            if any(info["bad"] >= 2 for info in groups.values()):
                diagnosis += " " + await notifications.async_text(self.hass, "failsafe_diagnosis_network")

            if state == "backup":
                await notifications.async_notify(
                    self.hass, self.name, notifications.CAUSE_SENSOR, "failsafe_sensor_backup",
                    cause=cause, backup=self._backup_sensor_entity_id, diagnosis=diagnosis,
                )
            else:
                await notifications.async_notify(
                    self.hass, self.name, notifications.CAUSE_SENSOR, "failsafe_sensor_limp",
                    cause=cause, on=self._limp_on_minutes, period=self._limp_period_minutes, diagnosis=diagnosis,
                )
        except Exception:
            _LOGGER.exception("%s [%s] Reporting the fail-safe state %r FAILED", LOG_PREFIX, self.name, state)

    async def _check_relay_notice(self) -> None:
        """
        Notify when a relay has been unreachable for a long time while heating is wanted.

        The notice and a "relay_unavailable"/"relay_recovered" event are sent once per episode.
        """
        now = dt_util.utcnow()
        unreachable = {
            relay: since for relay, since in self._relay_unavailable_since.items()
            if now - since >= RELAY_UNAVAILABLE_NOTICE_AFTER
        }
        active = bool(unreachable) and self._is_heating
        if active == self._relay_notice_active:
            return
        self._relay_notice_active = active
        try:
            relays = sorted(unreachable) if active else sorted(self._relay_unavailable_since)
            self.hass.bus.async_fire(EVENT_FAILSAFE, {
                "zone": self.name,
                "state": "relay_unavailable" if active else "relay_recovered",
                "relays": relays,
            })
            if active:
                minutes = int(max((now - since).total_seconds() for since in unreachable.values()) // 60)
                await notifications.async_notify(
                    self.hass, self.name, notifications.CAUSE_RELAY, "failsafe_relay",
                    minutes=minutes, relays=", ".join(relays),
                )
            else:
                notifications.dismiss(self.hass, self.name, notifications.CAUSE_RELAY)
        except Exception:
            _LOGGER.exception("%s [%s] Reporting the relay state FAILED", LOG_PREFIX, self.name)

    async def _run_sensor_chain(self):
        """
        One evaluation of the sensor chain: primary sensor -> backup sensor -> (no sensor).

        - primary fine: normal control (a declared fault ends here)
        - primary lost, backup fine: normal control on the backup reading
        - primary and backup lost: no reading; the heating is switched off
        """
        problem = self._sensor_problem()

        if problem is None:
            if self._sensor_fault is not None:
                state = self.hass.states.get(self._sensor_entity_id)
                try:
                    self._current_temp = float(state.state)
                except (AttributeError, ValueError, TypeError):
                    _LOGGER.error("%s [%s] Sensor reports no number after recovery", LOG_PREFIX, self.name)
                    return
                await self._end_fault_episode()
                await self._apply_reading()
                self.async_write_ha_state()
            return

        if self._sensor_fault is None:
            self._enter_fault_episode(problem)
        elif self._sensor_fault != problem:
            _LOGGER.warning("%s [%s] Sensor fault changed: %s → %s", LOG_PREFIX, self.name, self._sensor_fault, problem)
            self._sensor_fault = problem

        backup = self._backup_reading()
        if backup is not None:
            if self._sensor_source != SENSOR_SOURCE_BACKUP:
                _LOGGER.warning(
                    "%s [%s] Running on the backup sensor %s (%.2f°C)",
                    LOG_PREFIX, self.name, self._backup_sensor_entity_id, backup
                )
            self._sensor_source = SENSOR_SOURCE_BACKUP
            self._limp_state = None
            self._limp_outdoor_source = None
            self._current_temp = backup
            await self._announce_sensor_state("backup", self._sensor_fault)
            await self._apply_reading()
        else:
            if self._sensor_source != SENSOR_SOURCE_NONE or self._current_temp is not None:
                self._sensor_source = SENSOR_SOURCE_NONE
                self._current_temp = None  # never decide on an old value (also blocks piggyback heating)
                _LOGGER.error(
                    "%s [%s] FAIL-SAFE: no usable temperature sensor - limp mode (%d min on per %d min)",
                    LOG_PREFIX, self.name, self._limp_on_minutes, self._limp_period_minutes
                )
            await self._announce_sensor_state("limp", self._sensor_fault)
            await self._apply_limp()
        self.async_write_ha_state()

    # ==================================================================================
    # LIMP MODE (open-loop heating while no temperature sensor can be trusted)
    # ==================================================================================

    def _record_outdoor_sample(self, entity_id: str) -> None:
        """Feed a valid outdoor reading into the cautious-estimate window."""
        now = dt_util.utcnow()
        value = read_outdoor(self.hass, entity_id, now)
        if value is not None:
            self._outdoor_window.add(now, value)

    @callback
    async def _outdoor_sample_changed(self, event):
        """Outdoor sensor or backup source reported: remember the value for the estimate."""
        try:
            self._record_outdoor_sample(event.data["entity_id"])
        except Exception:
            _LOGGER.exception("%s [%s] Recording an outdoor sample FAILED", LOG_PREFIX, self.name)

    def _limp_decision(self) -> tuple[bool, str]:
        """
        Whether the heating should be on right now in limp mode, and why.

        The target temperature is ignored (there is no reading to compare it with). HVAC OFF and open
        doors/windows still switch the heating off. Otherwise heating runs for "on minutes" of every
        period, counted from local midnight; the on time is scaled by the outdoor temperature band and
        the cycle stops when it is warm outside (summer).
        """
        self._limp_effective_on = None  # set below only when the cycle really applies (never a stale value)
        if self._hvac_mode == HVACMode.OFF:
            return False, "HVAC off"
        for door in self._door_sensors:
            state = self.hass.states.get(door)
            if state and state.state == "on":
                return False, "door/window open"

        outdoor, source = effective_outdoor(
            self.hass, self._outdoor_sensor, self._outdoor_backup_entity_id,
            self._outdoor_window, dt_util.utcnow()
        )
        self._limp_outdoor_source = source
        if outdoor is not None and self._limp_outdoor_cutoff is not None and outdoor >= self._limp_outdoor_cutoff:
            return False, f"outdoor {outdoor:.1f}°C ({source}) >= cut-off {self._limp_outdoor_cutoff:.1f}°C"

        multiplier = outdoor_multiplier(outdoor) if outdoor is not None else 1.0
        on_minutes = min(self._limp_period_minutes, round(self._limp_on_minutes * multiplier))
        self._limp_effective_on = on_minutes
        local = dt_util.now()
        phase = (local.hour * 60 + local.minute) % self._limp_period_minutes
        wanted = phase < on_minutes
        outdoor_txt = f"{outdoor:.1f}°C ({source})" if outdoor is not None else "unknown"
        return wanted, (
            f"{on_minutes}/{self._limp_period_minutes} min, phase {phase}, outdoor {outdoor_txt} x{multiplier}"
        )

    async def _apply_limp(self):
        """Apply the limp decision through the normal switching path (relays, boiler, retries)."""
        wanted, detail = self._limp_decision()
        if self._limp_state != (wanted, detail.split(", phase")[0]):
            _LOGGER.warning(
                "%s [%s] LIMP MODE: heating %s (%s)", LOG_PREFIX, self.name, "ON" if wanted else "OFF", detail
            )
        self._limp_state = (wanted, detail.split(", phase")[0])
        await self._set_heating(wanted, reason=f"Limp mode: {detail}")

    async def _watchdog(self, now=None):
        """
        Periodic fail-safe (every minute): sensor chain, then retry of failed relay commands.

        Both parts are isolated: an error in one is logged and never stops the other.
        """
        try:
            await self._run_sensor_chain()
        except Exception:
            _LOGGER.exception("%s [%s] Watchdog: sensor chain evaluation FAILED", LOG_PREFIX, self.name)

        try:
            await self._retry_failed_commands()
        except Exception:
            _LOGGER.exception("%s [%s] Watchdog: retry of failed commands FAILED", LOG_PREFIX, self.name)

        try:
            if self._afterheat and not self._is_heating and self._boiler.has_real_demand():
                await self._evaluate_heating()  # join a running boiler without waiting for the next reading
        except Exception:
            _LOGGER.exception("%s [%s] Watchdog: afterheat evaluation FAILED", LOG_PREFIX, self.name)

        await self._check_relay_notice()

        self.async_write_ha_state()  # a retry changes relay_fault; publish it right away

    async def _retry_failed_commands(self):
        """
        Retry relay and boiler commands that failed earlier.

        Only a command that is still wanted is repeated, so a manual switch by the user is never
        overridden: a newer decision (or a detected manual override) drops the pending retry.
        """
        for relay_id, action in list(self._failed_relay_actions.items()):
            if (action == "turn_on") != self._is_heating:
                self._failed_relay_actions.pop(relay_id, None)
                continue
            _LOGGER.warning("%s [%s] Retrying failed relay command %s → %s", LOG_PREFIX, self.name, action, relay_id)
            await self._call_switch_service(action, relay_id)

        await self._boiler.retry_failed()

    # ==================================================================================
    # OVERHEAT PROTECTION
    # ==================================================================================

    async def _check_overheat_protection(self):
        """Overheat protection check."""
        if self._current_temp is None:
            return

        if self._current_temp >= self._overheat_temp:
            if self._is_heating:
                _LOGGER.error(
                    "%s [%s] OVERHEAT! Current=%.2f°C >= Limit=%.1f°C → Emergency shutdown",
                    LOG_PREFIX, self.name, self._current_temp, self._overheat_temp
                )
                await self._set_heating(False, reason=ERR_OVERHEAT)

    # ==================================================================================
    # AUTO HEAT RESTART (v1.6.0 - Only if explicitly set to OFF)
    # ==================================================================================

    async def _auto_heat_restart(self):
        """
        Auto-restart HEAT mode if temperature drops below target.

        NEW v1.6.0: Only restarts if HVAC was explicitly set to OFF.
        Normal operation (+/- buttons, presets) always keeps HVAC in HEAT mode.

        NEW v1.7.0: Uses adjusted target temperature.
        """
        if self._hvac_mode == HVACMode.OFF and self._current_temp is not None:
            adjusted_target = self._get_adjusted_target_temp()
            effective_hysteresis = self._get_effective_hysteresis()
            diff = adjusted_target - self._current_temp

            if diff > effective_hysteresis:
                _LOGGER.warning(
                    "%s [%s] AUTO HEAT RESTART! Temp %.2f°C < Adjusted Target %.2f°C → Switching to HEAT",
                    LOG_PREFIX, self.name, self._current_temp, adjusted_target
                )
                self._hvac_mode = HVACMode.HEAT
                self.async_write_ha_state()

    # ==================================================================================
    # TEMPERATURE OFFSET (v1.7.0 - Radiator vs Wall Thermostat)
    # ==================================================================================

    def _get_adjusted_target_temp(self) -> float:
        """
        Calculate adjusted target temperature based on thermostat type.

        Radiator thermostats mounted on the radiator valve measure higher
        temperatures than the actual room temperature. To compensate, we
        add an offset to the target temperature when using radiator thermostats.

        Returns:
            Adjusted target temperature in °C
        """
        if self._thermostat_type == THERMOSTAT_TYPE_RADIATOR:
            adjusted = self._target_temp + self._temp_offset
            _LOGGER.debug(
                "%s [%s] Adjusted target: %.1f°C (base) + %.1f°C (offset) = %.1f°C (radiator thermostat)",
                LOG_PREFIX, self.name, self._target_temp, self._temp_offset, adjusted
            )
            return adjusted
        else:
            # Wall thermostat - no adjustment needed
            return self._target_temp

    # ==================================================================================
    # ADAPTIVE HYSTERESIS
    # ==================================================================================

    def _get_effective_hysteresis(self) -> float:
        """Calculate effective hysteresis (adaptive or base)."""
        # NEW v1.6.0: Underfloor heating uses NO hysteresis
        if self._heating_mode == HEATING_MODE_UNDERFLOOR:
            return 0.0

        # Radiator mode: use adaptive or base hysteresis
        if not self._adaptive_hysteresis_enabled or self._outdoor_temp is None:
            return self._base_hysteresis

        multiplier = outdoor_multiplier(self._outdoor_temp)

        effective_hyst = self._base_hysteresis * multiplier

        _LOGGER.debug(
            "%s [%s] Adaptive hyst: %.2f × %.2f = %.2f (outdoor=%.1f°C)",
            LOG_PREFIX, self.name, self._base_hysteresis, multiplier,
            effective_hyst, self._outdoor_temp
        )

        return effective_hyst

    # ==================================================================================
    # PRESET MODES
    # ==================================================================================

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        if preset_mode not in PRESET_MODES:
            _LOGGER.warning("%s [%s] Invalid preset: %s", LOG_PREFIX, self.name, preset_mode)
            return

        old_preset = self._preset_mode
        self._preset_mode = preset_mode

        _LOGGER.info("%s [%s] Preset: %s → %s", LOG_PREFIX, self.name, old_preset, preset_mode)

        # NEW v1.6.0: Always ensure HVAC is in HEAT mode when changing presets
        if self._hvac_mode == HVACMode.OFF:
            self._hvac_mode = HVACMode.HEAT
            _LOGGER.info("%s [%s] Auto-switched to HEAT mode", LOG_PREFIX, self.name)

        if preset_mode == PRESET_AUTO:
            if self._schedule:
                self._apply_current_schedule_block()
                if not self._schedule_tracker:
                    self._schedule_tracker = async_track_time_interval(
                        self.hass,
                        self._check_schedule,
                        timedelta(minutes=15)
                    )
            else:
                _LOGGER.warning("%s [%s] AUTO preset but no schedule configured!", LOG_PREFIX, self.name)

        elif preset_mode == PRESET_MANUAL:
            if self._schedule_tracker:
                self._schedule_tracker()
                self._schedule_tracker = None

        elif preset_mode in [PRESET_COMFORT, PRESET_ECO, PRESET_AWAY]:
            self._target_temp = PRESET_TEMPERATURES[preset_mode]
            _LOGGER.info(
                "%s [%s] Preset '%s' → %.1f°C",
                LOG_PREFIX, self.name, preset_mode, self._target_temp
            )

            if self._schedule_tracker:
                self._schedule_tracker()
                self._schedule_tracker = None

        await self._evaluate_heating()
        self.async_write_ha_state()

    @property
    def preset_mode(self) -> Optional[str]:
        return self._preset_mode

    @property
    def preset_modes(self) -> list[str]:
        return PRESET_MODES

    # ==================================================================================
    # SCHEDULE
    # ==================================================================================

    def _apply_current_schedule_block(self):
        """Apply current schedule block."""
        if not self._schedule or self._preset_mode != PRESET_AUTO:
            return

        now = datetime.now().time()
        for block in self._schedule:
            try:
                start_time = datetime.strptime(str(block["start"])[:5], "%H:%M").time()
                end_time = datetime.strptime(str(block["end"])[:5], "%H:%M").time()

                if start_time <= end_time:
                    if start_time <= now < end_time:
                        self._target_temp = float(block["temp"])
                        _LOGGER.info(
                            "%s [%s] Schedule: %s (%.1f°C)",
                            LOG_PREFIX, self.name, block.get("label", "Period"), self._target_temp
                        )
                        return
                else:
                    if now >= start_time or now < end_time:
                        self._target_temp = float(block["temp"])
                        _LOGGER.info(
                            "%s [%s] Schedule: %s (%.1f°C)",
                            LOG_PREFIX, self.name, block.get("label", "Period"), self._target_temp
                        )
                        return
            except (KeyError, ValueError, TypeError) as e:
                _LOGGER.warning("%s [%s] Invalid schedule block: %s", LOG_PREFIX, self.name, e)

    async def _check_schedule(self, now):
        """Schedule check (periodic)."""
        if self._preset_mode != PRESET_AUTO:
            return

        old_target = self._target_temp
        self._apply_current_schedule_block()

        if old_target != self._target_temp:
            _LOGGER.info(
                "%s [%s] Schedule changed: %.1f → %.1f°C",
                LOG_PREFIX, self.name, old_target, self._target_temp
            )
            await self._evaluate_heating()
            self.async_write_ha_state()

    # ==================================================================================
    # HEATING CONTROL (v1.6.0 - Underfloor vs Radiator)
    # ==================================================================================

    async def _evaluate_heating(self):
        """Evaluate heating need."""
        if self._hvac_mode == HVACMode.OFF:
            if self._is_heating:
                await self._set_heating(False, reason="HVAC OFF")
            return

        if self._current_temp is None:
            _LOGGER.debug("%s [%s] Waiting for temperature...", LOG_PREFIX, self.name)
            return

        # Door/window check
        for door in self._door_sensors:
            state = self.hass.states.get(door)
            if state and state.state == "on":
                if self._is_heating:
                    await self._set_heating(False, reason="Door/window open")
                return

        # NEW v1.7.0: Get adjusted target temperature (compensates for radiator thermostats)
        adjusted_target = self._get_adjusted_target_temp()
        effective_hysteresis = self._get_effective_hysteresis()
        diff = adjusted_target - self._current_temp

        _LOGGER.debug(
            "%s [%s] Evaluate: current=%.2f target=%.2f adjusted_target=%.2f diff=%.2f hyst=%.2f mode=%s thermostat=%s",
            LOG_PREFIX, self.name, self._current_temp, self._target_temp, adjusted_target,
            diff, effective_hysteresis, self._heating_mode, self._thermostat_type
        )

        # NEW v1.6.0: Different logic for underfloor vs radiator
        if self._heating_mode == HEATING_MODE_UNDERFLOOR:
            # Underfloor: NO hysteresis - instant on/off
            if self._current_temp < adjusted_target:
                await self._set_heating(True, reason="Underfloor needs heat (no hysteresis)")
            elif self._current_temp >= adjusted_target:
                await self._set_heating(False, reason="Underfloor target reached (no hysteresis)")
        else:
            # Radiator: WITH hysteresis
            if diff > effective_hysteresis:
                if self._is_heating and self._afterheat_joined:
                    # The zone itself wants heat now: it is real demand, no longer just riding along
                    self._afterheat_joined = False
                    if self._boiler_entity:
                        await self._boiler.turn_on(self._boiler_entity, zone=self.name, afterheat=False)
                else:
                    await self._set_heating(True, reason=f"Needs heat (diff={diff:.2f}°C)")
            elif diff < -effective_hysteresis:
                await self._set_heating(False, reason=f"Too warm (diff={diff:.2f}°C)")
            elif self._afterheat and not self._is_heating and diff > 0 and self._boiler.has_real_demand():
                _LOGGER.info(
                    "%s [%s] AFTERHEAT: current=%.2f°C < target=%.2f°C, boiler runs for %s",
                    LOG_PREFIX, self.name, self._current_temp, adjusted_target, self._boiler.get_active_zones()
                )
                await self._set_heating(True, reason="Afterheat (boiler already running)", afterheat=True)

    async def _set_heating(self, enable: bool, reason: Optional[str] = None, afterheat: bool = False):
        """Control relays and boiler."""
        if enable == self._is_heating:
            return

        self._is_heating = enable
        self._afterheat_joined = enable and afterheat
        state_txt = "ON" if enable else "OFF"

        if enable:
            for relay in self._relay_entities:
                await self._call_switch_service("turn_on", relay)
            if self._boiler_entity:
                await self._boiler.turn_on(self._boiler_entity, zone=self.name, afterheat=afterheat)
        else:
            for relay in self._relay_entities:
                await self._call_switch_service("turn_off", relay)
            if self._boiler_entity:
                await self._boiler.turn_off(self._boiler_entity, zone=self.name)

        _LOGGER.info(
            "%s [%s] Heating %s %s",
            LOG_PREFIX, self.name, state_txt, f"({reason})" if reason else ""
        )
        self.async_write_ha_state()

    async def _call_switch_service(self, action: str, entity_id: str) -> bool:
        """Call switch service. A failed command is remembered and retried by the watchdog."""
        try:
            await self.hass.services.async_call(
                "switch",
                action,
                {"entity_id": entity_id},
                blocking=True,
            )
            _LOGGER.debug("%s [%s] switch.%s → %s", LOG_PREFIX, self.name, action, entity_id)
            self._failed_relay_actions.pop(entity_id, None)
            return True
        except Exception as e:
            self._failed_relay_actions[entity_id] = action
            _LOGGER.error(
                "%s [%s] Relay command FAILED %s → %s: %s (will retry)",
                LOG_PREFIX, self.name, action, entity_id, e
            )
            return False

    # ==================================================================================
    # THERMOSTAT INTERFACE (v1.6.0 - Always HEAT mode when adjusting)
    # ==================================================================================

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return

        old_target = self._target_temp
        self._target_temp = float(temp)

        # Auto MANUAL preset switch
        if self._preset_mode != PRESET_MANUAL:
            _LOGGER.info("%s [%s] Manual adjustment → MANUAL preset", LOG_PREFIX, self.name)
            self._preset_mode = PRESET_MANUAL

            if self._schedule_tracker:
                self._schedule_tracker()
                self._schedule_tracker = None

        # NEW v1.6.0: Always set to HEAT mode when adjusting temperature
        if self._hvac_mode == HVACMode.OFF:
            self._hvac_mode = HVACMode.HEAT
            _LOGGER.info("%s [%s] Temperature adjusted → Auto-switched to HEAT", LOG_PREFIX, self.name)

        _LOGGER.info(
            "%s [%s] Target: %.1f → %.1f°C",
            LOG_PREFIX, self.name, old_target, self._target_temp
        )
        await self._evaluate_heating()
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set HVAC mode (explicit OFF control)."""
        old_mode = self._hvac_mode
        self._hvac_mode = hvac_mode
        _LOGGER.info("%s [%s] HVAC: %s → %s", LOG_PREFIX, self.name, old_mode, hvac_mode)
        await self._evaluate_heating()
        self.async_write_ha_state()

    # ==================================================================================
    # PROPERTIES
    # ==================================================================================

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def hvac_action(self):
        """HVAC action (off/idle/heating)."""
        if self._hvac_mode == HVACMode.OFF:
            return "off"
        return "heating" if self._is_heating else "idle"

    @property
    def current_temperature(self) -> Optional[float]:
        return self._current_temp

    @property
    def target_temperature(self) -> float:
        return self._target_temp

    def _door_open(self) -> bool:
        """True if any door/window sensor of the zone is open."""
        return any(
            (state := self.hass.states.get(door)) is not None and state.state == "on"
            for door in self._door_sensors
        )

    def _limp_active(self) -> bool:
        """True while the zone runs in limp mode (no usable sensor)."""
        return self._sensor_fault is not None and self._sensor_source == SENSOR_SOURCE_NONE

    def _limp_next_in_min(self) -> Optional[int]:
        """Minutes until limp heating starts: None without a cycle, 0 while it is on, else the wait (bounded by midnight)."""
        if not self._limp_active() or self._limp_effective_on is None:
            return None
        local = dt_util.now()
        minute_of_day = local.hour * 60 + local.minute
        phase = minute_of_day % self._limp_period_minutes
        if phase < self._limp_effective_on:
            return 0
        return min(self._limp_period_minutes - phase, 24 * 60 - minute_of_day)

    def _reason(self, with_next: bool) -> dict:
        """The decision reason of the zone's current state (language-neutral)."""
        target = self._get_adjusted_target_temp()
        hysteresis = self._get_effective_hysteresis()
        limp_active = self._limp_active()
        reason = decision_reason(
            hvac_off=self._hvac_mode == HVACMode.OFF,
            no_reading=self._current_temp is None,
            door_open=self._door_open(),
            overheat=self._current_temp is not None and self._current_temp >= self._overheat_temp,
            limp_active=limp_active,
            limp_heating=limp_active and self._is_heating,
            limp_next_in_min=self._limp_next_in_min() if with_next else None,
            heating=self._is_heating,
            joined=self._afterheat_joined,
            current=self._current_temp,
            target=target,
            on_below=target - hysteresis,
            off_above=target + hysteresis,
        )
        if not with_next:
            reason.pop("next_in_min", None)  # a changing value would write the climate state every minute
        return reason

    def _safe_reason(self) -> Optional[dict]:
        """Reason for the climate attributes; a failure is logged and never blocks the state write."""
        try:
            return self._reason(with_next=False)
        except Exception:
            _LOGGER.exception("%s [%s] Computing the decision reason FAILED", LOG_PREFIX, self.name)
            return None

    def overview_snapshot(self) -> dict:
        """All data of this zone for the overview entity; every key is always present."""
        target = self._get_adjusted_target_temp()
        hysteresis = self._get_effective_hysteresis()
        next_change = None
        if self._preset_mode == PRESET_AUTO:
            next_change = next_schedule_change(self._schedule, datetime.now())
        return {
            "name": self.name,
            "entity_id": self.entity_id,
            "sensor_entity": self._sensor_entity_id,
            "heating_mode": self._heating_mode,
            "hvac_mode": str(self._hvac_mode),
            "hvac_action": self.hvac_action,
            "preset": self._preset_mode,
            "current": self._current_temp,
            "target": self._target_temp,
            "adjusted_target": target,
            "hysteresis": hysteresis,
            "on_below": target - hysteresis,
            "off_above": target + hysteresis,
            "sensor_source": self._sensor_source,
            "sensor_fault": self._sensor_fault,
            "limp": {
                "active": self._limp_active(),
                "on_min": self._limp_on_minutes,
                "effective_on_min": self._limp_effective_on if self._limp_active() else None,
                "period_min": self._limp_period_minutes,
                "next_in_min": self._limp_next_in_min(),
            },
            "next_change": next_change,
            "afterheat": self._afterheat,
            "joined": self._afterheat_joined,
            "relay_unavailable": sorted(self._relay_unavailable_since),
            "relay_fault": sorted(self._failed_relay_actions),
            "reason": self._reason(with_next=True),
        }

    @property
    def extra_state_attributes(self):
        """Extra attributes."""
        attrs = {
            "preset_mode": self._preset_mode,
            "heating_mode": self._heating_mode,
            "thermostat_type": self._thermostat_type,
            "temp_offset": self._temp_offset,
            "adjusted_target_temp": self._get_adjusted_target_temp(),
            "overheat_protection": self._overheat_temp,
            "base_hysteresis": self._base_hysteresis,
            "preset_temperatures": dict(PRESET_TEMPERATURES),
            "sensor_fault": self._sensor_fault,
            "sensor_source": self._sensor_source,
            "sensor_stale_hours": self._sensor_stale_timeout.total_seconds() / 3600,
            "afterheat": self._afterheat,
            "relay_fault": sorted(self._failed_relay_actions),
            "relay_unavailable": sorted(self._relay_unavailable_since),
            "limp_active": self._sensor_fault is not None and self._sensor_source == SENSOR_SOURCE_NONE,
            "outdoor_source": self._limp_outdoor_source,
            "limp_on_minutes": self._limp_on_minutes,
            "limp_period_minutes": self._limp_period_minutes,
            "reason": self._safe_reason(),
        }

        if self._adaptive_hysteresis_enabled and self._outdoor_temp is not None:
            attrs["outdoor_temperature"] = self._outdoor_temp
            attrs["effective_hysteresis"] = self._get_effective_hysteresis()

        return attrs

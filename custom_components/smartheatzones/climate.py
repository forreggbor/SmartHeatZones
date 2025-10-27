"""
SmartHeatZones - Climate Platform
Version: 1.5.1 (HA 2025.10+ compatible)
Author: forreggbor

FIXES in 1.5.1:
- Schedule reload on options update (update listener in __init__.py)
- Auto HEAT restart when temp drops below target (even if HVAC mode is OFF)
- DEFAULT_AUTO_SCHEDULE fallback removed (empty schedule = warning only)

FIXES in 1.5.0-fixed:
- Event-based relay monitoring (instant detection, no polling delay)
- Preset mode icons for Auto and Manual
- Schedule UI in options (compact, one row per period)
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

from .const import (
    DOMAIN,
    DATA_BOILER_MAIN,
    DATA_ACTIVE_ZONES,
    DATA_OUTDOOR_TEMP,
    CONF_SENSOR,
    CONF_ZONE_RELAYS,
    CONF_BOILER_MAIN,
    CONF_DOOR_SENSORS,
    CONF_HYSTERESIS,
    CONF_SCHEDULE,
    CONF_OVERHEAT_PROTECTION,
    CONF_OUTDOOR_SENSOR,
    CONF_ADAPTIVE_HYSTERESIS,
    DEFAULT_HYSTERESIS,
    DEFAULT_OVERHEAT_TEMP,
    DEFAULT_ADAPTIVE_HYSTERESIS,
    PRESET_AUTO,
    PRESET_MANUAL,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_AWAY,
    PRESET_MODES,
    PRESET_TEMPERATURES,
    ADAPTIVE_HYSTERESIS_MULTIPLIERS,
    LOG_PREFIX,
    ERR_OVERHEAT,
)


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Platform beállítása és zónák létrehozása."""
    name = entry.title
    data = entry.options if entry.options else entry.data

    sensor = data.get(CONF_SENSOR)
    relays = data.get(CONF_ZONE_RELAYS, [])
    boiler_entity = data.get(CONF_BOILER_MAIN)
    doors = data.get(CONF_DOOR_SENSORS, [])
    hysteresis = data.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)

    # FIX v1.5.1: No default schedule fallback - warn if empty
    schedule = data.get(CONF_SCHEDULE, [])
    if not schedule:
        _LOGGER.warning(
            "%s [%s] No schedule configured! Set it in Options. Auto preset will not work.",
            LOG_PREFIX, name
        )

    overheat_temp = data.get(CONF_OVERHEAT_PROTECTION, DEFAULT_OVERHEAT_TEMP)
    outdoor_sensor = data.get(CONF_OUTDOOR_SENSOR)
    adaptive_hyst = data.get(CONF_ADAPTIVE_HYSTERESIS, DEFAULT_ADAPTIVE_HYSTERESIS)

    _LOGGER.info(
        "%s Creating climate entity: %s | Sensor=%s | Relays=%s | Overheat=%.1f°C | Schedule=%d blocks",
        LOG_PREFIX, name, sensor, relays, overheat_temp, len(schedule)
    )

    entity = SmartHeatZoneClimate(
        hass=hass,
        name=name,
        sensor_entity_id=sensor,
        relay_entities=relays,
        boiler_entity=boiler_entity,
        door_sensors=doors,
        hysteresis=hysteresis,
        schedule=schedule,
        overheat_temp=overheat_temp,
        outdoor_sensor=outdoor_sensor,
        adaptive_hysteresis_enabled=adaptive_hyst,
    )
    async_add_entities([entity])
    _LOGGER.info("%s Climate entity created for %s", LOG_PREFIX, name)


class SmartHeatZoneClimate(ClimateEntity, RestoreEntity):
    """Zóna termosztát entitás v1.5.1."""

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
        sensor_entity_id: str,
        relay_entities: list[str],
        boiler_entity: Optional[str],
        door_sensors: list[str],
        hysteresis: float,
        schedule: list,
        overheat_temp: float,
        outdoor_sensor: Optional[str],
        adaptive_hysteresis_enabled: bool,
    ):
        """Inicializálás."""
        self.hass = hass
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{name.lower().replace(' ', '_')}"

        self._sensor_entity_id = sensor_entity_id
        self._relay_entities = relay_entities or []
        self._boiler_entity = boiler_entity
        self._door_sensors = door_sensors or []
        self._base_hysteresis = hysteresis
        self._schedule = schedule or []
        self._overheat_temp = overheat_temp
        self._outdoor_sensor = outdoor_sensor
        self._adaptive_hysteresis_enabled = adaptive_hysteresis_enabled

        self._current_temp = None
        self._target_temp = 21.0
        self._hvac_mode = HVACMode.HEAT
        self._is_heating = False
        self._preset_mode = PRESET_AUTO

        self._schedule_tracker = None
        self._outdoor_temp = None
        self._boiler = hass.data[DOMAIN][DATA_BOILER_MAIN]

        _LOGGER.info(
            "%s [%s] Initialized | Preset=%s | Overheat=%.1f°C | Adaptive=%s",
            LOG_PREFIX, self.name, self._preset_mode, self._overheat_temp,
            self._adaptive_hysteresis_enabled
        )

        if self._schedule and self._preset_mode == PRESET_AUTO:
            self._apply_current_schedule_block()

    async def async_added_to_hass(self):
        """Entitás hozzáadása HA-hoz."""
        await super().async_added_to_hass()

        # State restoration
        last_state = await self.async_get_last_state()
        if last_state:
            if last_state.attributes.get(ATTR_TEMPERATURE):
                self._target_temp = float(last_state.attributes[ATTR_TEMPERATURE])
                _LOGGER.info("%s [%s] Restored target: %.1f°C", LOG_PREFIX, self.name, self._target_temp)

            if last_state.state in [HVACMode.HEAT, HVACMode.OFF]:
                self._hvac_mode = last_state.state
                _LOGGER.info("%s [%s] Restored HVAC: %s", LOG_PREFIX, self.name, self._hvac_mode)

            if last_state.attributes.get("preset_mode"):
                self._preset_mode = last_state.attributes["preset_mode"]
                _LOGGER.info("%s [%s] Restored preset: %s", LOG_PREFIX, self.name, self._preset_mode)

        # Hőmérséklet szenzor
        if self._sensor_entity_id:
            async_track_state_change_event(
                self.hass,
                [self._sensor_entity_id],
                self._sensor_changed,
            )

            sensor_state = self.hass.states.get(self._sensor_entity_id)
            if sensor_state and sensor_state.state not in ["unavailable", "unknown", "none"]:
                try:
                    self._current_temp = float(sensor_state.state)
                    _LOGGER.info("%s [%s] Initial temp: %.2f°C", LOG_PREFIX, self.name, self._current_temp)
                except (ValueError, TypeError):
                    pass

        # FIX #1: EVENT-BASED RELAY MONITORING (Azonnali reagálás!)
        if self._relay_entities:
            for relay_id in self._relay_entities:
                async_track_state_change_event(
                    self.hass,
                    [relay_id],
                    self._relay_state_changed,
                )
            _LOGGER.info(
                "%s [%s] Event-based relay monitoring enabled for %d relays",
                LOG_PREFIX, self.name, len(self._relay_entities)
            )

        # Kültéri szenzor
        if self._outdoor_sensor and self._adaptive_hysteresis_enabled:
            async_track_state_change_event(
                self.hass,
                [self._outdoor_sensor],
                self._outdoor_sensor_changed,
            )

            outdoor_state = self.hass.states.get(self._outdoor_sensor)
            if outdoor_state and outdoor_state.state not in ["unavailable", "unknown", "none"]:
                try:
                    self._outdoor_temp = float(outdoor_state.state)
                    _LOGGER.info("%s [%s] Outdoor temp: %.2f°C", LOG_PREFIX, self.name, self._outdoor_temp)
                except (ValueError, TypeError):
                    pass

        # Ajtó/ablak szenzorok
        for door in self._door_sensors:
            async_track_state_change_event(
                self.hass,
                [door],
                self._door_changed,
            )

        # Schedule tracker
        if self._schedule and self._preset_mode == PRESET_AUTO:
            self._schedule_tracker = async_track_time_interval(
                self.hass,
                self._check_schedule,
                timedelta(minutes=15)
            )
            _LOGGER.debug("%s [%s] Schedule tracker enabled", LOG_PREFIX, self.name)

        await self._evaluate_heating()

    # ==================================================================================
    # FIX #1: EVENT-BASED RELAY MONITORING
    # ==================================================================================

    @callback
    async def _relay_state_changed(self, event):
        """
        AZONNALI relay állapot változás detektálás (event-based).

        Ha egy relay állapota megváltozik (manuális kapcsolás):
        - Azonnal frissíti az integráció állapotát
        - Szinkronizálja a kazán koordinációt
        """
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")

        if not new_state or not old_state:
            return

        # Ha állapot változott
        if new_state.state != old_state.state:
            relay_id = new_state.entity_id
            is_on = new_state.state == "on"

            _LOGGER.info(
                "%s [%s] Relay state changed: %s → %s (event-based detection)",
                LOG_PREFIX, self.name, relay_id, new_state.state.upper()
            )

            # Ellenőrizzük az összes relay állapotát
            relay_states = []
            for r_id in self._relay_entities:
                r_state = self.hass.states.get(r_id)
                if r_state:
                    relay_states.append(r_state.state == "on")

            # BÁRMELYIK relay BE → zóna heating
            actual_heating = any(relay_states) if relay_states else False

            # Ha eltér az integráció által várt állapottól
            if actual_heating != self._is_heating:
                _LOGGER.warning(
                    "%s [%s] MANUAL OVERRIDE DETECTED! Expected=%s, Actual=%s → Synchronizing immediately",
                    LOG_PREFIX, self.name, self._is_heating, actual_heating
                )

                # Szinkronizálás
                self._is_heating = actual_heating

                # Kazán koordináció
                if actual_heating and self._boiler_entity:
                    await self._boiler.turn_on(self._boiler_entity, zone=self.name)
                elif not actual_heating and self._boiler_entity:
                    await self._boiler.turn_off(self._boiler_entity, zone=self.name)

                self.async_write_ha_state()

                _LOGGER.info(
                    "%s [%s] Synchronized: heating=%s",
                    LOG_PREFIX, self.name, "ON" if actual_heating else "OFF"
                )

    # ==================================================================================
    # SZENZOR CALLBACKS
    # ==================================================================================

    @callback
    async def _sensor_changed(self, event):
        """Hőmérséklet szenzor változás."""
        new_state = event.data.get("new_state")
        if not new_state:
            return

        if new_state.state in ["unavailable", "unknown", "none"]:
            _LOGGER.warning("%s [%s] Sensor unavailable", LOG_PREFIX, self.name)
            return

        try:
            self._current_temp = float(new_state.state)
            _LOGGER.debug("%s [%s] Sensor: %.2f°C", LOG_PREFIX, self.name, self._current_temp)

            await self._check_overheat_protection()

            # FIX v1.5.1: Auto-restart HEAT if temp drops below target (even if HVAC mode is OFF)
            await self._auto_heat_restart()

            await self._evaluate_heating()

        except (ValueError, TypeError) as e:
            _LOGGER.error("%s [%s] Invalid sensor value: %s", LOG_PREFIX, self.name, new_state.state)

    @callback
    async def _outdoor_sensor_changed(self, event):
        """Kültéri hőmérséklet változás."""
        new_state = event.data.get("new_state")
        if not new_state or new_state.state in ["unavailable", "unknown", "none"]:
            return

        try:
            old_outdoor = self._outdoor_temp
            self._outdoor_temp = float(new_state.state)
            _LOGGER.debug(
                "%s [%s] Outdoor: %.2f°C",
                LOG_PREFIX, self.name, self._outdoor_temp
            )

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
        """Ajtó/ablak változás."""
        new_state = event.data.get("new_state")
        if new_state and new_state.state == "on":
            _LOGGER.warning("%s [%s] Door/window open – heating paused", LOG_PREFIX, self.name)
            await self._set_heating(False, reason="Door/window open")
        elif new_state and new_state.state == "off":
            _LOGGER.info("%s [%s] Door/window closed – re-evaluating", LOG_PREFIX, self.name)
            await self._evaluate_heating()

    # ==================================================================================
    # OVERHEAT PROTECTION
    # ==================================================================================

    async def _check_overheat_protection(self):
        """Túlmelegedés védelem."""
        if self._current_temp is None:
            return

        if self._current_temp >= self._overheat_temp:
            if self._is_heating:
                _LOGGER.error(
                    "%s [%s] OVERHEAT! Current=%.2f°C >= Limit=%.1f°C → Shutdown",
                    LOG_PREFIX, self.name, self._current_temp, self._overheat_temp
                )
                await self._set_heating(False, reason=ERR_OVERHEAT)

    # ==================================================================================
    # FIX v1.5.1: AUTO HEAT RESTART
    # ==================================================================================

    async def _auto_heat_restart(self):
        """
        Auto-restart HEAT mode if temperature drops below target.

        Scenario: User manually sets HVAC to OFF, but temperature drops.
        → Automatically switch back to HEAT mode to maintain comfort.
        """
        if self._hvac_mode == HVACMode.OFF and self._current_temp is not None:
            effective_hysteresis = self._get_effective_hysteresis()
            diff = self._target_temp - self._current_temp

            # If temp drops significantly below target, auto-restart heating
            if diff > effective_hysteresis:
                _LOGGER.warning(
                    "%s [%s] AUTO HEAT RESTART! Temp %.2f°C < Target %.2f°C (diff=%.2f, hyst=%.2f) → Switching to HEAT",
                    LOG_PREFIX, self.name, self._current_temp, self._target_temp, diff, effective_hysteresis
                )
                self._hvac_mode = HVACMode.HEAT
                self.async_write_ha_state()

    # ==================================================================================
    # ADAPTIVE HYSTERESIS
    # ==================================================================================

    def _get_effective_hysteresis(self) -> float:
        """Adaptív hiszterézis számítása."""
        if not self._adaptive_hysteresis_enabled or self._outdoor_temp is None:
            return self._base_hysteresis

        multiplier = 1.0
        for temp_threshold, mult in sorted(ADAPTIVE_HYSTERESIS_MULTIPLIERS.items()):
            if self._outdoor_temp < temp_threshold:
                multiplier = mult
                break

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
        """Preset mód beállítása."""
        if preset_mode not in PRESET_MODES:
            _LOGGER.warning("%s [%s] Invalid preset: %s", LOG_PREFIX, self.name, preset_mode)
            return

        old_preset = self._preset_mode
        self._preset_mode = preset_mode

        _LOGGER.info(
            "%s [%s] Preset: %s → %s",
            LOG_PREFIX, self.name, old_preset, preset_mode
        )

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
                _LOGGER.warning("%s [%s] AUTO but no schedule!", LOG_PREFIX, self.name)

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
        """Elérhető preset módok listája."""
        return PRESET_MODES

    # ==================================================================================
    # SCHEDULE
    # ==================================================================================

    def _apply_current_schedule_block(self):
        """Napszak alkalmazása."""
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
        """Schedule ellenőrzés."""
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
    # HEATING CONTROL
    # ==================================================================================

    async def _evaluate_heating(self):
        """Fűtési logika."""
        if self._hvac_mode == HVACMode.OFF:
            if self._is_heating:
                await self._set_heating(False, reason="HVAC OFF")
            return

        if self._current_temp is None:
            _LOGGER.debug("%s [%s] Waiting for temperature...", LOG_PREFIX, self.name)
            return

        for door in self._door_sensors:
            state = self.hass.states.get(door)
            if state and state.state == "on":
                if self._is_heating:
                    await self._set_heating(False, reason="Door/window open")
                return

        effective_hysteresis = self._get_effective_hysteresis()
        diff = self._target_temp - self._current_temp

        _LOGGER.debug(
            "%s [%s] Evaluate: current=%.2f target=%.2f diff=%.2f hyst=%.2f",
            LOG_PREFIX, self.name, self._current_temp, self._target_temp,
            diff, effective_hysteresis
        )

        if diff > effective_hysteresis:
            await self._set_heating(True, reason=f"Needs heat (diff={diff:.2f}°C)")
        elif diff < -effective_hysteresis:
            await self._set_heating(False, reason=f"Too warm (diff={diff:.2f}°C)")

    async def _set_heating(self, enable: bool, reason: Optional[str] = None):
        """Relék és kazán vezérlése."""
        if enable == self._is_heating:
            return

        self._is_heating = enable
        state_txt = "ON" if enable else "OFF"

        if enable:
            for relay in self._relay_entities:
                await self._call_switch_service("turn_on", relay)
            if self._boiler_entity:
                await self._boiler.turn_on(self._boiler_entity, zone=self.name)
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

    async def _call_switch_service(self, action: str, entity_id: str):
        """Switch service hívás."""
        try:
            await self.hass.services.async_call(
                "switch",
                action,
                {"entity_id": entity_id},
                blocking=True,
            )
            _LOGGER.debug("%s [%s] switch.%s → %s", LOG_PREFIX, self.name, action, entity_id)
        except Exception as e:
            _LOGGER.warning("%s [%s] Failed relay control %s: %s", LOG_PREFIX, self.name, entity_id, e)

    # ==================================================================================
    # THERMOSTAT INTERFACE
    # ==================================================================================

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Hőmérséklet beállítása."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return

        old_target = self._target_temp
        self._target_temp = float(temp)

        # Auto MANUAL váltás
        if self._preset_mode != PRESET_MANUAL:
            _LOGGER.info(
                "%s [%s] Manual adjustment → MANUAL preset",
                LOG_PREFIX, self.name
            )
            self._preset_mode = PRESET_MANUAL

            if self._schedule_tracker:
                self._schedule_tracker()
                self._schedule_tracker = None

        # Auto HVAC váltás
        if self._current_temp is not None:
            if self._target_temp > self._current_temp and self._hvac_mode == HVACMode.OFF:
                self._hvac_mode = HVACMode.HEAT
                _LOGGER.info(
                    "%s [%s] Auto HEAT (target %.1f > current %.1f)",
                    LOG_PREFIX, self.name, self._target_temp, self._current_temp
                )
            elif self._target_temp < self._current_temp and self._hvac_mode == HVACMode.HEAT:
                self._hvac_mode = HVACMode.OFF
                _LOGGER.info(
                    "%s [%s] Auto OFF (target %.1f < current %.1f)",
                    LOG_PREFIX, self.name, self._target_temp, self._current_temp
                )

        _LOGGER.info(
            "%s [%s] Target: %.1f → %.1f°C",
            LOG_PREFIX, self.name, old_target, self._target_temp
        )
        await self._evaluate_heating()
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """HVAC mód váltás."""
        old_mode = self._hvac_mode
        self._hvac_mode = hvac_mode
        _LOGGER.info(
            "%s [%s] HVAC: %s → %s",
            LOG_PREFIX, self.name, old_mode, hvac_mode
        )
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
        if self._hvac_mode == HVACMode.OFF:
            return "off"
        return "heating" if self._is_heating else "idle"

    @property
    def current_temperature(self) -> Optional[float]:
        return self._current_temp

    @property
    def target_temperature(self) -> float:
        return self._target_temp

    @property
    def extra_state_attributes(self):
        """Extra attribútumok."""
        attrs = {
            "preset_mode": self._preset_mode,
            "overheat_protection": self._overheat_temp,
            "base_hysteresis": self._base_hysteresis,
        }

        if self._adaptive_hysteresis_enabled and self._outdoor_temp is not None:
            attrs["outdoor_temperature"] = self._outdoor_temp
            attrs["effective_hysteresis"] = self._get_effective_hysteresis()

        return attrs

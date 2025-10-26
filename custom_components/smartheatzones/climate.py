"""
SmartHeatZones - Climate Platform (FIXED)
Version: 1.4.4 (HA 2025.10+ compatible)
Author: forreggbor
FIXES:
- Config/Options fallback logika
- Auto HVAC mode váltás
- Kezdeti HVAC mode = HEAT
- Schedule inicializálás
- State restoration
- Jobb hibaellenőrzés
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
    CONF_SENSOR,
    CONF_ZONE_RELAYS,
    CONF_BOILER_MAIN,
    CONF_DOOR_SENSORS,
    CONF_HYSTERESIS,
    CONF_SCHEDULE,
    DEFAULT_HYSTERESIS,
    LOG_PREFIX,
)


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Platform beállítása és zónák létrehozása."""
    name = entry.title

    # FIX #1: Config/Options fallback logika
    # Ha nincs options (új létrehozás), akkor data-ból olvassuk
    data = entry.options if entry.options else entry.data

    sensor = data.get(CONF_SENSOR)
    relays = data.get(CONF_ZONE_RELAYS, [])
    boiler_entity = data.get(CONF_BOILER_MAIN)
    doors = data.get(CONF_DOOR_SENSORS, [])
    hysteresis = data.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)
    schedule = data.get(CONF_SCHEDULE, [])

    _LOGGER.info(
        "%s Creating climate entity: %s | Sensor=%s | Relays=%s | Boiler=%s",
        LOG_PREFIX, name, sensor, relays, boiler_entity
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
    )
    async_add_entities([entity])
    _LOGGER.info("%s Climate entity created for %s", LOG_PREFIX, name)


class SmartHeatZoneClimate(ClimateEntity, RestoreEntity):
    """Zóna termosztát entitás (JAVÍTOTT VERZIÓ)."""

    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_min_temp = 5.0
    _attr_max_temp = 28.0

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
    ):
        """Inicializálás."""
        self.hass = hass
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{name.lower().replace(' ', '_')}"
        self._sensor_entity_id = sensor_entity_id
        self._relay_entities = relay_entities or []
        self._boiler_entity = boiler_entity
        self._door_sensors = door_sensors or []
        self._hysteresis = hysteresis
        self._schedule = schedule or []

        self._current_temp = None
        self._target_temp = 21.0

        # FIX #2: Kezdeti HVAC mode = HEAT (nem OFF!)
        self._hvac_mode = HVACMode.HEAT
        self._is_heating = False

        # Schedule tracker (később)
        self._schedule_tracker = None

        # BoilerManager
        self._boiler = hass.data[DOMAIN][DATA_BOILER_MAIN]

        # Debug infó
        _LOGGER.info(
            "%s [%s] Initialized | Sensor=%s | Relays=%s | Boiler=%s | Initial HVAC=%s",
            LOG_PREFIX,
            self.name,
            sensor_entity_id,
            relay_entities,
            boiler_entity,
            self._hvac_mode,
        )

        # FIX #3: Schedule inicializálás
        if self._schedule:
            self._apply_current_schedule_block()

    async def async_added_to_hass(self):
        """Regisztrálja az érzékelők figyelését és visszaállítja az állapotot."""
        await super().async_added_to_hass()

        # FIX #4: State restoration
        last_state = await self.async_get_last_state()
        if last_state:
            # Target temperature visszaállítás
            if last_state.attributes.get(ATTR_TEMPERATURE):
                self._target_temp = float(last_state.attributes[ATTR_TEMPERATURE])
                _LOGGER.info("%s [%s] Restored target temp: %.1f°C", LOG_PREFIX, self.name, self._target_temp)

            # HVAC mode visszaállítás
            if last_state.state in [HVACMode.HEAT, HVACMode.OFF]:
                self._hvac_mode = last_state.state
                _LOGGER.info("%s [%s] Restored HVAC mode: %s", LOG_PREFIX, self.name, self._hvac_mode)

        # Szenzor figyelés
        if self._sensor_entity_id:
            async_track_state_change_event(
                self.hass,
                [self._sensor_entity_id],
                self._sensor_changed,
            )
            _LOGGER.debug("%s [%s] Tracking sensor: %s", LOG_PREFIX, self.name, self._sensor_entity_id)

            # Kezdeti szenzor érték beolvasása
            sensor_state = self.hass.states.get(self._sensor_entity_id)
            if sensor_state and sensor_state.state not in ["unavailable", "unknown", "none"]:
                try:
                    self._current_temp = float(sensor_state.state)
                    _LOGGER.info("%s [%s] Initial temperature: %.2f°C", LOG_PREFIX, self.name, self._current_temp)
                except (ValueError, TypeError):
                    pass

        # Ajtó/ablak szenzor figyelés
        for door in self._door_sensors:
            async_track_state_change_event(
                self.hass,
                [door],
                self._door_changed,
            )

        # FIX #5: Schedule auto váltás (15 percenként)
        if self._schedule:
            self._schedule_tracker = async_track_time_interval(
                self.hass,
                self._check_schedule,
                timedelta(minutes=15)
            )
            _LOGGER.debug("%s [%s] Schedule tracker enabled (15 min interval)", LOG_PREFIX, self.name)

        # Kezdeti értékelés
        await self._evaluate_heating()

    @callback
    async def _sensor_changed(self, event):
        """Hőmérséklet szenzor változás."""
        new_state = event.data.get("new_state")
        if not new_state:
            return

        # FIX #6: Jobb hibaellenőrzés
        if new_state.state in ["unavailable", "unknown", "none"]:
            _LOGGER.warning("%s [%s] Sensor unavailable", LOG_PREFIX, self.name)
            return

        try:
            self._current_temp = float(new_state.state)
            _LOGGER.debug("%s [%s] Sensor updated: %.2f°C", LOG_PREFIX, self.name, self._current_temp)
            await self._evaluate_heating()
        except (ValueError, TypeError) as e:
            _LOGGER.error("%s [%s] Invalid sensor value: %s (%s)", LOG_PREFIX, self.name, new_state.state, e)

    @callback
    async def _door_changed(self, event):
        """Ajtó/ablak szenzor változás."""
        new_state = event.data.get("new_state")
        if new_state and new_state.state == "on":
            _LOGGER.warning("%s [%s] Door/window open – heating paused", LOG_PREFIX, self.name)
            await self._set_heating(False, reason="Door/window open")
        elif new_state and new_state.state == "off":
            _LOGGER.info("%s [%s] Door/window closed – re-evaluating heating", LOG_PREFIX, self.name)
            await self._evaluate_heating()

    def _apply_current_schedule_block(self):
        """Aktuális napszak szerinti target_temp beállítása."""
        if not self._schedule:
            return

        now = datetime.now().time()
        for block in self._schedule:
            try:
                start_time = datetime.strptime(str(block["start"]), "%H:%M").time()
                end_time = datetime.strptime(str(block["end"]), "%H:%M").time()

                # Éjfélen átnyúló időszak kezelése
                if start_time <= end_time:
                    if start_time <= now < end_time:
                        self._target_temp = float(block["temp"])
                        _LOGGER.info(
                            "%s [%s] Schedule applied: %s (%.1f°C)",
                            LOG_PREFIX, self.name, block.get("label", "Period"), self._target_temp
                        )
                        return
                else:  # Átnyúlik éjfélen (pl. 22:00-06:00)
                    if now >= start_time or now < end_time:
                        self._target_temp = float(block["temp"])
                        _LOGGER.info(
                            "%s [%s] Schedule applied: %s (%.1f°C)",
                            LOG_PREFIX, self.name, block.get("label", "Period"), self._target_temp
                        )
                        return
            except (KeyError, ValueError, TypeError) as e:
                _LOGGER.warning("%s [%s] Invalid schedule block: %s (%s)", LOG_PREFIX, self.name, block, e)

    async def _check_schedule(self, now):
        """Rendszeres napszak ellenőrzés (timer callback)."""
        old_target = self._target_temp
        self._apply_current_schedule_block()

        if old_target != self._target_temp:
            _LOGGER.info(
                "%s [%s] Schedule changed target: %.1f → %.1f°C",
                LOG_PREFIX, self.name, old_target, self._target_temp
            )
            await self._evaluate_heating()
            self.async_write_ha_state()

    async def _evaluate_heating(self):
        """Fűtési logika értékelése."""
        if self._hvac_mode == HVACMode.OFF:
            # Ha OFF módban vagyunk, kapcsoljuk ki a fűtést
            if self._is_heating:
                await self._set_heating(False, reason="HVAC mode is OFF")
            return

        if self._current_temp is None:
            _LOGGER.debug("%s [%s] Waiting for valid temperature...", LOG_PREFIX, self.name)
            return

        # Ha ajtó/ablak nyitva, nincs fűtés
        for door in self._door_sensors:
            state = self.hass.states.get(door)
            if state and state.state == "on":
                _LOGGER.debug("%s [%s] Door open, skipping heating", LOG_PREFIX, self.name)
                if self._is_heating:
                    await self._set_heating(False, reason="Door/window open")
                return

        diff = self._target_temp - self._current_temp
        _LOGGER.debug(
            "%s [%s] Evaluate: current=%.2f target=%.2f diff=%.2f hysteresis=%.2f",
            LOG_PREFIX,
            self.name,
            self._current_temp,
            self._target_temp,
            diff,
            self._hysteresis,
        )

        # Hiszterézis logika
        if diff > self._hysteresis:
            await self._set_heating(True, reason=f"Needs heat (diff={diff:.2f}°C)")
        elif diff < -self._hysteresis:
            await self._set_heating(False, reason=f"Too warm (diff={diff:.2f}°C)")
        # else: Hiszterézis sávban -> nincs változás

    async def _set_heating(self, enable: bool, reason: Optional[str] = None):
        """Zóna relék és kazán vezérlése."""
        if enable == self._is_heating:
            return

        self._is_heating = enable
        state_txt = "ON" if enable else "OFF"

        if enable:
            # Bekapcsolás
            for relay in self._relay_entities:
                await self._call_switch_service("turn_on", relay)
            if self._boiler_entity:
                await self._boiler.turn_on(self._boiler_entity, zone=self.name)
        else:
            # Kikapcsolás
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
        """Service hívás egy switch entity-hez."""
        try:
            await self.hass.services.async_call(
                "switch",
                action,
                {"entity_id": entity_id},
                blocking=True,
            )
            _LOGGER.debug("%s [%s] switch.%s → %s", LOG_PREFIX, self.name, action, entity_id)
        except Exception as e:
            _LOGGER.warning("%s [%s] Failed to control relay %s: %s", LOG_PREFIX, self.name, entity_id, e)

    # --- Lovelace termosztát interakciók -----------------------------------------

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Célhőmérséklet beállítása."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return

        old_target = self._target_temp
        self._target_temp = float(temp)

        # FIX #7: Auto HVAC mode váltás
        if self._current_temp is not None:
            if self._target_temp > self._current_temp and self._hvac_mode == HVACMode.OFF:
                self._hvac_mode = HVACMode.HEAT
                _LOGGER.info(
                    "%s [%s] Auto-switched to HEAT (target %.1f > current %.1f)",
                    LOG_PREFIX, self.name, self._target_temp, self._current_temp
                )
            elif self._target_temp < self._current_temp and self._hvac_mode == HVACMode.HEAT:
                self._hvac_mode = HVACMode.OFF
                _LOGGER.info(
                    "%s [%s] Auto-switched to OFF (target %.1f < current %.1f)",
                    LOG_PREFIX, self.name, self._target_temp, self._current_temp
                )

        _LOGGER.info(
            "%s [%s] Target temperature: %.1f → %.1f°C",
            LOG_PREFIX, self.name, old_target, self._target_temp
        )
        await self._evaluate_heating()
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """HVAC mód váltása."""
        old_mode = self._hvac_mode
        self._hvac_mode = hvac_mode
        _LOGGER.info(
            "%s [%s] HVAC mode: %s → %s",
            LOG_PREFIX, self.name, old_mode, hvac_mode
        )
        await self._evaluate_heating()
        self.async_write_ha_state()

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
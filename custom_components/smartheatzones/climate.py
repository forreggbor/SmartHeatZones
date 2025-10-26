"""
SmartHeatZones - Climate Platform
Version: 1.4.3 (HA 2025.10+ compatible)
Author: forreggbor
"""

import logging
from datetime import datetime
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
from homeassistant.helpers.event import async_track_state_change_event

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
    data = entry.options

    sensor = data.get(CONF_SENSOR)
    relays = data.get(CONF_ZONE_RELAYS, [])
    boiler_entity = data.get(CONF_BOILER_MAIN)
    doors = data.get(CONF_DOOR_SENSORS, [])
    hysteresis = data.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)
    schedule = data.get(CONF_SCHEDULE, [])

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


class SmartHeatZoneClimate(ClimateEntity):
    """Zóna termosztát entitás."""

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
        self._relay_entities = relay_entities
        self._boiler_entity = boiler_entity
        self._door_sensors = door_sensors
        self._hysteresis = hysteresis
        self._schedule = schedule

        self._current_temp = None
        self._target_temp = 21.0
        self._hvac_mode = HVACMode.OFF
        self._is_heating = False

        # BoilerManager
        self._boiler = hass.data[DOMAIN][DATA_BOILER_MAIN]

        # Debug infó
        _LOGGER.info(
            "%s [%s] Initialized | Sensor=%s | Relays=%s | Boiler=%s",
            LOG_PREFIX,
            self.name,
            sensor_entity_id,
            relay_entities,
            boiler_entity,
        )

    async def async_added_to_hass(self):
        """Regisztrálja az érzékelők figyelését."""
        if self._sensor_entity_id:
            async_track_state_change_event(
                self.hass,
                [self._sensor_entity_id],
                self._sensor_changed,
            )
            _LOGGER.debug("%s [%s] Tracking sensor: %s", LOG_PREFIX, self.name, self._sensor_entity_id)

        for door in self._door_sensors:
            async_track_state_change_event(
                self.hass,
                [door],
                self._door_changed,
            )

    @callback
    async def _sensor_changed(self, event):
        """Hőmérséklet szenzor változás."""
        new_state = event.data.get("new_state")
        if not new_state or not new_state.state.replace(".", "", 1).isdigit():
            return
        self._current_temp = float(new_state.state)
        _LOGGER.debug("%s [%s] Sensor updated: %.2f°C", LOG_PREFIX, self.name, self._current_temp)
        await self._evaluate_heating()

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

    async def _evaluate_heating(self):
        """Fűtési logika értékelése."""
        if self._hvac_mode == HVACMode.OFF:
            return

        if self._current_temp is None:
            _LOGGER.debug("%s [%s] Waiting for valid temperature...", LOG_PREFIX, self.name)
            return

        # Ha ajtó/ablak nyitva, nincs fűtés
        for door in self._door_sensors:
            state = self.hass.states.get(door)
            if state and state.state == "on":
                _LOGGER.debug("%s [%s] Door open, skipping heating", LOG_PREFIX, self.name)
                return

        diff = self._target_temp - self._current_temp
        _LOGGER.debug(
            "%s [%s] Evaluate: current=%.2f target=%.2f hysteresis=%.2f",
            LOG_PREFIX,
            self.name,
            self._current_temp,
            self._target_temp,
            self._hysteresis,
        )

        if diff > self._hysteresis:
            await self._set_heating(True)
        elif diff < -self._hysteresis:
            await self._set_heating(False)

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
            await self._boiler.turn_on(self._boiler_entity, zone=self.name)
        else:
            # Kikapcsolás
            for relay in self._relay_entities:
                await self._call_switch_service("turn_off", relay)
            await self._boiler.turn_off(self._boiler_entity, zone=self.name)

        _LOGGER.info(
            "%s [%s] Heating %s %s", LOG_PREFIX, self.name, state_txt, f"({reason})" if reason else ""
        )

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
        self._target_temp = float(temp)
        _LOGGER.info("%s [%s] Target temperature set to %.1f°C", LOG_PREFIX, self.name, self._target_temp)
        await self._evaluate_heating()
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """HVAC mód váltása."""
        self._hvac_mode = hvac_mode
        _LOGGER.info("%s [%s] HVAC mode changed to %s", LOG_PREFIX, self.name, hvac_mode)
        await self._evaluate_heating()
        self.async_write_ha_state()

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def hvac_action(self):
        return "heating" if self._is_heating else "idle"

    @property
    def current_temperature(self) -> Optional[float]:
        return self._current_temp

    @property
    def target_temperature(self) -> float:
        return self._target_temp

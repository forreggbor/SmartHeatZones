"""
SmartHeatZones - Climate entity handler
Version: 1.4.3 (HA 2025.10+ compatible)
Author: forreggbor
"""

import logging
from datetime import datetime, time
from typing import Optional

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
    STATE_ON,
    STATE_OFF,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    CONF_SENSOR,
    CONF_ZONE_RELAYS,
    CONF_DOOR_SENSORS,
    CONF_HYSTERESIS,
    CONF_SCHEDULE,
    CONF_BOILER_MAIN,
    DATA_BOILER_MAIN,
    DATA_ACTIVE_ZONES,
    DEFAULT_HYSTERESIS,
)
from .boiler_manager import BoilerManager

_LOGGER = logging.getLogger(__name__)


class SmartHeatZone(ClimateEntity):
    """Main Climate entity representing one heating zone."""

    _attr_has_entity_name = True
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]

    def __init__(self, hass: HomeAssistant, entry_id: str, name: str, config: dict):
        """Initialize a zone."""
        self.hass = hass
        self._entry_id = entry_id
        self._name = name
        self._sensor_entity = config.get(CONF_SENSOR)
        self._zone_relays = config.get(CONF_ZONE_RELAYS, [])
        self._door_sensors = config.get(CONF_DOOR_SENSORS, [])
        self._boiler_main = config.get(CONF_BOILER_MAIN)
        self._hysteresis = float(config.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS))
        self._schedule = config.get(CONF_SCHEDULE, [])
        self._current_temperature = None
        self._target_temperature = 21.0
        self._hvac_mode = HVACMode.OFF
        self._active = False

        _LOGGER.info(
            "[%s] Climate entity initialized with relays: %s", self._name, self._zone_relays
        )

        # Boiler manager shared instance
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        if DATA_BOILER_MAIN not in hass.data[DOMAIN]:
            hass.data[DOMAIN][DATA_BOILER_MAIN] = BoilerManager(hass)
        self._boiler_manager: BoilerManager = hass.data[DOMAIN][DATA_BOILER_MAIN]

    async def async_added_to_hass(self):
        """Entity added to HA."""
        _LOGGER.info("[%s] Added to Home Assistant", self._name)
        async_track_state_change_event(
            self.hass, [self._sensor_entity], self._async_sensor_changed
        )
        if self._door_sensors:
            async_track_state_change_event(
                self.hass, self._door_sensors, self._async_door_changed
            )

        # Register zone in active zones tracker
        if DATA_ACTIVE_ZONES not in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN][DATA_ACTIVE_ZONES] = set()
        _LOGGER.debug("[%s] Zone registered in active zone tracker", self._name)

    # --- ClimateEntity properties -------------------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def temperature_unit(self) -> str:
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self) -> Optional[float]:
        return self._current_temperature

    @property
    def target_temperature(self) -> Optional[float]:
        return self._target_temperature

    @property
    def hvac_mode(self) -> str:
        return self._hvac_mode

    # --- Handlers -----------------------------------------------------------------

    async def async_set_hvac_mode(self, hvac_mode: str):
        """Handle turning on/off the zone."""
        _LOGGER.info("[%s] HVAC mode changed to %s", self._name, hvac_mode)
        self._hvac_mode = hvac_mode
        await self._evaluate_heating()

    async def async_set_temperature(self, **kwargs):
        """Handle target temperature set from Lovelace."""
        if ATTR_TEMPERATURE in kwargs:
            new_temp = float(kwargs[ATTR_TEMPERATURE])
            _LOGGER.info("[%s] Target temperature set to %.2f°C", self._name, new_temp)
            self._target_temperature = new_temp

            # Thermostat-like auto mode switching
            if (
                self._current_temperature is not None
                and self._hvac_mode == HVACMode.OFF
                and new_temp > self._current_temperature
            ):
                self._hvac_mode = HVACMode.HEAT
                _LOGGER.debug("[%s] Auto mode → HEAT", self._name)
            elif (
                self._current_temperature is not None
                and self._hvac_mode == HVACMode.HEAT
                and new_temp < self._current_temperature
            ):
                self._hvac_mode = HVACMode.OFF
                _LOGGER.debug("[%s] Auto mode → OFF", self._name)

            await self._evaluate_heating()

    # --- Internal logic ------------------------------------------------------------

    @callback
    async def _async_sensor_changed(self, event):
        """Handle sensor state update."""
        new_state = event.data.get("new_state")
        if not new_state or new_state.state in ("unknown", "unavailable"):
            return
        try:
            self._current_temperature = float(new_state.state)
            _LOGGER.debug(
                "[%s] Sensor updated: %.2f°C", self._name, self._current_temperature
            )
            await self._evaluate_heating()
        except ValueError:
            _LOGGER.warning("[%s] Invalid sensor reading: %s", self._name, new_state.state)

    @callback
    async def _async_door_changed(self, event):
        """Handle door/window sensor changes."""
        new_state = event.data.get("new_state")
        if not new_state:
            return
        if new_state.state == STATE_ON:
            _LOGGER.info("[%s] Door/window open → disabling heating", self._name)
            await self._set_zone_relays(False)
            self._active = False
            self._boiler_manager.unregister_zone(self._name)
        elif new_state.state == STATE_OFF:
            _LOGGER.info("[%s] Door/window closed → reevaluating", self._name)
            await self._evaluate_heating()

    async def _evaluate_heating(self):
        """Main control logic."""
        if self._hvac_mode != HVACMode.HEAT:
            await self._set_zone_relays(False)
            self._active = False
            self._boiler_manager.unregister_zone(self._name)
            _LOGGER.debug("[%s] Mode OFF → relays OFF", self._name)
            return

        if self._current_temperature is None:
            _LOGGER.debug("[%s] Waiting for sensor data...", self._name)
            return

        # Door/window lockout
        for sensor in self._door_sensors:
            state = self.hass.states.get(sensor)
            if state and state.state == STATE_ON:
                _LOGGER.debug("[%s] Door/window open → skip heating", self._name)
                await self._set_zone_relays(False)
                self._active = False
                self._boiler_manager.unregister_zone(self._name)
                return

        diff = self._target_temperature - self._current_temperature
        _LOGGER.debug(
            "[%s] Evaluating heating: T=%.2f°C Target=%.2f°C Hyst=%.2f°C",
            self._name,
            self._current_temperature,
            self._target_temperature,
            self._hysteresis,
        )

        if diff > self._hysteresis / 2:
            await self._set_zone_relays(True)
            if not self._active:
                self._active = True
                self._boiler_manager.register_zone(self._name, self._boiler_main)
        elif diff < -self._hysteresis / 2:
            await self._set_zone_relays(False)
            if self._active:
                self._active = False
                self._boiler_manager.unregister_zone(self._name)
        else:
            _LOGGER.debug("[%s] Within hysteresis band → no change", self._name)

    async def _set_zone_relays(self, state: bool):
        """Turn relays on or off."""
        service = "turn_on" if state else "turn_off"
        for relay in self._zone_relays:
            try:
                await self.hass.services.async_call(
                    "switch",
                    service,
                    {"entity_id": relay},
                    blocking=True,
                )
                _LOGGER.info(
                    "[%s] Relay %s executed successfully (%s)", self._name, relay, service
                )
            except Exception as e:
                _LOGGER.error("[%s] Failed to toggle relay %s: %s", self._name, relay, e)

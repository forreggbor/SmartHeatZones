"""
SmartHeatZones - Limp mode settings helpers

Validation and resolution of the limp-mode (on minutes, period minutes) profile, plus the shared
"cleared optional field" handling of the config and options flows.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Optional

import voluptuous as vol
from homeassistant.helpers import selector

from .const import (
    CONF_BACKUP_SENSOR,
    CONF_BACKUP_SENSOR_OFFSET,
    CONF_LIMP_OUTDOOR_CUTOFF,
    CONF_OUTDOOR_BACKUP_SENSOR,
    DEFAULT_BACKUP_SENSOR_OFFSET,
    DEFAULT_LIMP_OUTDOOR_CUTOFF,
    CONF_LIMP_ON,
    CONF_LIMP_PERIOD,
    CONF_LIMP_RADIATOR_ON,
    CONF_LIMP_RADIATOR_PERIOD,
    CONF_LIMP_UNDERFLOOR_ON,
    CONF_LIMP_UNDERFLOOR_PERIOD,
    DEFAULT_LIMP_RADIATOR_ON,
    DEFAULT_LIMP_RADIATOR_PERIOD,
    DEFAULT_LIMP_UNDERFLOOR_ON,
    DEFAULT_LIMP_UNDERFLOOR_PERIOD,
    HEATING_MODE_UNDERFLOOR,
    LOG_PREFIX,
    MAX_LIMP_PERIOD,
    MIN_LIMP_PERIOD,
)

_LOGGER = logging.getLogger(__name__)

ERR_LIMP_PERIOD_RANGE = "limp_period_range"
ERR_LIMP_ON_EXCEEDS_PERIOD = "limp_on_exceeds_period"
ERR_LIMP_PAIR_REQUIRED = "limp_pair_required"


def _to_int(value: Any) -> Optional[int]:
    """A whole number from a stored/typed value, or None when it is not one."""
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    return int(number) if number == int(number) else None


def validate_limp_pair(on: Any, period: Any) -> Optional[str]:
    """Error key for an invalid (on minutes, period minutes) pair, or None when it is valid."""
    on_min, period_min = _to_int(on), _to_int(period)
    if on_min is None or period_min is None or not MIN_LIMP_PERIOD <= period_min <= MAX_LIMP_PERIOD:
        return ERR_LIMP_PERIOD_RANGE
    if not 0 <= on_min <= period_min:
        return ERR_LIMP_ON_EXCEEDS_PERIOD
    return None


def validate_common_limp(user_input: dict) -> dict[str, str]:
    """Form errors (field -> error key) of the common limp profiles; missing values mean "default"."""
    errors: dict[str, str] = {}
    for on_key, period_key, on_default, period_default in (
        (CONF_LIMP_RADIATOR_ON, CONF_LIMP_RADIATOR_PERIOD, DEFAULT_LIMP_RADIATOR_ON, DEFAULT_LIMP_RADIATOR_PERIOD),
        (CONF_LIMP_UNDERFLOOR_ON, CONF_LIMP_UNDERFLOOR_PERIOD, DEFAULT_LIMP_UNDERFLOOR_ON, DEFAULT_LIMP_UNDERFLOOR_PERIOD),
    ):
        error = validate_limp_pair(
            user_input.get(on_key, on_default), user_input.get(period_key, period_default)
        )
        if error:
            errors[period_key] = error
    return errors


def validate_zone_limp(user_input: dict) -> dict[str, str]:
    """Form errors of a zone's optional limp override: both fields set (and valid) or both empty."""
    on, period = user_input.get(CONF_LIMP_ON), user_input.get(CONF_LIMP_PERIOD)
    if on in (None, "") and period in (None, ""):
        return {}
    if on in (None, "") or period in (None, ""):
        return {CONF_LIMP_PERIOD: ERR_LIMP_PAIR_REQUIRED}
    error = validate_limp_pair(on, period)
    return {CONF_LIMP_PERIOD: error} if error else {}


def _profile(settings: dict, on_key: str, period_key: str, on_default: int, period_default: int, label: str):
    """A validated (on, period) profile from settings, falling back to the defaults with a log line."""
    on = settings.get(on_key, on_default)
    period = settings.get(period_key, period_default)
    if validate_limp_pair(on, period):
        _LOGGER.warning(
            "%s Invalid limp profile %s (%r / %r) - using %d / %d min",
            LOG_PREFIX, label, on, period, on_default, period_default
        )
        return on_default, period_default
    return _to_int(on), _to_int(period)


def resolve_limp(common: dict, zone: dict, heating_mode: str, zone_name: str) -> tuple[int, int]:
    """
    Effective (on minutes, period minutes) of a zone: zone override, else the profile of its heating
    mode from the common settings, else the defaults. Invalid stored values fall back loudly.
    """
    on, period = zone.get(CONF_LIMP_ON), zone.get(CONF_LIMP_PERIOD)
    if on is not None and period is not None:
        if validate_limp_pair(on, period) is None:
            return _to_int(on), _to_int(period)
        _LOGGER.warning(
            "%s [%s] Invalid limp override (%r / %r) - using the common profile",
            LOG_PREFIX, zone_name, on, period
        )

    if heating_mode == HEATING_MODE_UNDERFLOOR:
        return _profile(common, CONF_LIMP_UNDERFLOOR_ON, CONF_LIMP_UNDERFLOOR_PERIOD,
                        DEFAULT_LIMP_UNDERFLOOR_ON, DEFAULT_LIMP_UNDERFLOOR_PERIOD, "underfloor")
    return _profile(common, CONF_LIMP_RADIATOR_ON, CONF_LIMP_RADIATOR_PERIOD,
                    DEFAULT_LIMP_RADIATOR_ON, DEFAULT_LIMP_RADIATOR_PERIOD, "radiator")


def apply_optional_fields(
    data: dict,
    user_input: dict,
    keys: Iterable[str],
    null_keys: Iterable[str] = (),
) -> None:
    """
    Copy optional form fields into data; a cleared field must really disappear.

    Home Assistant omits cleared optional fields from user_input, so a plain dict.update would keep the
    old value. Keys in null_keys are stored as None instead (an explicit "disabled", as opposed to the
    default that an absent key means).
    """
    null_keys = set(null_keys)
    for key in keys:
        value = user_input.get(key)
        if value in (None, ""):
            if key in null_keys:
                data[key] = None
            else:
                data.pop(key, None)
        else:
            data[key] = value


# ----------------------------------------------------------------------------------
# Shared form pieces (config flow + options flow)
# ----------------------------------------------------------------------------------

COMMON_OPTIONAL_KEYS = (
    CONF_LIMP_RADIATOR_ON,
    CONF_LIMP_RADIATOR_PERIOD,
    CONF_LIMP_UNDERFLOOR_ON,
    CONF_LIMP_UNDERFLOOR_PERIOD,
    CONF_LIMP_OUTDOOR_CUTOFF,
    CONF_OUTDOOR_BACKUP_SENSOR,
)
COMMON_NULL_KEYS = (CONF_LIMP_OUTDOOR_CUTOFF,)
ZONE_OPTIONAL_KEYS = (CONF_BACKUP_SENSOR, CONF_BACKUP_SENSOR_OFFSET, CONF_LIMP_ON, CONF_LIMP_PERIOD)


def _minutes() -> selector.NumberSelector:
    """Number box for minutes."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=MAX_LIMP_PERIOD, step=1, unit_of_measurement="min", mode="box")
    )


def _suggest(value: Any) -> dict:
    """Pre-fill a field without making it a default (a cleared field must stay cleared)."""
    return {"suggested_value": value}


def common_limp_schema(values: dict) -> dict:
    """Form fields of the limp settings in the common settings, pre-filled from values."""
    return {
        vol.Optional(CONF_LIMP_RADIATOR_ON, description=_suggest(values.get(CONF_LIMP_RADIATOR_ON, DEFAULT_LIMP_RADIATOR_ON))): _minutes(),
        vol.Optional(CONF_LIMP_RADIATOR_PERIOD, description=_suggest(values.get(CONF_LIMP_RADIATOR_PERIOD, DEFAULT_LIMP_RADIATOR_PERIOD))): _minutes(),
        vol.Optional(CONF_LIMP_UNDERFLOOR_ON, description=_suggest(values.get(CONF_LIMP_UNDERFLOOR_ON, DEFAULT_LIMP_UNDERFLOOR_ON))): _minutes(),
        vol.Optional(CONF_LIMP_UNDERFLOOR_PERIOD, description=_suggest(values.get(CONF_LIMP_UNDERFLOOR_PERIOD, DEFAULT_LIMP_UNDERFLOOR_PERIOD))): _minutes(),
        vol.Optional(CONF_LIMP_OUTDOOR_CUTOFF, description=_suggest(values.get(CONF_LIMP_OUTDOOR_CUTOFF, DEFAULT_LIMP_OUTDOOR_CUTOFF))): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=40, step=0.5, unit_of_measurement="°C", mode="box")
        ),
        vol.Optional(CONF_OUTDOOR_BACKUP_SENSOR, description=_suggest(values.get(CONF_OUTDOOR_BACKUP_SENSOR))): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["weather", "sensor"])
        ),
    }


def zone_limp_schema(values: dict) -> dict:
    """Form fields of the backup sensor and the limp override in a zone, pre-filled from values."""
    return {
        vol.Optional(CONF_BACKUP_SENSOR, description=_suggest(values.get(CONF_BACKUP_SENSOR))): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_BACKUP_SENSOR_OFFSET, description=_suggest(values.get(CONF_BACKUP_SENSOR_OFFSET, DEFAULT_BACKUP_SENSOR_OFFSET))): selector.NumberSelector(
            selector.NumberSelectorConfig(min=-10, max=10, step=0.1, unit_of_measurement="°C", mode="box")
        ),
        vol.Optional(CONF_LIMP_ON, description=_suggest(values.get(CONF_LIMP_ON))): _minutes(),
        vol.Optional(CONF_LIMP_PERIOD, description=_suggest(values.get(CONF_LIMP_PERIOD))): _minutes(),
    }

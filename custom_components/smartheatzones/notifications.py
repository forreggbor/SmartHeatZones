"""
SmartHeatZones - Fail-safe notifications

Persistent notifications with translated text (one notification per cause per zone) and the helper
that reads those texts. Texts live in the "exceptions" translation category of translations/*.json
(a category hassfest accepts); the message key is the part after "exceptions.".
"""

from __future__ import annotations

import logging

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations

from .const import DOMAIN, LOG_PREFIX

_LOGGER = logging.getLogger(__name__)

CAUSE_SENSOR = "sensor"
CAUSE_RELAY = "relay"


def notification_id(zone: str, kind: str) -> str:
    """Stable id of a zone's notification of one kind (a new notice replaces the old one)."""
    return f"{DOMAIN}_{zone.lower().replace(' ', '_')}_{kind}"


async def async_text(hass: HomeAssistant, key: str, **placeholders: str) -> str:
    """The translated notification text for a key, in the configured language."""
    translations = await async_get_translations(hass, hass.config.language, "exceptions", [DOMAIN])
    template = translations.get(f"component.{DOMAIN}.exceptions.{key}.message")
    if template is None:
        _LOGGER.error("%s Missing notification translation: %s (%s)", LOG_PREFIX, key, hass.config.language)
        return key
    return template.format(**placeholders)


async def async_notify(hass: HomeAssistant, zone: str, kind: str, key: str, **placeholders: str) -> None:
    """Create (or replace) a zone's notification of one kind (CAUSE_SENSOR / CAUSE_RELAY)."""
    message = await async_text(hass, key, zone=zone, **placeholders)
    title = await async_text(hass, "failsafe_title", zone=zone)
    persistent_notification.async_create(hass, message, title=title, notification_id=notification_id(zone, kind))


def dismiss(hass: HomeAssistant, zone: str, kind: str) -> None:
    """Remove a zone's notification of one kind (no error when there is none)."""
    persistent_notification.async_dismiss(hass, notification_id(zone, kind))

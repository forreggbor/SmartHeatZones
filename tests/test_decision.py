"""Pure decision helpers: the reason of a zone's state and the next scheduled change."""
from datetime import datetime

import pytest

from custom_components.smartheatzones.decision import decision_reason, next_schedule_change

BASE = dict(
    hvac_off=False, no_reading=False, door_open=False, overheat=False, limp_active=False,
    limp_heating=False, limp_next_in_min=None, heating=False, joined=False,
    current=20.7, target=21.0, on_below=20.5, off_above=21.5,
)


def reason(**over) -> dict:
    return decision_reason(**{**BASE, **over})


@pytest.mark.parametrize(
    "over, expected",
    [
        ({"heating": True, "current": 20.0}, {"code": "needs_heat"}),
        ({"heating": True, "current": 21.2}, {"code": "holding", "off_above": 21.5}),
        ({"heating": True, "joined": True, "current": 20.8}, {"code": "afterheat"}),
        ({}, {"code": "in_band", "on_below": 20.5, "target": 21.0}),
        ({"current": 21.0}, {"code": "target_reached", "target": 21.0}),
        ({"current": 20.0}, {"code": "needs_heat"}),
        ({"door_open": True}, {"code": "door_open"}),
        ({"hvac_off": True}, {"code": "hvac_off"}),
        ({"no_reading": True, "current": None}, {"code": "no_reading"}),
        ({"overheat": True}, {"code": "overheat"}),
        ({"limp_active": True, "limp_heating": True}, {"code": "limp_heating"}),
        ({"limp_active": True, "limp_next_in_min": 12}, {"code": "limp_waiting", "next_in_min": 12}),
        ({"limp_active": True}, {"code": "limp_waiting", "next_in_min": None}),
    ],
)
def test_reason_codes_and_params(over, expected):
    assert reason(**over) == expected


def test_priority_hvac_off_beats_door_open():
    assert reason(hvac_off=True, door_open=True)["code"] == "hvac_off"


def test_priority_door_open_beats_limp():
    assert reason(door_open=True, limp_active=True)["code"] == "door_open"


def test_priority_door_open_beats_overheat():
    assert reason(door_open=True, overheat=True)["code"] == "door_open"


def test_priority_limp_beats_no_reading():
    assert reason(limp_active=True, no_reading=True)["code"] == "limp_waiting"


SCHEDULE = [
    {"start": "06:00", "end": "08:00", "temp": 21, "label": "Morning"},
    {"start": "17:00", "end": "22:00", "temp": 22.5, "label": "Evening"},
]


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, 23, hour, minute)


def test_next_change_between_two_periods():
    assert next_schedule_change(SCHEDULE, at(12)) == {"at": "17:00", "in_min": 300, "temp": 22.5, "label": "Evening"}


def test_next_change_wraps_to_tomorrow():
    result = next_schedule_change(SCHEDULE, at(23))
    assert result["at"] == "06:00" and result["in_min"] == 420 and result["temp"] == 21.0


def test_next_change_is_strictly_after_now():
    assert next_schedule_change(SCHEDULE, at(17))["at"] == "06:00"


def test_next_change_period_spanning_midnight():
    schedule = [{"start": "22:00", "end": "06:00", "temp": 18}, {"start": "06:00", "end": "22:00", "temp": 21}]
    assert next_schedule_change(schedule, at(23))["at"] == "06:00"
    assert next_schedule_change(schedule, at(3))["at"] == "06:00"


def test_next_change_label_is_optional():
    result = next_schedule_change([{"start": "06:00", "end": "07:00", "temp": 20}, {"start": "09:00", "end": "10:00", "temp": 19}], at(8))
    assert result["label"] == ""


@pytest.mark.parametrize("schedule", [[], None, [{"start": "x", "end": "y", "temp": 1}], [{"start": "08:00", "end": "08:00", "temp": 21}]])
def test_next_change_none_without_valid_schedule(schedule):
    assert next_schedule_change(schedule, at(12)) is None


def test_next_change_skips_malformed_block():
    schedule = [{"start": "bad", "end": "08:00", "temp": 21}, {"start": "09:00", "end": "10:00", "temp": 19}, {"start": "17:00", "end": "18:00", "temp": 20}]
    assert next_schedule_change(schedule, at(12))["at"] == "17:00"


def test_next_change_single_period_has_no_change():
    assert next_schedule_change([{"start": "00:00", "end": "23:59", "temp": 21}], at(12)) is None

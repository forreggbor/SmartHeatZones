"""Boiler manager: daily counters, stats snapshot and change listeners."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.smartheatzones.boiler_manager import BoilerManager

BOILER = "switch.boiler"


def local(hour: int, minute: int = 0, day: int = 23) -> datetime:
    """A local time on a fixed day in the test time zone."""
    return datetime(2026, 11, day, hour, minute, tzinfo=dt_util.get_default_time_zone())


@pytest.fixture
def boiler(hass, freezer):
    """A boiler manager with recorded switch calls, created at 10:00 local time."""
    freezer.move_to(local(10))
    async_mock_service(hass, "switch", "turn_on")
    async_mock_service(hass, "switch", "turn_off")
    return BoilerManager(hass)


async def test_first_zone_counts_a_start_a_second_does_not(boiler):
    await boiler.turn_on(BOILER, "A")
    await boiler.turn_on(BOILER, "B")

    stats = boiler.stats()
    assert stats["starts_today"] == 1
    assert stats["running"] is True
    assert stats["since"] is not None
    assert stats["held_by"] == ["A", "B"]


async def test_runtime_is_the_elapsed_time_after_the_last_release(boiler, freezer):
    await boiler.turn_on(BOILER, "A")
    freezer.tick(timedelta(seconds=90))
    assert boiler.stats()["runtime_today_s"] == 90  # the running period counts up to now

    await boiler.turn_off(BOILER, "A")
    freezer.tick(timedelta(seconds=30))

    stats = boiler.stats()
    assert stats["running"] is False
    assert stats["since"] is None
    assert stats["runtime_today_s"] == 90


async def test_afterheat_join_counts_once_per_join(boiler):
    await boiler.turn_on(BOILER, "A")
    await boiler.turn_on(BOILER, "B", afterheat=True)
    await boiler.turn_on(BOILER, "B", afterheat=True)

    stats = boiler.stats()
    assert stats["afterheat_joins_today"] == 1
    assert stats["afterheat_zones"] == ["B"]
    assert stats["held_by"] == ["A"]


async def test_midnight_splits_a_running_period(boiler, freezer):
    freezer.move_to(local(23, 59))
    await boiler.turn_on(BOILER, "A")
    freezer.move_to(local(0, 1, day=24))

    stats = boiler.stats()
    assert stats["runtime_today_s"] == 60  # only the part after midnight
    assert stats["starts_today"] == 0
    assert stats["running"] is True
    assert datetime.fromisoformat(stats["counters_since"]) == local(0, 0, day=24)
    assert boiler.stats() == stats  # consistent without events in between


async def test_midnight_rollover_also_happens_on_turn_on(boiler, freezer):
    await boiler.turn_on(BOILER, "A")
    await boiler.turn_off(BOILER, "A")
    freezer.move_to(local(0, 5, day=24))

    await boiler.turn_on(BOILER, "A")

    stats = boiler.stats()
    assert stats["starts_today"] == 1
    assert stats["runtime_today_s"] == 0


async def test_join_and_release_in_the_same_second(boiler):
    await boiler.turn_on(BOILER, "A")
    await boiler.turn_on(BOILER, "B", afterheat=True)
    await boiler.turn_off(BOILER, "B")

    stats = boiler.stats()
    assert stats["afterheat_joins_today"] == 1
    assert stats["held_by"] == ["A"]
    assert stats["afterheat_zones"] == []


async def test_bookkeeping_failure_still_turns_the_boiler_on(hass, boiler, monkeypatch, caplog):
    on = async_mock_service(hass, "switch", "turn_on")
    monkeypatch.setattr(boiler, "_count_change", MagicMock(side_effect=RuntimeError("boom")))

    await boiler.turn_on(BOILER, "A")

    assert len([c for c in on if c.data.get("entity_id") == BOILER]) == 1
    assert "boom" in caplog.text


async def test_register_and_unregister_notify_listeners(boiler):
    calls = []
    boiler.add_listener(lambda: calls.append(1))

    boiler.register_zone_entity("A", MagicMock())
    boiler.unregister_zone_entity("A")

    assert len(calls) == 2


async def test_listener_runs_once_per_membership_change(boiler):
    calls = []
    boiler.add_listener(lambda: calls.append(1))

    await boiler.turn_on(BOILER, "A")
    assert len(calls) == 1
    await boiler.turn_off(BOILER, "A")
    assert len(calls) == 2


async def test_listener_runs_when_a_joined_zone_becomes_real_demand(boiler):
    await boiler.turn_on(BOILER, "A")
    await boiler.turn_on(BOILER, "B", afterheat=True)
    calls = []
    boiler.add_listener(lambda: calls.append(1))

    await boiler.turn_on(BOILER, "B", afterheat=False)

    assert len(calls) == 1
    assert boiler.stats()["afterheat_zones"] == []


async def test_remover_stops_a_listener(boiler):
    calls = []
    remove = boiler.add_listener(lambda: calls.append(1))
    remove()

    await boiler.turn_on(BOILER, "A")

    assert calls == []


async def test_a_raising_listener_does_not_stop_the_others_or_turn_on(hass, boiler, caplog):
    on = async_mock_service(hass, "switch", "turn_on")
    good = []

    def bad():
        raise RuntimeError("listener broke")

    boiler.add_listener(bad)
    boiler.add_listener(lambda: good.append(1))

    await boiler.turn_on(BOILER, "A")

    assert good == [1]
    assert len([c for c in on if c.data.get("entity_id") == BOILER]) == 1
    assert "listener broke" in caplog.text


async def test_failed_action_is_reported(boiler, monkeypatch):
    boiler.hass.services.async_register("switch", "turn_on", AsyncMock(side_effect=RuntimeError("relay down")))
    await boiler.turn_on(BOILER, "A")

    assert boiler.stats()["failed_action"] == "turn_on"


async def test_counters_since_is_the_manager_creation_when_later_than_midnight(boiler):
    assert datetime.fromisoformat(boiler.stats()["counters_since"]) == local(10)


async def test_runtime_is_real_time_across_a_dst_change(hass, freezer):
    """Europe/Budapest, 2026-03-29: clocks jump 02:00 -> 03:00, so 00:00 -> 04:00 local is three real hours."""
    await hass.config.async_set_time_zone("Europe/Budapest")
    tz = dt_util.get_default_time_zone()
    async_mock_service(hass, "switch", "turn_on")
    async_mock_service(hass, "switch", "turn_off")
    freezer.move_to(datetime(2026, 3, 29, 0, 0, tzinfo=tz))
    boiler = BoilerManager(hass)
    await boiler.turn_on(BOILER, "A")

    freezer.move_to(datetime(2026, 3, 29, 4, 0, tzinfo=tz))

    assert boiler.stats()["runtime_today_s"] == 3 * 3600


def test_the_overview_attributes_stay_out_of_the_recorder():
    from custom_components.smartheatzones.sensor import OverviewSensor

    assert {"zones", "boiler", "health", "updated"} <= OverviewSensor._unrecorded_attributes

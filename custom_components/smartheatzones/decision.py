"""
SmartHeatZones - pure decision helpers (no Home Assistant imports).

decision_reason: why a zone is (not) heating, as a language-neutral object.
next_schedule_change: the next period start of a zone schedule.
"""

from datetime import datetime, timedelta
from typing import Optional


def decision_reason(
    *,
    hvac_off: bool,
    no_reading: bool,
    door_open: bool,
    overheat: bool,
    limp_active: bool,
    limp_heating: bool,
    limp_next_in_min: Optional[int],
    heating: bool,
    joined: bool,
    current: Optional[float],
    target: float,
    on_below: float,
    off_above: float,
) -> dict:
    """Reason of the zone's state as {"code": ..., params}. target/on_below/off_above are the adjusted values."""
    if hvac_off:
        return {"code": "hvac_off"}
    if door_open:
        return {"code": "door_open"}
    if limp_active:
        if limp_heating:
            return {"code": "limp_heating"}
        return {"code": "limp_waiting", "next_in_min": limp_next_in_min}
    if no_reading or current is None:
        return {"code": "no_reading"}
    if overheat:
        return {"code": "overheat"}
    if heating:
        if joined:
            return {"code": "afterheat"}
        if current >= target:
            return {"code": "holding", "off_above": float(off_above)}
        return {"code": "needs_heat"}
    if current >= target:
        return {"code": "target_reached", "target": float(target)}
    if current >= on_below:
        return {"code": "in_band", "on_below": float(on_below), "target": float(target)}
    return {"code": "needs_heat"}


def next_schedule_change(schedule: Optional[list], now: datetime) -> Optional[dict]:
    """Nearest period start strictly after now (wrapping to tomorrow) as {at, in_min, temp, label}, else None."""
    starts: dict[str, tuple] = {}
    for block in schedule or []:
        try:
            start = datetime.strptime(str(block["start"])[:5], "%H:%M").time()
            end = datetime.strptime(str(block["end"])[:5], "%H:%M").time()
            if start == end:
                continue
            starts[start.strftime("%H:%M")] = (start, float(block["temp"]), str(block.get("label", "")))
        except (KeyError, ValueError, TypeError):
            continue
    if len(starts) < 2:
        return None  # a single period never changes the target

    best = None
    for start, temp, label in starts.values():
        moment = datetime.combine(now.date(), start, tzinfo=now.tzinfo)
        if moment <= now:
            moment += timedelta(days=1)
        if best is None or moment < best[0]:
            best = (moment, temp, label)
    moment, temp, label = best
    return {
        "at": moment.strftime("%H:%M"),
        "in_min": int((moment - now).total_seconds() + 59) // 60,
        "temp": temp,
        "label": label,
    }

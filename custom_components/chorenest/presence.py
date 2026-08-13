"""Presence calculation — supports several presence patterns.

Presence config per child:
{
  "mode": "always" | "alt_weeks" | "fixed_days" | "weeks_of_month" | "combo",
  "start_date": "2024-01-05",
  "start_present": true,
  "days_present": [4, 5, 6],
  "weeks_present": ["1", "3"],
  "blocked_days": [0, 3],
  "override_present": null | true | false,
}
"""
from __future__ import annotations
from datetime import date, timedelta
import math

from .const import (
    PRESENCE_ALWAYS, PRESENCE_ALT_WEEKS, PRESENCE_FIXED_DAYS,
    PRESENCE_WEEKS_MONTH, PRESENCE_COMBO,
)


def _week_of_month(d: date) -> int:
    first_weekday = d.replace(day=1).weekday()
    return math.ceil((d.day + first_weekday) / 7)


def child_present_on(cfg: dict, d: date) -> bool:
    """Whether the child is present on date d (ignores blocked days)."""
    override = cfg.get("override_present")
    if override is not None:
        return bool(override)

    mode = cfg.get("mode", PRESENCE_ALWAYS)

    if mode == PRESENCE_ALWAYS:
        return True
    if mode == PRESENCE_ALT_WEEKS:
        return _alt_weeks(cfg, d)
    if mode == PRESENCE_FIXED_DAYS:
        return d.weekday() in _days_set(cfg)
    if mode == PRESENCE_WEEKS_MONTH:
        return _weeks_of_month(cfg, d)
    if mode == PRESENCE_COMBO:
        return _alt_weeks(cfg, d) and (d.weekday() in _days_set(cfg))

    return True


def child_available_on(cfg: dict, d: date) -> bool:
    """Present AND not blocked."""
    if not child_present_on(cfg, d):
        return False
    return d.weekday() not in set(cfg.get("blocked_days", []))


def _alt_weeks(cfg: dict, d: date) -> bool:
    try:
        start = date.fromisoformat(cfg.get("start_date", "2024-01-01"))
    except ValueError:
        return True
    start_present = cfg.get("start_present", True)
    delta_weeks = (d - start).days // 7
    return (delta_weeks % 2 == 0) == start_present


def _days_set(cfg: dict) -> set:
    return set(cfg.get("days_present", []))


def _weeks_of_month(cfg: dict, d: date) -> bool:
    weeks_present = cfg.get("weeks_present", ["1", "3"])
    wom = _week_of_month(d)
    if "last" in [str(w).lower() for w in weeks_present]:
        nxt = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
        last = nxt - timedelta(days=1)
        if wom == _week_of_month(last):
            return True
    return wom in [int(w) for w in weeks_present if str(w).lower() != "last"]


def presence_week_summary(cfg: dict, week_start: date) -> dict:
    """Presence + availability per day of the week."""
    result = {}
    for i in range(7):
        d = week_start + timedelta(days=i)
        result[d.isoformat()] = {
            "present": child_present_on(cfg, d),
            "available": child_available_on(cfg, d),
        }
    return result

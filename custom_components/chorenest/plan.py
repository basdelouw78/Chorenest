"""The week as it actually stands: schedule plus this week's swaps/moves."""
from __future__ import annotations
from datetime import date, timedelta

from .const import CONF_CHILDREN, CONF_CHILD_PRESENCE, CONF_ROTATION_TASKS, CONF_WEEK_TASKS, DAYS
from .scheduler import rotation_assignments, week_assignments
from .swaps import apply_week


def week_plan(cfg: dict, ws: date, swaps: list, collections: dict | None) -> dict:
    """{iso_date: [rotation and weekly tasks]} for the week starting ``ws``."""
    children = cfg.get(CONF_CHILDREN, [])
    pres = cfg.get(CONF_CHILD_PRESENCE, {})
    plan = {}
    for i in range(7):
        d = ws + timedelta(days=i)
        plan[d.isoformat()] = rotation_assignments(cfg.get(CONF_ROTATION_TASKS, []), children, pres, d) + \
            week_assignments(cfg.get(CONF_WEEK_TASKS, []), children, pres, d, collections=collections)
    plan = apply_week(plan, swaps)
    for iso, ts in plan.items():
        wd = DAYS[date.fromisoformat(iso).weekday()]
        for t in ts:
            if t.get("type") == "week":
                t["day"] = wd
    return plan

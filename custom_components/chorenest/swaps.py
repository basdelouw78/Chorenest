"""Task swaps — children trade tasks with each other, for the current week only.

A swap has one or two "legs". Each leg moves one task on one date from one
child to another:

    {"id": "a1b2c3d4", "week": "2026-10-26", "created": "...",
     "legs": [{"date": "2026-10-28", "task": "Plastic", "from": "Jasper", "to": "Nena"},
              {"date": "2026-10-30", "task": "Vaatwasser", "from": "Nena", "to": "Jasper"}]}

Two legs = an exchange (possibly on different days, e.g. "I do your Thursday
if you do my Wednesday"). One leg = a hand-over (the other child takes the
task, nothing in return). Only daily rotating and weekly tasks can be
swapped; monthly tasks are per child already. Swaps expire automatically when
the week is over: the normal schedule applies again from Monday.
"""
from __future__ import annotations
from datetime import date, timedelta

SWAPPABLE_TYPES = ("rotation", "week")


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def current_swaps(swaps: list, today: date) -> list:
    """Drop swaps from earlier weeks."""
    ws = week_start(today).isoformat()
    return [s for s in (swaps or []) if s.get("week") == ws]


def apply_swaps(tasks: list[dict], date_str: str, swaps: list) -> list[dict]:
    """Reassign the scheduled tasks of one day according to the swaps.

    Matches on the *scheduled* child, so a leg only applies while the
    schedule still gives that task to that child (if presence changes and the
    schedule moves the task elsewhere, the stale leg is simply ignored).
    """
    legs = [(s["id"], leg) for s in swaps for leg in s.get("legs", []) if leg.get("date") == date_str]
    if not legs:
        return tasks
    used = set()
    out = []
    for t in tasks:
        nt = t
        if t.get("type") in SWAPPABLE_TYPES:
            for i, (sid, leg) in enumerate(legs):
                if i in used:
                    continue
                if leg.get("task") == t.get("task") and leg.get("from") == t.get("child"):
                    nt = {**t, "child": leg["to"], "swapped_from": leg["from"], "swap_id": sid}
                    used.add(i)
                    break
        out.append(nt)
    return out

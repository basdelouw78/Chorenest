"""Task swaps — children trade tasks with each other, for the current week only.

A swap has one or two "legs". Each leg moves one task on one date from one
child to another:

    {"id": "a1b2c3d4", "week": "2026-10-26", "created": "...",
     "legs": [{"date": "2026-10-28", "task": "Plastic", "from": "Jasper", "to": "Nena"},
              {"date": "2026-10-30", "task": "Vaatwasser", "from": "Nena", "to": "Jasper"}]}

A leg may also carry "to_date": the task moves to another day of the same
week (a child moving her own task to a free day, or swapping two of her own
days). Two legs = an exchange (possibly on different days, e.g. "I do your Thursday
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


def apply_week(plan: dict, swaps: list) -> dict:
    """Apply the week's swaps to a plan {iso_date: [task, ...]}.

    A leg moves one task (matched on name and *scheduled* child) to another
    child ("to") and/or another date ("to_date", default the same date). A
    leg whose task is no longer scheduled that way (presence changed) is
    simply ignored. Moved tasks carry "moved_from" (the original date),
    handed-over tasks "swapped_from" (the original child), both "swap_id".
    "Everyone" tasks can only be moved by the child himself, not handed over.
    """
    out = {d: list(ts) for d, ts in plan.items()}
    for s in swaps:
        for leg in s.get("legs", []):
            src = out.get(leg.get("date"))
            to_date = leg.get("to_date") or leg.get("date")
            if src is None or to_date not in out:
                continue
            own = leg.get("to") == leg.get("from")
            for i, t in enumerate(src):
                if (t.get("type") in SWAPPABLE_TYPES and not t.get("swap_id")
                        and t.get("task") == leg.get("task") and t.get("child") == leg.get("from")
                        and (own or not t.get("everyone"))):
                    nt = {**t, "child": leg["to"], "swap_id": s["id"]}
                    if not own:
                        nt["swapped_from"] = leg["from"]
                    if to_date != leg["date"]:
                        nt["moved_from"] = leg["date"]
                        del src[i]
                        out[to_date].append(nt)
                    else:
                        src[i] = nt
                    break
    return out


def apply_swaps(tasks: list[dict], date_str: str, swaps: list) -> list[dict]:
    """Single-day variant (kept for compatibility): hand-overs on that day only."""
    same_day = [{**s, "legs": [l for l in s.get("legs", []) if (l.get("to_date") or l.get("date")) == l.get("date")]} for s in swaps]
    return apply_week({date_str: tasks}, same_day)[date_str]

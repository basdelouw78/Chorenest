"""Task scheduler — fair fallback when a child is unavailable."""
from __future__ import annotations
from datetime import date, timedelta

from .const import DAY_INDEX, DAYS, MONTH_WEEK_KEYS, WEEK_MODE_AUTO, WEEK_MODE_EVEN, WEEK_MODE_ODD, WEEK_MODE_FIXED
from .presence import child_available_on, presence_cycle_index


def _iso_week(d: date) -> int:
    return d.isocalendar()[1]


def _nth_weekday_of_month(year: int, month: int, weekday: int, n) -> date | None:
    if n == "last":
        nxt = (date(year, month, 28) + timedelta(days=4)).replace(day=1)
        last = nxt - timedelta(days=1)
        return last - timedelta(days=(last.weekday() - weekday) % 7)
    n = int(n)
    first = date(year, month, 1)
    cand = first + timedelta(days=(weekday - first.weekday()) % 7 + (n - 1) * 7)
    return cand if cand.month == month else None


def _available_children(children, presence_map, d: date) -> list[str]:
    return [c for c in children if child_available_on(presence_map.get(c, {}), d)]


def _fewest_tasks_child(candidates: list[str], already_assigned: dict[str, int]) -> str:
    """Child with the fewest tasks so far today (fair distribution)."""
    return min(candidates, key=lambda c: already_assigned.get(c, 0))


# ── Rotation tasks ──────────────────────────────────────────────────────────

def rotation_assignments(task_cfg, children, presence_map, d: date, assigned_count=None) -> list[dict]:
    if assigned_count is None:
        assigned_count = {c: 0 for c in children}

    epoch = date(2024, 1, 1)
    day_idx = (d - epoch).days
    available = _available_children(children, presence_map, d)
    result = []

    for i, task in enumerate(task_cfg):
        fixed = task.get("fixed_child")
        if fixed and fixed in available:
            child = fixed
        elif not available:
            continue
        else:
            order = [c for c in (task.get("children_order") or children) if c in available]
            if not order:
                continue
            child = order[(day_idx + i) % len(order)]

        assigned_count[child] = assigned_count.get(child, 0) + 1
        result.append({"task": task["name"], "child": child, "type": "rotation"})
    return result


# ── Weekly tasks ─────────────────────────────────────────────────────────────

def week_assignments(task_cfg, children, presence_map, d: date, assigned_count=None) -> list[dict]:
    if assigned_count is None:
        assigned_count = {c: 0 for c in children}

    today_wd = d.weekday()
    week_num = _iso_week(d)
    available = _available_children(children, presence_map, d)
    result = []

    for task in task_cfg:
        if DAY_INDEX.get(task.get("day", "monday"), 0) != today_wd:
            continue

        mode = task.get("mode", WEEK_MODE_AUTO)
        order = task.get("children_order") or children

        if mode == WEEK_MODE_FIXED:
            candidate = task.get("fixed_child", "")
        elif mode in (WEEK_MODE_EVEN, WEEK_MODE_ODD):
            even_c, odd_c = task.get("even_child", ""), task.get("odd_child", "")
            # Alternate by presence *cycle* (consecutive present weeks), not
            # by raw calendar-week parity — see presence_cycle_index().
            ref_cfg = presence_map.get(even_c) or presence_map.get(odd_c) or {}
            cycle = presence_cycle_index(ref_cfg, d)
            is_even = (cycle % 2 == 0) if cycle is not None else (week_num % 2 == 0)
            if mode == WEEK_MODE_EVEN:
                candidate = even_c if is_even else odd_c
            else:
                candidate = odd_c if not is_even else even_c
        else:  # auto_rotate
            avail_ordered = [c for c in order if c in available]
            if avail_ordered:
                cycle = presence_cycle_index(presence_map.get(avail_ordered[0], {}), d)
                idx = cycle if cycle is not None else week_num
                candidate = avail_ordered[idx % len(avail_ordered)]
            else:
                candidate = ""

        if not candidate or not child_available_on(presence_map.get(candidate, {}), d):
            if available:
                candidate = _fewest_tasks_child(available, assigned_count)
            else:
                continue

        if candidate in children:
            assigned_count[candidate] = assigned_count.get(candidate, 0) + 1
            result.append({"task": task["name"], "child": candidate, "type": "week", "day": task.get("day", "")})
    return result


# ── Monthly tasks ────────────────────────────────────────────────────────────

def month_assignments_for_date(task_cfg, children, presence_map, d: date) -> list[dict]:
    result = []
    for task in task_cfg:
        wl = task.get("week_of_month", "last")
        day_name = task.get("day_of_week", "sunday")
        day_num = DAY_INDEX.get(day_name, 6)
        trigger = _nth_weekday_of_month(d.year, d.month, day_num, wl)
        if not trigger:
            continue

        eligible = [c for c in (task.get("children_order") or children) if c in children]
        for child in eligible:
            actual = trigger
            for offset in range(7):
                check = trigger + timedelta(days=offset)
                if child_available_on(presence_map.get(child, {}), check):
                    actual = check
                    break
            else:
                continue

            if actual == d:
                result.append({
                    "task": task["name"], "child": child, "type": "month",
                    "trigger_date": actual.isoformat(),
                    "original_trigger": trigger.isoformat(),
                    "shifted": actual != trigger,
                })
    return result


def next_month_occurrence(task, children, presence_map, from_date: date) -> dict:
    result = {}
    eligible = [c for c in (task.get("children_order") or children) if c in children]
    for mo in range(13):
        d = from_date + timedelta(days=mo * 28)
        yr, mn = d.year, d.month
        if mn > 12:
            yr += 1
            mn -= 12

        wl = task.get("week_of_month", "last")
        dn = DAY_INDEX.get(task.get("day_of_week", "sunday"), 6)
        trigger = _nth_weekday_of_month(yr, mn, dn, wl)
        if not trigger or trigger < from_date:
            continue

        for child in eligible:
            if child in result:
                continue
            for off in range(7):
                check = trigger + timedelta(days=off)
                if child_available_on(presence_map.get(child, {}), check):
                    result[child] = check.isoformat()
                    break
    return result

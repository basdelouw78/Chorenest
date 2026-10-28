"""Waste-collection dates — let a weekly task follow a collection sensor.

A weekly task can name a sensor that holds the next collection date (e.g. the
Afvalinfo integration: state "dd-mm-yyyy", attribute "year_month_day_date"
"yyyy-mm-dd") plus an offset in days: "-1" = put the bin out the day
before, "0" = on the collection day itself. The task then appears on that
day instead of on its fixed weekday.

Such sensors only show the *next* date, so the moment a collection has passed
the date jumps ahead. Every date seen is remembered (for a few weeks) so the
task stays visible on earlier days of the current week, done-state included.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta

KEEP_DAYS = 21
ATTRS = ("year_month_day_date", "date", "next_date")


def _to_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def parse_collection(state) -> date | None:
    """Next collection date from a HA state object (None if unknown)."""
    if state is None:
        return None
    for a in ATTRS:
        d = _to_date(state.attributes.get(a))
        if d:
            return d
    return _to_date(state.state)


def all_dates(state) -> list[date]:
    """Every date the sensor exposes: the next one, plus the whole-year list
    and the last collection when the integration fills them."""
    out = []
    nxt = parse_collection(state)
    if nxt:
        out.append(nxt)
    if state is not None:
        whole = state.attributes.get("whole_year_dates")
        if isinstance(whole, (list, tuple)):
            out += [x for x in (_to_date(v) for v in whole) if x]
        last = _to_date(state.attributes.get("last_collection_date"))
        if last:
            out.append(last)
    return out


def collection_sensors(week_tasks: list) -> list[str]:
    return sorted({t["collection_sensor"] for t in week_tasks or [] if t.get("collection_sensor")})


def remember(known: dict, sensor: str, dates: list, today: date) -> bool:
    """Add seen dates and drop old ones. Returns True if something changed."""
    cut = (today - timedelta(days=KEEP_DAYS)).isoformat()
    end = (today + timedelta(days=KEEP_DAYS)).isoformat()
    old = list(known.get(sensor, []))
    new = {x for x in old if x >= cut}
    new |= {d.isoformat() for d in dates if cut <= d.isoformat() <= end}
    new = sorted(new)
    known[sensor] = new
    return new != old


def due_by_collection(task: dict, d: date, known: dict | None) -> bool | None:
    """True/False when the task follows a collection sensor with known
    dates; None when it doesn't (or nothing is known yet), so the caller
    falls back to the fixed weekday."""
    sensor = task.get("collection_sensor")
    if not sensor:
        return None
    dates = (known or {}).get(sensor)
    if not dates:
        return None
    try:
        offset = int(task.get("collection_offset", -1))
    except (TypeError, ValueError):
        offset = -1
    return (d - timedelta(days=offset)).isoformat() in dates

"""ChoreNest — kid-friendly household task planner."""
from __future__ import annotations
import logging
import uuid
from datetime import date, datetime
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from .const import (
    DOMAIN, PLATFORMS, CONF_CHILD_PRESENCE, CONF_CHILDREN,
    CONF_ROTATION_TASKS, CONF_WEEK_TASKS,
)
from .presence import child_available_on
from .scheduler import rotation_assignments, week_assignments
from .swaps import SWAPPABLE_TYPES, apply_swaps, current_swaps, week_start

_LOGGER = logging.getLogger(__name__)
STORAGE_KEY = f"{DOMAIN}_done"
STORAGE_VERSION = 1
SWAP_STORAGE_KEY = f"{DOMAIN}_swaps"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    stored = await store.async_load() or {}
    swap_store = Store(hass, STORAGE_VERSION, SWAP_STORAGE_KEY)
    swaps = current_swaps((await swap_store.async_load() or {}).get("swaps", []), date.today())
    hass.data[DOMAIN][entry.entry_id] = {
        "config": {**entry.data, **entry.options},
        "done": stored,
        "store": store,
        "swaps": swaps,
        "swap_store": swap_store,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_mark_done(call):
        key = call.data.get("key", "")
        if not key:
            child = call.data.get("child", "")
            task = call.data.get("task", "")
            task_type = call.data.get("task_type", "rot")
            date_str = call.data.get("date", "")
            month_key = call.data.get("month_key", "")
            if task_type == "month":
                key = f"month__{month_key}__{child}__{task}"
            elif task_type == "wk":
                key = f"wk__{date_str}__{child}__{task}"
            else:
                key = f"rot__{date_str}__{child}__{task}"
        ed = hass.data[DOMAIN][entry.entry_id]
        ed["done"][key] = not ed["done"].get(key, False)
        await ed["store"].async_save(ed["done"])
        hass.bus.async_fire(f"{DOMAIN}_updated")

    async def handle_reset_week(call):
        ed = hass.data[DOMAIN][entry.entry_id]
        ed["done"] = {k: v for k, v in ed["done"].items() if k.startswith("month__")}
        await ed["store"].async_save(ed["done"])
        hass.bus.async_fire(f"{DOMAIN}_updated")

    async def handle_reset_all(call):
        ed = hass.data[DOMAIN][entry.entry_id]
        ed["done"] = {}
        await ed["store"].async_save({})
        hass.bus.async_fire(f"{DOMAIN}_updated")

    async def handle_set_presence(call):
        child = call.data.get("child", "")
        present = call.data.get("present")
        config = dict(hass.data[DOMAIN][entry.entry_id]["config"])
        pres = dict(config.get(CONF_CHILD_PRESENCE, {}))
        if child in pres:
            pres[child] = dict(pres[child])
            pres[child]["override_present"] = present
            config[CONF_CHILD_PRESENCE] = pres
            hass.data[DOMAIN][entry.entry_id]["config"] = config
            hass.config_entries.async_update_entry(entry, options=config)
            hass.bus.async_fire(f"{DOMAIN}_updated")

    async def handle_clear_presence_override(call):
        child = call.data.get("child", "")
        config = dict(hass.data[DOMAIN][entry.entry_id]["config"])
        pres = dict(config.get(CONF_CHILD_PRESENCE, {}))
        if child in pres:
            pres[child] = dict(pres[child])
            pres[child]["override_present"] = None
            config[CONF_CHILD_PRESENCE] = pres
            hass.data[DOMAIN][entry.entry_id]["config"] = config
            hass.config_entries.async_update_entry(entry, options=config)
            hass.bus.async_fire(f"{DOMAIN}_updated")

    # ── Swapping tasks between children (current week only) ──────────────────
    def _scheduled(cfg, d: date, swaps: list) -> list[dict]:
        """Swappable tasks of one day as they currently stand (swaps applied)."""
        children = cfg.get(CONF_CHILDREN, [])
        pres = cfg.get(CONF_CHILD_PRESENCE, {})
        tasks = rotation_assignments(cfg.get(CONF_ROTATION_TASKS, []), children, pres, d) + \
            week_assignments(cfg.get(CONF_WEEK_TASKS, []), children, pres, d)
        return apply_swaps(tasks, d.isoformat(), swaps)

    def _parse_day(value, what: str) -> date:
        try:
            return date.fromisoformat(str(value))
        except ValueError as err:
            raise HomeAssistantError(f"Ongeldige datum voor {what}: {value}") from err

    async def _log(message: str):
        if hass.services.has_service("logbook", "log"):
            await hass.services.async_call("logbook", "log", {"name": "ChoreNest", "message": message})

    async def _save_swaps(ed):
        await ed["swap_store"].async_save({"swaps": ed["swaps"]})
        hass.bus.async_fire(f"{DOMAIN}_updated")

    async def handle_swap_task(call):
        ed = hass.data[DOMAIN][entry.entry_id]
        cfg = ed["config"]
        children = cfg.get(CONF_CHILDREN, [])
        pres = cfg.get(CONF_CHILD_PRESENCE, {})
        today = date.today()
        ws = week_start(today)
        ed["swaps"] = current_swaps(ed["swaps"], today)

        child_a, child_b = call.data["child"], call.data["with_child"]
        task_a = call.data["task"]
        day_a = _parse_day(call.data["date"], "de taak")
        task_b = call.data.get("other_task") or ""
        if task_b and not call.data.get("other_date"):
            raise HomeAssistantError("Geef ook de datum van de taak die je terug doet.")
        day_b = _parse_day(call.data["other_date"], "de taak terug") if task_b else None

        for c in (child_a, child_b):
            if c not in children:
                raise HomeAssistantError(f"Onbekend kind: {c}")
        if child_a == child_b:
            raise HomeAssistantError("Kies twee verschillende kinderen om te ruilen.")
        for d in filter(None, (day_a, day_b)):
            if d < today or week_start(d) != ws:
                raise HomeAssistantError("Ruilen kan alleen voor vandaag en de rest van deze week.")

        def find(d: date, task: str, child: str) -> dict:
            for t in _scheduled(cfg, d, ed["swaps"]):
                if t["task"] == task and t["child"] == child and t.get("type") in SWAPPABLE_TYPES:
                    if t.get("swap_id"):
                        raise HomeAssistantError(f"{task} op {d.isoformat()} is al geruild. Draai die ruil eerst terug.")
                    return t
            raise HomeAssistantError(f"{child} heeft op {d.isoformat()} geen taak '{task}' die geruild kan worden.")

        find(day_a, task_a, child_a)
        if not child_available_on(pres.get(child_b, {}), day_a):
            raise HomeAssistantError(f"{child_b} is op {day_a.isoformat()} niet thuis of heeft geen tijd.")
        legs = [{"date": day_a.isoformat(), "task": task_a, "from": child_a, "to": child_b}]
        if task_b:
            find(day_b, task_b, child_b)
            if not child_available_on(pres.get(child_a, {}), day_b):
                raise HomeAssistantError(f"{child_a} is op {day_b.isoformat()} niet thuis of heeft geen tijd.")
            if day_b == day_a and task_b == task_a:
                raise HomeAssistantError("Dat is dezelfde taak.")
            legs.append({"date": day_b.isoformat(), "task": task_b, "from": child_b, "to": child_a})

        swap = {"id": uuid.uuid4().hex[:8], "week": ws.isoformat(), "created": datetime.now().isoformat(timespec="seconds"), "legs": legs}
        ed["swaps"].append(swap)
        await _save_swaps(ed)
        if task_b:
            msg = f"{child_a} en {child_b} ruilen: {child_b} doet '{task_a}' ({day_a.isoformat()}), {child_a} doet '{task_b}' ({day_b.isoformat()})"
        else:
            msg = f"{child_b} neemt '{task_a}' ({day_a.isoformat()}) over van {child_a}"
        await _log(msg + " — alleen deze week")

    async def handle_undo_swap(call):
        ed = hass.data[DOMAIN][entry.entry_id]
        sid = call.data["swap_id"]
        ed["swaps"] = current_swaps(ed["swaps"], date.today())
        gone = [s for s in ed["swaps"] if s["id"] == sid]
        if not gone:
            raise HomeAssistantError("Die ruil bestaat niet (meer).")
        ed["swaps"] = [s for s in ed["swaps"] if s["id"] != sid]
        await _save_swaps(ed)
        legs = gone[0]["legs"]
        await _log("Ruil teruggedraaid: " + "; ".join(f"'{l['task']}' ({l['date']}) weer bij {l['from']}" for l in legs))

    hass.services.async_register(DOMAIN, "swap_task", handle_swap_task)
    hass.services.async_register(DOMAIN, "undo_swap", handle_undo_swap)
    hass.services.async_register(DOMAIN, "mark_done", handle_mark_done)
    hass.services.async_register(DOMAIN, "reset_week", handle_reset_week)
    hass.services.async_register(DOMAIN, "reset_all", handle_reset_all)
    hass.services.async_register(DOMAIN, "set_presence", handle_set_presence)
    hass.services.async_register(DOMAIN, "clear_presence_override", handle_clear_presence_override)

    entry.async_on_unload(
        entry.add_update_listener(lambda h, e: h.config_entries.async_reload(e.entry_id))
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok

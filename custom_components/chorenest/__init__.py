"""ChoreNest — kid-friendly household task planner."""
from __future__ import annotations
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from .const import DOMAIN, PLATFORMS, CONF_CHILD_PRESENCE

_LOGGER = logging.getLogger(__name__)
STORAGE_KEY = f"{DOMAIN}_done"
STORAGE_VERSION = 1


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    stored = await store.async_load() or {}
    hass.data[DOMAIN][entry.entry_id] = {
        "config": {**entry.data, **entry.options},
        "done": stored,
        "store": store,
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

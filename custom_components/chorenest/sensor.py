"""Sensor platform — presence-aware task overview."""
from __future__ import annotations
from datetime import date, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import (
    DOMAIN, CONF_LANG, CONF_CHILDREN, CONF_CHILD_COLORS, CONF_CHILD_PRESENCE,
    CONF_ROTATION_TASKS, CONF_WEEK_TASKS, CONF_MONTH_TASKS,
    DAYS, CHILD_COLOR_OPTIONS, COLOR_EMOJI, DEFAULT_COLOR_ORDER, DEFAULT_LANG,
)
from .config_flow import T as LANG_TEXT
from .presence import child_present_on, child_available_on, presence_week_summary
from .scheduler import rotation_assignments, week_assignments, month_assignments_for_date, next_month_occurrence


def _day_labels(lang):
    return LANG_TEXT.get(lang, LANG_TEXT[DEFAULT_LANG])["days"]


def _month_week_labels(lang):
    return LANG_TEXT.get(lang, LANG_TEXT[DEFAULT_LANG])["month_weeks"]


def _child_theme(child, children, child_colors):
    idx = children.index(child) if child in children else 0
    color_name = child_colors.get(child, DEFAULT_COLOR_ORDER[idx % len(DEFAULT_COLOR_ORDER)])
    colors = CHILD_COLOR_OPTIONS.get(color_name, list(CHILD_COLOR_OPTIONS.values())[0])
    return {"bg": colors[0], "light": colors[1], "emoji": COLOR_EMOJI.get(color_name, "⭐"), "color_name": color_name}


def _cfg(hass, entry):
    return hass.data[DOMAIN].get(entry.entry_id, {}).get("config", entry.data)


def _done(hass, entry):
    return hass.data[DOMAIN].get(entry.entry_id, {}).get("done", {})


async def async_setup_entry(hass, entry, async_add_entities):
    children = _cfg(hass, entry).get(CONF_CHILDREN, [])
    entities = [ChoreNestDashboardSensor(hass, entry)]
    for child in children:
        entities.append(ChoreNestChildSensor(hass, entry, child))
    async_add_entities(entities, True)


class ChoreNestDashboardSensor(SensorEntity):
    _attr_icon = "mdi:calendar-check"

    def __init__(self, hass, entry):
        self.hass = hass
        self._entry = entry
        self._attr_name = "ChoreNest Week"
        self._attr_unique_id = f"{DOMAIN}_week_{entry.entry_id}"

    async def async_added_to_hass(self):
        @callback
        def _upd(_e):
            self.async_write_ha_state()
        self.async_on_remove(self.hass.bus.async_listen(f"{DOMAIN}_updated", _upd))

    @property
    def state(self):
        return "active"

    @property
    def extra_state_attributes(self):
        config = _cfg(self.hass, self._entry)
        done_map = _done(self.hass, self._entry)
        lang = config.get(CONF_LANG, DEFAULT_LANG)
        children = config.get(CONF_CHILDREN, [])
        child_colors = config.get(CONF_CHILD_COLORS, {})
        child_presence = config.get(CONF_CHILD_PRESENCE, {})
        rot_tasks = config.get(CONF_ROTATION_TASKS, [])
        week_tasks = config.get(CONF_WEEK_TASKS, [])
        month_tasks = config.get(CONF_MONTH_TASKS, [])
        day_labels = _day_labels(lang)

        child_themes = {c: _child_theme(c, children, child_colors) for c in children}
        today = date.today()
        today_key = DAYS[today.weekday()]
        week_start = today - timedelta(days=today.weekday())

        week = {}
        for offset, day_key in enumerate(DAYS):
            day_date = week_start + timedelta(days=offset)
            date_str = day_date.isoformat()
            month_key = day_date.strftime("%Y-%m")
            tasks_list = []

            for t in rotation_assignments(rot_tasks, children, child_presence, day_date):
                key = f"rot__{date_str}__{t['child']}__{t['task']}"
                th = child_themes.get(t["child"], {})
                tasks_list.append({**t, "icon": "🔄", "done": done_map.get(key, False), "date": date_str, "key": key,
                                    **{k: th.get(k, "") for k in ["bg", "light", "emoji"]}})

            for t in week_assignments(week_tasks, children, child_presence, day_date):
                key = f"wk__{date_str}__{t['child']}__{t['task']}"
                th = child_themes.get(t["child"], {})
                tasks_list.append({**t, "icon": "📅", "done": done_map.get(key, False), "date": date_str, "key": key,
                                    **{k: th.get(k, "") for k in ["bg", "light", "emoji"]}})

            for t in month_assignments_for_date(month_tasks, children, child_presence, day_date):
                key = f"month__{month_key}__{t['child']}__{t['task']}"
                th = child_themes.get(t["child"], {})
                tasks_list.append({**t, "icon": "🗓️", "done": done_map.get(key, False), "date": date_str,
                                    "month_key": month_key, "key": key,
                                    **{k: th.get(k, "") for k in ["bg", "light", "emoji"]}})

            presence_status = {}
            for child in children:
                pres_cfg = child_presence.get(child, {})
                presence_status[child] = {
                    "present": child_present_on(pres_cfg, day_date),
                    "available": child_available_on(pres_cfg, day_date),
                }

            week[day_key] = {
                "label": day_labels.get(day_key, day_key),
                "date": date_str,
                "date_display": day_date.strftime("%-d %b"),
                "tasks": tasks_list,
                "is_today": day_date == today,
                "presence": presence_status,
            }

        month_overview = []
        mw_labels = _month_week_labels(lang)
        for mt in month_tasks:
            nexts = next_month_occurrence(mt, children, child_presence, today)
            child_info = {}
            for child, trigger_str in nexts.items():
                mk = trigger_str[:7]
                key = f"month__{mk}__{child}__{mt['name']}"
                child_info[child] = {"trigger": trigger_str, "done": done_map.get(key, False), "month_key": mk}
            month_overview.append({
                "name": mt["name"],
                "week_of_month": mw_labels.get(mt.get("week_of_month", ""), mt.get("week_of_month", "")),
                "day_of_week": day_labels.get(mt.get("day_of_week", ""), mt.get("day_of_week", "")),
                "next_by_child": child_info,
            })

        coparenting = {}
        for child in children:
            pres_cfg = child_presence.get(child, {})
            coparenting[child] = {
                "present_this_week": child_present_on(pres_cfg, today),
                "mode": pres_cfg.get("mode", "always"),
                "week_summary": presence_week_summary(pres_cfg, week_start),
            }

        return {
            "week": week,
            "day_order": DAYS,
            "children": children,
            "child_themes": child_themes,
            "today": today.isoformat(),
            "today_key": today_key,
            "today_label": day_labels.get(today_key, today_key),
            "month_overview": month_overview,
            "coparenting": coparenting,
            "lang": lang,
        }


class ChoreNestChildSensor(SensorEntity):
    _attr_icon = "mdi:account-check"

    def __init__(self, hass, entry, child):
        self.hass = hass
        self._entry = entry
        self._child = child
        self._attr_name = f"ChoreNest {child}"
        self._attr_unique_id = f"{DOMAIN}_child_{child.lower()}_{entry.entry_id}"

    async def async_added_to_hass(self):
        @callback
        def _upd(_e):
            self.async_write_ha_state()
        self.async_on_remove(self.hass.bus.async_listen(f"{DOMAIN}_updated", _upd))

    @property
    def state(self):
        return len(self._today_tasks())

    @property
    def extra_state_attributes(self):
        config = _cfg(self.hass, self._entry)
        pres_cfg = config.get(CONF_CHILD_PRESENCE, {}).get(self._child, {})
        today = date.today()
        tasks = self._today_tasks()
        done_cnt = sum(1 for t in tasks if t["done"])
        return {
            "child": self._child,
            "tasks_today": tasks,
            "total": len(tasks),
            "done_count": done_cnt,
            "all_done": done_cnt == len(tasks) and len(tasks) > 0,
            "free_day": len(tasks) == 0,
            "present": child_present_on(pres_cfg, today),
            "available": child_available_on(pres_cfg, today),
        }

    def _today_tasks(self):
        config = _cfg(self.hass, self._entry)
        done_map = _done(self.hass, self._entry)
        children = config.get(CONF_CHILDREN, [])
        child_pres = config.get(CONF_CHILD_PRESENCE, {})
        today = date.today()
        date_str = today.isoformat()
        month_key = today.strftime("%Y-%m")
        result = []

        for t in rotation_assignments(config.get(CONF_ROTATION_TASKS, []), children, child_pres, today):
            if t["child"] == self._child:
                key = f"rot__{date_str}__{self._child}__{t['task']}"
                result.append({**t, "icon": "🔄", "done": done_map.get(key, False), "date": date_str, "key": key})

        for t in week_assignments(config.get(CONF_WEEK_TASKS, []), children, child_pres, today):
            if t["child"] == self._child:
                key = f"wk__{date_str}__{self._child}__{t['task']}"
                result.append({**t, "icon": "📅", "done": done_map.get(key, False), "date": date_str, "key": key})

        for t in month_assignments_for_date(config.get(CONF_MONTH_TASKS, []), children, child_pres, today):
            if t["child"] == self._child:
                key = f"month__{month_key}__{self._child}__{t['task']}"
                result.append({**t, "icon": "🗓️", "done": done_map.get(key, False), "date": date_str,
                                "month_key": month_key, "key": key})

        return result

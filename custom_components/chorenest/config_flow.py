"""
ChoreNest config flow.

Design goals (v1.0 rewrite):
- Minimal initial setup: language + children only. Everything else (presence
  patterns, tasks) is optional and can be added later from Settings.
- No more comma-separated text blobs: every task/child is added, edited or
  removed one at a time through short, focused forms.
- The Options flow always returns to a small menu after every save, so
  adding several tasks in a row takes a few quick taps instead of having to
  retype a whole list each time.
- Language (NL/EN/DE) is chosen once during setup and can be changed later;
  it drives the dynamic labels (colours, days, patterns) independently of
  the Home Assistant admin's own UI language.
"""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN, LANGUAGES, DEFAULT_LANG, MAX_CHILDREN,
    CONF_LANG, CONF_CHILDREN, CONF_CHILD_COLORS, CONF_CHILD_PRESENCE,
    CONF_ROTATION_TASKS, CONF_WEEK_TASKS, CONF_MONTH_TASKS,
    CHILD_COLOR_OPTIONS, DEFAULT_COLOR_ORDER, DAYS, MONTH_WEEK_KEYS,
    PRESENCE_ALWAYS, PRESENCE_ALT_WEEKS, PRESENCE_FIXED_DAYS,
    PRESENCE_WEEKS_MONTH, PRESENCE_COMBO,
    WEEK_MODE_AUTO, WEEK_MODE_EVEN, WEEK_MODE_ODD, WEEK_MODE_FIXED,
)

LANG_CHOICES = {
    "nl": "🇳🇱  Nederlands",
    "en": "🇬🇧  English",
    "de": "🇩🇪  Deutsch",
}

# ─────────────────────────────────────────────────────────────────────────
# Dynamic (in-flow) translations. These drive labels/help text that are
# chosen by the user inside the wizard (self._lang), independent of the
# admin's Home Assistant UI language (which drives translations/*.json).
# ─────────────────────────────────────────────────────────────────────────
T = {
    "nl": {
        "colors": {
            "blue": "⭐ Blauw", "green": "🌟 Groen", "orange": "🎯 Oranje", "pink": "🌈 Roze",
            "purple": "🦋 Paars", "teal": "🚀 Teal", "indigo": "🏆 Indigo", "red": "💎 Rood",
            "yellow": "🌻 Geel", "cyan": "🌊 Cyaan",
        },
        "presence": {
            PRESENCE_ALWAYS: "🏠 Altijd thuis",
            PRESENCE_ALT_WEEKS: "🔄 Om de week (co-ouderschap)",
            PRESENCE_FIXED_DAYS: "📅 Vaste dagen per week",
            PRESENCE_WEEKS_MONTH: "🗓️ Bepaalde weken per maand",
            PRESENCE_COMBO: "🔄📅 Om de week + vaste dagen",
        },
        "presence_help": {
            PRESENCE_ALWAYS: "Dit kind woont altijd bij jou.",
            PRESENCE_ALT_WEEKS: "Startdatum = eerste maandag van een week dat het kind bij jou is.",
            PRESENCE_FIXED_DAYS: "Vink hieronder aan op welke dagen het kind bij jou is.",
            PRESENCE_WEEKS_MONTH: "Vink hieronder aan in welke weken van de maand het kind bij jou is.",
            PRESENCE_COMBO: "Combineert 'om de week' met vaste dagen — vul beide hieronder in.",
        },
        "week_modes": {
            WEEK_MODE_AUTO: "🔄 Automatisch roteren", WEEK_MODE_EVEN: "Even weken",
            WEEK_MODE_ODD: "Oneven weken", WEEK_MODE_FIXED: "Altijd hetzelfde kind",
        },
        "days": dict(zip(DAYS, ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"])),
        "month_weeks": dict(zip(MONTH_WEEK_KEYS, ["1e week", "2e week", "3e week", "4e week", "Laatste week"])),
        "auto_none": "— automatisch / geen —",
        "children_intro": (
            "Voer de namen van de kinderen in, gescheiden door een komma "
            "(bijv. Emma, Liam).\n\n"
            "Heeft elk kind een eigen schema nodig (bijv. co-ouderschap)? "
            "Zet dan 'Individuele schema's' aan — dan doorloop je zo de "
            "instellingen per kind. Staat dit uit, dan zijn alle kinderen "
            "gewoon altijd thuis; dat kun je later altijd nog aanpassen."
        ),
        "finish_title": "Klaar met de basisinstellingen! 🎉",
        "finish_desc": (
            "{names} {is_are} toegevoegd.\n\n"
            "Taken toevoegen doe je hierna via Instellingen → Apparaten & "
            "Diensten → ChoreNest → Configureren. Daar kun je dagelijkse, "
            "wekelijkse en maandelijkse taken één voor één toevoegen."
        ),
        "is_are_1": "is", "is_are_n": "zijn",
        "blocked_help": "Vink dagen aan waarop dit kind WEL thuis is maar GEEN tijd heeft voor taken (die dag gaat automatisch naar een ander kind).",
        "rotation_help": "Taken die elke dag terugkomen en automatisch rouleren tussen de kinderen.",
        "week_help": "Een taak die één keer per week terugkomt op een vaste dag.",
        "month_help": "Een taak die één keer per maand terugkomt.",
        "remove_label": "🗑️ Deze verwijderen",
        "no_items": "Nog niets toegevoegd.",
    },
    "en": {
        "colors": {
            "blue": "⭐ Blue", "green": "🌟 Green", "orange": "🎯 Orange", "pink": "🌈 Pink",
            "purple": "🦋 Purple", "teal": "🚀 Teal", "indigo": "🏆 Indigo", "red": "💎 Red",
            "yellow": "🌻 Yellow", "cyan": "🌊 Cyan",
        },
        "presence": {
            PRESENCE_ALWAYS: "🏠 Always home",
            PRESENCE_ALT_WEEKS: "🔄 Alternate weeks (co-parenting)",
            PRESENCE_FIXED_DAYS: "📅 Fixed days per week",
            PRESENCE_WEEKS_MONTH: "🗓️ Specific weeks per month",
            PRESENCE_COMBO: "🔄📅 Alternate weeks + fixed days",
        },
        "presence_help": {
            PRESENCE_ALWAYS: "This child lives with you full time.",
            PRESENCE_ALT_WEEKS: "Start date = first Monday of a week the child is with you.",
            PRESENCE_FIXED_DAYS: "Check below which days the child is with you.",
            PRESENCE_WEEKS_MONTH: "Check below which weeks of the month the child is with you.",
            PRESENCE_COMBO: "Combines alternating weeks with fixed days — fill in both below.",
        },
        "week_modes": {
            WEEK_MODE_AUTO: "🔄 Auto rotate", WEEK_MODE_EVEN: "Even weeks",
            WEEK_MODE_ODD: "Odd weeks", WEEK_MODE_FIXED: "Always the same child",
        },
        "days": dict(zip(DAYS, ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])),
        "month_weeks": dict(zip(MONTH_WEEK_KEYS, ["1st week", "2nd week", "3rd week", "4th week", "Last week"])),
        "auto_none": "— automatic / none —",
        "children_intro": (
            "Enter the children's names separated by commas (e.g. Emma, Liam).\n\n"
            "Does each child need their own schedule (e.g. co-parenting)? "
            "Turn on 'Individual schedules' to walk through each child's "
            "settings. Leave it off and every child is simply always home "
            "— you can always change this later."
        ),
        "finish_title": "Basic setup complete! 🎉",
        "finish_desc": (
            "{names} {is_are} been added.\n\n"
            "Add tasks next via Settings → Devices & Services → ChoreNest → "
            "Configure. There you can add daily, weekly and monthly tasks "
            "one at a time."
        ),
        "is_are_1": "has", "is_are_n": "have",
        "blocked_help": "Check days when this child IS home but has NO time for tasks (those tasks automatically go to another child).",
        "rotation_help": "Tasks that recur every day and rotate automatically between the children.",
        "week_help": "A task that recurs once a week on a fixed day.",
        "month_help": "A task that recurs once a month.",
        "remove_label": "🗑️ Remove this",
        "no_items": "Nothing added yet.",
    },
    "de": {
        "colors": {
            "blue": "⭐ Blau", "green": "🌟 Grün", "orange": "🎯 Orange", "pink": "🌈 Rosa",
            "purple": "🦋 Lila", "teal": "🚀 Blaugrün", "indigo": "🏆 Indigo", "red": "💎 Rot",
            "yellow": "🌻 Gelb", "cyan": "🌊 Cyan",
        },
        "presence": {
            PRESENCE_ALWAYS: "🏠 Immer zuhause",
            PRESENCE_ALT_WEEKS: "🔄 Jede zweite Woche (Co-Elternschaft)",
            PRESENCE_FIXED_DAYS: "📅 Feste Wochentage",
            PRESENCE_WEEKS_MONTH: "🗓️ Bestimmte Wochen im Monat",
            PRESENCE_COMBO: "🔄📅 Jede zweite Woche + feste Tage",
        },
        "presence_help": {
            PRESENCE_ALWAYS: "Dieses Kind wohnt immer bei dir.",
            PRESENCE_ALT_WEEKS: "Startdatum = erster Montag einer Woche, in der das Kind bei dir ist.",
            PRESENCE_FIXED_DAYS: "Hake unten ab, an welchen Tagen das Kind bei dir ist.",
            PRESENCE_WEEKS_MONTH: "Hake unten ab, in welchen Wochen des Monats das Kind bei dir ist.",
            PRESENCE_COMBO: "Kombiniert 'jede zweite Woche' mit festen Tagen — beides unten ausfüllen.",
        },
        "week_modes": {
            WEEK_MODE_AUTO: "🔄 Automatisch rotieren", WEEK_MODE_EVEN: "Gerade Wochen",
            WEEK_MODE_ODD: "Ungerade Wochen", WEEK_MODE_FIXED: "Immer dasselbe Kind",
        },
        "days": dict(zip(DAYS, ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"])),
        "month_weeks": dict(zip(MONTH_WEEK_KEYS, ["1. Woche", "2. Woche", "3. Woche", "4. Woche", "Letzte Woche"])),
        "auto_none": "— automatisch / keine —",
        "children_intro": (
            "Gib die Namen der Kinder ein, durch Komma getrennt (z. B. Emma, Liam).\n\n"
            "Braucht jedes Kind einen eigenen Zeitplan (z. B. Co-Elternschaft)? "
            "Aktiviere 'Individuelle Zeitpläne', um die Einstellungen pro Kind "
            "durchzugehen. Ist es aus, sind alle Kinder einfach immer zuhause "
            "— das kannst du später jederzeit ändern."
        ),
        "finish_title": "Grundeinrichtung abgeschlossen! 🎉",
        "finish_desc": (
            "{names} wurde{is_are} hinzugefügt.\n\n"
            "Aufgaben fügst du danach über Einstellungen → Geräte & Dienste → "
            "ChoreNest → Konfigurieren hinzu — dort kannst du tägliche, "
            "wöchentliche und monatliche Aufgaben einzeln hinzufügen."
        ),
        "is_are_1": "", "is_are_n": "n",
        "blocked_help": "Tage abhaken, an denen dieses Kind zuhause ist, aber KEINE Zeit für Aufgaben hat (diese gehen automatisch an ein anderes Kind).",
        "rotation_help": "Aufgaben, die jeden Tag anfallen und automatisch zwischen den Kindern rotieren.",
        "week_help": "Eine Aufgabe, die einmal pro Woche an einem festen Tag anfällt.",
        "month_help": "Eine Aufgabe, die einmal im Monat anfällt.",
        "remove_label": "🗑️ Entfernen",
        "no_items": "Noch nichts hinzugefügt.",
    },
}


def _select(options: dict, multiple: bool = False):
    """Build a SelectSelector from a {value: label} dict — the modern HA
    idiom that guarantees the displayed label and the stored value are
    kept separate (unlike relying on vol.In(dict) rendering behaviour)."""
    return selector.SelectSelector(selector.SelectSelectorConfig(
        options=[selector.SelectOptionDict(value=k, label=v) for k, v in options.items()],
        mode=selector.SelectSelectorMode.DROPDOWN,
        multiple=multiple,
    ))


def _t(lang):
    return T.get(lang, T[DEFAULT_LANG])


def _split_names(raw: str) -> list[str]:
    return [s.strip() for s in raw.split(",") if s.strip()]


def _color_choices(lang):
    t = _t(lang)
    return {key: t["colors"].get(key, key) for key in DEFAULT_COLOR_ORDER}


def _next_color(children, child_colors, idx):
    return child_colors.get(children[idx] if idx < len(children) else "", DEFAULT_COLOR_ORDER[idx % len(DEFAULT_COLOR_ORDER)])


def _child_choices(children, lang, include_auto=True):
    choices = {}
    if include_auto:
        choices[""] = _t(lang)["auto_none"]
    for c in children:
        choices[c] = c
    return choices


# ─────────────────────────────────────────────────────────────────────────
# Shared schema/description builders (used by both the config flow and the
# options flow so the two stay in sync).
# ─────────────────────────────────────────────────────────────────────────

def build_child_pattern_schema(color_default, pattern_default, lang):
    t = _t(lang)
    return vol.Schema({
        vol.Optional("color", default=color_default): _select(_color_choices(lang)),
        vol.Optional("pattern", default=pattern_default): _select(t["presence"]),
    })


def build_child_details_schema(mode, cur_presence, lang):
    t = _t(lang)
    fields = {}
    help_parts = [t["presence_help"].get(mode, "")]

    if mode in (PRESENCE_ALT_WEEKS, PRESENCE_COMBO):
        fields[vol.Optional("start_date", default=cur_presence.get("start_date", "2025-01-06"))] = str
        fields[vol.Optional("start_present", default=cur_presence.get("start_present", True))] = bool

    if mode in (PRESENCE_FIXED_DAYS, PRESENCE_COMBO):
        cur_days = set(cur_presence.get("days_present", []))
        for i, day in enumerate(DAYS):
            fields[vol.Optional(f"day_{day}", default=(i in cur_days))] = bool

    if mode == PRESENCE_WEEKS_MONTH:
        cur_weeks = {str(w) for w in cur_presence.get("weeks_present", [])}
        for key in MONTH_WEEK_KEYS:
            fields[vol.Optional(f"week_{key}", default=(key in cur_weeks))] = bool

    help_parts.append("")
    help_parts.append(t["blocked_help"])
    cur_blocked = set(cur_presence.get("blocked_days", []))
    for i, day in enumerate(DAYS):
        fields[vol.Optional(f"blocked_{day}", default=(i in cur_blocked))] = bool

    return vol.Schema(fields), "\n".join(help_parts)


def parse_child_details(ui, mode) -> dict:
    days_present = [i for i, day in enumerate(DAYS) if ui.get(f"day_{day}", False)]
    weeks_present = [key for key in MONTH_WEEK_KEYS if ui.get(f"week_{key}", False)]
    blocked_days = [i for i, day in enumerate(DAYS) if ui.get(f"blocked_{day}", False)]
    return {
        "mode": mode,
        "start_date": ui.get("start_date", "2025-01-06"),
        "start_present": ui.get("start_present", True),
        "days_present": days_present,
        "weeks_present": weeks_present,
        "blocked_days": blocked_days,
        "override_present": None,
    }


def needs_details_step(mode) -> bool:
    """Every mode still needs the details step, if only for blocked days —
    kept as a single explicit function so the intent is obvious at call sites."""
    return True


def build_task_rotation_schema(children, cur, lang):
    t = _t(lang)
    fields = {
        vol.Required("name", default=cur.get("name", "")): str,
        vol.Optional("fixed_child", default=cur.get("fixed_child") or ""): _select(_child_choices(children, lang)),
    }
    return vol.Schema(fields)


def parse_task_rotation(ui, children):
    return {
        "name": ui["name"].strip(),
        "fixed_child": ui.get("fixed_child") or None,
        "children_order": children,
    }


def build_task_week_schema(children, cur, lang):
    t = _t(lang)
    ch_choices = _child_choices(children, lang)
    return vol.Schema({
        vol.Required("name", default=cur.get("name", "")): str,
        vol.Optional("day", default=cur.get("day", DAYS[2])): _select(t["days"]),
        vol.Optional("mode", default=cur.get("mode", WEEK_MODE_AUTO)): _select(t["week_modes"]),
        vol.Optional("fixed_child", default=cur.get("fixed_child") or ""): _select(ch_choices),
        vol.Optional("even_child", default=cur.get("even_child") or ""): _select(ch_choices),
        vol.Optional("odd_child", default=cur.get("odd_child") or ""): _select(ch_choices),
    })


def parse_task_week(ui, children):
    return {
        "name": ui["name"].strip(),
        "day": ui.get("day", DAYS[2]),
        "mode": ui.get("mode", WEEK_MODE_AUTO),
        "fixed_child": ui.get("fixed_child") or (children[0] if children else ""),
        "even_child": ui.get("even_child") or (children[0] if children else ""),
        "odd_child": ui.get("odd_child") or (children[-1] if children else ""),
        "children_order": children,
    }


def build_task_month_schema(cur, lang):
    t = _t(lang)
    return vol.Schema({
        vol.Required("name", default=cur.get("name", "")): str,
        vol.Optional("week_of_month", default=cur.get("week_of_month", "last")): _select(t["month_weeks"]),
        vol.Optional("day_of_week", default=cur.get("day_of_week", DAYS[-1])): _select(t["days"]),
    })


def parse_task_month(ui):
    return {
        "name": ui["name"].strip(),
        "week_of_month": ui.get("week_of_month", "last"),
        "day_of_week": ui.get("day_of_week", DAYS[-1]),
    }


# ─────────────────────────────────────────────────────────────────────────
# Config flow — initial setup. Deliberately short: language + children only.
# ─────────────────────────────────────────────────────────────────────────

class ChoreNestConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    def __init__(self):
        self._lang = DEFAULT_LANG
        self._children: list[str] = []
        self._different_schedules = False
        self._child_idx = 0
        self._child_colors: dict = {}
        self._child_presence: dict = {}
        self._pending_mode: dict = {}

    async def async_step_user(self, ui=None):
        if ui is not None:
            self._lang = ui.get("language", DEFAULT_LANG)
            return await self.async_step_children()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("language", default=DEFAULT_LANG): _select(LANG_CHOICES),
            }),
        )

    async def async_step_children(self, ui=None):
        errors = {}
        if ui is not None:
            names = _split_names(ui.get("children", ""))
            if not names:
                errors["children"] = "min_one_child"
            elif len(names) > MAX_CHILDREN:
                errors["children"] = "max_children"
            else:
                self._children = names
                self._different_schedules = ui.get("different_schedules", False)
                if not self._different_schedules:
                    for i, child in enumerate(names):
                        self._child_colors[child] = DEFAULT_COLOR_ORDER[i % len(DEFAULT_COLOR_ORDER)]
                        self._child_presence[child] = {
                            "mode": PRESENCE_ALWAYS, "start_date": "", "start_present": True,
                            "days_present": [], "weeks_present": [], "blocked_days": [],
                            "override_present": None,
                        }
                    return await self.async_step_finish()
                self._child_idx = 0
                return await self.async_step_child_pattern()
        return self.async_show_form(
            step_id="children",
            data_schema=vol.Schema({
                vol.Required("children"): str,
                vol.Optional("different_schedules", default=False): bool,
            }),
            errors=errors,
            description_placeholders={"intro": _t(self._lang)["children_intro"]},
        )

    async def async_step_child_pattern(self, ui=None):
        child = self._children[self._child_idx]
        n, total = self._child_idx + 1, len(self._children)
        lang = self._lang

        if ui is not None:
            self._child_colors[child] = ui.get("color", DEFAULT_COLOR_ORDER[0])
            self._pending_mode[child] = ui.get("pattern", PRESENCE_ALWAYS)
            return await self.async_step_child_details()

        default_color = _next_color(self._children, self._child_colors, self._child_idx)
        return self.async_show_form(
            step_id="child_pattern",
            data_schema=build_child_pattern_schema(default_color, PRESENCE_ALWAYS, lang),
            description_placeholders={"child": child, "n": str(n), "total": str(total)},
        )

    async def async_step_child_details(self, ui=None):
        child = self._children[self._child_idx]
        n, total = self._child_idx + 1, len(self._children)
        mode = self._pending_mode.get(child, PRESENCE_ALWAYS)
        cur = self._child_presence.get(child, {})

        if ui is not None:
            self._child_presence[child] = parse_child_details(ui, mode)
            self._child_idx += 1
            if self._child_idx < len(self._children):
                return await self.async_step_child_pattern()
            return await self.async_step_finish()

        schema, help_text = build_child_details_schema(mode, cur, self._lang)
        return self.async_show_form(
            step_id="child_details",
            data_schema=schema,
            description_placeholders={"child": child, "n": str(n), "total": str(total), "help": help_text},
        )

    async def async_step_finish(self, ui=None):
        t = _t(self._lang)
        if ui is not None:
            return self.async_create_entry(
                title="ChoreNest",
                data={
                    CONF_LANG: self._lang,
                    CONF_CHILDREN: self._children,
                    CONF_CHILD_COLORS: self._child_colors,
                    CONF_CHILD_PRESENCE: self._child_presence,
                    CONF_ROTATION_TASKS: [],
                    CONF_WEEK_TASKS: [],
                    CONF_MONTH_TASKS: [],
                },
            )
        names = ", ".join(self._children)
        is_are = t["is_are_1"] if len(self._children) == 1 else t["is_are_n"]
        desc = t["finish_desc"].format(names=names, is_are=is_are)
        return self.async_show_form(
            step_id="finish",
            data_schema=vol.Schema({}),
            description_placeholders={"desc": desc},
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        return ChoreNestOptionsFlow(entry)


# ─────────────────────────────────────────────────────────────────────────
# Options flow — everything else happens here, one item at a time, always
# returning to a small menu so multiple edits in a row stay quick.
# ─────────────────────────────────────────────────────────────────────────

class ChoreNestOptionsFlow(config_entries.OptionsFlow):

    def __init__(self, entry):
        self._entry = entry
        # Merge initial data with any previously-saved options so reopening
        # "Configure" (and the runtime sensors) always see the latest state —
        # options-flow saves are written to entry.options, not entry.data.
        d = {**entry.data, **entry.options}
        self._lang = d.get(CONF_LANG, DEFAULT_LANG)
        self._children = list(d.get(CONF_CHILDREN, []))
        self._child_colors = dict(d.get(CONF_CHILD_COLORS, {}))
        self._child_presence = dict(d.get(CONF_CHILD_PRESENCE, {}))
        self._rotation_tasks = list(d.get(CONF_ROTATION_TASKS, []))
        self._week_tasks = list(d.get(CONF_WEEK_TASKS, []))
        self._month_tasks = list(d.get(CONF_MONTH_TASKS, []))
        self._edit_child = None
        self._pending_mode = {}
        self._edit_task_name = None

    def _save(self):
        return self.async_create_entry(title="", data={
            CONF_LANG: self._lang,
            CONF_CHILDREN: self._children,
            CONF_CHILD_COLORS: self._child_colors,
            CONF_CHILD_PRESENCE: self._child_presence,
            CONF_ROTATION_TASKS: self._rotation_tasks,
            CONF_WEEK_TASKS: self._week_tasks,
            CONF_MONTH_TASKS: self._month_tasks,
        })

    # ── Main menu ────────────────────────────────────────────────────────
    async def async_step_init(self, ui=None):
        return self.async_show_menu(step_id="init", menu_options=[
            "children", "tasks_rotation", "tasks_week", "tasks_month", "language",
        ])

    async def async_step_language(self, ui=None):
        if ui is not None:
            self._lang = ui.get("language", self._lang)
            return self._save()
        return self.async_show_form(
            step_id="language",
            data_schema=vol.Schema({
                vol.Required("language", default=self._lang): _select(LANG_CHOICES),
            }),
        )

    # ── Children ─────────────────────────────────────────────────────────
    async def async_step_children(self, ui=None):
        return self.async_show_menu(step_id="children", menu_options=["child_add", "child_edit", "init"])

    async def async_step_child_add(self, ui=None):
        errors = {}
        if ui is not None:
            name = ui.get("name", "").strip()
            if not name:
                errors["name"] = "min_one_child"
            elif name in self._children:
                errors["name"] = "duplicate_child"
            elif len(self._children) >= MAX_CHILDREN:
                errors["name"] = "max_children"
            else:
                self._children.append(name)
                self._edit_child = name
                return await self.async_step_child_pattern()
        return self.async_show_form(
            step_id="child_add", data_schema=vol.Schema({vol.Required("name"): str}), errors=errors,
        )

    async def async_step_child_edit(self, ui=None):
        if not self._children:
            return await self.async_step_children()
        if ui is not None:
            self._edit_child = ui.get("child")
            return await self.async_step_child_pattern()
        return self.async_show_form(
            step_id="child_edit",
            data_schema=vol.Schema({vol.Required("child"): _select({c: c for c in self._children})}),
        )

    async def async_step_child_pattern(self, ui=None):
        child = self._edit_child
        cur_presence = self._child_presence.get(child, {})
        cur_color = self._child_colors.get(child, DEFAULT_COLOR_ORDER[0])
        cur_mode = cur_presence.get("mode", PRESENCE_ALWAYS)

        if ui is not None:
            self._child_colors[child] = ui.get("color", cur_color)
            self._pending_mode[child] = ui.get("pattern", PRESENCE_ALWAYS)
            return await self.async_step_child_details()

        return self.async_show_form(
            step_id="child_pattern",
            data_schema=build_child_pattern_schema(cur_color, cur_mode, self._lang),
            description_placeholders={"child": child, "n": "1", "total": "1"},
        )

    async def async_step_child_details(self, ui=None):
        child = self._edit_child
        mode = self._pending_mode.get(child, PRESENCE_ALWAYS)
        cur = self._child_presence.get(child, {})

        if ui is not None:
            remove = ui.pop("remove_child", False)
            if remove:
                self._children = [c for c in self._children if c != child]
                self._child_colors.pop(child, None)
                self._child_presence.pop(child, None)
            else:
                self._child_presence[child] = parse_child_details(ui, mode)
            return self._save()

        schema, help_text = build_child_details_schema(mode, cur, self._lang)
        schema = schema.extend({vol.Optional("remove_child", default=False): bool})
        return self.async_show_form(
            step_id="child_details",
            data_schema=schema,
            description_placeholders={"child": child, "n": "1", "total": "1", "help": help_text},
        )

    # ── Rotation tasks ───────────────────────────────────────────────────
    async def async_step_tasks_rotation(self, ui=None):
        return self.async_show_menu(step_id="tasks_rotation", menu_options=[
            "task_rotation_add", "task_rotation_pick", "init",
        ])

    async def async_step_task_rotation_add(self, ui=None):
        self._edit_task_name = None
        return await self.async_step_task_rotation_form(ui)

    async def async_step_task_rotation_pick(self, ui=None):
        if not self._rotation_tasks:
            return await self.async_step_tasks_rotation()
        if ui is not None:
            self._edit_task_name = ui.get("task")
            return await self.async_step_task_rotation_form()
        names = {tk["name"]: tk["name"] for tk in self._rotation_tasks}
        return self.async_show_form(
            step_id="task_rotation_pick", data_schema=vol.Schema({vol.Required("task"): _select(names)}),
        )

    async def async_step_task_rotation_form(self, ui=None):
        cur = next((tk for tk in self._rotation_tasks if tk["name"] == self._edit_task_name), {}) if self._edit_task_name else {}
        if ui is not None:
            if ui.pop("remove", False) and self._edit_task_name:
                self._rotation_tasks = [tk for tk in self._rotation_tasks if tk["name"] != self._edit_task_name]
            else:
                new_task = parse_task_rotation(ui, self._children)
                if self._edit_task_name:
                    self._rotation_tasks = [new_task if tk["name"] == self._edit_task_name else tk for tk in self._rotation_tasks]
                else:
                    self._rotation_tasks.append(new_task)
            return await self.async_step_tasks_rotation()

        schema = build_task_rotation_schema(self._children, cur, self._lang)
        if self._edit_task_name:
            schema = schema.extend({vol.Optional("remove", default=False): bool})
        return self.async_show_form(
            step_id="task_rotation_form", data_schema=schema,
            description_placeholders={"help": _t(self._lang)["rotation_help"]},
        )

    # ── Weekly tasks ─────────────────────────────────────────────────────
    async def async_step_tasks_week(self, ui=None):
        return self.async_show_menu(step_id="tasks_week", menu_options=[
            "task_week_add", "task_week_pick", "init",
        ])

    async def async_step_task_week_add(self, ui=None):
        self._edit_task_name = None
        return await self.async_step_task_week_form(ui)

    async def async_step_task_week_pick(self, ui=None):
        if not self._week_tasks:
            return await self.async_step_tasks_week()
        if ui is not None:
            self._edit_task_name = ui.get("task")
            return await self.async_step_task_week_form()
        names = {tk["name"]: tk["name"] for tk in self._week_tasks}
        return self.async_show_form(
            step_id="task_week_pick", data_schema=vol.Schema({vol.Required("task"): _select(names)}),
        )

    async def async_step_task_week_form(self, ui=None):
        cur = next((tk for tk in self._week_tasks if tk["name"] == self._edit_task_name), {}) if self._edit_task_name else {}
        if ui is not None:
            if ui.pop("remove", False) and self._edit_task_name:
                self._week_tasks = [tk for tk in self._week_tasks if tk["name"] != self._edit_task_name]
            else:
                new_task = parse_task_week(ui, self._children)
                if self._edit_task_name:
                    self._week_tasks = [new_task if tk["name"] == self._edit_task_name else tk for tk in self._week_tasks]
                else:
                    self._week_tasks.append(new_task)
            return await self.async_step_tasks_week()

        schema = build_task_week_schema(self._children, cur, self._lang)
        if self._edit_task_name:
            schema = schema.extend({vol.Optional("remove", default=False): bool})
        return self.async_show_form(
            step_id="task_week_form", data_schema=schema,
            description_placeholders={"help": _t(self._lang)["week_help"]},
        )

    # ── Monthly tasks ────────────────────────────────────────────────────
    async def async_step_tasks_month(self, ui=None):
        return self.async_show_menu(step_id="tasks_month", menu_options=[
            "task_month_add", "task_month_pick", "init",
        ])

    async def async_step_task_month_add(self, ui=None):
        self._edit_task_name = None
        return await self.async_step_task_month_form(ui)

    async def async_step_task_month_pick(self, ui=None):
        if not self._month_tasks:
            return await self.async_step_tasks_month()
        if ui is not None:
            self._edit_task_name = ui.get("task")
            return await self.async_step_task_month_form()
        names = {tk["name"]: tk["name"] for tk in self._month_tasks}
        return self.async_show_form(
            step_id="task_month_pick", data_schema=vol.Schema({vol.Required("task"): _select(names)}),
        )

    async def async_step_task_month_form(self, ui=None):
        cur = next((tk for tk in self._month_tasks if tk["name"] == self._edit_task_name), {}) if self._edit_task_name else {}
        if ui is not None:
            if ui.pop("remove", False) and self._edit_task_name:
                self._month_tasks = [tk for tk in self._month_tasks if tk["name"] != self._edit_task_name]
            else:
                new_task = parse_task_month(ui)
                if self._edit_task_name:
                    self._month_tasks = [new_task if tk["name"] == self._edit_task_name else tk for tk in self._month_tasks]
                else:
                    self._month_tasks.append(new_task)
            return await self.async_step_tasks_month()

        schema = build_task_month_schema(cur, self._lang)
        if self._edit_task_name:
            schema = schema.extend({vol.Optional("remove", default=False): bool})
        return self.async_show_form(
            step_id="task_month_form", data_schema=schema,
            description_placeholders={"help": _t(self._lang)["month_help"]},
        )

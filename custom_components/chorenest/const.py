"""Constants for ChoreNest."""

DOMAIN = "chorenest"
PLATFORMS = ["sensor"]

CONF_LANG               = "lang"
CONF_CHILDREN            = "children"
CONF_CHILD_COLORS        = "child_colors"
CONF_CHILD_PRESENCE      = "child_presence"
CONF_ROTATION_TASKS      = "rotation_tasks"
CONF_WEEK_TASKS          = "week_tasks"
CONF_MONTH_TASKS         = "month_tasks"

LANGUAGES = ["nl", "en", "de"]
DEFAULT_LANG = "en"

# Internal (English) day/week identifiers used everywhere in stored data,
# independent of the language chosen for the UI.
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_INDEX = {d: i for i, d in enumerate(DAYS)}

MONTH_WEEK_KEYS = ["1", "2", "3", "4", "last"]

# Presence patterns (internal keys, independent of UI language)
PRESENCE_ALWAYS       = "always"
PRESENCE_ALT_WEEKS    = "alt_weeks"
PRESENCE_FIXED_DAYS   = "fixed_days"
PRESENCE_WEEKS_MONTH  = "weeks_of_month"
PRESENCE_COMBO        = "combo"
PRESENCE_MODES = [
    PRESENCE_ALWAYS, PRESENCE_ALT_WEEKS, PRESENCE_FIXED_DAYS,
    PRESENCE_WEEKS_MONTH, PRESENCE_COMBO,
]

# Weekly task distribution modes (internal keys)
WEEK_MODE_AUTO  = "auto_rotate"
WEEK_MODE_EVEN  = "even"
WEEK_MODE_ODD   = "odd"
WEEK_MODE_FIXED = "fixed"
WEEK_MODES = [WEEK_MODE_AUTO, WEEK_MODE_EVEN, WEEK_MODE_ODD, WEEK_MODE_FIXED]

DEFAULT_ROTATION_TASKS = []
DEFAULT_WEEK_TASKS = []
DEFAULT_MONTH_TASKS = []

CHILD_COLOR_OPTIONS = {
    "blue":   ["#1565C0", "#42A5F5"],
    "green":  ["#2E7D32", "#66BB6A"],
    "orange": ["#E65100", "#FFA726"],
    "pink":   ["#AD1457", "#F48FB1"],
    "purple": ["#6A1B9A", "#CE93D8"],
    "teal":   ["#00695C", "#4DB6AC"],
    "indigo": ["#283593", "#7986CB"],
    "red":    ["#B71C1C", "#EF9A9A"],
    "yellow": ["#F57F17", "#FFF176"],
    "cyan":   ["#006064", "#80DEEA"],
}
COLOR_EMOJI = {
    "blue": "⭐", "green": "🌟", "orange": "🎯", "pink": "🌈", "purple": "🦋",
    "teal": "🚀", "indigo": "🏆", "red": "💎", "yellow": "🌻", "cyan": "🌊",
}
DEFAULT_COLOR_ORDER = list(CHILD_COLOR_OPTIONS.keys())

MAX_CHILDREN = 8

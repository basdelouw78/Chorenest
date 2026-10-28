# 📋 ChoreNest — Home Assistant integration

A kid-friendly HACS integration for tracking household chores per child. Supports co-parenting, automatic daily rotation, and weekly/monthly tasks — redesigned from the ground up to be quick to set up and easy to adjust.

**Languages:** 🇳🇱 Nederlands · 🇬🇧 English · 🇩🇪 Deutsch — chosen during setup, changeable anytime.

> ChoreNest is a rewrite of the earlier "Kindertaken Planner" project, under a new name and a new `chorenest` domain. It is a fresh integration, not an in-place upgrade — see **Coming from Kindertaken Planner** below.

---

## ✨ What's different from the old version

- **Setup takes two screens, not twenty.** Pick a language, enter the children's names, done. Co-parenting schedules and tasks are optional extras you add afterwards, only if you need them.
- **No more comma-separated text blobs.** Every child and every task is added, edited or removed one at a time on its own small screen — no risk of a typo wiping out your whole task list.
- **A real menu, not a wizard you have to restart.** Settings → ChoreNest → Configure opens a menu (Children / Daily tasks / Weekly tasks / Monthly tasks / Language). Adding five tasks in a row is five quick taps, each one returning to the same menu.
- **Blocked ("no time for tasks") days now work for every presence pattern**, including children who are always home — previously only co-parenting patterns supported this.

---

## ✨ Features

Flexible for 1–8 children with freely chosen names, each with their own colour and emoji shown on the dashboard. Presence patterns cover always-home, alternating weeks (co-parenting), fixed days per week, specific weeks per month, or a combination of alternating weeks and fixed days — plus optional "blocked" days where a child is home but has no time for chores. Every task (daily rotating, weekly, or monthly) can optionally be limited to a chosen subset of children instead of everyone — handy for splitting chores into separate rotation groups (e.g. two children rotate the bathroom while the other two rotate the bins). Daily rotating tasks are automatically divided fairly among the children who are actually present; weekly tasks recur on a fixed day with automatic, even/odd-week, or fixed-child distribution; monthly tasks recur once a month on a chosen week and day, automatically shifting to the next available day if a child is away. Tasks are marked done by tapping them on the dashboard card, and completion state survives restarts.

---

## 📦 Installation

Unzip the archive and copy these into your Home Assistant `config` folder:

```
config/
├── custom_components/
│   └── chorenest/                 ← copy this whole folder
└── www/
    └── chorenest-card/
        └── chorenest-card.js      ← copy this file
```

Register the Lovelace resource under **Settings → Dashboards → Resources → Add**:

| URL | Type |
|-----|------|
| `/local/chorenest-card/chorenest-card.js` | JavaScript module |

or in `configuration.yaml`:
```yaml
lovelace:
  resources:
    - url: /local/chorenest-card/chorenest-card.js
      type: module
```

Restart Home Assistant, then go to **Settings → Devices & Services → + Add integration → "ChoreNest"**. The wizard asks for a language and the children's names — that's it. Add tasks afterwards via **Configure**.

Add the dashboard card:
```yaml
type: custom:chorenest-card
entity: sensor.chorenest_week
```

For a compact "today's tasks only" card for one child — handy on that child's own dashboard page in the mobile app — point the same card at the child's sensor. `title`, `emoji` and `color` are optional:
```yaml
type: custom:chorenest-card
entity: sensor.chorenest_jasper
title: Jasper
emoji: ⭐
color: "#1565C0"
```

---

## ✏️ Changing things after setup

**Settings → Devices & Services → ChoreNest → Configure** opens a menu:

- **Children** — add a child, or edit/remove an existing one (colour, presence pattern, blocked days).
- **Daily rotating tasks / Weekly tasks / Monthly tasks** — add a new task, or pick an existing one to edit or remove.
- **Language** — switch between Dutch, English and German at any time.

Every screen returns you to the relevant menu afterwards, so adding several tasks is just repeating "➕ Add a task" a few times.

---

## 🔧 Services

`chorenest.mark_done` toggles a task done/not done — call with either a `key` (from the sensor's task attributes) or `child`+`task`. `chorenest.set_presence` manually overrides a child's presence (`present: true/false`, or omit/`null` to go back to automatic). `chorenest.clear_presence_override` clears that override. `chorenest.reset_week` clears completed weekly tasks (monthly tasks are kept); `chorenest.reset_all` clears everything. `chorenest.swap_task` / `chorenest.undo_swap` trade tasks between children for the current week (see below).

### 🔁 Swapping tasks

Children can trade tasks with each other for the current week — from Monday the normal schedule applies again. Daily rotating and weekly tasks can be swapped; monthly tasks are per child already.

`chorenest.swap_task` with `child`, `task`, `date` and `with_child` hands a task over to another child (e.g. someone who has a free day). Add `other_task` + `other_date` to make it an exchange, possibly on a different day — "I'll do your Thursday task if you do my Wednesday one":
```yaml
action: chorenest.swap_task
data:
  child: Jasper
  task: Plastic buitenzetten
  date: "2026-10-28"
  with_child: Nena
  other_task: Badkamer schoonmaken   # optional: what Jasper does in return
  other_date: "2026-11-01"
```
Only today and later days of the current week can be swapped, the other child must be home and available on that day, and a task that was already swapped has to be swapped back first. `chorenest.undo_swap` with the `swap_id` reverts a swap. Swapped tasks carry `swapped_from` and `swap_id` in the sensor attributes, `sensor.chorenest_week` lists the week's swaps in `swaps`, and every swap and undo is written to the Home Assistant logbook. The card shows a 🔁 marker on swapped tasks.

### 🗑️ Bin days from a waste-collection sensor

A weekly task can follow a collection sensor instead of a fixed weekday — handy for bins, whose collection day shifts around holidays or isn't weekly at all. In **Configure → Weekly tasks**, pick the sensor under *Collection sensor* (any sensor whose state or `year_month_day_date` attribute holds the next date, e.g. the [Afvalinfo](https://github.com/heyajohnny/afvalinfo) integration) and choose *The day before* or *On the collection day*. The task then lands on that day, with the task's normal distribution (auto rotate, even/odd, fixed). Without a known date yet it falls back to the fixed day. Dates already seen are remembered for three weeks, so the task stays visible (and ticked off) after the sensor jumps to the next collection. Tasks that follow a sensor carry `collection: true` in the sensor attributes.

Example automation — reset every Monday at 00:01:
```yaml
automation:
  - alias: "ChoreNest weekly reset"
    trigger:
      - platform: time
        at: "00:01:00"
    condition:
      - condition: time
        weekday: [mon]
    action:
      - service: chorenest.reset_week
```

---

## 🧩 Entities

`sensor.chorenest_week` holds the full week overview used by the dashboard card. `sensor.chorenest_<name>` holds today's tasks for one child, with attributes `tasks_today`, `total`, `done_count`, `all_done`, `free_day`, `present`, `available`.

---

## Coming from Kindertaken Planner

ChoreNest uses a new domain (`chorenest` instead of `kindertaken`) and a redesigned configuration format, so it is installed as a separate integration rather than an automatic upgrade:

1. Install ChoreNest alongside (or instead of) Kindertaken Planner.
2. Recreate your children, presence patterns and tasks through the new, much shorter wizard/menu.
3. Update your dashboard to use `custom:chorenest-card` / `sensor.chorenest_week`.
4. Remove the old Kindertaken Planner integration and its resource once you're happy.

Given how much shorter the new setup is, this is normally quicker than it sounds — most households are back up and running in a couple of minutes. If you'd like an automatic one-time import of your existing Kindertaken Planner configuration instead, that can be added as a follow-up.

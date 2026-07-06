# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
============================================================
  TODAY'S SCHEDULE  (MONDAY, JULY 06, 2026)
  Caregiver: Jordan
============================================================
  08:00  │  Morning walk      (Biscuit, 30 min)       [HIGH]
  08:30  │  Feeding           (Biscuit, 10 min)       [HIGH]
  08:40  │  Feeding           (Mochi, 10 min)         [HIGH]
  18:00  │  Play time         (Mochi, 20 min)         [LOW]
  18:20  │  Litter cleanup    (Mochi, 15 min)         [MEDIUM]
  18:35  │  Training          (Biscuit, 20 min)       [MEDIUM]
------------------------------------------------------------
  Total scheduled time: 105 / 120 min
============================================================

Conflict warnings:
  ⚠️ Conflict (different pets): 'Feeding' for Biscuit at 08:30 overlaps 'Feeding' for Mochi at 08:30.

Why this plan:
  Considered 6 eligible task(s); scheduled 6 within a 120-minute budget (105 min used). Tasks were ordered by priority (high first), then by shorter duration to fit more in. Moved to avoid overlap: Feeding (08:30→08:40).
```


## 🧪 Testing PawPal+

Run the full suite from the project root:

```bash
python -m pytest          # run all tests

================================================= 15 passed in 0.11s =================================================


python -m pytest --cov     # optional: with coverage
```

### What the tests cover

The suite lives in `tests/test_pawpal.py` (15 tests) and targets the logic that
actually makes scheduling decisions:

- **Sorting correctness** — `sort_by_time()` returns tasks in chronological
  order (untimed tasks sink to the end), and `sort_tasks()` orders by priority
  first, shorter duration as the tie-breaker.
- **Recurrence logic** — completing a **daily** task auto-creates the next
  instance due the following day (fresh id, `completed=False`); one-off tasks
  spawn nothing; `weekdays` recurrence rolls Friday → Monday; asking a
  non-recurring task for its next occurrence raises.
- **Conflict detection** — the `Scheduler` flags two tasks at the *same* time,
  labels same-pet vs. different-pet clashes, and treats back-to-back
  (touching-but-not-overlapping) tasks as *no* conflict.
- **Conflict resolution** — when two tasks want the same slot, the second is
  bumped back-to-back and the move is recorded for the plan's explanation.
- **Budget fitting** — a zero-minute budget schedules nothing; the greedy fit
  will schedule a smaller lower-priority task when a higher-priority one is too
  big to fit.
- **Edge cases** — a pet with no tasks produces a valid, empty plan without
  crashing.

### Successful test run

```
============================= test session starts =============================
platform win32 -- Python 3.13.3, pytest-9.1.0, pluggy-1.6.0
rootdir: C:\Users\kytra\Documents\CodePath\AI110\ai110-module2show-pawpal-starter
collected 15 items

tests\test_pawpal.py ...............                                     [100%]

============================= 15 passed in 0.03s ==============================
```

### Confidence Level

**★★★★☆ (4 / 5)**

All 15 tests pass and cover the core decision-making paths — sorting, recurrence,
budget-fitting, and both conflict detection and resolution — including their
boundary cases. I'm holding back the fifth star because two known quirks are
documented-but-untested: weekly `next_occurrence()` advances by 7 days without
re-anchoring to `recurrence_weekday`, and a late task can roll past midnight and
sort to the front of the plan. Neither is exercised yet, so reliability on those
paths is unverified.

## 📐 Smarter Scheduling

PawPal+ turns a flat list of tasks into an ordered, time-budgeted, conflict-aware
daily plan. All of this logic lives in `pawpal_system.py`. The quick map:

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Sort by time | `Scheduler.sort_by_time()` | Lambda `key` on zero-padded `"HH:MM"` strings; untimed tasks sink to the end |
| Sort by priority | `Scheduler.sort_tasks()` | High priority first, then shorter duration as a tie-breaker |
| Filter by pet / status | `Scheduler.filter_tasks()` | Filter by `pet_id` or `pet_name`, by `category`, and by completion status |
| Conflict detection | `Scheduler.detect_conflicts()` | Returns warning strings for overlapping time windows; never crashes |
| Conflict resolution | `Scheduler.resolve_conflicts()` | Places tasks back-to-back and records any that were bumped |
| Recurring tasks | `Task.occurs_on()`, `Task.next_due_date()`, `Task.next_occurrence()`, `Pet.mark_task_complete()` | Daily / weekly / weekdays; completing one auto-creates the next |
| Full pipeline | `Scheduler.generate_plan()` | filter → sort → fit budget → place → explain |

### Sorting behavior

- **`Scheduler.sort_by_time()`** orders tasks chronologically. It sorts with a
  lambda `key` that renders each task's `preferred_time` as an `"HH:MM"` string —
  because hours and minutes are zero-padded, plain string comparison matches
  clock order. Tasks without a preferred time map to `"99:99"` so they sort to
  the end instead of raising on `None`.
- **`Scheduler.sort_tasks()`** orders by importance: highest `Priority` first,
  then shorter `duration` as a tie-breaker so more tasks fit into the budget.

### Filtering behavior

**`Scheduler.filter_tasks()`** is the single filtering entry point. By default it
keeps only tasks that are **not completed** and that **occur today**
(via `Task.occurs_on()`). Optional keyword arguments narrow the results further:

- `pet_id=...` or `pet_name=...` — restrict to one pet (name is case-insensitive
  and resolved to an id through the owner's pet list).
- `category=...` — restrict to one kind of task (e.g. `"feeding"`).
- `include_completed=True` — keep finished tasks, for a review/history view.

The app uses this both for the per-pet task tables and the "show completed" toggle.

### Conflict detection logic

Two methods split the work:

- **`Scheduler.detect_conflicts()`** is a lightweight, read-only check. It sorts
  the timed tasks by the same `"HH:MM"` key, then compares each task's intended
  window (`preferred_time` → `preferred_time + duration`) against the ones after
  it. Because the list is sorted, it can `break` as soon as a later task starts
  after the current one ends. It **returns a list of human-readable warning
  strings** (flagging whether the clash is for the *same pet* or *different
  pets*) rather than raising — so the UI shows a warning and the program keeps
  running. These land in `Schedule.warnings`.
- **`Scheduler.resolve_conflicts()`** actually places tasks on the clock,
  back-to-back with no overlaps, honoring each `preferred_time` when the slot is
  still free. When a preferred slot is already taken, the task is bumped later
  and the move is recorded so `explain()` can report it (e.g. `Feeding
  (08:30→08:40)`).

### Recurring task logic

Recurrence is modeled on `Task` (`recurrence`, `recurrence_weekday`, `due_date`)
and driven by three methods plus one on `Pet`:

- **`Task.occurs_on(day)`** decides whether a task is due on a given day:
  `daily` every day, `weekly` on its anchor weekday, `weekdays` Monday–Friday.
- **`Task.next_due_date(after)`** uses `datetime.timedelta` to compute the next
  occurrence accurately (handling month/year rollovers): `daily` → `after + 1
  day`, `weekly` → `after + 7 days`, `weekdays` → the next Mon–Fri.
- **`Task.next_occurrence()`** builds the follow-up task — a copy with
  `completed=False` and an advanced `due_date`.
- **`Pet.mark_task_complete(task_id)`** ties it together: it marks the task done
  and, if the task recurs, automatically creates and attaches the next instance
  (with a fresh id). One-off tasks simply complete.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->

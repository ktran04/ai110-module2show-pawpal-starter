"""PawPal+ system classes.

Data-holding objects (Task, Pet, Owner, Schedule) are dataclasses; Scheduler
holds the planning logic — it retrieves tasks across an owner's pets, orders them
by priority, fits them into the owner's time budget, assigns clock times, and
explains its choices.

Design based on diagrams/uml.mmd.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import date, datetime, time, timedelta
from enum import IntEnum


class Priority(IntEnum):
    """Task priority, ordered so higher value = more important (sortable)."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


# Recurrence values that mean "this task happens today regardless of weekday".
_ALWAYS_TODAY = {None, "daily"}


@dataclass
class Task:
    """A single pet-care activity (e.g., a walk, feeding, or meds)."""

    task_id: int
    pet_id: int
    name: str
    category: str
    duration: int  # minutes
    priority: Priority
    preferred_time: time | None = None
    recurrence: str | None = None  # "daily" | "weekly" | "weekdays" | None (one-off)
    recurrence_weekday: int | None = None  # for "weekly": 0=Mon .. 6=Sun
    due_date: date | None = None  # the day this instance is due
    completed: bool = False

    def edit(self, **changes) -> None:
        """Update the given fields in place; unknown keys raise KeyError."""
        valid = {f.name for f in fields(self)}
        for key, value in changes.items():
            if key not in valid:
                raise KeyError(f"Task has no field {key!r}")
            setattr(self, key, value)

    def mark_done(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def is_recurring(self) -> bool:
        """Return True if this task repeats (has a recurrence)."""
        return self.recurrence is not None

    def next_due_date(self, after: date) -> date:
        """Compute the next due date after ``after`` for this task's recurrence.

        Uses ``timedelta`` so month/year rollovers are handled correctly:
        - "daily": the next day (after + 1 day).
        - "weekly": seven days later (after + 7 days).
        - "weekdays": the next Mon–Fri, skipping the weekend.
        Non-recurring tasks just return ``after`` (there is no next occurrence).
        """
        if self.recurrence == "daily":
            return after + timedelta(days=1)
        if self.recurrence == "weekly":
            return after + timedelta(days=7)
        if self.recurrence == "weekdays":
            nxt = after + timedelta(days=1)
            while nxt.weekday() >= 5:  # Sat(5)/Sun(6) -> roll to Monday
                nxt += timedelta(days=1)
            return nxt
        return after

    def next_occurrence(self, new_id: int | None = None) -> "Task":
        """Build the next, uncompleted instance of this recurring task.

        The new task copies every field but resets ``completed`` to False and
        advances ``due_date`` to the next occurrence (relative to this instance's
        due_date, or today if it had none). Raises ValueError if not recurring.
        """
        if not self.is_recurring():
            raise ValueError(f"Task {self.name!r} is not recurring; no next occurrence.")
        base = self.due_date if self.due_date is not None else date.today()
        return Task(
            task_id=new_id if new_id is not None else self.task_id,
            pet_id=self.pet_id,
            name=self.name,
            category=self.category,
            duration=self.duration,
            priority=self.priority,
            preferred_time=self.preferred_time,
            recurrence=self.recurrence,
            recurrence_weekday=self.recurrence_weekday,
            due_date=self.next_due_date(base),
            completed=False,
        )

    def occurs_on(self, day: date) -> bool:
        """Return True if this task is due on ``day`` given its recurrence rule.

        Recurrence handling:
        - ``None`` / "daily": occurs every day.
        - "weekly": occurs only when ``day``'s weekday matches the task's anchor
          weekday (``recurrence_weekday``). If no anchor was set, it defaults to
          occurring — better to show it than to silently hide it.
        - "weekdays": occurs Monday–Friday only.
        A one-off task (``None``) is always eligible; the completion filter, not
        this method, is what removes finished tasks.
        """
        if self.recurrence in _ALWAYS_TODAY:
            return True
        if self.recurrence == "weekly":
            if self.recurrence_weekday is None:
                return True  # no anchor set yet — don't hide it
            return day.weekday() == self.recurrence_weekday
        if self.recurrence == "weekdays":
            return day.weekday() < 5  # Mon(0)–Fri(4)
        return False


@dataclass
class Pet:
    """A pet and the care tasks that belong to it."""

    pet_id: int
    owner_id: int
    name: str
    species: str
    breed: str
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet, stamping it with this pet's id."""
        task.pet_id = self.pet_id
        self.tasks.append(task)

    def edit_task(self, task_id: int, **changes) -> None:
        """Edit an existing task by id. Raises KeyError if not found."""
        self._find(task_id).edit(**changes)

    def remove_task(self, task_id: int) -> None:
        """Remove a task from this pet by id. Raises KeyError if not found."""
        task = self._find(task_id)
        self.tasks.remove(task)

    def list_tasks(self) -> list[Task]:
        """Return this pet's tasks."""
        return self.tasks

    def mark_task_complete(self, task_id: int) -> Task | None:
        """Mark a task done; if it recurs, auto-create and attach the next instance.

        Returns the newly created follow-up Task (for daily/weekly/weekdays
        tasks) or None for one-off tasks. The new instance gets a fresh id
        (max existing id + 1) so ids stay unique within this pet.
        """
        task = self._find(task_id)
        task.mark_done()
        if not task.is_recurring():
            return None
        new_id = max((t.task_id for t in self.tasks), default=0) + 1
        follow_up = task.next_occurrence(new_id=new_id)
        self.tasks.append(follow_up)
        return follow_up

    def _find(self, task_id: int) -> Task:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        raise KeyError(f"Pet {self.name!r} has no task with id {task_id}")


@dataclass
class Owner:
    """A pet owner: manages multiple pets and exposes all their tasks."""

    owner_id: int
    name: str
    available_minutes: int  # time budget for the day
    preferences: dict = field(default_factory=dict)  # e.g., {"start_time": time(8, 0)}
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        pet.owner_id = self.owner_id
        self.pets.append(pet)

    def set_preferences(self, preferences: dict) -> None:
        """Merge new preferences into the existing ones."""
        self.preferences.update(preferences)

    def set_available_time(self, minutes: int) -> None:
        """Set the owner's available time budget for the day."""
        self.available_minutes = minutes

    def get_all_tasks(self) -> list[Task]:
        """Flatten and return tasks across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]


@dataclass
class Schedule:
    """The resulting daily plan: an ordered list of time-slotted tasks."""

    date: date
    entries: list[tuple[time, Task]] = field(default_factory=list)
    reasoning: str = ""
    warnings: list[str] = field(default_factory=list)  # e.g., time-conflict alerts

    def add_entry(self, slot: time, task: Task) -> None:
        """Add a time-slotted task and keep entries ordered by start time."""
        self.entries.append((slot, task))
        self.entries.sort(key=lambda e: e[0])

    def total_time(self) -> int:
        """Return total scheduled minutes."""
        return sum(task.duration for _, task in self.entries)

    def display(self) -> str:
        """Return a human-readable rendering of the plan (and print it)."""
        lines = [f"Daily plan for {self.date.isoformat()}:"]
        if not self.entries:
            lines.append("  (no tasks scheduled)")
        for slot, task in self.entries:
            lines.append(
                f"  {slot.strftime('%H:%M')} — {task.name} "
                f"({task.duration} min) [priority: {task.priority.name.lower()}]"
            )
        if self.reasoning:
            lines.append("")
            lines.append(self.reasoning)
        text = "\n".join(lines)
        print(text)
        return text


class Scheduler:
    """Builds a daily Schedule from candidate tasks and owner constraints.

    Reads constraints (available time, preferences) directly from the Owner so
    there is a single source of truth. Tasks default to the owner's tasks across
    all pets, but can be passed explicitly for testing.
    """

    DEFAULT_START = time(8, 0)

    def __init__(self, plan_date: date, owner: Owner, tasks: list[Task] | None = None):
        self.date = plan_date
        self.owner = owner  # source of available_minutes + preferences
        self.tasks = tasks if tasks is not None else owner.get_all_tasks()
        self._skipped: list[Task] = []  # tasks dropped for lack of time (for explain)
        # Conflicts detected while placing tasks: (task, wanted_time, actual_time).
        self._conflicts: list[tuple[Task, time, time]] = []
        # Cache of the last built pipeline so explain() doesn't recompute it.
        self._eligible: list[Task] = []
        self._chosen: list[Task] = []

    def filter_tasks(
        self,
        tasks: list[Task] | None = None,
        *,
        pet_id: int | None = None,
        pet_name: str | None = None,
        category: str | None = None,
        include_completed: bool = False,
    ) -> list[Task]:
        """Keep only tasks eligible today, with optional pet/status filters.

        By default: not completed and occurring today. Filter to one pet by
        ``pet_id`` or by ``pet_name`` (case-insensitive), narrow to a
        ``category``, or pass ``include_completed=True`` to keep finished tasks
        (e.g. for a review view).
        """
        tasks = self.tasks if tasks is None else tasks

        # Resolve a pet name to its id via the owner so callers can filter by the
        # human-friendly name rather than the numeric id.
        if pet_name is not None:
            match = next(
                (p for p in self.owner.pets if p.name.lower() == pet_name.lower()),
                None,
            )
            pet_id = match.pet_id if match else -1  # -1 matches nothing

        result = []
        for t in tasks:
            if not include_completed and t.completed:
                continue
            if not t.occurs_on(self.date):
                continue
            if pet_id is not None and t.pet_id != pet_id:
                continue
            if category is not None and t.category != category:
                continue
            result.append(t)
        return result

    def sort_tasks(self, tasks: list[Task] | None = None) -> list[Task]:
        """Order tasks by priority (high first), then by shorter duration."""
        tasks = self.tasks if tasks is None else tasks
        return sorted(tasks, key=lambda t: (-int(t.priority), t.duration))

    def sort_by_time(self, tasks: list[Task] | None = None) -> list[Task]:
        """Order tasks chronologically by preferred_time.

        Uses a lambda ``key`` that renders each time as an "HH:MM" string; because
        the hours/minutes are zero-padded, lexicographic string order matches
        clock order. Untimed tasks map to "99:99" so they sink to the end.
        """
        tasks = self.tasks if tasks is None else tasks
        return sorted(
            tasks,
            key=lambda t: t.preferred_time.strftime("%H:%M") if t.preferred_time else "99:99",
        )

    def _fit_to_budget(self, ordered: list[Task]) -> list[Task]:
        """Greedily keep highest-priority tasks that fit the budget; record drops in self._skipped."""
        budget = self.owner.available_minutes
        chosen, used = [], 0
        self._skipped = []
        for task in ordered:
            if used + task.duration <= budget:
                chosen.append(task)
                used += task.duration
            else:
                self._skipped.append(task)
        return chosen

    def resolve_conflicts(self, tasks: list[Task]) -> list[tuple[time, Task]]:
        """Assign non-overlapping, back-to-back clock times, honoring preferred_time when possible.

        Places tasks in preferred-time order so earlier preferences win the slot.
        When a task's preferred_time is already occupied (the cursor has moved
        past it), it is bumped later and recorded in ``self._conflicts`` as
        (task, wanted_time, actual_time) so the owner can be told.
        """
        start = self.owner.preferences.get("start_time", self.DEFAULT_START)
        cursor = datetime.combine(self.date, start)
        placed: list[tuple[time, Task]] = []
        self._conflicts = []
        # Place timed tasks in chronological order so conflicts are detected
        # consistently regardless of the incoming (priority) order.
        for task in self.sort_by_time(tasks):
            if task.preferred_time is not None:
                preferred = datetime.combine(self.date, task.preferred_time)
                if preferred >= cursor:
                    cursor = preferred
                else:
                    # Wanted a slot that's already taken — bump it and flag it.
                    self._conflicts.append(
                        (task, task.preferred_time, cursor.time())
                    )
            placed.append((cursor.time(), task))
            cursor += timedelta(minutes=task.duration)
        return placed

    def detect_conflicts(self, tasks: list[Task] | None = None) -> list[str]:
        """Lightweight conflict check: return warning strings, never raise.

        Looks at each task's *intended* window (preferred_time to preferred_time
        + duration) and flags any pair whose windows overlap — whether they
        belong to the same pet or different pets. Untimed tasks can't collide, so
        they're ignored here. Returns a list of human-readable warnings (empty
        if none), so callers can print them instead of the program crashing.
        """
        tasks = self.tasks if tasks is None else tasks
        timed = [t for t in tasks if t.preferred_time is not None]
        # Sort by the same "HH:MM" lambda key so we only compare neighbors.
        timed.sort(key=lambda t: t.preferred_time.strftime("%H:%M"))

        pet_names = {p.pet_id: p.name for p in self.owner.pets}
        warnings: list[str] = []
        for i, a in enumerate(timed):
            a_start = datetime.combine(self.date, a.preferred_time)
            a_end = a_start + timedelta(minutes=a.duration)
            for b in timed[i + 1:]:
                b_start = datetime.combine(self.date, b.preferred_time)
                if b_start >= a_end:
                    break  # sorted — no later task can overlap `a` either
                same = "same pet" if a.pet_id == b.pet_id else "different pets"
                warnings.append(
                    f"⚠️ Conflict ({same}): '{a.name}' for "
                    f"{pet_names.get(a.pet_id, '?')} at {a.preferred_time.strftime('%H:%M')} "
                    f"overlaps '{b.name}' for {pet_names.get(b.pet_id, '?')} "
                    f"at {b.preferred_time.strftime('%H:%M')}."
                )
        return warnings

    def generate_plan(self) -> Schedule:
        """Run the full pipeline: filter -> sort -> fit budget -> place -> explain."""
        # Build once and cache the pieces so explain() doesn't recompute them.
        self._eligible = self.filter_tasks()
        ordered = self.sort_tasks(self._eligible)
        self._chosen = self._fit_to_budget(ordered)
        placed = self.resolve_conflicts(self._chosen)

        schedule = Schedule(date=self.date)
        for slot, task in placed:
            schedule.add_entry(slot, task)
        schedule.warnings = self.detect_conflicts(self._eligible)
        schedule.reasoning = self.explain()
        return schedule

    def explain(self) -> str:
        """Return a human-readable explanation of the plan's choices.

        Reads the cached pipeline results from the last ``generate_plan`` so the
        explanation always matches the plan (and isn't recomputed).
        """
        budget = self.owner.available_minutes
        eligible, chosen = self._eligible, self._chosen
        used = sum(t.duration for t in chosen)

        parts = [
            f"Considered {len(eligible)} eligible task(s); "
            f"scheduled {len(chosen)} within a {budget}-minute budget "
            f"({used} min used).",
            "Tasks were ordered by priority (high first), then by shorter "
            "duration to fit more in.",
        ]
        if self._skipped:
            names = ", ".join(t.name for t in self._skipped)
            parts.append(f"Skipped for lack of time: {names}.")
        if self._conflicts:
            bumps = ", ".join(
                f"{t.name} ({wanted.strftime('%H:%M')}→{actual.strftime('%H:%M')})"
                for t, wanted, actual in self._conflicts
            )
            parts.append(f"Moved to avoid overlap: {bumps}.")
        return " ".join(parts)

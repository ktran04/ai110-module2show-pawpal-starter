"""Tests for PawPal+ core behaviors.

Covers the logic that actually makes decisions: sorting, recurrence,
budget-fitting, and conflict detection/resolution. Dates are fixed so the
suite is deterministic (2026-07-06 is a Monday, matching the README sample).
"""

from datetime import date, time

from pawpal_system import Owner, Pet, Task, Priority, Scheduler

# A fixed Monday, so weekday-dependent logic is deterministic.
PLAN_DATE = date(2026, 7, 6)  # Monday


def make_task(task_id=1, name="Walk"):
    """Helper: build a simple task for tests."""
    return Task(task_id=task_id, pet_id=1, name=name, category="walk",
                duration=20, priority=Priority.HIGH)


def make_scheduler(tasks, available_minutes=120):
    """Helper: an Owner with one Pet holding ``tasks``, plus a Scheduler.

    The pet is registered so Scheduler.detect_conflicts can resolve pet names,
    and available_minutes drives the budget for generate_plan tests.
    """
    owner = Owner(owner_id=1, name="Jordan", available_minutes=available_minutes)
    pet = Pet(pet_id=1, owner_id=1, name="Biscuit", species="dog", breed="Golden")
    for t in tasks:
        pet.add_task(t)
    owner.add_pet(pet)
    return Scheduler(PLAN_DATE, owner)


# --- Starter tests --------------------------------------------------------

def test_mark_done_changes_status():
    """Calling mark_done() flips a task from not-completed to completed."""
    task = make_task()
    assert task.completed is False  # starts incomplete

    task.mark_done()

    assert task.completed is True


def test_add_task_increases_pet_task_count():
    """Adding a task to a Pet grows that pet's task list by one."""
    pet = Pet(pet_id=1, owner_id=1, name="Biscuit", species="dog", breed="Golden")
    assert len(pet.tasks) == 0  # starts with no tasks

    pet.add_task(make_task())

    assert len(pet.tasks) == 1


# --- Sorting correctness --------------------------------------------------

def test_sort_by_time_is_chronological():
    """sort_by_time returns tasks in clock order regardless of input order."""
    tasks = [
        Task(1, 1, "Evening", "walk", 20, Priority.LOW, preferred_time=time(18, 0)),
        Task(2, 1, "Morning", "walk", 20, Priority.LOW, preferred_time=time(8, 0)),
        Task(3, 1, "Noon", "walk", 20, Priority.LOW, preferred_time=time(12, 0)),
    ]
    scheduler = make_scheduler(tasks)

    names = [t.name for t in scheduler.sort_by_time(tasks)]

    assert names == ["Morning", "Noon", "Evening"]


def test_sort_by_time_puts_untimed_tasks_last():
    """Tasks without a preferred_time sink to the end (mapped to '99:99')."""
    tasks = [
        Task(1, 1, "Untimed", "walk", 20, Priority.LOW),  # no preferred_time
        Task(2, 1, "Morning", "walk", 20, Priority.LOW, preferred_time=time(8, 0)),
    ]
    scheduler = make_scheduler(tasks)

    names = [t.name for t in scheduler.sort_by_time(tasks)]

    assert names == ["Morning", "Untimed"]


def test_sort_tasks_by_priority_then_duration():
    """High priority first; within a priority, shorter duration wins the tie."""
    tasks = [
        Task(1, 1, "LongHigh", "walk", 40, Priority.HIGH),
        Task(2, 1, "Low", "walk", 10, Priority.LOW),
        Task(3, 1, "ShortHigh", "walk", 10, Priority.HIGH),
    ]
    scheduler = make_scheduler(tasks)

    names = [t.name for t in scheduler.sort_tasks(tasks)]

    assert names == ["ShortHigh", "LongHigh", "Low"]


# --- Recurrence logic -----------------------------------------------------

def test_complete_daily_task_creates_next_day_instance():
    """Completing a daily task auto-creates the next instance, due the next day."""
    pet = Pet(pet_id=1, owner_id=1, name="Biscuit", species="dog", breed="Golden")
    pet.add_task(Task(1, 1, "Walk", "walk", 20, Priority.HIGH,
                      recurrence="daily", due_date=PLAN_DATE))

    follow_up = pet.mark_task_complete(1)

    assert follow_up is not None
    assert follow_up.completed is False
    assert follow_up.due_date == date(2026, 7, 7)  # the following day
    assert follow_up.task_id != 1  # fresh id
    assert len(pet.tasks) == 2  # original (done) + new instance


def test_complete_one_off_task_creates_nothing():
    """A non-recurring task just completes; no follow-up is spawned."""
    pet = Pet(pet_id=1, owner_id=1, name="Biscuit", species="dog", breed="Golden")
    pet.add_task(Task(1, 1, "Vet visit", "meds", 30, Priority.HIGH))  # recurrence=None

    follow_up = pet.mark_task_complete(1)

    assert follow_up is None
    assert len(pet.tasks) == 1
    assert pet.tasks[0].completed is True


def test_weekdays_recurrence_skips_the_weekend():
    """A 'weekdays' task due Friday rolls to Monday, skipping Sat/Sun."""
    friday = date(2026, 7, 10)  # Friday
    task = Task(1, 1, "Meds", "meds", 10, Priority.HIGH, recurrence="weekdays")

    assert task.next_due_date(friday) == date(2026, 7, 13)  # Monday


def test_next_occurrence_on_non_recurring_task_raises():
    """Asking a one-off task for its next occurrence is an error."""
    task = Task(1, 1, "Vet visit", "meds", 30, Priority.HIGH)  # not recurring
    try:
        task.next_occurrence()
        assert False, "expected ValueError for non-recurring task"
    except ValueError:
        pass


# --- Conflict detection & resolution --------------------------------------

def test_detect_conflicts_flags_duplicate_times():
    """Two tasks at the exact same time produce a conflict warning."""
    tasks = [
        Task(1, 1, "Feeding", "feeding", 10, Priority.HIGH, preferred_time=time(8, 30)),
        Task(2, 1, "Meds", "meds", 10, Priority.HIGH, preferred_time=time(8, 30)),
    ]
    scheduler = make_scheduler(tasks)

    warnings = scheduler.detect_conflicts(tasks)

    assert len(warnings) == 1
    assert "Conflict" in warnings[0]


def test_adjacent_tasks_do_not_conflict():
    """A task ending exactly when the next begins is not an overlap."""
    tasks = [
        Task(1, 1, "A", "walk", 30, Priority.HIGH, preferred_time=time(8, 0)),   # 8:00-8:30
        Task(2, 1, "B", "walk", 15, Priority.HIGH, preferred_time=time(8, 30)),  # 8:30-8:45
    ]
    scheduler = make_scheduler(tasks)

    assert scheduler.detect_conflicts(tasks) == []


def test_resolve_conflicts_bumps_the_second_task():
    """When two tasks want the same slot, the second is placed back-to-back."""
    tasks = [
        Task(1, 1, "Feeding", "feeding", 10, Priority.HIGH, preferred_time=time(8, 30)),
        Task(2, 1, "Meds", "meds", 10, Priority.HIGH, preferred_time=time(8, 30)),
    ]
    scheduler = make_scheduler(tasks)

    placed = scheduler.resolve_conflicts(tasks)
    slots = [slot for slot, _ in placed]

    assert slots == [time(8, 30), time(8, 40)]  # second bumped 10 min later
    assert len(scheduler._conflicts) == 1  # the bump was recorded for explain()


# --- Budget fitting -------------------------------------------------------

def test_zero_budget_schedules_nothing():
    """With no available minutes, the plan is empty and doesn't crash."""
    tasks = [Task(1, 1, "Walk", "walk", 20, Priority.HIGH)]
    scheduler = make_scheduler(tasks, available_minutes=0)

    schedule = scheduler.generate_plan()

    assert schedule.entries == []


def test_budget_fills_lower_priority_when_higher_does_not_fit():
    """Greedy fit: a high-priority task too big to fit is skipped, and a
    smaller lower-priority task that DOES fit still gets scheduled."""
    tasks = [
        Task(1, 1, "BigHigh", "walk", 40, Priority.HIGH),  # too big for 30-min budget
        Task(2, 1, "SmallLow", "walk", 20, Priority.LOW),  # fits
    ]
    scheduler = make_scheduler(tasks, available_minutes=30)

    schedule = scheduler.generate_plan()
    scheduled = [task.name for _, task in schedule.entries]

    assert scheduled == ["SmallLow"]


# --- Empty / no-op cases --------------------------------------------------

def test_pet_with_no_tasks_produces_empty_plan():
    """An owner whose pet has no tasks yields an empty schedule, no error."""
    scheduler = make_scheduler([])

    schedule = scheduler.generate_plan()

    assert schedule.entries == []
    assert "(no tasks scheduled)" in schedule.display()

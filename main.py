"""PawPal+ demo script.

Builds a small owner/pets/tasks world and exercises the "smart" scheduling
logic in the terminal: sorting (by priority and by time), filtering (by status
and by pet), recurring-task auto-generation, and conflict detection.

Run with:  python main.py
"""

import sys
from datetime import date, time

from pawpal_system import Owner, Pet, Task, Priority, Scheduler

# The plan uses box-drawing / emoji characters; make sure the Windows terminal
# (default cp1252) can print them instead of crashing on UnicodeEncodeError.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def build_world() -> Owner:
    """Create an owner with two pets and a handful of care tasks.

    Tasks are intentionally added *out of order* (by both time and priority) so
    the sorting methods have something real to reorder. Two tasks share the
    8:30 slot so the conflict detector has something to catch.
    """
    owner = Owner(
        owner_id=1,
        name="Jordan",
        available_minutes=120,  # two hours of care time today
        preferences={"start_time": time(8, 0)},
    )

    biscuit = Pet(pet_id=1, owner_id=1, name="Biscuit", species="dog", breed="Golden Retriever")
    mochi = Pet(pet_id=2, owner_id=1, name="Mochi", species="cat", breed="Tabby")
    owner.add_pet(biscuit)
    owner.add_pet(mochi)

    # Added out of order on purpose (evening play first, morning walk last).
    biscuit.add_task(Task(3, 1, "Training", "enrichment", 20, Priority.MEDIUM))
    mochi.add_task(Task(6, 2, "Play time", "enrichment", 20, Priority.LOW, preferred_time=time(18, 0)))
    biscuit.add_task(
        Task(2, 1, "Feeding", "feeding", 10, Priority.HIGH,
             preferred_time=time(8, 30), recurrence="daily")
    )
    mochi.add_task(Task(5, 2, "Litter cleanup", "grooming", 15, Priority.MEDIUM))
    # Conflict on purpose: Mochi's feeding wants 8:30 too, colliding with Biscuit's.
    mochi.add_task(Task(4, 2, "Feeding", "feeding", 10, Priority.HIGH, preferred_time=time(8, 30)))
    biscuit.add_task(
        Task(1, 1, "Morning walk", "walk", 30, Priority.HIGH,
             preferred_time=time(8, 0), recurrence="daily")
    )

    return owner


def demo_sorting_and_filtering(owner: Owner) -> None:
    """Show the sort_by_time / sort_tasks / filter_tasks methods working."""
    scheduler = Scheduler(date.today(), owner)
    all_tasks = owner.get_all_tasks()

    print("\n--- Tasks as entered (out of order) ---")
    for t in all_tasks:
        pref = t.preferred_time.strftime("%H:%M") if t.preferred_time else "  —  "
        print(f"  {pref}  {t.name:<14} [{t.priority.name}]")

    print("\n--- Sorted by TIME (lambda key on 'HH:MM') ---")
    for t in scheduler.sort_by_time(all_tasks):
        pref = t.preferred_time.strftime("%H:%M") if t.preferred_time else "  —  "
        print(f"  {pref}  {t.name:<14} [{t.priority.name}]")

    print("\n--- Sorted by PRIORITY (high first, then shorter) ---")
    for t in scheduler.sort_tasks(all_tasks):
        print(f"  {t.priority.name:<6}  {t.name:<14} ({t.duration} min)")

    print("\n--- Filtered to Mochi only (by pet name) ---")
    for t in scheduler.filter_tasks(all_tasks, pet_name="Mochi"):
        print(f"  {t.name:<14} ({t.category})")

    print("\n--- Filtered to incomplete only (default) vs. including completed ---")
    incomplete = scheduler.filter_tasks(all_tasks)
    everything = scheduler.filter_tasks(all_tasks, include_completed=True)
    print(f"  incomplete today: {len(incomplete)} | including completed: {len(everything)}")


def demo_recurring(owner: Owner) -> None:
    """Complete a daily task and show the next instance is auto-created."""
    biscuit = owner.pets[0]
    walk = next(t for t in biscuit.tasks if t.name == "Morning walk")

    print("\n--- Recurring auto-generation ---")
    print(f"  Before: Biscuit has {len(biscuit.tasks)} task(s).")
    follow_up = biscuit.mark_task_complete(walk.task_id)
    print(f"  Completed '{walk.name}' (recurrence={walk.recurrence}).")
    if follow_up:
        print(
            f"  Auto-created next '{follow_up.name}' due {follow_up.due_date} "
            f"(id {follow_up.task_id}, completed={follow_up.completed})."
        )
    print(f"  After:  Biscuit has {len(biscuit.tasks)} task(s).")


def print_schedule(owner: Owner, schedule) -> None:
    """Print today's schedule in a clean, aligned, readable format."""
    pet_names = {pet.pet_id: pet.name for pet in owner.pets}
    width = 60

    print("=" * width)
    print(f"  TODAY'S SCHEDULE  ({schedule.date.strftime('%A, %B %d, %Y')})".upper())
    print(f"  Caregiver: {owner.name}")
    print("=" * width)

    if not schedule.entries:
        print("  No tasks scheduled today.")
    else:
        for slot, task in schedule.entries:
            pet = pet_names.get(task.pet_id, "?")
            detail = f"({pet}, {task.duration} min)"
            print(
                f"  {slot.strftime('%H:%M')}  │  {task.name:<16}"
                f"  {detail:<22}  [{task.priority.name}]"
            )

    print("-" * width)
    print(f"  Total scheduled time: {schedule.total_time()} / {owner.available_minutes} min")
    print("=" * width)

    if schedule.warnings:
        print("\nConflict warnings:")
        for w in schedule.warnings:
            print(f"  {w}")

    if schedule.reasoning:
        print("\nWhy this plan:")
        print(f"  {schedule.reasoning}")


def main() -> None:
    owner = build_world()

    # Step 1 & 2: sorting and filtering.
    demo_sorting_and_filtering(owner)

    # Step 4: build the plan (conflict detection runs inside generate_plan).
    schedule = Scheduler(date.today(), owner).generate_plan()
    print()
    print_schedule(owner, schedule)

    # Step 3: recurring auto-generation.
    demo_recurring(owner)


if __name__ == "__main__":
    main()

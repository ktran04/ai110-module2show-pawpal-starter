"""Basic tests for PawPal+ core behaviors."""

from pawpal_system import Pet, Task, Priority


def make_task(task_id=1, name="Walk"):
    """Helper: build a simple task for tests."""
    return Task(task_id=task_id, pet_id=1, name=name, category="walk",
                duration=20, priority=Priority.HIGH)


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

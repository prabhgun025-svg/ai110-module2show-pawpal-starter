from datetime import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pawpal_system import Pet, Priority, RecurrenceType, Task


def test_mark_complete_updates_task_status():
    task = Task(
        task_id="task_001",
        name="Morning walk",
        description="Take the dog for a walk",
        duration_minutes=20,
        priority=Priority.HIGH,
        recurrence=RecurrenceType.DAILY,
        preferred_time=time(hour=8, minute=0),
        deadline=time(hour=9, minute=0),
    )

    assert task.is_completed is False

    task.mark_complete()

    assert task.is_completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet(
        pet_id="pet_001",
        name="Buddy",
        species="dog",
        breed="Labrador",
        age=3,
        weight=25.5,
        medical_notes="Healthy",
    )

    task = Task(
        task_id="task_002",
        name="Feed Buddy",
        description="Provide dinner",
        duration_minutes=10,
        priority=Priority.MEDIUM,
        recurrence=RecurrenceType.DAILY,
        preferred_time=time(hour=18, minute=0),
        deadline=time(hour=19, minute=0),
    )

    assert len(pet.tasks) == 0

    pet.add_task(task)

    assert len(pet.tasks) == 1

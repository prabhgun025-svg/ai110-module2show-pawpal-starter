"""
PawPal Pet Care App - Core Domain Model
Manages pet owner information, pet profiles, task scheduling, and daily plan generation.
"""

from enum import Enum
from datetime import datetime, date, time, timedelta
from typing import List, Optional
from dataclasses import dataclass, field


# ============================================================================
# ENUMERATIONS
# ============================================================================

class Priority(Enum):
    """Task priority levels for scheduling."""
    HIGH = 3
    MEDIUM = 2
    LOW = 1
    
    def urgency_score(self) -> int:
        """Return numeric urgency score for sorting."""
        return self.value


class RecurrenceType(Enum):
    """Task recurrence patterns."""
    DAILY = "daily"
    WEEKLY = "weekly"
    ONE_TIME = "one_time"


# ============================================================================
# TASK CLASS
# ============================================================================

@dataclass
class Task:
    """
    Represents a single pet care task - the atomic scheduling unit.
    Everything the scheduler reasons about comes from here.
    """
    task_id: str
    name: str
    description: str
    duration_minutes: int
    priority: Priority
    recurrence: RecurrenceType
    preferred_time: time
    deadline: time
    is_completed: bool = False
    pet: Optional['Pet'] = None

    def set_priority(self, priority: Priority) -> None:
        """Update task priority."""
        self.priority = priority
    
    def set_duration(self, minutes: int) -> None:
        """Update task duration in minutes."""
        if minutes < 0:
            raise ValueError("Duration must be non-negative")
        self.duration_minutes = minutes
    
    def set_preferred_time(self, time_: time) -> None:
        """Update preferred execution time."""
        self.preferred_time = time_
    
    def is_overdue(self) -> bool:
        """Check if task deadline has passed."""
        if self.is_completed:
            return False
        return datetime.now().time() > self.deadline
    
    def conflicts_with(self, other: 'Task') -> bool:
        """Detect if this task overlaps with another in preferred time slots."""
        if self.task_id == other.task_id:
            return False
        self_start = self.preferred_time.hour * 60 + self.preferred_time.minute
        self_end = self_start + self.duration_minutes
        other_start = other.preferred_time.hour * 60 + other.preferred_time.minute
        other_end = other_start + other.duration_minutes
        return self_start < other_end and other_start < self_end
    
    def toggle_complete(self) -> None:
        """Mark task as complete or incomplete."""
        self.is_completed = not self.is_completed

    def mark_complete(self) -> None:
        """Mark task as complete."""
        self.is_completed = True


# ============================================================================
# PET CLASS
# ============================================================================

@dataclass
class Pet:
    """
    Represents an individual pet with profile and task management.
    """
    pet_id: str
    name: str
    species: str
    breed: str
    age: int
    weight: float
    medical_notes: str
    tasks: List[Task] = field(default_factory=list)
    
    def add_task(self, task: Task) -> None:
        """Add a task to this pet's task list."""
        if any(existing.task_id == task.task_id for existing in self.tasks):
            raise ValueError(f"Task with id {task.task_id} already exists for pet {self.name}")
        task.pet = self
        self.tasks.append(task)
    
    def edit_task(self, task_id: str, updated_task: Task) -> None:
        """Update an existing task."""
        for index, existing in enumerate(self.tasks):
            if existing.task_id == task_id:
                updated_task.pet = self
                self.tasks[index] = updated_task
                return
        raise ValueError(f"Task {task_id} not found for pet {self.name}")
    
    def remove_task(self, task_id: str) -> None:
        """Remove a task by ID."""
        for index, existing in enumerate(self.tasks):
            if existing.task_id == task_id:
                existing.pet = None
                del self.tasks[index]
                return
        raise ValueError(f"Task {task_id} not found for pet {self.name}")
    
    def get_tasks(self) -> List[Task]:
        """Return all tasks for this pet."""
        return list(self.tasks)
    
    def get_tasks_by_priority(self, priority: Priority) -> List[Task]:
        """Return tasks filtered by priority level."""
        return [task for task in self.tasks if task.priority == priority]


# ============================================================================
# PET OWNER CLASS
# ============================================================================

@dataclass
class PetOwner:
    """
    Top-level identity in the system - everything else belongs to the owner.
    """
    owner_id: str
    name: str
    email: str
    phone: str
    address: str
    pets: List[Pet] = field(default_factory=list)
    
    def add_pet(self, pet: Pet) -> None:
        """Add a pet to the owner's collection."""
        if any(existing.pet_id == pet.pet_id for existing in self.pets):
            raise ValueError(f"Pet with id {pet.pet_id} already exists")
        self.pets.append(pet)
    
    def remove_pet(self, pet_id: str) -> None:
        """Remove a pet by ID."""
        for index, pet in enumerate(self.pets):
            if pet.pet_id == pet_id:
                del self.pets[index]
                return
        raise ValueError(f"Pet {pet_id} not found")
    
    def get_pets(self) -> List[Pet]:
        """Return all pets owned by this owner."""
        return list(self.pets)
    
    def get_all_tasks(self) -> List[Task]:
        """Return all tasks across every pet."""
        tasks: List[Task] = []
        for pet in self.pets:
            tasks.extend(pet.get_tasks())
        return tasks
    
    def find_pet_by_task_id(self, task_id: str) -> Optional[Pet]:
        """Look up the pet that owns a given task."""
        for pet in self.pets:
            for task in pet.tasks:
                if task.task_id == task_id:
                    return pet
        return None
    
    def update_contact_info(self, email: str, phone: str, address: str) -> None:
        """Update owner's contact information."""
        self.email = email
        self.phone = phone
        self.address = address
    
    def generate_daily_schedule(self) -> 'Schedule':
        """Build the owner's daily schedule using the scheduler."""
        scheduler = Scheduler(self)
        return scheduler.build_daily_schedule()


# ============================================================================
# SCHEDULER CLASS
# ============================================================================

@dataclass
class Scheduler:
    """
    The brain of the PawPal schedule system.
    Retrieves tasks from the owner and produces a daily plan.
    """
    owner: PetOwner
    schedule_date: date = field(default_factory=date.today)
    
    def retrieve_all_tasks(self) -> List[Task]:
        """Collect tasks from every pet owned by the owner."""
        return self.owner.get_all_tasks()
    
    def retrieve_tasks_by_priority(self, priority: Priority) -> List[Task]:
        """Return tasks across pets filtered by priority."""
        return [task for task in self.retrieve_all_tasks() if task.priority == priority]
    
    def build_daily_schedule(self) -> Schedule:
        """Build a schedule for the owner using all available task data."""
        schedule_id = f"{self.owner.owner_id}-{self.schedule_date.isoformat()}"
        schedule = Schedule(schedule_id=schedule_id, date=self.schedule_date, owner=self.owner)
        schedule.generate(self.retrieve_all_tasks())
        return schedule


# ============================================================================
# SCHEDULE SLOT CLASS
# ============================================================================

@dataclass
class ScheduleSlot:
    """
    Represents a single scheduled task slot in the daily plan.
    Stores both the what (task) and the why (reasoning note).
    """
    task: Task
    start_time: time
    end_time: time
    pet: Pet
    reasoning_note: str
    
    def get_duration(self) -> int:
        """Return slot duration in minutes."""
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        return max(0, end_minutes - start_minutes)
    
    def overlaps_with(self, other: 'ScheduleSlot') -> bool:
        """Check if this slot overlaps with another in time."""
        self_start = self.start_time.hour * 60 + self.start_time.minute
        self_end = self.end_time.hour * 60 + self.end_time.minute
        other_start = other.start_time.hour * 60 + other.start_time.minute
        other_end = other.end_time.hour * 60 + other.end_time.minute
        return self_start < other_end and other_start < self_end
    
    def to_display_string(self) -> str:
        """Return formatted string for display to user."""
        time_str = f"{self.start_time.strftime('%H:%M')}"
        task_str = f"{self.pet.name} - {self.task.name}"
        details_str = f"Duration: {self.task.duration_minutes}m | Priority: {self.task.priority.name}"
        deadline_str = f"Deadline: {self.task.deadline.strftime('%H:%M')}"
        
        return f"{time_str} ║ {task_str}\n       ║ {details_str} | {deadline_str}\n       ║ {self.task.description}\n       ║"


# ============================================================================
# SCHEDULE CLASS
# ============================================================================

@dataclass
class Schedule:
    """
    Represents the generated daily plan with all scheduled slots and skipped tasks.
    """
    schedule_id: str
    date: date
    owner: PetOwner
    slots: List[ScheduleSlot] = field(default_factory=list)
    skipped_tasks: List[Task] = field(default_factory=list)
    total_minutes: int = 0
    generated_at: Optional[datetime] = None
    
    def _minutes_to_time(self, minutes: int) -> time:
        """Convert minutes since midnight into a time object."""
        hours = minutes // 60
        minutes = minutes % 60
        return time(hour=hours, minute=minutes)
    
    def _find_next_available_start(self, preferred_start: time, duration: int, cutoff: time) -> Optional[time]:
        """Find the next free start time for a task before the cutoff time."""
        candidate_minutes = preferred_start.hour * 60 + preferred_start.minute
        cutoff_minutes = cutoff.hour * 60 + cutoff.minute
        while candidate_minutes + duration <= cutoff_minutes:
            candidate_start = self._minutes_to_time(candidate_minutes)
            candidate_end = self._minutes_to_time(candidate_minutes + duration)
            overlap = False
            for slot in self.slots:
                if not (candidate_end <= slot.start_time or candidate_start >= slot.end_time):
                    overlap = True
                    break
            if not overlap:
                return candidate_start
            candidate_minutes += 5
        return None
    
    def _format_task_reason(self, task: Task, scheduled_time: time, moved: bool) -> str:
        """Return a human-readable reason for the chosen task timing."""
        if task.is_completed:
            return "Completed task - no scheduling required"
        return (
            "Scheduled at preferred time"
            if not moved
            else "Preferred time conflicted, moved to next available slot"
        )
    
    def generate(self, tasks: List[Task]) -> None:
        """Generate the daily schedule from a list of tasks."""
        self.slots = []
        self.skipped_tasks = []
        self.total_minutes = 0
        self.generated_at = datetime.now()

        work_end = time(hour=22, minute=0)
        sorted_tasks = sorted(
            [task for task in tasks if not task.is_completed],
            key=lambda task: (
                -task.priority.urgency_score(),
                task.deadline.hour * 60 + task.deadline.minute,
                task.preferred_time.hour * 60 + task.preferred_time.minute,
            ),
        )

        for task in sorted_tasks:
            task_pet = task.pet or self.owner.find_pet_by_task_id(task.task_id)
            if task_pet is None:
                self.skipped_tasks.append(task)
                continue
            proposed_start = task.preferred_time
            if any(task.conflicts_with(existing.task) for existing in self.slots):
                proposed_start = self._find_next_available_start(proposed_start, task.duration_minutes, work_end)
            else:
                conflict = any(
                    not (
                        self._minutes_to_time(proposed_start.hour * 60 + proposed_start.minute + task.duration_minutes) <= slot.start_time
                        or proposed_start >= slot.end_time
                    )
                    for slot in self.slots
                )
                if conflict:
                    proposed_start = self._find_next_available_start(proposed_start, task.duration_minutes, work_end)

            if proposed_start is None:
                self.skipped_tasks.append(task)
                continue

            proposed_end_minutes = proposed_start.hour * 60 + proposed_start.minute + task.duration_minutes
            proposed_end = self._minutes_to_time(proposed_end_minutes)
            if proposed_end > work_end:
                self.skipped_tasks.append(task)
                continue

            moved = proposed_start != task.preferred_time
            reasoning = self._format_task_reason(task, proposed_start, moved)
            slot = ScheduleSlot(
                task=task,
                start_time=proposed_start,
                end_time=proposed_end,
                pet=task_pet,
                reasoning_note=reasoning,
            )
            self.add_slot(slot)

    def add_slot(self, slot: ScheduleSlot) -> None:
        """Add a schedule slot to the plan."""
        self.slots.append(slot)
        self.slots.sort(key=lambda s: (s.start_time.hour * 60 + s.start_time.minute))
        self.total_minutes = sum(item.get_duration() for item in self.slots)
    
    def remove_slot(self, slot_id: str) -> None:
        """Remove a slot from the plan."""
        for index, slot in enumerate(self.slots):
            if slot.task.task_id == slot_id:
                del self.slots[index]
                self.total_minutes = sum(item.get_duration() for item in self.slots)
                return
        raise ValueError(f"Slot with task id {slot_id} not found")
    
    def display(self) -> str:
        """Return formatted string representation of the entire schedule."""
        date_str = self.date.strftime('%B %d, %Y') if self.date else 'Unknown Date'
        lines = [
            "┌─── TODAY'S SCHEDULE " + ("─" * (46 - len(date_str))) + f"{date_str} ───┐",
            "│" + " " * 60 + "│",
        ]
        
        if not self.slots:
            lines.append("│  No scheduled tasks" + " " * 40 + "│")
        else:
            for slot in self.slots:
                slot_lines = slot.to_display_string().split("\n")
                for line in slot_lines:
                    lines.append("│ " + line + (" " * (58 - len(line))) + "│")

        if self.skipped_tasks:
            lines.append("│" + " " * 60 + "│")
            lines.append("│ Skipped Tasks:" + " " * 45 + "│")
            for task in self.skipped_tasks:
                pet_name = task.pet.name if task.pet else 'Unknown pet'
                task_line = f"  • {task.name} ({task.duration_minutes}m) - {pet_name}"
                lines.append("│ " + task_line + (" " * (58 - len(task_line))) + "│")
        
        lines.append("│" + " " * 60 + "│")
        lines.append("└" + "─" * 60 + "┘")
        return "\n".join(lines)
    
    def get_reasoning(self) -> List[str]:
        """Return list of reasoning notes for why slots were scheduled as they are."""
        return [slot.reasoning_note for slot in self.slots]
    
    def get_skipped_tasks(self) -> List[Task]:
        """Return tasks that didn't fit in the schedule."""
        return list(self.skipped_tasks)
    
    def validate(self) -> bool:
        """Check if the schedule is valid (no overlaps, all slots properly formed)."""
        if any(slot.get_duration() <= 0 for slot in self.slots):
            return False
        for i, current in enumerate(self.slots):
            for other in self.slots[i + 1:]:
                if current.overlaps_with(other):
                    return False
        calculated_total = sum(slot.get_duration() for slot in self.slots)
        return calculated_total == self.total_minutes


# ============================================================================
# TEST FIXTURE CLASS
# ============================================================================

class ScheduleTest:
    """
    Test fixture with pre-built objects and helper methods.
    Implements four core test groups: priority ordering, conflict detection,
    duration fitting, and reasoning output.
    """
    
    def __init__(self):
        """Initialize test fixture."""
        self.test_owner: Optional[PetOwner] = None
        self.test_pet: Optional[Pet] = None
        self.test_schedule: Optional[Schedule] = None
    
    def setUp(self) -> None:
        """Set up fresh test objects before each test."""
        self.test_owner = PetOwner(owner_id="owner1", name="Alex", email="alex@example.com", phone="000-000-0000", address="123 Main St")
        self.test_pet = Pet(pet_id="pet1", name="Buddy", species="Dog", breed="Mixed", age=4, weight=22.5, medical_notes="None")
        self.test_owner.add_pet(self.test_pet)
        self.test_schedule = self.test_owner.generate_daily_schedule()
    
    def tearDown(self) -> None:
        """Clear state after each test."""
        self.test_owner = None
        self.test_pet = None
        self.test_schedule = None
    
    def build_task(self, name: str, priority: Priority, duration: int) -> Task:
        """Helper to quickly construct a task for testing."""
        return Task(
            task_id=name.lower().replace(" ", "_"),
            name=name,
            description=f"{name} for pet",
            duration_minutes=duration,
            priority=priority,
            recurrence=RecurrenceType.ONE_TIME,
            preferred_time=time(hour=9, minute=0),
            deadline=time(hour=18, minute=0),
        )
    
    def test_priority_ordering(self) -> None:
        """Verify tasks are scheduled in priority order."""
        task_high = self.build_task("High Priority", Priority.HIGH, 30)
        task_medium = self.build_task("Medium Priority", Priority.MEDIUM, 30)
        self.test_pet.add_task(task_medium)
        self.test_pet.add_task(task_high)
        schedule = self.test_owner.generate_daily_schedule()
        first_slot = schedule.slots[0]
        assert first_slot.task.priority == Priority.HIGH
    
    def test_conflict_detection(self) -> None:
        """Verify the scheduler detects and handles conflicting tasks."""
        task_one = self.build_task("Morning Walk", Priority.MEDIUM, 60)
        task_two = self.build_task("Vet Call", Priority.MEDIUM, 60)
        task_two.preferred_time = time(hour=9, minute=30)
        self.test_pet.add_task(task_one)
        self.test_pet.add_task(task_two)
        schedule = self.test_owner.generate_daily_schedule()
        assert len(schedule.slots) == 2
        assert schedule.slots[0].end_time <= schedule.slots[1].start_time
    
    def test_duration_fitting(self) -> None:
        """Verify tasks that don't fit are added to skipped_tasks."""
        long_task = self.build_task("Marathon Grooming", Priority.LOW, 900)
        self.test_pet.add_task(long_task)
        schedule = self.test_owner.generate_daily_schedule()
        assert long_task in schedule.skipped_tasks
    
    def test_reasoning_output(self) -> None:
        """Verify reasoning notes explain why slots were scheduled and tasks skipped."""
        task_one = self.build_task("Training", Priority.HIGH, 30)
        task_two = self.build_task("Vet Call", Priority.HIGH, 30)
        task_two.preferred_time = time(hour=9, minute=15)
        self.test_pet.add_task(task_one)
        self.test_pet.add_task(task_two)
        schedule = self.test_owner.generate_daily_schedule()
        notes = schedule.get_reasoning()
        assert any("Preferred time conflicted" in note for note in notes)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("PawPal Pet Care App - Core Domain Model Loaded")

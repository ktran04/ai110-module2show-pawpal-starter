# PawPal+ Project Reflection

## 1. System Design

### Step 1 — Three Core Actions
A user (pet owner) should be able to:

1. **Add owner and pet info** — Enter their own name and available time, then register a pet with details like name, species, and breed.
2. **Add or edit care tasks** — Create tasks such as walks, feeding, meds, or grooming for a pet, giving each a duration and a priority (and edit or remove them later).
3. **Generate a daily plan** — Ask the app to build a schedule for the day that fits the owner's available time and task priorities, and explains why it chose that plan.

### Step 2 — Building Blocks (Objects)

**Owner**
- *Attributes:* `owner_id`, `name`, `available_minutes` (time budget for the day),`preferences` (e.g., preferred start time, quiet hours)
- *Methods:* `add_pet(pet)`, `set_preferences(...)`, `set_available_time(minutes)`

**Pet**
- *Attributes:* `pet_id`, `owner_id`, `name`, `species`, `breed`, `tasks` (list of Task)
- *Methods:* `add_task(task)`, `edit_task(task_id, ...)`, `remove_task(task_id)`,
  `list_tasks()`

**Task**
- *Attributes:* `task_id`, `pet_id`, `name`, `category` (walk/feeding/meds/etc.),
  `duration` (minutes), `priority` (high/medium/low), `preferred_time` (optional),
  `recurrence` (e.g., daily/weekly), `completed` (bool)
- *Methods:* `edit(...)`, `mark_done()`, `is_recurring()`

**Scheduler** (builds the plan)
- *Attributes:* `date`, `constraints` (available time, preferences), `tasks` (candidate tasks)
- *Methods:* `sort_tasks()` (by priority, then duration), `filter_tasks()` (drop tasks that
  don't fit the time budget), `resolve_conflicts()` (handle overlapping time slots),
  `generate_plan()` → returns a `Schedule`, `explain()` (reasoning for the plan)

**Schedule** (the resulting daily plan)
- *Attributes:* `date`, `entries` (ordered list of time-slotted tasks), `reasoning`
- *Methods:* `add_entry(time, task)`, `total_time()`, `display()`

*Relationships:* An **Owner** has one or more **Pets**; a **Pet** has many **Tasks**; the
**Scheduler** takes an Owner's constraints plus a Pet's Tasks and produces a **Schedule**.


**a. Initial design**

- Briefly describe your initial UML design.

My design contains five main classes: 'Owner', 'Pet', 'Task', 'Scheduler', and 'Schedule'.

- Owner: stores the pet owner's basic information, daily time budget, and preferences, and it can manage the pets linked to that owner.
- Pet: represents an individual pet and keeps track of that pet's care tasks.
- Task: represents one care activity, such as feeding, walking, medication, or grooming, including its duration, priority, and optional preferred time.
- Scheduler: takes the owner's constraints and the available tasks, then sorts, filters, and organizes them into a daily plan.
- :Schedule: stores the final plan for the day, including the ordered task entries and the reasoning behind the schedule.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Yes, I added a get_all_tasks to link owner to task. Before, owner would know to complete 5 tasks but would not know what all 5 of them are at the same time. Now, that links the 2 objects completely.
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

My scheduler considers three constraints:

1. **Time budget** — the owner only has so much time in a day to schedule tasks. The scheduler will not plan more task time than the owner has.
2. **Priority** — every task is HIGH, MEDIUM, or LOW. Tasks are ordered high-first, and when time runs out,the lowest-priority tasks are the ones dropped.
3. **Preferences / preferred times** — the owner sets a start time for the day, and individual tasks can request a preferred clock time (e.g., a morning walk at 8:00).

I decided priority mattered most, then time, then preferred time. For pet care, doing the important things (meds, feeding, a walk) matters more than
doing everything, which matters more than doing them at an exact minute. Being a little off on feeding or giving them a walk does not affect the pet as much, but the owner should, for example, give the pet the proper meds before worrying about walking it. Because of that, the pipeline sorts by priority, packs tasks until the time budget is full, and only then tries to honor preferred times when placing them on the clock.

**b. Tradeoffs**

**Tradeoff:** priority ordering can override a task's preferred time. Because the scheduler
sorts by priority before it assigns clock times, a high-priority task placed earlier can push
the cursor forward so that a later task misses its preferred slot. For example, a walk that
prefers 8:00 ended up at 9:20 because a 9:00 feeding (also high priority) was placed first.

This tradeoff is reasonable for pet care because the goal is that important tasks get done,
not that they happen at an exact time. A walk at 9:20 instead of 8:00 is still a completed
walk; skipping the walk to protect the 8:00 slot would be worse. The plan is always valid
(no overlaps, never exceeds the time budget), which is the property that actually matters for a
busy owner. Honoring exact preferred times would require a more complex time-anchored pass,
which I will note as a future improvement.

A second, related tradeoff is that budget packing is greedy: it fills highest-priority-first
rather than searching for the combination of tasks that uses time most efficiently. A single
large high-priority task can block several small ones that together would have been more
valuable. Greedy keeps the logic simple and predictable, which is easier to trust and test.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

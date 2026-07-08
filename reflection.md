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

**Tradeoff:** priority decides what gets dropped, not what time a task happens at. When the
owner runs out of time, the scheduler fills the budget highest-priority-first, so the
lowest-priority tasks are the ones that get cut. That means a task can lose its spot completely,
even if it had an early preferred time it wanted, because something more important used up the
minutes first. For example, if the day is full, a LOW-priority play time can get skipped while
the HIGH-priority feeding and walk still make it in.

I think this is the right call for pet care. The goal is that the important things (meds,
feeding, a walk) actually get done, not that everything gets done. Dropping a play session to
protect a feeding is better than doing it the other way around. The plan is also always valid
(no overlaps, never over the time budget), which is the part that actually matters to a busy
owner.

**Tradeoff:** the plan is placed in time order, so a task can still miss its exact preferred
time, but when that happens it is because an earlier task ran long and pushed into its slot, not because of priority. For example, two feedings both wanted 8:30, so the second one got bumped to
8:40 to sit back-to-back. Honoring every exact preferred time would need a more complex
time-anchored pass, which I will note as a future improvement.

A related tradeoff is that the budget packing is greedy: it fills highest-priority-first instead
of searching for the combination of tasks that uses the time most efficiently. So one big
high-priority task can block a few small ones that together would have been more useful. I kept
it greedy because it is simple and predictable, which makes it easier to trust and to test.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?

I used it a lot for coding out what I wanted (add features, making it smart, etc). I also used it to help with the UML diagram after I described the objects and actions

- What kinds of prompts or questions were most helpful?
Focused prompts one at a time with clear outputs/results.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
To be completely honest, I did not check the AI's suggestion as well as I would have liked. I made sure to read through everything it suggested, but ended up accepting a lot of the suggestions.

- How did you evaluate or verify what the AI suggested?
Primarily just seeing if its logic/reasoning matched up with the code and then test its functionality. I also like to look and see if the code is disproportionately long compared to its functionality.
---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
Some behaviors I tested include basic adding tasks, making a scheduler, marking tasks as done, sorting, recurring tasks, and all the way to edge cases like pet with no tasks (you can have a pet without giving it a task so basically it sits there and have fun and will give you an empty plan that does not take time).

- Why were these tests important?
Basic starter tests (adding tasks, making a scheduler, marking tasks as done) and sorting are fundamental features of the system. That must work before trying to make it smart and account for edge cases. Edge cases are important to test for smooth user experience (i.e. a user's app should not crash or behave weirdly just because their pet doesn't have a task yet) or prevent threat actors from inputting malicious things into our system to crash or make it do weird things.

**b. Confidence**

- How confident are you that your scheduler works correctly?
4 out of 5 like I stated. All functions work correctly and UI is very easy on the eyes.

- What edge cases would you test next if you had more time?
If a task runs past midnight or start earlier than owner's start day. If 2 tasks ties at same priority and preferred time.
---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
Getting to practice system design by coming up with objects and defining their actions. Using AI to double check and suggest further extensions was also fun and made me more confident. 

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
Implement challenge 2 to have data persistence for the pets. Making it actually save your pets and tasks between runs would be the most useful real-world upgrade, since everything resets when you restart it.


**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
Checking its outputs to see if it matches its reasoning is very important in ensuring the code does not stray from the design and get us lost.
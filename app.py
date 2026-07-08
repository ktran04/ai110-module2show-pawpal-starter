import datetime

import streamlit as st

# --- Step 1: Establish the connection -------------------------------------
# Bring the specific classes we need from the logic layer into the UI.
from pawpal_system import Owner, Pet, Task, Priority, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# --- Step 2: Manage the application "memory" ------------------------------
# Streamlit re-runs this whole script top-to-bottom on every interaction, so a
# plain `owner = Owner(...)` here would be recreated empty each time. We store
# the Owner in st.session_state (a dict that survives reruns) and only create it
# once — the `if ... not in` check is the "does it already exist in the vault?"
# guard. On later reruns we reuse the same object, so pets/tasks persist.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(
        owner_id=1,
        name="Jordan",
        available_minutes=120,
        preferences={"start_time": datetime.time(8, 0)},
    )
    # Simple id counters so each new pet/task gets a unique id.
    st.session_state.next_pet_id = 1
    st.session_state.next_task_id = 1

owner: Owner = st.session_state.owner  # the persisted instance


# --- Owner settings -------------------------------------------------------
st.subheader("Owner settings")
col1, col2 = st.columns(2)
with col1:
    owner.name = st.text_input("Owner name", value=owner.name)
with col2:
    owner.set_available_time(
        st.number_input(
            "Available minutes today",
            min_value=0,
            max_value=1440,
            value=owner.available_minutes,
            step=15,
        )
    )
owner.preferences["start_time"] = st.time_input(
    "Day start time", value=owner.preferences.get("start_time", datetime.time(8, 0))
)

st.divider()

# --- Step 3: Wire "Add a pet" to Owner.add_pet ----------------------------
st.subheader("Add a pet")
with st.form("add_pet_form", clear_on_submit=True):
    pet_name = st.text_input("Pet name", value="")
    species = st.selectbox("Species", ["dog", "cat", "other"])
    breed = st.text_input("Breed", value="")
    submitted_pet = st.form_submit_button("Add pet")

if submitted_pet and pet_name.strip():
    # The form data is handed to the class method that owns this behavior:
    # Owner.add_pet(). Because `owner` lives in session_state, the new Pet
    # object stays in memory across reruns.
    owner.add_pet(
        Pet(
            pet_id=st.session_state.next_pet_id,
            owner_id=owner.owner_id,
            name=pet_name.strip(),
            species=species,
            breed=breed.strip(),
        )
    )
    st.session_state.next_pet_id += 1
    st.success(f"Added {pet_name.strip()}!")

# --- Wire "Add a task" to Pet.add_task ------------------------------------
st.subheader("Add a task")
if not owner.pets:
    st.info("Add a pet first, then you can give it tasks.")
else:
    # Map each pet's display name to its object so we can call add_task on it.
    pet_by_label = {f"{p.name} ({p.species})": p for p in owner.pets}
    with st.form("add_task_form", clear_on_submit=True):
        pet_label = st.selectbox("For which pet?", list(pet_by_label.keys()))
        task_name = st.text_input("Task title", value="Morning walk")
        category = st.selectbox(
            "Category", ["walk", "feeding", "meds", "grooming", "enrichment", "other"]
        )
        c1, c2 = st.columns(2)
        with c1:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        with c2:
            priority_label = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        c3, c4 = st.columns(2)
        with c3:
            recurrence_label = st.selectbox(
                "Repeats", ["one-off", "daily", "weekly", "weekdays"]
            )
        with c4:
            # Only meaningful for weekly tasks; picks the weekday it recurs on.
            weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            weekday_label = st.selectbox("Weekly on", weekday_names)
        use_pref = st.checkbox("Has a preferred time?")
        preferred = st.time_input("Preferred time", value=datetime.time(8, 0)) if use_pref else None
        submitted_task = st.form_submit_button("Add task")

    if submitted_task and task_name.strip():
        pet = pet_by_label[pet_label]
        recurrence = None if recurrence_label == "one-off" else recurrence_label
        recurrence_weekday = (
            weekday_names.index(weekday_label) if recurrence == "weekly" else None
        )
        pet.add_task(
            Task(
                task_id=st.session_state.next_task_id,
                pet_id=pet.pet_id,
                name=task_name.strip(),
                category=category,
                duration=int(duration),
                priority=Priority[priority_label.upper()],
                preferred_time=preferred,
                recurrence=recurrence,
                recurrence_weekday=recurrence_weekday,
            )
        )
        st.session_state.next_task_id += 1
        st.success(f"Added '{task_name.strip()}' for {pet.name}!")

# --- Show current pets and their tasks ------------------------------------
if owner.pets:
    st.subheader("Current pets & tasks")

    # A throwaway Scheduler gives us the sort/filter helpers for the list views.
    view = Scheduler(datetime.date.today(), owner)
    c1, c2 = st.columns(2)
    with c1:
        sort_mode = st.radio("Sort tasks by", ["Priority", "Time"], horizontal=True)
    with c2:
        show_done = st.checkbox("Show completed tasks", value=True)

    # Proactive "schedule health" check across ALL of the owner's tasks, so the
    # owner sees clashes *while editing* — not only after generating the plan.
    all_today = view.filter_tasks(owner.get_all_tasks())
    conflicts = view.detect_conflicts(all_today)
    if conflicts:
        st.warning(
            f"**{len(conflicts)} time conflict(s) found.** "
            "The schedule will still be built — PawPal+ shifts the later task to "
            "back-to-back — but you may want to move a preferred time so nothing "
            "gets bumped:"
        )
        for w in conflicts:
            # `w` already starts with a ⚠️ marker; show each on its own line.
            st.markdown(f"- {w}")
    else:
        st.success("No time conflicts — every task has a clear slot. 🎉")

    for pet in owner.pets:
        with st.expander(f"{pet.name} — {pet.species} ({pet.breed or 'unknown breed'})", expanded=True):
            # Filter (by this pet + completion status), then sort by the chosen key.
            tasks = view.filter_tasks(
                pet.list_tasks(), pet_id=pet.pet_id, include_completed=show_done
            )
            tasks = view.sort_by_time(tasks) if sort_mode == "Time" else view.sort_tasks(tasks)

            if not tasks:
                st.caption("No tasks to show.")
            else:
                st.table(
                    [
                        {
                            "Task": t.name,
                            "Category": t.category,
                            "Duration (min)": t.duration,
                            "Priority": t.priority.name,
                            "Preferred": t.preferred_time.strftime("%H:%M") if t.preferred_time else "—",
                            "Repeats": t.recurrence or "one-off",
                            "Done": "✅" if t.completed else "",
                        }
                        for t in tasks
                    ]
                )

            # Complete a task — recurring ones auto-spawn their next instance.
            open_tasks = [t for t in pet.list_tasks() if not t.completed]
            if open_tasks:
                task_by_label = {f"{t.name} (id {t.task_id})": t for t in open_tasks}
                cc1, cc2 = st.columns([3, 1])
                with cc1:
                    to_complete = st.selectbox(
                        "Mark complete", list(task_by_label.keys()), key=f"complete_{pet.pet_id}"
                    )
                with cc2:
                    if st.button("Done", key=f"done_btn_{pet.pet_id}"):
                        chosen = task_by_label[to_complete]
                        follow_up = pet.mark_task_complete(chosen.task_id)
                        if follow_up:
                            st.success(
                                f"Completed '{chosen.name}'. Next one due "
                                f"{follow_up.due_date} (auto-created)."
                            )
                        else:
                            st.success(f"Completed '{chosen.name}'.")
                        st.rerun()

st.divider()

# --- Generate schedule ----------------------------------------------------
st.subheader("Build today's schedule")
if st.button("Generate schedule", type="primary"):
    if not owner.get_all_tasks():
        st.warning("No tasks to schedule yet. Add a pet and some tasks first.")
    else:
        schedule = Scheduler(datetime.date.today(), owner).generate_plan()
        pet_names = {p.pet_id: p.name for p in owner.pets}

        st.markdown(f"**Daily plan for {schedule.date.strftime('%A, %B %d, %Y')}**")
        if schedule.entries:
            st.table(
                [
                    {
                        "Time": slot.strftime("%H:%M"),
                        "Task": task.name,
                        "Pet": pet_names.get(task.pet_id, "?"),
                        "Duration (min)": task.duration,
                        "Priority": task.priority.name,
                    }
                    for slot, task in schedule.entries
                ]
            )
        else:
            st.info("Nothing fit in the plan.")

        # Surface any detected time conflicts as warnings (not a crash). We give
        # them a single heading so they read as one "here's what to know" block
        # rather than a scatter of alerts, and confirm plainly when there are none.
        if schedule.warnings:
            st.warning(f"**Heads up — {len(schedule.warnings)} time conflict(s):**")
            for w in schedule.warnings:
                st.markdown(f"- {w}")
            st.caption(
                "PawPal+ resolved these by placing the tasks back-to-back "
                "(see *Why this plan* below). To keep a task at its exact time, "
                "give the overlapping one a different preferred time."
            )
        else:
            st.success("No time conflicts — everything fits cleanly. 🎉")

        st.caption(
            f"Total scheduled: {schedule.total_time()} / {owner.available_minutes} min"
        )
        st.markdown(f"**Why this plan:** {schedule.reasoning}")

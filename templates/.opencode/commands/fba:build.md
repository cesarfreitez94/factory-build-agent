---
description: Generate Odoo v18 module code from SDD and individual task files
agent: constructor
---

# fba:build

Generate complete Odoo v18 module source code by processing each task
incrementally. Each task runs in a fresh sub-agent session with a dedicated
git commit.

## Pre-conditions
- `.factory/state.json` must have `current_phase: "construction"`.
- `.factory/sdd.md` exists.
- `.factory/tasks/index.json` exists with a valid task index.
- All individual task files `.factory/tasks/T*.json` exist.
- The project has a git repository initialized.

## Steps

### 1. Load Context
Read `.factory/sdd.md` and `.factory/tasks/index.json`.

### 2. Determine Output Directory
The Odoo module is created in the project root, named `<module_name>` from
the SDD. Initialize the module skeleton if it does not already exist:
- Create `<module_name>/__init__.py`
- Create `<module_name>/__manifest__.py` based on SDD metadata

### 3. Iterative Task Execution
For each task in `index.json`, ordered by `order`:

a. **Read the task file** `.factory/tasks/<file>` to get:
   - `files_to_generate[]` — exact files to create/modify
   - `components[]` — component specifications (models, views, security, data)
   - `dependencies[]` — task IDs already completed

b. **Read relevant SDD sections** for this task's `sdd_components[]`.
   Include only the SDD content relevant to the current task to keep context focused.

c. **Read already-generated code** from the module directory — include a
   brief summary of existing files and their key structures (models defined,
   views created, security groups registered). Only include files that are
   dependencies of the current task.

d. **Invoke a fresh sub-agent session** using the `task` tool:
   ```
   task(
     description="Build task TXXX: <name>",
     prompt="You are building Odoo v18 module code for task TXXX.

   Context:
   - Task specification: <summarize task JSON>
   - SDD sections: <relevant SDD excerpts>
   - Existing code summary: <brief summary of already-generated files>

   Generate the files listed in files_to_generate[] following Odoo v18
   conventions. Return which files you created/modified and a brief summary.",
     subagent_type="general"
   )
   ```
   Do NOT pass `task_id` — each task must be a fresh session.

e. **Commit the generated code**:
   ```bash
   git add <module_name>/ && git commit -m "feat(#XX): task <id> <name>"
   ```
   Replace `<id>` with the task ID (e.g., T001) and `<name>` with the task name.

f. **Log progress** — append an event to `.factory/events.jsonl`:
   ```json
   {"type": "task_built", "data": {"task_id": "<id>", "files_generated": [...], "status": "complete"}}
   ```

### 4. Finalize
After all tasks complete:
- Update `.factory/state.json`: set `phases.construction.status` to `"complete"`.
  DO NOT change `current_phase` — the orchestrator handles transitions.
- Append a `build_complete` event to `.factory/events.jsonl`.

## Iterative Protocol Rules

1. **One session per task** — never reuse `task_id` between tasks.
2. **Context isolation** — each session only receives SDD sections relevant
   to its task, plus a brief summary of existing code (not full files).
3. **Ordered execution** — tasks must be processed in `order` sequence.
   A task with unmet dependencies must wait.
4. **Per-task commits** — each task gets its own git commit with `feat(#XX): task <id> <name>`.

## Post-conditions
- A valid Odoo v18 module directory exists with all files from `files_to_generate[]`.
- One git commit per task in the project repository.
- `phases.construction.status` is `"complete"`.
- Ready for `/fba:test`.

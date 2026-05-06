---
description: Break down the technical plan into implementable tasks
agent: planificador
---

# fba:tasks

Decompose the SDD and technical plan into a sequenced list of individual
implementation tasks, each in its own structured JSON file under `.factory/tasks/`.

## Pre-conditions
- `.factory/state.json` must have `current_phase: "tasks"`.
- `.factory/sdd.md` and `.factory/plan.md` exist.

## Steps

1. Read `.factory/sdd.md` and `.factory/plan.md`.
2. Create `.factory/tasks/` directory.
3. Generate `.factory/tasks/index.json` with:
   - `module_name` — from SDD
   - `total_tasks` — count of tasks
   - `tasks[]` — ordered list with `id`, `name`, `file`, `dependencies[]`, `order`, `estimated_effort`, `sdd_components[]`
4. For each task in the index, generate `.factory/tasks/<file>` as a structured JSON file conforming to `task_item.schema.json`:
   - `id`, `name`, `description`
   - `components[]` — each with `type`, `name`, `description`, model/view/security-specific fields, `sdd_reference`
   - `files_to_generate[]` — concrete file paths relative to the Odoo module
   - `dependencies[]` — task IDs this task depends on
5. Update `.factory/state.json`: set `phases.tasks.status` to `"complete"`.
   DO NOT change `current_phase` — the orchestrator handles transitions.
6. Append a `tasks_complete` event to `.factory/events.jsonl` with:
   ```json
   {"type": "tasks_complete", "data": {"total_tasks": <N>, "index": ".factory/tasks/index.json"}}
   ```

## Output Structure

```
.factory/tasks/
├── index.json              # Manifest: task metadata and ordering
├── T001-modelos.json        # Task: Odoo models
├── T002-vistas.json         # Task: XML views
├── T003-seguridad.json      # Task: security (groups, ACL, record rules)
└── T004-datos-demo.json     # Task: demo data
```

## Post-conditions
- `.factory/tasks/index.json` exists and is valid against `task_index.schema.json`.
- All individual `T*.json` task files exist and are valid against `task_item.schema.json`.
- `phases.tasks.status` is `"complete"`.
- Ready for `/fba:build`.

> Note: The orchestrator runs `fba gate tasks` after this phase to validate the task files.

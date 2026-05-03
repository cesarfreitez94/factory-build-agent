---
description: Generate Odoo v18 module code from SDD and task list
agent: constructor
---

# fba:build

Generate complete Odoo v18 module source code following the SDD and task list.

## Pre-conditions
- `.factory/state.json` must have `current_phase: "tasks"` (or `"planning"`).
- `.factory/sdd.md` and `.factory/tasks.md` exist.

## Steps

1. Read `.factory/sdd.md` and `.factory/tasks.md`.
2. Generate the Odoo v18 module directory with:
   - `__manifest__.py` — module metadata and dependencies
   - `models/` — Python model classes with fields and methods
   - `views/` — XML view definitions (tree, form, search, kanban)
   - `security/` — `ir.model.access.csv` for access control
   - `data/` — demo data and initial configuration
3. Update `.factory/state.json`: set `current_phase` to `"construction"`,
   mark `phases.construction.status` as `"complete"`.
4. Append a `build_complete` event to `.factory/events.jsonl`.

## Post-conditions
- A valid Odoo v18 module directory exists with all required files.
- Ready for `/fba:test`.

> Note: Full code generation is implemented in M3.

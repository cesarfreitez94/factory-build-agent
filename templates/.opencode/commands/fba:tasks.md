---
description: Break down the technical plan into implementable tasks
agent: planificador
---

# fba:tasks

Decompose the SDD and technical plan into a sequenced list of implementable
tasks for the construction phase.

## Pre-conditions
- `.factory/state.json` must have `current_phase: "planning"`.
- `.factory/sdd.md` and `.factory/plan.md` exist.

## Steps

1. Read `.factory/sdd.md` and `.factory/plan.md`.
2. Generate `tasks.md` in `.factory/` with:
   - Sequenced task list with dependencies
   - Each task references the SDD component it implements
   - Estimated effort per task
3. Update `.factory/state.json`: set `current_phase` to `"tasks"`.
4. Append a `tasks_complete` event to `.factory/events.jsonl`.

## Post-conditions
- `.factory/tasks.md` exists with a complete implementation sequence.
- Ready for `/fba:build`.

> Note: Full task decomposition is implemented in M2.

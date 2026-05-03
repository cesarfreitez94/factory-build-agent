---
description: Generate technical plan and Software Design Document (SDD.md) from PRD
agent: planificador
---

# fba:plan

Generate a Software Design Document and technical plan specific to Odoo v18
architecture, with full traceability to the PRD.

## Pre-conditions
- `.factory/state.json` must have `current_phase: "documentation"`.
- `.factory/prd.md` exists and is valid.

## Steps

1. Read `.factory/prd.md` to understand requirements.
2. Generate `sdd.md` in `.factory/` with:
   - Odoo v18 architecture (modules, models, views)
   - Security design (groups, ACLs, access rights)
   - Module dependencies
   - File structure for the Odoo module
3. Generate `plan.md` in `.factory/` with:
   - Implementation sequence
   - Technology stack
   - Identified risks
   - Estimates
4. Ensure traceability: each PRD requirement maps to an SDD component.
5. Update `.factory/state.json`: set `current_phase` to `"planning"`,
   mark `phases.planning.status` as `"complete"`.
6. Append a `plan_complete` event to `.factory/events.jsonl`.

## Post-conditions
- `.factory/sdd.md` and `.factory/plan.md` exist.
- Traceability matrix PRD -> SDD is documented.
- Ready for `/fba:tasks`.

> Note: Full SDD generation with traceability is implemented in M2.

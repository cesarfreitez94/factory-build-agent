---
description: Generate a Product Requirements Document (PRD.md) from elicited requirements
agent: documentador
---

# fba:specify

Generate a structured PRD.md from the elicited requirements.

## Pre-conditions
- `.factory/state.json` must have `current_phase: "elicitation"`.
- Elicited requirements are available in `.factory/context/`.

## Steps

1. Read elicited requirements from `.factory/context/`.
2. Generate `prd.md` in `.factory/` with the following sections:
   - Vision
   - Stakeholders
   - Objectives
   - Functional Requirements
   - Non-Functional Requirements
   - Acceptance Criteria
   - Glossary
3. Validate `prd.md` against the PRD schema (when available in M1).
4. Update `.factory/state.json`: set `current_phase` to `"documentation"`,
   mark `phases.documentation.status` as `"complete"`.
5. Append a `specify_complete` event to `.factory/events.jsonl`.

## Post-conditions
- `.factory/prd.md` exists and is valid.
- Ready for `/fba:plan`.

> Note: Full PRD generation with schema validation is implemented in M1.

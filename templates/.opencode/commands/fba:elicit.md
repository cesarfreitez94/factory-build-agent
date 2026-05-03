---
description: Elicit requirements for an Odoo v18 module using BABOK methodology
agent: elicitador
---

# fba:elicit

Elicit functional and non-functional requirements following BABOK methodology.

## Pre-conditions
- `.factory/state.json` must have `current_phase: "init"` or `"elicitation"`.
- The user provides a brief description of the desired Odoo module.

## Steps

1. Read `.factory/state.json` to confirm the project is in the correct phase.
2. Interview the user using BABOK structured questions:
   - Business context and stakeholders
   - Objectives and goals
   - Functional requirements
   - Non-functional requirements
   - Constraints and dependencies
   - Acceptance criteria
3. Document all elicited requirements in `.factory/context/`.
4. Update `.factory/state.json`: set `current_phase` to `"elicitation"`,
   mark `phases.elicitation.status` as `"in_progress"`.
5. Append an `elicitation_start` event to `.factory/events.jsonl`.

## Post-conditions
- Requirements are documented and ready for the `/fba:specify` phase.
- `state.json` reflects the elicitation phase status.

> Note: Full elicitation flow is implemented in M1.

---
description: Generate a Product Requirements Document (PRD.md + prd.json) from elicited requirements
agent: documentador
---

# fba:specify

Generate a structured PRD from the elicited requirements produced by `/fba:elicit`.

## Pre-conditions
- `.factory/state.json` must have `current_phase: "elicitation"`.
- `.factory/context/elicitation.json` must exist with structured BABOK output.

## Steps

### 1. Validate Pre-conditions
Read `.factory/state.json` to confirm the project is in the `elicitation` phase.
Verify `.factory/context/elicitation.json` exists. If not found, instruct the user to
run `/fba:elicit` first.

### 2. Load Elicited Requirements
Read `.factory/context/elicitation.json`. Review the structured data:
- Initial description and business context
- Stakeholders
- Objectives
- Functional requirements
- Non-functional requirements
- Constraints and dependencies
- Acceptance criteria

### 3. Generate PRD Documents
Follow the documentador agent instructions in `.opencode/agents/documentador.md`:

#### 3a. Generate `.factory/prd.json`
Create the machine-readable PRD in JSON format conforming to the PRD schema
(`schemas/prd.schema.json`). Populate all required fields:
- `vision`: Synthesize from business context and objectives
- `stakeholders`: As provided or inferred from context
- `objectives`: As provided, ensure they are measurable
- `functional_requirements`: Map from elicitation, add acceptance criteria
- `non_functional_requirements`: Map with correct categories
- `acceptance_criteria`: Link to their related RFs
- `constraints`: Include Odoo v18 compatibility if not specified
- `dependencies`: Include Odoo base modules if applicable
- `glossary`: Define key terms from the domain

#### 3b. Generate `.factory/prd.md`
Render the PRD as a human-readable Markdown document with all sections
properly formatted:
- Vision
- Stakeholders (table)
- Objectives (numbered list)
- Functional Requirements (detailed per RF)
- Non-Functional Requirements (detailed per RNF)
- Acceptance Criteria (table with traceability)
- Constraints (bullet list)
- Dependencies (bullet list)
- Glossary (table)

### 4. Validate PRD
Run schema validation on the generated `prd.json`:
```bash
fba validate prd
```

If validation fails:
- Read the error message
- Fix the identified issue in `prd.json`
- Re-run `fba validate prd`
- Repeat until validation passes

### 5. Update State and Record Events
After successful validation:
1. Record the event:
   ```bash
   fba record specification_complete \
     --data '{"artifacts":["prd.json","prd.md"]}'
   ```
2. Add artifacts to state:
   ```bash
   fba add-artifact prd
   ```
3. Transition phase:
   ```bash
   fba transition documentation
   ```

### 6. Report Summary and Ask to Proceed
Display a summary of the generated PRD:
- Module name / vision
- Number of functional requirements
- Number of non-functional requirements
- Number of acceptance criteria
- Validation status: passed

Then follow the **Phase Progression Protocol** from the orchestrator agent
definition. If the user approves progression, invoke the planificador
sub-agent using the `task` tool with the instructions from
`.opencode/commands/fba:plan.md`.

## Post-conditions
- `.factory/prd.json` exists and passes schema validation.
- `.factory/prd.md` exists with human-readable PRD.
- `.factory/state.json` has `current_phase: "documentation"`.
- `.factory/events.jsonl` contains the `specification_complete` event.
- Ready for the next phase: planning.

## Example Output

```
✅ PRD generado y validado

📄 .factory/prd.json — valid
📄 .factory/prd.md — documentacion legible

Resumen:
  - Vision: Modulo de registro de vehiculos para Odoo v18
  - 5 Functional Requirements (RF-01 a RF-05)
  - 3 Non-Functional Requirements (RNF-01 a RNF-03)
  - 4 Acceptance Criteria (CA-01 a CA-04)
  - 3 Stakeholders
  - 2 Constraints, 2 Dependencies

Fase actual: documentation

> [Uses question tool]
> Header: "Fase completada: documentation"
> Q: "¿Como procedemos?"
> - A) Continuar a la siguiente fase (planning)
> - B) Quiero revisar los artefactos generados primero
> - C) Quiero hacer cambios en esta fase
```

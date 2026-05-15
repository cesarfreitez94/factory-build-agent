---
description: Elicit Odoo v18 requirements using the full BABOK, Impact Mapping, Event Storming, and Example Mapping stack
agent: orchestrator
---

# fba:elicit

Elicit functional and non-functional requirements for an Odoo v18 module using
`--method-stack full` by default. Full mode chains BABOK, Impact Mapping, Event
Storming, and Example Mapping. Use `--method-stack babok` only when the user
explicitly requests the legacy minimum flow.

## Pre-conditions
- `.factory/state.json` must have `current_phase: "init"`.
- The project was initialized with `fba init`.
- The user provides a brief description of the desired Odoo module.

## Steps

### 1. Validate State
Read `.factory/state.json` to confirm the project is in the `init` phase.
If the current phase is not `init`, report the current state and ask the user
to run the appropriate command to reach the correct phase.

### 2. Receive Initial Description
If the user provided a module description in the command (e.g.,
`/fba:elicit "modulo de registro de vehiculos"`), use it directly.
If the command includes `--method-stack babok`, use the BABOK-only flow.
Otherwise, default to `--method-stack full`.
Otherwise, ask the user to describe their module idea in natural language.

### 3. Consult Methodology Stack
Read `.opencode/agents/elicitador.md` to understand the methodology stack for
Odoo v18 module elicitation. Based on the user's module description and selected
method stack, determine which areas are most relevant and what specific
questions will yield the best requirements.

### 4. Execute Elicitation via Question Tool

CRITICAL: You MUST use the `question` tool to present elicitation questions
interactively. This allows the user to select options (letters) rather than
typing free-form responses. The user can also write a custom answer when
they choose "Otro (especificar)".

**Question Generation Guidelines:**

Based on the user's module idea, generate selection-based questions grouped by
method. In `full` mode, use 10-16 total questions. In `babok` mode, use the
legacy 8-12 BABOK questions.

**BABOK baseline:**

| Category | Focus | Min Questions |
|----------|-------|---------------|
| A. Business Context & Stakeholders | Domain, users, stakeholders, problem | 2 |
| B. Objectives & Scope | Goals, success metrics, in/out scope | 2 |
| C. Functional Requirements | Core features needed for the specific module | 3 |
| D. Non-Functional Requirements | Performance, security, usability, maintainability | 2 |
| E. Constraints & Dependencies | Technical limits, Odoo dependencies, data | 1 |
| F. Acceptance Criteria | Measurable criteria for module acceptance | 1 |

**Additional full-stack coverage:**

| Method | Focus | Min Questions |
|--------|-------|---------------|
| Impact Mapping | Goal, actors, impacts, deliverables | 2 |
| Event Storming | Events, commands, aggregates, policies/read models | 2 |
| Example Mapping | Business rules, examples, edge cases, open questions | 2 |

**For each question:**
- Provide 4-6 predefined options as lettered choices (A, B, C, ...)
- ALWAYS include "Otro (especificar)" as the last option
- Tailor options to the specific module domain (do NOT use generic templates)
- For stakeholder/user questions, allow multiple selection (`multiple: true`)

**After the first batch**, if responses are incomplete or reveal gaps:
- Ask targeted follow-up questions for the missing BABOK categories
- In `full` mode, ask targeted follow-ups for missing Impact Mapping, Event Storming, or Example Mapping coverage
- Always use the `question` tool with selection format

### 5. Generate Structured Output
Parse the user's selected responses into `.factory/context/elicitation.json`
following the format defined in `.opencode/agents/elicitador.md`.

Ensure the JSON file has all required sections:
- `initial_description`: user's original description
- `business_context`: business process context
- `stakeholders[]`: (name, role, interest each)
- `objectives[]`: measurable objectives
- `functional_requirements[]`: (id RF-NN, description, priority)
- `non_functional_requirements[]`: (id RNF-NN, description, category, priority)
- `constraints[]`: technical/business constraints
- `dependencies[]`: external dependencies
- `acceptance_criteria[]`: (id CA-NN, criterion, related_requirements)
- `glossary[]`: (term, definition)
- `methodology_stack`: optional extension. Required when method stack is `full`;
  include Impact Mapping, Event Storming, and Example Mapping sections with
  stable IDs such as ACT-01, IMP-01, DEL-01, EVT-01, CMD-01, AGG-01, BR-01, EX-01.

### 6. Generate Semantic Graph Emission

After saving `elicitation.json`, write or update
`.factory/graph_emissions/elicitador.json` using refs from the artifact. In
`full` mode, include nodes for goal, actor, impact, deliverable, event,
command, aggregate, policy, read_model, business_rule, and example when present.
Do not write directly to `.factory/graph.json`; consolidation is done with
`fba graph consolidate`.

### 7. Update State and Record Events
After saving `elicitation.json`:
1. Record the elicitation event:
    ```bash
    fba record elicitation_complete \
      --data '{"methodology":"BABOK","method_stack":"full","rf_count":N,"rnf_count":M}'
    ```
2. Transition to elicitation phase:
   ```bash
   fba transition elicitation
   ```

### 8. Report Results and Ask to Proceed
Summarize what was elicited:
- Number of stakeholders identified
- Number of functional requirements (RF)
- Number of non-functional requirements (RNF)
- Number of acceptance criteria (CA)
- Method stack used and number of Impact Mapping/Event Storming/Example Mapping items, when `full`
- Key constraints and dependencies

Then follow the **Phase Progression Protocol** from the orchestrator agent
definition. If the user approves progression, invoke the documentador
sub-agent using the `task` tool with the instructions from
`.opencode/commands/fba:specify.md`.

## Post-conditions
- `.factory/context/elicitation.json` exists with structured requirements.
- `.factory/graph_emissions/elicitador.json` exists with semantic graph emission.
- `.factory/state.json` has `current_phase: "elicitation"`, phases.elicitation.status: "in_progress".
- `.factory/events.jsonl` contains the `elicitation_complete` event.
- Ready for the next phase: documentation.

## Example Interaction

```
User: /fba:elicit "modulo de registro de vehiculos con marca, modelo, ano, placa"

Agent (Orchestrator):
[Consults method stack in elicitador.md]
[Generates contextual questions for fleet management domain]

> [Uses question tool]
> Header: "Contexto del Negocio"
> Q: "¿Cual es el dominio principal de este modulo?"
> - A) Gestion de flota vehicular y transporte
> - B) Gestion de activos fijos (vehiculos como activos)
> - C) Control de mantenimiento de vehiculos
> - D) Control de combustible y gastos por vehiculo
> - E) Otro (especificar)

User selects option A

Agent:
> [Uses question tool again]
> Header: "Stakeholders"
> Q: "¿Quienes usaran el modulo?" (multiple: true)
> - A) Conductores (registran datos del vehiculo)
> - B) Gerentes de flota (consultas, reportes)
> - C) Mecanicos (registran mantenimiento)
> - D) Administradores del sistema
> - E) Otro (especificar)

User selects A, B

[... continues with remaining questions ...]

Agent:
> ✅ Elicitacion completada. Resultados:
> - 3 stakeholders identificados
> - 8 requisitos funcionales (RF-01 a RF-08)
> - 4 requisitos no funcionales (RNF-01 a RNF-04)
> - 5 criterios de aceptacion (CA-01 a CA-05)
>
> El contexto se guardo en .factory/context/elicitation.json
> Fase actual: elicitation

Agent:
> [Uses question tool]
> Header: "Fase completada: elicitation"
> Q: "¿Como procedemos?"
> - A) Continuar a la siguiente fase (documentation)
> - B) Quiero revisar los artefactos generados primero
> - C) Quiero hacer cambios en esta fase

User selects option A

Agent:
> [Invoca al documentador via task tool con las instrucciones de fba:specify.md]
> ...
> ✅ PRD generado y validado
```

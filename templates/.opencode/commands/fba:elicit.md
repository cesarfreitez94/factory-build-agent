---
description: Elicit requirements for an Odoo v18 module using BABOK methodology
agent: elicitador
---

# fba:elicit

Elicit functional and non-functional requirements following BABOK methodology
for an Odoo v18 module.

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
Otherwise, ask the user to describe their module idea in natural language.

### 3. Execute BABOK Elicitation (Single-Pass)
Follow the elicitation process defined in `.opencode/agents/elicitador.md`:
- Present the full BABOK questionnaire (context, stakeholders, objectives,
  functional requirements, non-functional requirements, constraints, acceptance criteria)
  in a single structured message.
- Let the user respond to all questions at once.
- If responses are incomplete, ask targeted follow-ups for the missing sections.

### 4. Generate Structured Output
Parse user responses into `.factory/context/elicitation.json` with the format
defined in the elicitador agent.

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

### 5. Update State and Record Events
After saving `elicitation.json`:
1. Record the elicitation event:
   ```bash
   fba record elicitation_complete \
     --data '{"methodology":"BABOK","rf_count":N,"rnf_count":M}'
   ```
2. Transition to elicitation phase:
   ```bash
   fba transition elicitation
   ```

### 6. Report Results
Summarize what was elicited:
- Number of stakeholders identified
- Number of functional requirements (RF)
- Number of non-functional requirements (RNF)
- Number of acceptance criteria (CA)
- Key constraints and dependencies

## Post-conditions
- `.factory/context/elicitation.json` exists with structured requirements.
- `.factory/state.json` has `current_phase: "elicitation"`, phases.elicitation.status: "in_progress".
- `.factory/events.jsonl` contains the `elicitation_complete` event.
- Ready for `/fba:specify`.

## Example Interaction

```
User: /fba:elicit "modulo de registro de vehiculos con marca, modelo, ano, placa"

Agent (Elicitador):
> Entendido. Voy a realizar la elicitacion BABOK. Por favor responde las
> siguientes preguntas sobre tu modulo Odoo v18:

> ### A. Contexto del Negocio y Stakeholders
> 1. ¿Cual es el proceso de negocio que este modulo debe soportar?
> 2. ¿Quienes son los usuarios principales?
> ...

User: [responde todas las preguntas]

Agent (Elicitador):
> ✅ Elicitacion completada. Resultados:
> - 3 stakeholders identificados
> - 5 requisitos funcionales (RF-01 a RF-05)
> - 3 requisitos no funcionales (RNF-01 a RNF-03)
> - 4 criterios de aceptacion (CA-01 a CA-04)
>
> El contexto se guardo en .factory/context/elicitation.json
> Fase actual: elicitation
>
> Siguiente paso: /fba:specify para generar el PRD.md
```

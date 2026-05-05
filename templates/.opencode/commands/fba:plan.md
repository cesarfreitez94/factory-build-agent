---
description: Generate a Software Design Document (SDD) and technical plan for Odoo v18 from validated PRD
agent: planificador
---

# fba:plan

Generate an Odoo v18 Software Design Document (SDD) and technical plan from
a validated PRD, with full traceability from requirements to design components.

## Pre-conditions
- `.factory/state.json` must have `current_phase: "documentation"`.
- `.factory/prd.json` must exist and pass schema validation.
- `.factory/prd.md` must exist (human-readable version).

## Steps

### 1. Validate Pre-conditions
Read `.factory/state.json` to confirm the project is in the `documentation` phase.
Verify `.factory/prd.json` exists. If not found, instruct the user to
run `/fba:specify` first.

### 2. Load PRD
Read `.factory/prd.json` to understand:
- Module vision and objectives
- Functional requirements (RFs)
- Non-functional requirements (RNFs)
- Stakeholders
- Constraints and dependencies
- Acceptance criteria

Also read `.factory/prd.md` for human-readable context.

### 3. Generate SDD and Plan
Follow the planificador agent instructions in `.opencode/agents/planificador.md`:

#### 3a. Generate `.factory/sdd.json`
Create the machine-readable SDD conforming to the SDD JSON schema
(`schemas/sdd.schema.json`). This file describes the complete Odoo v18
module architecture:
- **module_name**: Technical module name (e.g., `vehicle_registry`)
- **architecture**: High-level design description
- **models**: All Odoo models with fields, types, relations, and traceability
- **views**: Form, tree, search views for each model
- **security**: Groups, access rights, record rules
- **dependencies**: Required and optional Odoo addons
- **workflows**: State machines and automation flows
- **reporting**: Report definitions if applicable
- **file_structure**: Complete module file tree
- **traceability_matrix**: Maps every RF/RNF to its SDD components

#### 3b. Generate `.factory/sdd.md`
Render the SDD as a human-readable Markdown document with all sections
properly formatted:
- Architecture Overview
- Models (detailed per model with field tables)
- Views (table per view type)
- Security Design (groups + access rights)
- Dependencies
- Workflows
- Reporting
- File Structure (tree)
- Traceability Matrix (global mapping table)

#### 3c. Generate `.factory/plan.md`
Create a technical plan with:
- Technology Stack (Odoo v18, Python 3.11+, Odoo ORM, etc.)
- Implementation Phases (Foundation → Views → Security → Logic → Polish)
- Risks and Mitigations table
- Estimates per phase with complexity ratings

### 4. Validate SDD
Run schema validation on the generated `sdd.json`:
```bash
fba validate sdd
```

If validation fails:
- Read the error message
- Fix the identified issue in `sdd.json`
- Re-run `fba validate sdd`
- Repeat until validation passes

### 5. Verify Traceability
Check that the traceability matrix is complete:
- Every RF from the PRD must appear in at least one mapping
- Every RNF from the PRD must appear in at least one mapping
- All SDD components must have traceability tags

### 6. Run Gate Validation
Verify that the planning phase gate passes:
```bash
fba gate planning
```

If the gate fails, fix the identified issues before proceeding.

### 7. Update State and Record Events
After successful gate validation:
1. Record the event:
   ```bash
   fba record plan_complete \
     --data '{"artifacts":["sdd.json","sdd.md","plan.md"],"traceability_complete":true}'
   ```
2. Add artifacts to state:
   ```bash
   fba add-artifact sdd
   ```
3. Transition phase:
   ```bash
   fba transition planning
   ```

### 8. Report Summary and Ask to Proceed
Display a summary of the generated SDD:
- Module name
- Number of models designed
- Number of fields across all models
- Number of views (form, tree, search)
- Security groups and access rights
- Dependencies
- Traceability coverage (RFs mapped / total RFs)
- Validation status: passed

Then follow the **Phase Progression Protocol** from the orchestrator agent
definition. If the user approves progression, instruct the user on the
next slash command for task breakdown.

## Post-conditions
- `.factory/sdd.json` exists and passes schema validation.
- `.factory/sdd.md` exists with human-readable SDD.
- `.factory/plan.md` exists with technical plan.
- `.factory/state.json` has `current_phase: "planning"`.
- `.factory/events.jsonl` contains the `plan_complete` event.
- Ready for the next phase: tasks.

## Example Output

```
✅ SDD y plan tecnico generados y validados

📄 .factory/sdd.json — valid
📄 .factory/sdd.md — documentacion de diseno legible
📄 .factory/plan.md — plan tecnico

Resumen:
  - Modulo: vehicle_registry (Vehicle Registry)
  - 1 modelo disenado (vehicle.registry)
  - 7 campos, 2 relaciones
  - 3 vistas (form, tree, search)
  - 1 grupo de seguridad, 1 regla de acceso
  - Dependencias: base (required), mail (optional)
  - Trazabilidad: 5/5 RFs mapeados, 3/3 RNFs mapeados

Fase actual: planning

> [Uses question tool]
> Header: "Fase completada: planning"
> Q: "¿Como procedemos?"
> - A) Continuar a la siguiente fase (tasks)
> - B) Quiero revisar los artefactos generados primero
> - C) Quiero hacer cambios en esta fase
```

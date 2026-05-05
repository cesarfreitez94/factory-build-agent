---
description: Run semantic validation on project artifacts to verify relevance against original request
agent: validador_semantico
---

# fba:semantic-check

Run LLM-based semantic validation to verify that generated artifacts (PRD, SDD)
correspond to the original module request, not just structurally correct.

## Pre-conditions
- `.factory/state.json` must exist with a valid current phase.
- `.factory/context/elicitation.json` must exist (the ground truth).
- The current phase must have a `semantic_check` gate rule defined in
  `state.json["gates"]`.
- The target artifact (prd.json or sdd.json) must exist.

## Steps

### 1. Identify the Semantic Check Context
Read `.factory/state.json` to determine:
- `current_phase`: documentation, planning, or any phase with semantic_check
- `gates[<phase>].rules`: find the `semantic_check` rule with source_path and target_path

### 2. Read Artifacts
- Read `.factory/context/elicitation.json` (source of truth)
- Read the target artifact (`.factory/prd.json` or `.factory/sdd.json`)

### 3. Evaluate Semantic Dimensions
For each dimension in the rule's `dimensions` array, assess whether the target
artifact is semantically aligned with the source:

| Dimension | What it checks |
|-----------|---------------|
| `domain_consistency` | Does the target describe the same Odoo domain? |
| `objective_alignment` | Do objectives address the business context? |
| `terminology_match` | Is glossary terminology consistent with domain? |
| `stakeholder_relevance` | Are stakeholders appropriate for the domain? |
| `requirement_relevance` | Do requirements address the requested problem? |

### 4. Generate semantic_report.json
Create `.factory/semantic_report.json` with structured results:
```json
{
  "phase": "<current_phase>",
  "timestamp": "<ISO8601>",
  "source": ".factory/context/elicitation.json",
  "target": ".factory/prd.json",
  "overall_passed": true,
  "dimensions": [
    {
      "name": "domain_consistency",
      "passed": true,
      "explanation": "..."
    }
  ],
  "summary": "...",
  "recommendations": []
}
```

### 5. Present Results
Follow the **Procedure** from `.opencode/agents/validador_semantico.md`
(Step 5: Present results and offer correction).

Display a summary:
- Phase validated
- Number of dimensions checked
- Number passed / failed
- Each failure with its dimension and explanation

Then present options using the `question` tool:
- A) Corregir artefacto (re-invocar agente dueno en sesion nueva)
- B) Revisar reporte detallado
- C) Continuar sin corregir (usar --force)

### 6. Handle Correction
If the user chooses to correct:
- Read the `owner_agent` from the failing gate definition
- Prepare a task prompt with the original agent instructions and specific
  semantic errors as correction context
- Invoke the owning sub-agent via `task` tool **without task_id** (fresh session)
- Re-run validation after correction completes
- Present updated results

## Post-conditions
- `.factory/semantic_report.json` exists with current validation results.
- All semantic dimensions are passing, OR the user has acknowledged
  the failures and chosen to bypass.
- The project is semantically validated for the current phase.

## Example Output

```
🔍 Semantic Validation: documentation

   Dimensions evaluated:
     ✅ domain_consistency: Both source and target describe inventory
     ✅ objective_alignment: Target objectives cover all source objectives
     ✅ terminology_match: Glossary terms consistent with inventory domain
     ✅ stakeholder_relevance: Stakeholders map to warehouse roles
     ✅ requirement_relevance: All RFs address inventory operations

   Result: 5/5 passed

> [Uses question tool]
> Header: "Validacion Semantica: documentation"
> Q: "Resultado: 5/5 dimensiones pasaron. ¿Como procedemos?"
> - A) Continuar a la siguiente fase
> - B) Revisar reporte detallado
> - C) Quiero hacer cambios en esta fase
```

If validation fails:

```
🔍 Semantic Validation: documentation

   Dimensions evaluated:
     ❌ domain_consistency: Source describes inventory, target describes fleet
     ❌ terminology_match: Target uses "vehicle, driver" instead of "stock, warehouse"
     ✅ objective_alignment: Objectives are aligned
     ❌ stakeholder_relevance: Target lists "chofer" instead of warehouse operators
     ✅ requirement_relevance: Requirements are generic CRUD, applicable

   Result: 2/5 passed — 3 failure(s)

> [Uses question tool]
> Header: "Validacion Semantica: documentation"
> Q: "Resultado: 2/5 dimensiones pasaron. ¿Como procedemos?"
> - A) Corregir artefacto (re-invocar documentador en sesion nueva)
> - B) Revisar reporte detallado
> - C) Continuar sin corregir (usar --force)
```

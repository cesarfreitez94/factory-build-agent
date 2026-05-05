---
description: Run gate validation and diagnostics for project artifacts
agent: revisor_artefactos
---

# fba:gate

Run the gate validation system to check that all artifacts for the current
phase pass their declared gates. If failures are found, diagnose and offer
a correction cycle with the owning sub-agent.

## Pre-conditions
- `.factory/state.json` must exist with a valid current phase.
- Gate definitions must exist in `state.json["gates"]` (created by `fba init`).

## Steps

### 1. Load Current State
Read `.factory/state.json` to determine:
- `current_phase`: which phase gates to evaluate
- `gates`: the gate definitions to check

### 2. Run Gate Validation
Execute the gate command for the current phase:
```bash
fba gate
```

If a specific phase is needed:
```bash
fba gate <phase>
```

Or to check all defined gates:
```bash
fba gate --all
```

### 2b. Check for Pending Semantic Validation

After running gate validation, check the output for `⏳` rules.
These are `semantic_check` rules that require LLM-based evaluation
by the validador_semantico agent.

If `pending agent evaluation(s)` appears in the output, invoke the
validador_semantico agent in a FRESH session (no task_id):
```
task(
  description="Validacion semantica para <phase>",
  prompt="Run /fba:semantic-check for phase <phase>. The validador_semantico
    agent will read elicitation.json and the target artifact, evaluate all
    semantic dimensions, generate semantic_report.json, and present results.",
  subagent_type="general"
)
```

After semantic validation completes, re-run `fba gate` to confirm all
checks pass (both structural and semantic).

### 3. Run Schema Validation
Execute full artifact schema validation:
```bash
fba validate
```

### 4. Diagnose Failures
For each failed rule, identify:
- Which artifact has the issue
- What the issue is (missing field, invalid format, missing traceability,
  semantic misalignment)
- Which agent should fix it (`owner_agent` from the gate definition)

### 5. Generate Validation Report
Create `.factory/gate_report.json` with:
```json
{
  "phase": "<current_phase>",
  "timestamp": "<ISO8601>",
  "passed": true/false,
  "gate_results": {
    "<phase>": {
      "passed": true/false,
      "rules": [ ... ]
    }
  },
  "schema_results": {
    "prd": {"passed": true, "errors": []},
    "sdd": {"passed": true, "errors": []}
  },
  "semantic_pending": true/false,
  "recommendations": [
    "actionable suggestion 1",
    "actionable suggestion 2"
  ]
}
```

### 6. Present Results and Offer Correction
Follow the **Procedure** from `.opencode/agents/revisor_artefactos.md`
(Step 2b for semantic checks, Step 6 for structural correction).

Display a summary:
- Phase validated
- Number of gates checked (structural + semantic pending)
- Number passed / failed
- Each failure with its message and owning agent
- If semantic checks are pending, indicate `⏳` and invoke validador_semantico

Then present the options (correct / review / skip) using the
revisor_artefactos agent's correction cycle protocol.

### 7. Handle Correction
If the user chooses to correct:
- **Structural failures**: extract validation errors, invoke the owning
  sub-agent with the errors as context in a FRESH session (no task_id).
- **Semantic failures**: the validador_semantico handles this — it reads
  the semantic errors from semantic_report.json, invokes the owning agent
  in a fresh session to correct the artifact, and re-runs validation.
- After correction completes, re-run `fba gate` and `fba validate`
- Present updated results

If all gates pass (structural + semantic), report success and suggest
transitioning to the next phase.

## Post-conditions
- `.factory/gate_report.json` exists with current validation results.
- Gates for the current phase are all passing, OR the user has
  acknowledged the failures and chosen to bypass.
- The project is ready for phase transition (if all gates passed).

## Example Output

All gates passing (structural only, no semantic checks pending):

```
🔍 Gate Validation: documentation
   ✅ prd_json_exists: Artifact exists: .factory/prd.json
   ✅ prd_md_exists: Artifact exists: .factory/prd.md
   ✅ prd_schema_valid: Schema validation passed: .factory/prd.json

   Result: 3/3 passed

   Fase documentation: ✅ ready to transition

> [Uses question tool]
> Header: "Validacion de artefactos: documentation"
> Q: "¿Como procedemos?"
> - A) Continuar a la siguiente fase (planning)
> - B) Revisar reporte detallado
> - C) Quiero hacer cambios en esta fase
```

All passing with pending semantic check:

```
🔍 Gate Validation: documentation
   ✅ prd_json_exists: Artifact exists: .factory/prd.json
   ✅ prd_md_exists: Artifact exists: .factory/prd.md
   ✅ prd_schema_valid: Schema validation passed: .factory/prd.json
   ⏳ prd_semantic_relevance: Semantic check pending: comparing .factory/context/elicitation.json → .factory/prd.json across 5 dimensions — requires agent evaluation

   Result: 3/3 structural passed
   ⏳ 1 pending agent evaluation(s)
   Owner agent: documentador

> [Invokes validador_semantico in fresh session via task tool]
```

If gates fail:

```
🔍 Gate Validation: documentation
   ❌ prd_json_exists: Artifact not found: .factory/prd.json
   ❌ prd_md_exists: Artifact not found: .factory/prd.md
   ❌ prd_schema_valid: Artifact for schema check not found: .factory/prd.json

   Result: 0/3 passed — 3 failure(s)
   Owner agent: documentador

> [Uses question tool]
> Header: "Validacion de artefactos: documentation"
> Q: "¿Como procedemos?"
> - A) Corregir artefactos (re-invocar al agente documentador)
> - B) Revisar reporte detallado
> - C) Continuar sin corregir (usar --force)
```

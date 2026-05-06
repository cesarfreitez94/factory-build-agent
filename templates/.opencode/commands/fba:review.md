---
description: Review generated Odoo v18 module for code quality, security, and spec adherence (PRD/SDD). Produce structured review report.
agent: revisor_codigo
---

# fba:review

Review the generated Odoo v18 module for code quality (PEP8, Odoo v18
conventions), security (ACL, validation, sensitive data), and spec adherence
(PRD/SDD traceability to schema.json SSOT).

## Pre-conditions
- `.factory/state.json` must have `current_phase: "testing"` and
  `phases.testing.status` as `"complete"`.
- `.factory/schema.json` (SSOT) exists.
- `.factory/prd.json` and `.factory/prd.md` exist.
- `.factory/sdd.json` and `.factory/sdd.md` exist.
- The Odoo module code and test report exist.

## Steps

### 1. Load All Inputs
Read `.factory/schema.json`, `.factory/prd.json`, `.factory/sdd.json`,
and all generated module files.

### 2. Quality Review
Review all Python files for:
- PEP8 compliance and import ordering
- Odoo field naming conventions (Many2one → `_id`, Many2many → `_ids`)
- Model structure (_name, _description, _inherit)
- Odoo field types and parameters (string, required, size, help, tracking)

Review all XML files for:
- Odoo v18 view tags: `<list>` NOT `<tree>`, `<form><sheet>`, `<chatter/>`
- Direct attributes: `invisible="condition"` NOT `attrs="{'invisible': ...}"`
- Proper widget usage: `widget="statusbar"`, `widget="many2many_tags"`, etc.
- View ↔ model field consistency

Review all data files for:
- `<odoo>` wrapper (NOT `<openerp>` or `<data>`)
- `noupdate="1"` where appropriate
- Correct use of `ref()` and `eval()`

### 3. Security Review
- **ACL**: every model has entries in `ir.model.access.csv`
- **Groups**: hierarchy correct, `implied_ids` defined, `category_id` valid
- **Record Rules**: `domain_force` valid, groups correctly assigned
- **Input Validation**: required fields marked, size limits, no SQL injection
- **Sensitive Data**: no hardcoded credentials, password fields use `password=True`

### 4. Spec Adherence Review
Compare generated code against `schema.json` (SSOT):
- Every model, field, view, security entry in schema exists in code
- Field types match (Char → fields.Char, Many2one → fields.Many2one)
- Relation strings match comodel names
- View field lists match schema view definitions

Compare against `prd.json`:
- Each functional requirement is implemented
- Each non-functional requirement is satisfied
- Each acceptance criterion can be validated

Compare against `sdd.json`:
- Each SDD component is present in the code
- Traceability matrix requirements are all satisfied

### 5. Generate Review Reports
Create `.factory/review_report.json`:
```json
{
  "module": "<module_name>",
  "timestamp": "<ISO8601>",
  "overall": "passed",
  "categories": {
    "quality": {"status": "passed", "critical": 0, "warning": 0, "info": 0, "findings": []},
    "security": {"status": "passed", "critical": 0, "warning": 0, "info": 0, "findings": []},
    "spec_adherence": {"status": "passed", "critical": 0, "warning": 0, "info": 0, "findings": []}
  },
  "critical_issues": 0,
  "warnings": 0,
  "files_reviewed": [],
  "recommendations": []
}
```

Create `.factory/review_report.md` with findings by category, severity,
and actionable recommendations.

### 6. Update State and Log Events
Set `phases.review.status` to `"complete"` in `.factory/state.json`.
Do NOT change `current_phase` — the orchestrator handles transitions.

Append a `review_complete` event to `.factory/events.jsonl`:
```json
{"type": "review_complete", "data": {"overall": "<passed|warnings|failed>", "critical_issues": <N>}}
```

## Post-conditions
- `.factory/review_report.json` exists and is valid.
- `.factory/review_report.md` exists.
- `phases.review.status` is `"complete"`.
- No critical issues found (or user acknowledged them).
- Ready for `/fba:ship`.

## Severity Classification

| Severity | Meaning | Blocks Gate? |
|----------|---------|-------------|
| `critical` | Security gap, missing ACL, deprecated tag, spec not implemented | Yes |
| `warning` | PEP8 violation, missing help text, minor naming issue | No |
| `info` | Suggestion, improvement opportunity | No |

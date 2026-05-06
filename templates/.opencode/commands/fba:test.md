---
description: Generate and run Odoo v18 TestCase tests for the generated module, produce structured test reports with pass/fail summary
agent: tester_qa
---

# fba:test

Generate Odoo v18 TestCase tests from `schema.json` (SSOT), create test files
in the generated module, and produce structured pass/fail test reports with
traceability to the SSOT.

## Pre-conditions
- `.factory/state.json` must have `current_phase: "construction"` and
  `phases.construction.status` as `"complete"`.
- `.factory/schema.json` (SSOT) exists and is valid.
- The Odoo v18 module code exists in `<module_name>/`.
- Gate `construction` passed (`fba gate construction`).

## Steps

### 1. Load the SSOT and Module Code
Read `.factory/schema.json` to understand the complete module structure
(models, fields, views, security groups, ACL, record rules, demo data).
Read all generated module files in `<module_name>/`.

### 2. Generate Model Tests
Create `<module_name>/tests/test_models.py` with Odoo v18 TestCase classes.
For EACH model in schema.json, generate:
- CRUD tests (create, read, update, delete)
- Validation tests (required fields, constraints)
- Relational field tests (Many2one, One2many, Many2many)
- Computed field tests (if compute specified)
- Selection/state transition tests
- Mail thread tests (if mail_thread enabled)

### 3. Generate View Tests
Create `<module_name>/tests/test_views.py`:
For EACH view in schema.json, generate:
- View existence tests (form, list, search, kanban)
- Field presence tests (verify fields in view arch)

### 4. Generate Security Tests
Create `<module_name>/tests/test_security.py`:
For EACH group in schema.json, generate:
- Read permission tests
- Write permission tests
- Create permission tests
- Delete permission tests
- Record rule visibility tests (if record_rules exist)

### 5. Generate Integration Tests
Create `<module_name>/tests/test_integration.py`:
- End-to-end workflows spanning multiple models
- Relation traversal tests
- Complete business process tests

### 6. Generate Test Reports
Create `.factory/test_report.json` with structured results:
```json
{
  "module": "<module_name>",
  "timestamp": "<ISO8601>",
  "total_tests": <N>,
  "passed": <N>,
  "failed": <N>,
  "errors": <N>,
  "categories": [
    {"name": "models", "tests": <N>, "passed": <N>, "failed": <N>},
    {"name": "views", "tests": <N>, "passed": <N>, "failed": <N>},
    {"name": "security", "tests": <N>, "passed": <N>, "failed": <N>},
    {"name": "integration", "tests": <N>, "passed": <N>, "failed": <N>}
  ]
}
```

Create `.factory/test_report.md` with human-readable results:
- Summary (total, passed, failed, errors)
- Results by category with test table
- Traceability section linking tests to schema.json entries

### 7. Update State and Log Events
Set `phases.testing.status` to `"complete"` in `.factory/state.json`.
Do NOT change `current_phase` — the orchestrator handles transitions.

Append a `test_complete` event to `.factory/events.jsonl`:
```json
{"type": "test_complete", "data": {"total_tests": <N>, "passed": <N>}}
```

## Post-conditions
- `<module_name>/tests/` directory exists with test files.
- `.factory/test_report.json` exists and is valid.
- `.factory/test_report.md` exists.
- `phases.testing.status` is `"complete"`.
- Ready for `/fba:review`.

## Odoo v18 Test Conventions

- Extend `TransactionCase` for rollback per test.
- Test class pattern: `class Test<ModelName>(TransactionCase)`.
- Method naming: `test_<action>_<entity>`.
- Security tests: create users with specific groups, use `sudo()` and `with_user()`.
- View tests: use `self.env.ref()` with full XML ID.
- No manifest registration needed — Odoo auto-discovers `tests/__init__.py`.

---
description: Generate and run tests for the generated Odoo v18 module
agent: tester
---

# fba:test

Generate Odoo TestCase tests and execute them against the generated module.

## Pre-conditions
- `.factory/state.json` must have `current_phase: "construction"`.
- The Odoo v18 module code exists.

## Steps

1. Read the generated module code to understand its structure.
2. Generate tests in `tests/` using Odoo TestCase:
   - Model tests (CRUD operations)
   - View tests (rendering, fields)
   - Security tests (access rights)
   - Integration tests (end-to-end flows)
3. Execute the test suite.
4. Generate `test_report.md` in `.factory/` with pass/fail summary.
5. Update `.factory/state.json`: set `current_phase` to `"testing"`,
   mark `phases.testing.status` as `"complete"` (if all pass).
6. Append a `test_complete` event to `.factory/events.jsonl`.

## Post-conditions
- All tests pass.
- `.factory/test_report.md` exists.
- Ready for `/fba:review`.

> Note: Full test generation and execution is implemented in M3.

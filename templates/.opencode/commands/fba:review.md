---
description: Review code quality, security, and spec adherence for the generated module
agent: revisor
---

# fba:review

Review the generated Odoo v18 module for quality, security, and adherence
to PRD and SDD specifications.

## Pre-conditions
- `.factory/state.json` must have `current_phase: "testing"`.
- The Odoo module code and `.factory/prd.md` exist.

## Steps

1. Review code quality:
   - PEP8 / Odoo coding conventions
   - Code organization and naming
   - Proper use of Odoo ORM and patterns
2. Review security:
   - Access control definitions (CSV and model-level)
   - Input validation and sanitization
   - Sensitive data exposure
3. Review spec adherence:
   - Verify each PRD requirement is implemented
   - Verify each SDD component is correctly built
4. Generate `review_report.md` in `.factory/` with findings.
5. Update `.factory/state.json`: set `current_phase` to `"review"`,
   mark `phases.review.status` as `"complete"` (if no critical issues).
6. Append a `review_complete` event to `.factory/events.jsonl`.

## Post-conditions
- `.factory/review_report.md` exists with no critical issues.
- Ready for `/fba:ship`.

> Note: Full review is implemented in M3.

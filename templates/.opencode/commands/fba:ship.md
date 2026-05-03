---
description: Generate CI/CD workflow and prepare the module for release
agent: cicd_manager
---

# fba:ship

Generate the CI/CD workflow for the Odoo module and prepare for release.

## Pre-conditions
- `.factory/state.json` must have `current_phase: "review"`.
- The Odoo module code has passed review with no critical issues.

## Steps

1. Read module structure to determine build requirements.
2. Generate GitHub Actions workflow for the module.
3. Update `.factory/state.json`: set `current_phase` to `"ci_cd"`,
   mark `phases.ci_cd.status` as `"complete"`, set `current_phase` to `"complete"`.
4. Append a `ship_complete` event to `.factory/events.jsonl`.

## Post-conditions
- CI/CD workflow is available in `.github/workflows/`.
- `.factory/state.json` has `current_phase: "complete"`.
- The module is ready for production deployment.

> Note: Full CI/CD integration is implemented in M3.

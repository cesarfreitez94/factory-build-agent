---
description: Generate CI/CD workflow and prepare the module for release
agent: cicd_manager
---

# fba:ship

Generate the CI/CD GitHub Actions workflow for the Odoo v18 module, validate
release readiness, produce ship reports, and finalize the project lifecycle.

## Pre-conditions
- `.factory/state.json` must have `current_phase: "review"` and
  `phases.review.status` as `"complete"`.
- `.factory/schema.json` (SSOT) exists.
- `.factory/test_report.json` exists (tests passed).
- `.factory/review_report.json` exists (no critical issues).
- The Odoo module code exists in `<module_name>/`.
- Gate `review` passed (`fba gate review`).

## Steps

### 1. Load All Inputs
Read `.factory/schema.json` to understand module structure (manifest, models,
dependencies). Read `.factory/test_report.json` and `.factory/review_report.json`
for quality gate results. Read `.factory/state.json` for project metadata.

### 2. Validate Release Readiness
Verify all release prerequisites:
- `test_report.json` has tests with `passed > 0`
- `review_report.json` has `critical_issues == 0`
- `schema.json` is valid
- Module directory exists with `__manifest__.py`, `models/`, `views/`, `security/`

Stop and report any failures before proceeding.

### 3. Generate GitHub Actions Workflow
Create `.github/workflows/factory-ci.yml` with:
- Push and PR triggers on `main` branch
- Python matrix: 3.11, 3.12, 3.13
- Steps: setup Python, install fba, lint module with ruff, verify module structure,
  run pytest (framework tests), verify CLI, validate artifacts, run gates
- Customize module name from `schema.json["manifest"]["name"]`

### 4. Generate Ship Reports
Create `.factory/ship_report.json` with:
```json
{
  "module": "<module_name>",
  "timestamp": "<ISO8601>",
  "framework_version": "<version>",
  "release_ready": true,
  "artifacts": {
    "prd": true, "sdd": true, "schema": true,
    "tests": true, "review": true, "ci_workflow": true
  },
  "test_summary": { "total": <N>, "passed": <N>, "failed": <N> },
  "review_summary": { "overall": "<passed|warnings>", "critical_issues": <N>, "warnings": <N> },
  "module_stats": { "models": <N>, "views": <N>, "security_groups": <N>, "python_files": <N>, "xml_files": <N> }
}
```

Create `.factory/ship_report.md` with human-readable summary:
- Artifact status table
- Test and review results
- Module structure stats
- CI/CD workflow location

### 5. Update State and Log Events
Set `phases.ci_cd.status` to `"complete"`, set `current_phase` to `"complete"`,
and add a `complete` phase entry in `.factory/state.json`.

Append a `ship_complete` event to `.factory/events.jsonl`:
```json
{"type": "ship_complete", "data": {"module": "<module_name>", "release_ready": true}}
```

## Post-conditions
- `.github/workflows/factory-ci.yml` exists with valid CI/CD pipeline.
- `.factory/ship_report.json` exists and is valid.
- `.factory/ship_report.md` exists.
- `.factory/state.json` has `current_phase: "complete"`.
- The project lifecycle is complete. Module is ready for release.

> Note: This is the terminal phase. After completion, the orchestrator reports
> success and stops. No further phase progression is possible.

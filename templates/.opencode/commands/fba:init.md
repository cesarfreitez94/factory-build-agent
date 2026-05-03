---
description: Initialize and validate the Factory Build Agent project structure
agent: orchestrator
---

# fba:init

Initialize a project with Factory Build Agent. This command must be run
before any other FBA slash command.

## Pre-conditions
- A project directory exists (the current directory).
- The user has Python 3.11+ and the `fba` CLI installed.

## Steps

1. Confirm `.factory/` does NOT exist. If it does, report that the project
   is already initialized and exit.

2. Run `fba init` in the project directory to create:
   - `.factory/state.json` — state machine tracking
   - `.factory/events.jsonl` — append-only event log
   - `.opencode/agents/` — agent definitions (Markdown)
   - `.opencode/commands/` — slash command definitions
   - `.github/workflows/factory-ci.yml` — CI/CD template
   - `AGENTS.md` — project context for OpenCode agents

3. Verify all key files were created:
   - `.factory/state.json` exists and is valid JSON
   - `.opencode/agents/orchestrator.md` exists
   - `.opencode/commands/fba:init.md` exists
   - `.github/workflows/factory-ci.yml` exists
   - `AGENTS.md` exists

4. Validate the generated `state.json` against the schema at
   `schemas/state.schema.json`.

5. Report successful initialization and guide the user to the next step:
   `/fba:elicit "describe your Odoo module idea"`

## Post-conditions
- `.factory/state.json` has `current_phase: "init"` and all phases marked `pending`.
- `.factory/events.jsonl` contains the init event.
- The project is ready for the elicitation phase.

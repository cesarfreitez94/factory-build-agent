---
description: Initialize project with Factory Build Agent structure
---

# fba:init

Initialize the project with Factory Build Agent directories and configuration:

1. Create `.factory/` directory with `state.json` and `events.jsonl` for state management.
2. Create `.opencode/` with slash commands and agent definitions.
3. Create `.github/workflows/` with CI/CD templates.
4. Generate a project-specific `AGENTS.md` with workflow instructions.

The project is now ready for the development flow: elicit -> specify -> plan -> tasks -> build -> test -> review -> ship.

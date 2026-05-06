---
description: Assemble deterministic schema.json (SSOT) from tasks and generate Odoo v18 module code with zero interpretation
agent: constructor
---

# fba:build

Generate complete Odoo v18 module source code through a two-phase deterministic
pipeline: Schema Assembly (produce SSOT) → Code Rendering (zero interpretation).

## Architecture

```
tasks/index.json + T*.json + SDD.md + module_registry.json
        │
        ▼
  Schema Manager (assembly + normalization + registry lookup)
        │
        ▼
  schema.json (SSOT — single source of truth)
        │
        ▼
  Code Renderer (iterative per task, zero interpretation)
        │
        ▼
  odoo_module/
```

## Pre-conditions
- `.factory/state.json` must have `current_phase: "construction"`.
- `.factory/sdd.md` exists.
- `.factory/tasks/index.json` exists with a valid task index.
- All individual task files `.factory/tasks/T*.json` exist.
- `.factory/module_registry.json` exists (copied by `fba init`).
- The project has a git repository initialized.
- Gates `tasks` passed (`fba gate tasks`).

## Phase 1: Schema Assembly

### 1.1 Load All Inputs
Read all sources that define what the module should be:
- `.factory/sdd.md` — architecture, models, views, security specification
- `.factory/tasks/index.json` — task manifest and ordering
- `.factory/tasks/T*.json` — each task's components, fields, files_to_generate
- `.factory/module_registry.json` — Odoo core modules and their canonical models

### 1.2 Assemble Deterministic Schema
Produce `.factory/schema.json` by normalizing all task components into a single
deterministic structure. This is the Schema Manager's core responsibility.

#### Normalization Rules
1. **Merge models**: if two tasks reference the same model, merge their fields.
   Deduplicate by field `name`. Conflicts (same name, different type) are errors.
2. **Naming conventions**:
   - Many2one fields MUST end with `_id` (e.g., `partner_id`, not `partner`)
   - Many2many fields MUST end with `_ids` (e.g., `tag_ids`, not `tags`)
   - One2many fields MUST end with `_ids` (e.g., `line_ids`)
   - Model names: lowercase dot-separated (e.g., `vehicle.vehicle`)
   - View names: `{model}.{type}` (e.g., `vehicle.vehicle.form`)
3. **Relation resolution**: Every relational field (Many2one, One2many, Many2many)
   MUST specify `relation` pointing to an existing model in the schema OR in the
   module registry.
4. **Registry lookup**: For each model being created, check `module_registry.json`:
   - If a core model matches the intent → mode MUST be `extend`, not `new`
   - If no match → mode is `new`

### 1.3 schema.json Structure
```json
{
  "manifest": {
    "name": "vehicle_registry",
    "version": "18.0.1.0.0",
    "summary": "Vehicle registration module",
    "depends": ["base"],
    "license": "LGPL-3"
  },
  "models": [
    {
      "name": "vehicle.vehicle",
      "description": "Main vehicle record",
      "inherit": null,
      "mode": "new",
      "fields": [
        {
          "name": "plate",
          "type": "Char",
          "label": "Placa",
          "required": true,
          "size": 20
        },
        {
          "name": "brand_id",
          "type": "Many2one",
          "label": "Marca",
          "relation": "vehicle.brand",
          "string": "Marca"
        }
      ]
    }
  ],
  "views": [
    {
      "name": "vehicle.vehicle.form",
      "type": "form",
      "model": "vehicle.vehicle",
      "fields": ["plate", "brand_id", "model_id", "year", "color"]
    }
  ],
  "security": {
    "groups": [
      {"name": "vehicle_user", "category": "Vehicle Registry"}
    ],
    "access_rights": [
      {"model": "vehicle.vehicle", "group": "vehicle_user", "perm_read": true, "perm_write": true, "perm_create": true, "perm_unlink": true}
    ],
    "record_rules": []
  },
  "data": []
}
```

### 1.4 Validate schema.json
Run `fba gate schema` to validate:
- Schema passes `schema.schema.json` validation
- All field names follow naming conventions
- All view fields reference existing model fields
- No duplicate of Odoo core models (unless mode=extend)
- All relations resolve to existing models

Do NOT proceed to Phase 2 if validation fails.

### 1.5 Commit schema.json
```bash
git add .factory/schema.json && git commit -m "feat(#XX): schema SSOT assembly"
```

## Phase 2: Iterative Code Rendering

The Code Renderer generates code files STRICTLY from `schema.json`. It has ZERO
interpretation authority — it is a translator from schema to Odoo Python/XML.

### Builder Contract (MANDATORY)
- **Input**: schema.json ONLY (not SDD, not tasks)
- **No interpretation**: do not rename fields, do not add/remove fields, do not
  change model structure. The schema IS the truth.
- **No invention**: do not create models or fields not present in schema.json
- **Module registry is final**: if schema says mode=extend for a model, extend
  the core model via `_inherit` — do not create a new model

### 2.1 Iterate Tasks
For each task in `index.json`, ordered by `order`:

a. **Read the task file** to get `files_to_generate[]` and `sdd_components[]`.

b. **Extract schema subset**: from `schema.json`, extract only the models,
   fields, views, and security entries that this task owns (matched via
   `sdd_components[]`).

c. **Read existing code** from the module directory — include a brief
   summary of already-generated files (models defined, views created).

d. **Invoke a fresh sub-agent session** using the `task` tool:
   ```
   task(
     description="Render task TXXX: <name>",
     prompt="You are RENDERING Odoo v18 module code from schema.json.
     You do NOT interpret, design, or make decisions. You translate
     schema entries into Python/XML files exactly as specified.

   Context:
   - Schema subset: <schema entries for this task>
   - Files to generate: <files_to_generate[]>
   - Existing code summary: <brief summary of already-generated files>

   Render the files EXACTLY as specified in the schema. Return which files
   you created/modified and a brief summary.",
     subagent_type="general"
   )
   ```
   Do NOT pass `task_id` — each task must be a fresh session.

e. **Commit the generated code**:
   ```bash
   git add <module_name>/ && git commit -m "feat(#XX): task <id> <name>"
   ```

f. **Log progress** — append an event to `.factory/events.jsonl`:
   ```json
   {"type": "task_built", "data": {"task_id": "<id>", "files_generated": [...], "status": "complete"}}
   ```

### 2.2 Finalize
After all tasks complete:
- Update `.factory/state.json`: set `phases.construction.status` to `"complete"`.
  DO NOT change `current_phase` — the orchestrator handles transitions.
- Append a `build_complete` event to `.factory/events.jsonl`.

## Iterative Protocol Rules

1. **One session per task** — never reuse `task_id` between tasks.
2. **Schema ONLY** — code renderer sub-agents receive schema subset, not raw tasks/SDD.
3. **Ordered execution** — tasks must be processed in `order` sequence.
4. **Per-task commits** — each task gets its own git commit.
5. **No interpretation** — the schema is the SSOT. Render exactly what it specifies.

## Post-conditions
- `.factory/schema.json` exists and is valid (SSOT).
- A valid Odoo v18 module directory exists with all files from `files_to_generate[]`.
- All code is generated deterministically from schema.json (zero interpretation).
- One git commit per task + one commit for schema assembly.
- `phases.construction.status` is `"complete"`.
- Ready for `/fba:test`.

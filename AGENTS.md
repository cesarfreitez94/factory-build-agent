# Factory Build Agent (FBA)

> Este archivo es el contexto del proyecto para OpenCode y los agentes de IA.
> Al iniciar una sesion, OpenCode lee este archivo para entender el proyecto.

## What is this project?

Factory Build Agent is a multi-agent development framework that runs on OpenCode. Its purpose is to
automate the full lifecycle of Odoo v18 module development — from requirements elicitation to CI/CD
deployment — using specialized AI agents coordinated by an orchestrator.

See: [README.md](README.md) for project overview, [ROADMAP.md](ROADMAP.md) for current status,
[docs/PRD.md](docs/PRD.md) for the framework's own PRD.

## What we are NOT building

This project is NOT an Odoo module. It is a framework that GENERATES Odoo v18 modules. The output
of this framework is Odoo addons; the framework itself is a development tool.

## Architecture

### Runtime
- **OpenCode**: The agent CLI that executes slash commands and manages sub-agents.
- **Aux CLI**: Python 3.11+ (Click library) for the `fba` command-line tool.

### State Management
- `.factory/state.json` — State machine tracking current phase, artifacts, agent assignments.
- `.factory/events.jsonl` — Append-only event log for audit trail.
- Communication: Hybrid (file-based artifacts + event log + git).

### Agent System

1 orchestrator + 9 sub-agents defined declaratively in `.opencode/agents/*.md`:
- **Orchestrator** — Coordinates phases, validates artifacts, invokes sub-agents.
- **Elicitador** — Requirements elicitation using BABOK methodology.
- **Documentador** — Generates PRD.md and SDD.md documentation.
- **Planificador** — Generates technical plan and Odoo v18 architecture.
- **Revisor de Artefactos** — Validates artifacts against schemas and cross-artifact coherence.
- **Validador Semantico** — Validates semantic alignment of artifacts against original request.
- **Code Generator** — Generates Odoo v18 module code. Internally operates as:
  - Schema Manager — Assembles deterministic `schema.json` (SSOT) from tasks + SDD + module registry.
  - Code Renderer — Generates code files from `schema.json` with zero interpretation.
- **Tester/QA** — Generates and runs tests for the generated Odoo modules.
- **Revisor de Codigo** — Code quality, security, and spec-adherence review.
- **CI/CD Manager** — Generates GitHub Actions workflows and manages releases.

The agent system is extensible: adding a new sub-agent = adding a Markdown definition + a slash command.

### Pipeline (tasks → construction)

```
planner → tasks/index.json + T*.json → code-generator
                                          ├── Schema Manager: assembly + normalization + registry lookup
                                          │   → produces schema.json (SSOT)
                                          └── Code Renderer: iterative generation per task
                                              → produces odoo_module/
```

The Schema Manager eliminates ambiguity before code generation. Downstream agents
(code renderer, view generator, security generator) consume ONLY `schema.json`,
never reinterpret structure independently.

## Development Workflow

> **IMPORTANTE**: Todo desarrollo debe seguir el flujo descrito en [CONTRIBUTING.md](CONTRIBUTING.md).
> Este documento es la fuente de verdad del proceso.

### Reglas Fundamentales

1. **NUNCA hacer commit directo a `main`**. Solo se mergea via Pull Request.
2. **Siempre crear un GitHub Issue antes de escribir codigo**. Nada se desarrolla sin issue.
3. **Usar branching**: `milestone/X.0-descripcion` para milestones, `feat/X.Y.Z-descripcion` para sub-tareas.
4. **Referenciar el issue en cada commit**: `feat(#XX): descripcion`.
5. **Tests deben pasar** antes de abrir PR.
6. **Un feat branch por sub-tarea**. Secuencial: no empezar feat/X.Y+1 hasta que feat/X.Y este mergeado.
7. **Si un feat ya mergeado necesita fix**: crear `feat/X.Y.Z` donde Z es fix/mejora.
8. **Todos los PRs requieren 1 aprobacion** antes de merge.
9. **Cada milestone incluye `docs/testing/`** con instrucciones para el usuario.
10. **PR de milestone a `main` requiere validacion manual del usuario.**
    Sin confirmacion explicita del usuario, el PR a `main` no se abre.
11. **Cambios de alcance o arquitectura requieren actualizar documentacion.**
    Agentes nuevos, fases, artefactos, schemas, o componentes arquitectonicos
    → actualizar AGENTS.md, ROADMAP.md, CHANGELOG.md, y templates/docs/testing/.
12. **El PR de milestone a `main` DEBE incluir ROADMAP.md y CHANGELOG.md actualizados.**
    El milestone debe aparecer como ✅ Completado con fecha de fin. Sin esto, el PR no se aprueba.

### Ciclo de Vida de un Milestone

```
1. Crear Epic Issue en GitHub (label: epic, milestone/X)
2. Crear branch: milestone/X.0-descripcion (desde main)
3. Desglosar sub-issues con labels de fase y tipo
4. Iterar feat/X.Y.Z → PR → merge a milestone branch
5. Completadas todas las sub-issues → preparar PR a main:
   a. Actualizar ROADMAP.md: marcar milestone como ✅ Completado con fecha de fin
   b. Actualizar CHANGELOG.md: agregar entrada de cierre del milestone
   c. Ejecutar pytest y confirmar 0 fallos
6. Validar el milestone branch manualmente:
   a. Seguir los pasos en docs/testing/mX-*.md
   b. El usuario debe dar confirmacion explicita
   c. El agente NO PUEDE abrir PR a main sin esta confirmacion
7. PR de milestone/X.0 → main → aprobar → merge
8. Verificar post-merge: confirmar que ROADMAP.md en main muestra ✅ Completado
9. Cerrar Epic Issue

⛔ REGLA BLOQUEANTE: El PR de milestone a main DEBE incluir la actualizacion
   de ROADMAP.md y CHANGELOG.md. No se aprueba un PR sin estos cambios.
```

### Convencion de Commits

Todos los commits deben seguir [Conventional Commits](https://www.conventionalcommits.org/):
```
feat(#XX): descripcion    # nueva feature
fix(#XX): descripcion     # bug fix
docs(#XX): descripcion    # documentacion
test(#XX): descripcion    # tests
chore(#XX): descripcion   # mantenimiento
refactor(#XX): descripcion # refactor sin cambio funcional
```

### Estructura de Branches

```
main (PROTEGIDO - solo PR merge)
├── milestone/1.0-elicitacion-babok
│   ├── feat/1.1-elicitacion-prompt
│   ├── feat/1.1.1-corregir-stakeholders  (fix post-merge de feat/1.1)
│   └── feat/1.2-flujo-preguntas
├── milestone/2.0-planificacion-sdd
└── milestone/3.0-construccion-mvp
```

### Labels de Issues

| Label | Uso |
|-------|-----|
| `epic` | Issue padre de milestone |
| `milestone/0`, `milestone/1`, ... | Fase del milestone |
| `phase/elicitacion`, `phase/docs`, ... | Agente/fase especifica |
| `type/feature`, `type/test`, `type/docs`, `type/chore` | Tipo de tarea |
| `priority/high`, `priority/medium`, `priority/low` | Prioridad |

## Integration Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Runtime | OpenCode | Existing open-source agent CLI, multi-model, multi-session |
| Language | Python 3.11+ | Odoo is Python, SpecKit is Python, ERP ecosystem alignment |
| Methodology | BABOK v1 | Industry-standard business analysis framework |
| Communication | Files + Events | Simple, traceable, no external infrastructure |
| CI/CD | GitHub Actions | Native GitHub integration |
| OpenSpec/SpecKit | Native compatibility | Artifact format compatibility, no hard dependencies |
| Extensibility | Markdown declarative | Add agents/methodologies without modifying core code |
| SSOT | schema.json | Single source of truth for module structure, eliminates ambiguity between tasks and code |

## Development Phases

See [ROADMAP.md](ROADMAP.md) for full milestone details and progress tracking.

- **M0: Foundation** — COMPLETED. Repo structure, orchestrator, `fba init` CLI, CI/CD for the framework.
- **M1: Elicitation + Documentation** — COMPLETED. BABOK elicitation flow, PRD.md generation.
- **M2: Planning + SDD** — COMPLETED. SDD.md generation, technical plan, traceability PRD→SDD.
- **M3: Construction + MVP** — COMPLETED. Full E2E: Odoo v18 CRUD module built, tested, reviewed, shipped.
- **M4: Gates System** — COMPLETED. Declarative gate system, artifact reviewer, semantic validator.
- **M5: Bug Fixes & Stability** — COMPLETED. Post-release fixes and stabilization.
- **M10: Framework Meta-Development** — COMPLETED. Meta-agents for autonomous framework development.
- **M11: Foundation Hardening** — IN PROGRESS. Bug fixes (#2, #7, #9, #10) and `fba doctor`.
  M12-M15 will be implemented sequentially after M11 (replaces M6-M9 — see ROADMAP.md).

## Tech Stack

- **Python 3.11+** with pyproject.toml (setuptools)
- **Click** for CLI
- **pytest** for framework testing
- **JSON Schema** (jsonschema) for artifact validation
- **PyYAML** for frontmatter and state file parsing

## Project Structure

```
factory-build-agent/
├── AGENTS.md              # This file — context for OpenCode
├── CONTRIBUTING.md        # Development workflow (MUST READ)
├── README.md              # Human-facing project overview
├── ROADMAP.md             # Milestones and progress tracking
├── CHANGELOG.md           # Release changelog
├── pyproject.toml         # Python package configuration
├── .github/
│   ├── workflows/ci.yml   # Framework CI
│   ├── ISSUE_TEMPLATE/    # Issue templates
│   └── PULL_REQUEST_TEMPLATE.md
├── .opencode/             # Framework's own agent/command definitions
│   ├── agents/            # Meta-agent definitions (framework-orchestrator, planner, builder)
│   └── commands/          # Slash commands for meta-development (/fba:fw, /fba:fw-plan, /fba:fw-build)
├── .factory/              # Framework's own development state
│   └── framework-state.json
├── src/fba/               # Framework source code
├── templates/             # Templates copied by `fba init`
├── schemas/               # JSON Schemas for artifact validation
├── tests/                 # Framework tests
└── docs/                  # Framework documentation
```

## Conventions

- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/).
- **Tests**: Required for every feature. Run with `pytest`.
- **Docs**: Document testing procedures in `docs/testing/`.
- **No comments** in code unless explicitly requested.
- **Language**: Project communication and documentation in Spanish. Code identifiers in English.

## Framework Meta-Development

> El desarrollo del propio framework FBA se gestiona con 3 agentes meta.
> Este sistema es el punto de entrada para toda mejora del framework desde M10 en adelante.

### Meta-Agents

| Agente | Modo | Rol |
|--------|------|-----|
| `framework-orchestrator` | `primary` | Coordinador. Traduce intenciones del usuario en delegacion. NUNCA implementa. |
| `framework-planner` | `subagent` (hidden) | Arquitecto. Descompone intenciones en `fw-brief.md`. CERO suposiciones. |
| `framework-builder` | `subagent` (hidden) | Constructor. Ejecuta briefs siguiendo estrictamente CONTRIBUTING.md. |

### Flujo

```
/fba:fw → orchestrator lee ROADMAP/state/changelog → presenta resumen
                                                      ↓
                                            espera intencion del usuario
                                                      ↓
                              ┌───────────────────────┼───────────────────────┐
                              ↓                       ↓                       ↓
                        /fba:fw-plan            /fba:fw-build            respuesta directa
                              ↓                       ↓
                         planner genera          builder ejecuta
                         fw-brief.md           feats secuenciales
                                                  ↓
                                           pytest → commit → PR al milestone
```

### Archivos del sistema

- `.factory/framework-state.json` — Estado persistente entre sesiones.
- `.factory/fw-brief.md` — Plan ejecutable generado por el planner.
- `.opencode/agents/framework-*.md` — Definiciones de los 3 agentes meta.
- `.opencode/commands/fba:fw*.md` — Slash commands del sistema meta.

Los agentes meta **no van en templates/** — son para el desarrollo de este repositorio,
no para proyectos Odoo generados.

## Working on this project

When working on this project within OpenCode:
1. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the full development workflow.
2. Read [ROADMAP.md](ROADMAP.md) to know the current milestone and pending tasks.
3. Read this file (AGENTS.md) for architectural context.
4. Check open GitHub Issues for current tasks.
5. NEVER commit directly to `main`.
6. Create an Issue before writing code.
7. Run `pytest` after every change.
8. Use conventional commits referencing the issue number.

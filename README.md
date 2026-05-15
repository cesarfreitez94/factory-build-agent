# Factory Build Agent

Framework multi-agente para desarrollo de modulos Odoo v18 con IA.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenCode](https://img.shields.io/badge/runs_on-OpenCode-orange.svg)](https://opencode.ai)

## Que es FBA?

Factory Build Agent es un framework de desarrollo por agentes de IA que automatiza
el ciclo completo de creacion de modulos Odoo v18:

- **Elicita** requisitos usando BABOK + Impact Mapping + Event Storming + Example Mapping
- **Genera** PRD (Product Requirements Document) y SDD (Software Design Document)
- **Construye** modulos Odoo v18 automaticamente (modelos, vistas, seguridad, datos)
- **Prueba** los modulos generados con tests unitarios y de integracion
- **Revisa** la calidad del codigo generado
- **Integra** CI/CD con GitHub Actions para despliegue continuo

Se ejecuta sobre **OpenCode** como runtime, aprovechando su sistema de agentes,
slash commands y soporte multi-modelo.

Inspirado en los conceptos de **OpenSpec** (Fission-AI) y **SpecKit** (GitHub).
Compatible con sus formatos de artefactos.

## Instalacion

```bash
pip install fba
```

## Uso Rapido

```bash
# 1. Inicializar un proyecto Odoo para usar FBA
cd mi-proyecto-odoo
fba init

# 2. Abrir con OpenCode y empezar el flujo
opencode .

# 3. Dentro de OpenCode, elicitar requisitos
# > /fba:elicit "Quiero un modulo de facturacion electronica para Odoo 18"

# 4. Seguir el flujo completo
# > /fba:specify
# > /fba:plan
# > /fba:tasks
# > /fba:construct
# > /fba:test
# > /fba:review
# > /fba:ship
```

## Flujo de Desarrollo

```
/fba:init ──► /fba:elicit ──► /fba:specify ──► /fba:plan ──► /fba:tasks
                                                                    │
/fba:ship ◄── /fba:review ◄── /fba:test ◄── /fba:construct ◄───────────┘
```

## Current Status

**11/13 milestones completados** | **719 tests** | **0 failures**

| Milestone | Status |
|-----------|--------|
| M0: Foundation | ✅ |
| M1: Elicitation + Docs | ✅ |
| M2: Planning + SDD | ✅ |
| M3: Construction + MVP | ✅ |
| M4: Gates System | ✅ |
| M5: Bug Fixes | ✅ |
| M10: Framework Meta-Dev | ✅ |
| M11: Foundation Hardening | ✅ |
| M12: Diff & Trazabilidad | ✅ |
| M13: Reliability & Quality | ✅ |
| M14: Odoo Depth | ✅ |
| M15: Advanced QA | ⏳ |

### M14: Odoo Depth (latest)
Enterprise-grade Odoo v18 module generation:
- **Wizards** — TransientModel + form/action views
- **Workflows** — ir.actions.server + cron automation
- **Reports** — QWeb templates + paperformat
- **Controllers** — http.Controller + @http.route
- **Migrations** — DiffEngine-based schema change detection → pre/post/end-migrate.py
- **i18n** — .pot + .po generation (es_ES, es_CL), OCA-ready

## Arquitectura

### Agent System

FBA has **two orchestrator levels**:

#### Framework Orchestrator (meta-development)
1 orchestrator + 5 meta-agents for autonomous framework development:
- **framework-orchestrator** — Entry point for all framework improvements since M10
- **framework-explorer** — Read-only repo exploration
- **framework-registry** — State persistence (.factory/framework-state.json)
- **framework-planner** — Decomposes intent into executable briefs (fw-brief.md)
- **framework-builder** — Implements briefs following CONTRIBUTING.md
- **framework-git** — Git operations with validations

#### Project Orchestrator (Odoo module generation)
1 orchestrator + 9 sub-agents for Odoo v18 module lifecycle:
- **Orchestrator** — Coordinates phases, validates artifacts, invokes sub-agents
- **Elicitador** — Requirements elicitation with BABOK + Impact Mapping + Event Storming + Example Mapping
- **Documentador** — PRD.md + SDD.md generation
- **Planificador** — Technical plan + Odoo v18 architecture
- **Code Generator** — Schema Manager (SSOT) + Code Renderer
- **Tester/QA** — Test generation and execution
- **Revisor de Codigo** — Code quality, security, spec-adherence
- **CI/CD Manager** — GitHub Actions workflows + releases
- **Revisor de Artefactos** — Artifact validation against schemas
- **Validador Semantico** — Semantic alignment validation

Los agentes se comunican mediante un sistema hibrido: artefactos en archivos
(.factory/) + registro de eventos (events.jsonl) + git.

## Development Phases

See [ROADMAP.md](ROADMAP.md) for full details.

- **M0-M5, M10-M14**: ✅ Completed (11 milestones)
- **M15: Advanced QA**: ⏳ Planned — Playwright E2E, performance, concurrency

## Documentacion

| Documento | Descripcion |
|-----------|-------------|
| [ROADMAP.md](ROADMAP.md) | Estado del proyecto y plan de hitos |
| [docs/PRD.md](docs/PRD.md) | PRD del propio framework |
| [AGENTS.md](AGENTS.md) | Contexto tecnico para asistentes AI (OpenCode) |

## Estructura del Proyecto

```
factory-build-agent/
├── AGENTS.md              # Contexto para OpenCode
├── CONTRIBUTING.md        # Workflow de desarrollo
├── README.md              # Este archivo
├── ROADMAP.md             # Hitos y progreso
├── CHANGELOG.md           # Registro de cambios
├── LICENSE                # Licencia MIT
├── pyproject.toml         # Configuracion del paquete Python
├── .github/               # CI/CD del framework (workflows, templates)
├── src/fba/               # Codigo fuente del framework
├── templates/             # Plantillas que `fba init` copia al proyecto Odoo
├── schemas/               # JSON Schemas para validacion de artefactos
├── tests/                 # Tests del framework
└── docs/                  # Documentacion del framework
    └── testing/           # Guias de testing por milestone
```

## Requisitos

- Python 3.11 o superior
- OpenCode ([opencode.ai](https://opencode.ai))

## Licencia

MIT - Ver [LICENSE](LICENSE)

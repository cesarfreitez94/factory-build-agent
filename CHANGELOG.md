# Changelog

Todas las cambios notables del proyecto Factory Build Agent se documentan en este archivo.

El formato esta basado en [Keep a Changelog](https://keepachangelog.com/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### M17 Semantic Core
- #157 feat/17.1: Ontologia cerrada NodeType/EdgeType para el grafo semantico, schema `schemas/graph.schema.json`, comando `fba graph validate` y documentacion inicial de testing M17.
- #159 feat/17.2: `GraphManager` persiste `.factory/graph.json` con atomic writes, genera UUID v4 via `StableIdManager` y expone queries `full_trace`, `impact_of`, `is_covered`, `orphan_nodes`, `dependents` y `governing_adrs` con comandos `fba graph trace/impact/orphans`.

---

## M16: Foundation Intelligence — 2026-05-14

### Resumen
- ModuleRegistry autoindexado con `fba registry index/inspect`
- Odoo version layer (`base/`, `v18/`, `v17/`) + CLI patterns
- Odoo Pattern Knowledge Base con JSON patterns, schema y tests
- Agent Observer Plugin para monitorear agentes meta y generar reportes de observabilidad por sesion

### Feats completados
- #147 feat/16.1: `fba registry index/inspect` autoindexa addons Odoo individuales o carpetas `addons/`, mezcla resultados con `.factory/module_registry.json` dando prioridad al indice nuevo, y persiste el detalle profundo en `.factory/registry_index.json`.
- #151 feat/16.2: Capa version-aware `src/fba/odoo_versions/` con resolver `base/` + `v18/`/`v17/`, merge version-sobre-base y CLI `fba patterns query/list`.
- #152 feat/16.3: Odoo Pattern Knowledge Base poblado con entradas JSON de patrones, deprecaciones y novedades para Odoo, schema `knowledge_entry.schema.json` y tests de integridad/cobertura.
- #154 feat/16.4: Agent Observer Plugin — plugin local `.opencode/plugins/fba-agent-observer.ts` para monitorear agentes meta del framework en `.opencode/agents`, atribuir tokens/costo por agente observado, registrar invocaciones agente-a-agente, herramientas y acceso observable a archivos, y generar reportes Markdown y JSONL por sesion en `.factory/observability/`.
- #146: Infraestructura de colaboracion — creado marco `.codex/` para trabajar con Codex en el meta-desarrollo del framework, con roles operativos, checklist de inicio M16 y plantilla de brief sin modificar runtime ni templates.

### Planificacion
- #148/#147: Preparado arranque de M16 con epic, primer issue funcional (`feat/16.1-module-registry-autoindexado`) y brief local `.factory/fw-brief-m16.md`.
- #144: Integrado `fba-mejoras-post-roadmap.md` al roadmap oficial como milestones planificados M16-M22.
- #144: Movido el detalle historico de milestones completados M0-M15 a `ROADMAP_CHECK.md`, dejando `ROADMAP.md` enfocado en el roadmap activo.
- M16-M22 quedan ordenados por dependencias: Foundation Intelligence, Semantic Core, Input & Extension Layer, Governance & Observability, Graph Enforcement Gates, Learning Loop, y Sustainability & Cost Control.
- Reactivados conceptos pospuestos de M6-M9 cuando ahora tienen prerequisitos cubiertos; los restantes quedan explicitamente pospuestos.

---

## M15: Advanced QA (Capa 4) — 2026-05-13

### Nuevas Capacidades
- **Playwright**: `fba test --playwright` genera specs browser automation para vistas Odoo form, list y kanban desde `schema.json`
- **Performance**: `fba perf` ejecuta benchmarks de carga de schema, generacion con `SchemaManager`, escaneo de artefactos, tiempo y memoria pico
- **Concurrency**: `StateManager` emite warnings si `state.json` cambio desde el ultimo load antes de save
- **Doctor**: `fba doctor --concurrency` detecta marcadores de rollback, temp files atomicos y cambios durante lectura de `state.json`

### Tests
- 12 nuevos tests (`test_playwright.py`, `test_performance.py`, `test_concurrency.py`)
- Issues: #139, #138, #137; epic #140

---

## M14: Odoo Depth (Capa 3) — 2026-05-13

### Nuevas Capacidades
- **Wizards**: Generacion de modelos TransientModel con vistas form/action desde schema.json
- **Workflows**: Generacion de ir.actions.server + ir.cron para automations
- **Reports**: Generacion de QWeb templates + ir.actions.report + paperformat
- **Controllers**: Generacion de clases http.Controller con @http.route
- **Migraciones**: Deteccion de cambios de schema via DiffEngine → pre/post/end-migrate.py + bump de version
- **i18n**: Generacion de .pot + .po para es_ES y es_CL con estandar OCA

### Tests
- 64 nuevos tests (20 wizards + 22 migraciones + 22 i18n)
- 719 tests totales, 0 fallos

---

## M13: Reliability & Quality (Capa 2) — 2026-05-13
- #129 feat/13.5: `ValidationCache` — cache de validacion hash-based en `.factory/.cache/`. Skip de re-validacion si el hash del artefacto no cambio (SHA256). Coexiste con diff engine de M12. Comando: `fba gate --verbose` muestra cache hits/misses. 22 tests.
- #127 feat/13.1: Fix meta-desarrollo (pre-parte del milestone): permissions, subtask, git flow corregidos
- #1 feat/13.2: Security scans: bandit + pip-audit + detect-secrets como gates fail-fast en construction
- #5 feat/13.3: Pre-commit hooks (ruff, black, bandit) con `.pre-commit-config.yaml`
- #6 feat/13.4: Mypy strict mode en `pyproject.toml` (exclude vendor/), `mypy src/fba/` pasa sin errores
- Documentacion: `docs/testing/m13-reliability-quality.md`

### Branch
`milestone/13.0-reliability-quality` (5/5 feats mergeados)

---

## [0.8.0] - 2026-05-13

### M12: Diff, Dependencies & Trazabilidad (Capa 1 avanzada) — ✅ Completado
- #118 feat/12.1: `DiffEngine` — core diff engine para artefactos JSON del pipeline. Compara PRD, SDD, schema.json, tasks/index.json y produce changelogs estructurados (texto y JSON). Comando: `fba diff <file_v1> <file_v2> [--format text|json]`. 34 tests.
- #119 feat/12.2: `ContractEngine` — capa de contratos declarativos (JSON) con invariantes, ownership y allowed mutations por tipo de artefacto. Extiende `fba validate --contract <type>`. Contratos en `schemas/contracts/`. 29 tests.
- #120 feat/12.3: `DependencyAnalyzer` — analisis de integridad de dependencias Odoo. Detecta dependencias no usadas, faltantes y circulares en `__manifest__.py`. Comando: `fba deps check`. 24 tests.
- #121 feat/12.4: `StableIdManager` — sistema de stable IDs con UUID v4 para requisitos, modelos y campos. Asignacion en creacion, inmutabilidad validada por contrato, trazabilidad con `fba trace <uuid>`. 24 tests.
- Documentacion: `docs/testing/m12-diff-deps-traza.md`

### Branch
`milestone/12.0-diff-deps-traza` (4/4 feats mergeados, 604 tests pasando)

---

## [0.6.0] - 2026-05-09

### M10: Framework Meta-Development System (completado)
- Sistema de 3 agentes meta para desarrollo autonomo del framework:
  - `framework-orchestrator`: coordinador, solo delega, no implementa. Optimizado a ~3k tokens (de ~25k).
  - `framework-planner`: arquitecto de mejoras, zero suposiciones
  - `framework-builder`: constructor autonomo, respeta CONTRIBUTING.md estrictamente
- Archivo de estado persistente: `.factory/framework-state.json`
- 3 slash commands: `/fba:fw`, `/fba:fw-plan`, `/fba:fw-build`
- Template de brief: `docs/fw-brief-template.md`
- Schema de validacion: `schemas/framework-state.schema.json`
- M11-M15 se ejecutaran usando este sistema (reemplaza el roadmap M6-M9 original)

---

## [0.7.0] - 2026-05-12

### M11: Foundation Hardening — ✅ Completado (2026-05-12)
- #106: Atomic writes en archivos criticos (`_atomic_write()` con temp file + fsync + os.replace en state.py, cli.py, schema_manager.py)
- #107: Rollback atomico en `StateManager.transition_to()` — backup y restauracion automatica del state si record_event falla
- #108: `ModuleRegistry` con validacion de carga y `warnings.warn()` explicitos para 5 escenarios de error
- #109: Comando `fba doctor` con 5 checks diagnosticos (registry, state, JSON, writability, schema alignment) y exit codes 0/1/2
- #110: `SchemaManager.IMPLEMENTED_TYPES` + deteccion de tipos no implementados (wizard, workflow, report, controller) con AssemblyWarning
- 5 nuevos archivos de test (40 tests nuevos): `test_state_atomicity.py`, `test_state_rollback.py`, `test_registry_robustez.py`, `test_fba_doctor.py`, `test_schema_manager_unknown_types.py`
- Total: 493 tests, 0 fallos

### M12: Diff, Dependencies & Trazabilidad (Capa 1 avanzada)
- #15: Diff engine para artefactos JSON (PRD, SDD, schema, tasks) con changelog estructurado
- Artifact contracts layer: invariantes, ownership, allowed mutations por artefacto
- #12: Analisis de integridad de dependencias Odoo (modulos innecesarios, mixins sin depends, dependencias circulares)
- Stable IDs foundation (UUID v4) para entidades clave: requisitos (RF-*), modelos, campos
- **Absorbe**: Artifact Contracts (old M6.5), Stable IDs (old M6.6)

### M13: Reliability & Quality (Capa 2)
- #1: Security scans: bandit + pip-audit + detect-secrets como gates en construction
- #5: Configuracion de pre-commit hooks (ruff, black, bandit)
- #6: Mypy strict mode progresivo
- #8: Cache de validacion hash-based en `.factory/.cache/`
- **Absorbe**: Cache de validacion (old M8.3)

### M14: Odoo Depth (Capa 3)
- #9 full: Implementacion completa de wizard, workflow, report, controller en SchemaManager + Code Renderer
- #3: Deteccion de cambios de schema y produccion de migraciones Odoo
- #4: Internacionalizacion i18n (generacion .pot/.po, es_ES default, OCA readiness)

### M15: Advanced QA (Capa 4)
- #11: Browser automation con Playwright para vistas Odoo (form, list, kanban)
- #13: Performance test suite (benchmarks de generacion, memoria, tiempo)
- #14: Concurrency safety warnings (deteccion de escrituras concurrentes en state.json)
- **Absorbe**: Playwright (old M9.2)

---

## [0.5.1] - 2026-05-06

### Corregido

- fix: renombrar agente `constructor` → `code-generator` y comando `fba:build` → `fba:construct` (#71)
  - `constructor` es propiedad readonly de `Object.prototype` en JS — causa crash `TypeError` al iniciar `opencode .`
  - `build` es agente built-in de OpenCode — conflicto de nombres
  - Renombrados todos los archivos: templates (2 renames), commands (4 contenido), source cli.py, tests (7 archivos), docs (7 archivos)
- M5: Bug Fixes & Stability — completado (#76)

---

## [0.5.0] - 2026-05-06

### Agregado

- M3: Construccion + MVP (completado) (#59)
  - M3.0a: Task System Redesign — archivos por task (#64)
  - M3.1: Constructor Core — Schema Manager + Modulo Skeleton + Modelos (#60)
    - Schema Manager: capa de determinismo entre tasks y codigo
    - `schema.json`: SSOT (single source of truth) para estructura del modulo
    - `module_registry.json`: registry de modulos core Odoo v18
    - Normalizacion de nombres (many2one → *_id, etc.)
    - Code Renderer: generacion iterativa desde schema (zero interpretation)
    - Gate `schema` validando schema.json
  - M3.2: Constructor Completo — Vistas, Seguridad, Datos (#61)
    - Constructor extendido: vistas (form, list, search, kanban), seguridad (grupos XML, ACL CSV, record rules), datos demo
    - Odoo v18 corrections: `tree` → `list`, `attrs` deprecado, atributos directos (`invisible`, `widget`, `groups`, `tracking`, `states`)
    - Schema extendido: `mail_thread`, `mail_activity`, `manifest.data`, `manifest.demo`, `noupdate`, `category_id`
    - Bugs corregidos: security group assembly, record rule domain, data type, field type case normalization
    - `code-generator.md`: instrucciones completas de rendering Odoo v18 con ejemplos
    - Gate `construction` con nuevas reglas: `view_coverage`, `view_field_check`, `acl_coverage`
    - Tests: 15 nuevos (test_construction_gate.py + extendidos en test_schema_manager.py), 386 total
    - Guia de testing: `docs/testing/m3.2-constructor-completo.md`
  - M3.3: Tester QA + Code Reviewer (#62)
    - Agente `tester_qa.md`: genera tests Odoo TestCase (modelos, vistas, seguridad), ejecuta tests y genera `test_report.md`
    - Agente `revisor_codigo.md`: revisa calidad (PEP8, Odoo conventions), seguridad (ACL, validacion), adherencia a specs (PRD/SDD)
    - Comandos `/fba:test` y `/fba:review` con gates `testing` y `review`
    - Integracion con el orquestador: transiciones `construction` → `testing` → `review` → `ci_cd`
    - Tests de los agentes tester y revisor
  - M3.4: CI/CD Manager + Integracion E2E + Docs (#63)
    - Agente `ci_cd_manager.md`: genera GitHub Actions workflow, valida release readiness, produce ship_report.json/md
    - Comando `/fba:ship` expandido con flujo completo: precondiciones, generacion CI, ship reports, state update
    - Gate `ci_cd`: valida factory-ci.yml, ship_report.json, ship_report.md
    - Fase `ci_cd` integrada en el sistema de fases y transiciones (review → ci_cd → complete)
    - Tests: 8 nuevos (TestCicdManagerAgent + gate ci_cd), ~430 total
    - Documentacion E2E: `docs/testing/m3-construccion.md` con paso 11 (verificacion M3.4)
    - Version bump: 0.4.0 → 0.5.0

---

## [0.4.0] - 2026-05-05

### Agregado

- M4: Sistema de Gates con Agente Revisor de Artefactos (completado) (#46)
  - `src/fba/gate.py`: GateRunner con `RuleResult`, `GateResult`, `GateError` y validaciones declarativas (#47)
  - Integracion de gates en `StateManager.transition_to()`: bloquea transiciones invalidas con `skip_gates` opcional (#48)
  - Comando `fba gate [--all] [phase]` para diagnostico manual de gates (#49)
  - `fba transition --force`: permite saltar gates cuando el usuario lo autoriza (#49)
  - Gates definidos en `state.json["gates"]`, inicializados por `fba init` para elicitation, documentation, planning (#49)
  - `state.schema.json` actualizado con seccion `gates` declarativa (#49)
  - Sub-agente Revisor de Artefactos (`revisor_artefactos.md`): valida artefactos, verifica coherencia cross-artifact, soporta ciclo de correccion (#50)
  - Slash command `/fba:gate`: flujo completo de validacion, diagnostico y correccion (#50)
  - Orquestador actualizado: `/fba:gate` en phase flow, gate check en Phase Progression Protocol (#51)
  - Slash commands `fba:specify` y `fba:plan` actualizados con paso `fba gate` antes de transicion (#51)
  - 43 tests unitarios e integracion del sistema de gates (#52)
  - `docs/testing/m4-gates.md` con 11 pasos de verificacion manual (#53)
  - Validacion semantica de artefactos: nueva regla `semantic_check` en gates (#54)
    - `src/fba/gate.py`: `_check_semantic()` empaqueta datos para evaluacion LLM con `requires_agent: true`
    - `RuleResult.requires_agent` y `GateResult.pending_agent_checks` para detectar reglas que requieren agente
    - `state.schema.json`: nuevo tipo `semantic_check` con `source_path`, `target_path`, `dimensions`
    - CLI `fba gate`: output con `⏳` para reglas pending y contador de `pending agent evaluation(s)`
    - Agente `validador_semantico.md`: evalua 5 dimensiones (dominio, objetivos, terminologia, stakeholders, requisitos)
    - Slash command `/fba:semantic-check` con ciclo de correccion en sesiones nuevas
    - Orquestador y Revisor de Artefactos detectan `pending_agent_checks` y delegan al validador
    - Correcciones delegadas al agente dueno en sesion fresca sin task_id
  - Total: 231 tests

---

## [0.3.0] - 2026-05-04

### Agregado

- M2: Planificacion + SDD (completado)
- Sub-agente Planificador (`planificador.md`) con diseno Odoo v18: modelos, vistas, seguridad, dependencias, workflows, file structure (#34)
- Slash command `/fba:plan` con flujo completo de planificacion y Phase Progression Protocol (#35)
- Schema SDD (`sdd.schema.json`) con validacion completa de 12 componentes (41 tests) (#37)
- Verificacion de trazabilidad PRD -> SDD en `fba validate sdd`: detecta requisitos no mapeados (#38)
- `docs/testing/m2-planificacion.md` con 10 pasos de verificacion manual (#39)
- Total: 171 tests

---

## [0.2.2] - 2026-05-04

### Corregido

- `orchestrator.md`: agregado `question: allow` al bloque de permisos para que el question tool este disponible (#30)
- `fba:elicit.md`: agregado `agent: orchestrator` al frontmatter para que el comando corra en contexto de agente primario (#30)

---

## [0.2.1] - 2026-05-03

### Corregido

- Agentes definidos como `.yaml` convertidos a `.md` con frontmatter OpenCode (#28)
- `fba:elicit` ahora encuentra correctamente al agente `elicitador`
- `StateManager._get_valid_transitions()` ahora lee de `state.json` en vez de parsear `orchestrator.yaml`

### Agregado

- Paso de validacion manual del milestone branch antes del PR a `main` (CONTRIBUTING.md)
- Milestone Completion Protocol en `orchestrator.md`: el agente solicita confirmacion explicita antes de abrir PR a `main`
- Nuevos tests para formato `.md` de agentes (frontmatter, body, modos, permisos)
- Comando `fba update` para actualizar plantillas en proyectos existentes sin tocar estado ni artefactos
- `_cleanup_obsolete()` elimina archivos `.yaml` viejos al ejecutar `fba update`

### Cambiado

- `src/fba/state.py`: eliminada dependencia de `PyYAML` en `StateManager`
- `templates/.opencode/agents/*.yaml` → `templates/.opencode/agents/*.md`
- Documentacion actualizada: `AGENTS.md`, `ROADMAP.md`, `docs/testing/`

---

## [0.2.0] - 2026-05-03

### Agregado

- M1: Elicitacion BABOK + Documentacion (completado)
- Schema PRD (`schemas/prd.schema.json`) con validacion completa (30 tests)
- Modulo `src/fba/state.py`: StateManager para gestion de fases, eventos y artefactos
- Comandos CLI: `fba status`, `fba transition`, `fba record`, `fba validate`
- Agente Elicitador (`elicitador.yaml`) con flujo BABOK single-pass
- Agente Documentador (`documentador.yaml`) con generacion de prd.json + prd.md
- Slash commands expandidos: `fba:elicit.md`, `fba:specify.md`
- `fba init` ahora copia schemas a `.factory/schemas/`
- Tests de integracion simulando flujo elicitacion completo (7 tests)
- Tests de definiciones de agentes (25 tests)
- Guia de testing para M1 (`docs/testing/m1-elicitacion.md`)
- Total: 101 tests, lint limpio

### Cambiado

- `state.schema.json`: fase `init` agregada a las fases
- `orchestrator.yaml`: `specification` → `documentation` para consistencia
- `fba:elicit.md` y `fba:specify.md` expandidos de stubs a documentacion completa

---

## [0.1.0] - 2026-05-02

### Agregado

- Fundacion del proyecto Factory Build Agent (M0 - completado)
- Estructura de directorios y configuracion Python (`pyproject.toml`)
- CLI `fba init` con opcion `--project-dir`
- Templates para proyectos Odoo destino: `.factory/`, `.opencode/`, `.github/`
- Schema JSON para validacion de estado (`state.schema.json`)
- Definicion declarativa del orquestador con valid_transitions (`orchestrator.yaml`)
- 9 slash commands definidos: init, elicit, specify, plan, tasks, build, test, review, ship
- CI/CD del framework con GitHub Actions (ci.yml + main-guard.yml)
- Tests unitarios del CLI (11 tests, 95% cobertura)
- Documentacion raiz: AGENTS.md, README.md, ROADMAP.md
- PRD del propio framework (`docs/PRD.md`)
- CONTRIBUTING.md con workflow de desarrollo
- Guia de testing para M0 (`docs/testing/m0-fundacion.md`)
- GitHub labels, issue templates y PR template
- Branch protection en `main`

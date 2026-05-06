# Changelog

Todas las cambios notables del proyecto Factory Build Agent se documentan en este archivo.

El formato esta basado en [Keep a Changelog](https://keepachangelog.com/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/).

---

## [0.5.1] - 2026-05-06

### Corregido

- fix: renombrar agente `constructor` → `code-generator` y comando `fba:build` → `fba:construct` (#71)
  - `constructor` es propiedad readonly de `Object.prototype` en JS — causa crash `TypeError` al iniciar `opencode .`
  - `build` es agente built-in de OpenCode — conflicto de nombres
  - Renombrados todos los archivos: templates (2 renames), commands (4 contenido), source cli.py, tests (7 archivos), docs (7 archivos)

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

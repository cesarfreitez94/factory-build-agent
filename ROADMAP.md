# Roadmap - Factory Build Agent

Ver tambien: [README.md](README.md) | [AGENTS.md](AGENTS.md) | [docs/PRD.md](docs/PRD.md)

---

## Estado General

| Milestone | Estado | Inicio |
|-----------|--------|--------|
| M0: Fundacion | ✅ Completado | 2026-05-02 / 2026-05-02 |
| M1: Elicitacion + Documentacion | ✅ Completado | 2026-05-03 / 2026-05-03 |
| M2: Planificacion + SDD | ✅ Completado | 2026-05-04 / 2026-05-04 |
| M4: Sistema de Gates | ✅ Completado | 2026-05-05 / 2026-05-05 |
| M3: Construccion + MVP | ✅ Completado | 2026-05-05 / 2026-05-06 |
| M5: Bug Fixes & Stability | ✅ Completado | 2026-05-06 / 2026-05-08 |
| M10: Framework Meta-Development | ✅ Completado | 2026-05-09 / 2026-05-09 |
| M11: Foundation Hardening | ✅ Completado | 2026-05-09 / 2026-05-12 |
| M12: Diff, Dependencies & Trazabilidad | ⏳ Planificado | — / — |
| M13: Reliability & Quality | ⏳ Planificado | — / — |
| M14: Odoo Depth | ⏳ Planificado | — / — |
| M15: Advanced QA | ⏳ Planificado | — / — |

---

## M0: Fundacion
**Objetivo**: Esqueleto del framework funcionando en OpenCode.

**Alcance**: El framework puede inicializar un proyecto Odoo con toda la estructura
necesaria para empezar a trabajar con agentes.

### Tareas

- [x] Definicion de arquitectura y decisiones de diseno
- [x] Documentos raiz: AGENTS.md, README.md, ROADMAP.md
- [x] Repositorio GitHub + git init (incluye issues, templates, workflows)
- [x] `pyproject.toml` con dependencias (Click, pytest, jsonschema, PyYAML)
- [x] Estructura de directorios: `src/fba/`, `templates/`, `schemas/`, `tests/`, `docs/`
- [x] CLI: comando `fba init` que genera estructura `.factory/` y `.opencode/`
- [x] Templates: `state.json`, `events.jsonl`, comandos slash base, agentes YAML
- [x] Schemas: `state.schema.json`
- [x] Orquestador base: slash command `/fba:init` y `orchestrator.yaml`
- [x] AGENTS.md para proyecto Odoo destino (template que `fba init` copia)
- [x] CI del framework: GitHub Actions para tests + lint (ci.yml y main-guard.yml)
- [x] Tests unitarios de CLI y sistema de estado (10 tests, cobertura > 80%)
- [x] `docs/PRD.md` del propio framework

### Verificacion (M8)

```bash
# Paralelizacion
fba construct --parallel 4  # models en paralelo, XML secuencial

# Pipeline resumible
fba resume                  # continua desde ultima fase completada

# Cache
fba gate --verbose          # muestra cache hits/misses

# Multi-modulo
fba init --multi-module
fba module add fleet_management
fba module add vehicle_registry --depends fleet_management
fba module build --all
```

---

## M1: Elicitacion BABOK + Documentacion
**Objetivo**: Elicitar requisitos con BABOK y generar PRD.md valido.

**Alcance**: Un usuario puede describir su idea de modulo Odoo y el framework
genera un PRD estructurado siguiendo la metodologia BABOK.

### Tareas

- [x] Sub-agente Elicitador (BABOK Elicitation & Collaboration, Requirements Life Cycle)
- [x] Slash command `/fba:elicit` con flujo completo BABOK single-pass
- [x] Flujo de preguntas estructurado BABOK:
  - Contexto del negocio y stakeholders
  - Objetivos y metas
  - Requisitos funcionales
  - Requisitos no funcionales
  - Restricciones y dependencias
  - Criterios de aceptacion
- [x] Sub-agente Documentador: toma output del elicitador y genera PRD.md + prd.json
- [x] Template PRD.md (Vision, Stakeholders, Requisitos, Criterios, Glosario)
- [x] Schema JSON para validar PRD (`schemas/prd.schema.json`)
- [x] State management (`src/fba/state.py`) con StateManager
- [x] Comandos CLI: `fba status`, `fba transition`, `fba record`, `fba validate`
- [x] Tests unitarios + integracion (101 tests, flujo elicitacion completo)

### Verificacion

```
fba init
fba transition elicitation   # simula /fba:elicit
fba transition documentation # simula /fba:specify
fba validate prd             # valida PRD contra schema
```

---

## M2: Planificacion + SDD
**Objetivo**: Generar SDD y plan tecnico desde PRD.

**Alcance**: A partir de un PRD valido, el framework genera el diseno tecnico
especifico para Odoo v18 con trazabilidad completa.

### Tareas

- [x] Sub-agente Planificador (arquitectura Odoo v18)
- [x] Slash command `/fba:plan`
- [x] Template SDD.md (Arquitectura, Modelos, Vistas, Seguridad, Dependencias, API)
- [x] Template plan.md (Stack, Fases, Riesgos, Estimaciones)
- [x] Schema JSON para validar SDD
- [x] Trazabilidad PRD -> SDD (cada requisito mapeado a componente de diseno)
- [x] Tests

### Verificacion

```
/fba:plan  # produce SDD.md + plan.md validos con trazabilidad al PRD
```

---

## M3: Construccion + MVP Completo
**Objetivo**: Flujo E2E completo con un modulo Odoo v18 funcional.

**Alcance**: El framework completa el ciclo entero: elicitacion -> diseno ->
construccion -> pruebas -> revision -> CI/CD, produciendo un modulo Odoo v18
instalable y funcional de "Registro de Vehiculos" (CRUD con modelo + vistas).

M3 se divide en 5 sub-milestones secuenciales para facilitar la implementacion
incremental. Cada sub-milestone es un deliverable independiente y demostrable.

### Branching

```
main
  └── milestone/3.0-construccion-mvp        ← creado desde main
        ├── feat/3.0a-task-files            ← desde milestone/3.0 (sistema de tasks rediseñado)
        ├── feat/3.1-constructor-core        ← desde milestone/3.0
        ├── feat/3.2-constructor-completo    ← desde milestone/3.0 (mergea M3.1 a M3.0 primero)
        ├── feat/3.3-tester-reviewer         ← desde milestone/3.0 (mergea M3.2 a M3.0 primero)
        └── feat/3.4-cicd-e2e               ← desde milestone/3.0 (mergea M3.3 a M3.0 primero)
```

Flujo: `feat/3.0a → PR → merge a milestone/3.0 → feat/3.1 → PR → merge a milestone/3.0 → ...`

---

### M3.0a: Task System Redesign — Archivos por Task
**Objetivo**: Rediseñar el sistema de tasks para generar un archivo por task
en lugar de un solo `tasks.md`, permitiendo construccion iterativa con commits
por task.

**Entregables**:
- [x] Schema `task_index.schema.json` y `task_item.schema.json`
- [x] Gate `tasks` con rule type `task_files_exist`
- [x] Comando `/fba:tasks` actualizado: genera `index.json` + `T*.json`
- [x] Comando `/fba:construct` rediseñado: flujo iterativo task-por-task con sesiones frescas
- [x] Orquestador actualizado con nueva tabla de fases
- [x] Tests unitarios del nuevo sistema de tasks
- [x] Documentacion de testing: `docs/testing/m3-tasks-files.md`

**Depende de**: M2 (SDD + plan)

---

### M3.1: Constructor Core — Schema Manager + Modulo Skeleton + Modelos
**Objetivo**: Introducir el Schema Manager como capa de determinismo entre tasks
y codigo. Producir `schema.json` (SSOT) y generar `__manifest__.py`, `__init__.py`,
y modelos Odoo v18 funcionales.

**Arquitectura interna del code-generator**:
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

**Entregables**:
- [x] Agente `code-generator.md` con Schema Manager + Code Renderer
- [x] Schema `schema.schema.json` para validar el SSOT deterministico
- [x] Module Registry (`module_registry.json`) con modulos core de Odoo v18
- [x] Normalizacion de nombres: many2one → `*_id`, many2many → `*_ids`, etc.
- [x] Comando `/fba:construct` con flujo: assembly schema → validate → render iterativo
- [x] Gate `schema` validando schema.json contra schema.schema.json
- [x] Gate `construction` extendido con validacion de consistencia schema ↔ codigo
- [x] Builder contract: code renderer no interpreta, no renombra, no reestructura
- [x] Tests unitarios del Schema Manager, Module Registry, y Code Renderer
- [x] Prueba manual: modulo minimo instalable en Odoo v18

**Depende de**: SDD valido + tasks/index.json (fase `tasks`)

---

### M3.2: Constructor Completo — Vistas, Seguridad, Datos
**Objetivo**: Constructor completo genera todo el modulo Odoo v18 (vistas,
seguridad, datos demo).

**Entregables**:
- [x] Constructor extendido para generar vistas (form, list, search, kanban)
- [x] Constructor extendido para generar seguridad (grupos, ACL, record rules)
- [x] Constructor extendido para generar datos demo
- [x] Gate `construction` extendido con validacion de vistas y seguridad (view_coverage, view_field_check, acl_coverage)
- [x] Esquemas actualizados a Odoo v18: `tree` → `list`, `attrs` deprecado, atributos directos (`invisible`, `widget`, `groups`, `tracking`, `states`)
- [x] Schema.schema.json extendido con `mail_thread`, `mail_activity`, `manifest.data`, `manifest.demo`, `noupdate`, `category_id`
- [x] Bugs corregidos: security group assembly, record rule domain, data type hardcodeado, field type case normalization
- [x] Tests del constructor completo (15 nuevos, 386 total)
- [x] Documentacion de testing: `docs/testing/m3.2-constructor-completo.md`

**Depende de**: M3.1 (constructor core)

---

### M3.3: Tester QA + Code Reviewer
**Objetivo**: El framework puede probar y revisar el modulo generado automaticamente.

**Entregables**:
- [x] Agente `tester_qa.md` + comando `/fba:test`
  - Genera tests Odoo TestCase: modelos, vistas, seguridad
  - Ejecuta tests y genera `test_report.md`
  - Gate `testing`
- [x] Agente `revisor_codigo.md` + comando `/fba:review`
  - Revisa calidad (PEP8, Odoo conventions)
  - Revisa seguridad (ACL, validacion, datos sensibles)
  - Revisa adherencia a specs (PRD/SDD)
  - Genera `review_report.md`
  - Gate `review`
- [x] Tests de los agentes tester y revisor
- [x] Integracion con el orquestador

**Depende de**: M3.2 (constructor completo — necesita codigo generado)

---

### M3.4: CI/CD Manager + Integracion E2E + Docs
**Objetivo**: Framework completo E2E funcionando, probado y documentado.

**Entregables**:
- [x] Agente `ci_cd_manager.md` + comando `/fba:ship`
  - Genera GitHub Actions workflow para el modulo Odoo
  - Gate `ci_cd`
- [x] Flujo E2E completo con modulo "Registro de Vehiculos":
  ```
  fba init → /fba:elicit → /fba:specify → /fba:plan → /fba:tasks
  → /fba:construct → /fba:test → /fba:review → /fba:ship
  ```
- [x] Tests E2E del framework completo
- [x] Documentacion de usuario final: `docs/testing/m3-construccion.md`
- [x] Actualizacion de ROADMAP, CHANGELOG, version (bump a 0.5.0)

**Depende de**: M3.3 (tester y revisor completos)

---

### Verificacion Final

```bash
# Flujo completo desde cero
fba init
/fba:elicit "modulo de registro de vehiculos con marca, modelo, ano, placa"
/fba:specify
/fba:plan
/fba:tasks
/fba:construct
/fba:test
/fba:review
/fba:ship
# Resultado: modulo Odoo v18 instalable, probado, con PR para merge
```

---

## M4: Sistema de Gates con Agente Revisor de Artefactos

**Objetivo**: Implementar un sistema de gates que bloquee automaticamente
cualquier transicion de fase si los artefactos de la fase actual no pasan
validacion. Ninguna fase avanza sin artefactos validados.

**Alcance**: El `StateManager` ejecuta validaciones forzosas antes de cada
transicion. Si un artefacto no pasa, la transicion se rechaza. Un nuevo agente
Revisor de Artefactos diagnostica fallos y orquesta el ciclo de correccion.
El sistema de gates es declarativo: las reglas de validacion se definen en
`state.json` y son extensibles sin modificar codigo.

### Tareas

- [x] Modulo `src/fba/gate.py`: GateRunner con definiciones de gates declarativas
  - Gate por fase: schema, content, traceability, cross-artifact, semantic_check
  - Resultado estructurado con mensajes de error descriptivos
  - Carga de reglas desde `state.json`
- [x] Integrar gates en `StateManager.transition_to()`: bloquea transicion si gate falla
- [x] Comando CLI `fba gate`: validacion manual de gates para diagnostico
- [x] Sub-agente Revisor de Artefactos (`revisor_artefactos.md`)
  - Valida artefactos contra sus schemas
  - Verifica coherencia cross-artifact (ej. trazabilidad PRD→SDD)
  - Genera reporte de validacion
  - Soporta ciclo: generar → validar → fallo → corregir → revalidar
- [x] Sub-agente Validador Semantico (`validador_semantico.md`)
  - Valida alineacion semantica de artefactos contra la solicitud original
  - Evalua 5 dimensiones: dominio, objetivos, terminologia, stakeholders, requisitos
  - Correcciones delegadas al agente dueno en sesion fresca (sin task_id)
- [x] Slash commands `/fba:gate` y `/fba:semantic-check`
- [x] Actualizar orquestador: flujo incluye validacion de gates + semantica en cada transicion
- [x] Actualizar slash commands existentes: cada comando ejecuta `fba validate` + gate check
- [x] Actualizar `state.schema.json` con seccion `gates` y rule types `semantic_check`
- [x] Tests unitarios + integracion de gates (incluyendo semantic_check)
- [x] Guia de testing: `docs/testing/m4-gates.md`

### Verificacion

```bash
# Gates bloquean transiciones invalidas
fba transition planning   # sin PRD valido → ERROR: gate documentation failed
fba gate                   # diagnostica que gate falla y por que

# Flujo con gates
/fba:specify               # genera PRD
fba gate                   # ✅ PRD valid
fba transition planning    # ✅ gate documentation passed, transicion ok
/fba:plan                  # genera SDD
fba gate                   # ✅ SDD valid + traceability
fba transition tasks       # ✅ gate planning passed, transicion ok
```

---

## M5: Bug Fixes & Stability

**Objetivo**: Corregir bugs encontrados post-release de los milestones core (M0-M4).

**Estado**: ✅ Completado

### Tareas

- [x] fix(#71): renombrar agente `constructor` → `code-generator` (JS `constructor` readonly property)
- [x] fix(#71): renombrar comando `fba:build` → `fba:construct` (`build` es built-in de OpenCode)

### Verificacion

```bash
fba init --project-dir ../fba-test/v3/
opencode .  # debe abrir sin error
```

---

## M10: Framework Meta-Development System

**Objetivo**: Implementar un sistema de 3 agentes meta (orchestrator, planner, builder) que
gestiona el desarrollo del propio framework FBA de forma autonoma, eliminando la friccion
entre sesiones y permitiendo ejecucion de milestones sin intervencion constante del usuario.

**Alcance**: Los meta-agentes coordinan, planifican y construyen mejoras del framework.
M11-M15 se ejecutaran usando este sistema (reemplaza a M6-M9 originales).

### Tareas

- [x] `.factory/framework-state.json` — estado persistente entre sesiones
- [x] `schemas/framework-state.schema.json` — validacion del archivo de estado
- [x] `.opencode/agents/framework-orchestrator.md` — coordinador (solo delega, no implementa)
- [x] `.opencode/agents/framework-planner.md` — arquitecto de mejoras (zero suposiciones)
- [x] `.opencode/agents/framework-builder.md` — constructor autonomo (respeta CONTRIBUTING.md)
- [x] `.opencode/commands/fba:fw.md` — punto de entrada del sistema meta
- [x] `.opencode/commands/fba:fw-plan.md` — acceso directo a planificacion
- [x] `.opencode/commands/fba:fw-build.md` — acceso directo a construccion
- [x] `docs/fw-brief-template.md` — template de referencia del brief
- [x] `docs/testing/m10-framework-meta-dev.md` — instrucciones de testing
- [x] Documentacion actualizada: AGENTS.md, ROADMAP.md, CHANGELOG.md

### Verificacion

```bash
opencode .                    # abrir el framework en OpenCode
/fba:fw                       # orchestrator presenta resumen del roadmap
/fba:fw-plan "[mejora]"       # planner genera fw-brief.md (pregunta si hay ambiguedad)
/fba:fw-build                 # builder ejecuta el brief segun CONTRIBUTING.md
pytest                        # todos los tests pasan
```

---

## M11: Foundation Hardening (Capa 1 — inmediato)

**Objetivo**: Corregir bugs criticos (#10 atomicidad, #2 rollback, #7 registry, #9 schema alignment)
y proporcionar herramienta de diagnostico (`fba doctor`). Este milestone sienta las bases de robustez
sin las cuales ningun feature nuevo es confiable.

**Alcance**: Atomic writes en state.py/cli.py, rollback en StateManager, validacion de ModuleRegistry,
comando `fba doctor`, y alineacion de schema con SchemaManager.

**Branch**: `milestone/11.0-foundation-hardening`

### Feats

| Orden | Feat | Depende de | Descripcion | Estado |
|-------|------|------------|-------------|--------|
| 1 | feat/11.1-atomicity-writes | — | #10: Atomic writes en state.py y cli.py con temp file + fsync + os.replace | ✅ |
| 2 | feat/11.2-rollback-state | feat/11.1 | #2: Rollback en StateManager.transition_to() — revertir state si operacion post-save falla | ✅ |
| 3 | feat/11.3-registry-robustez | — | #7: ModuleRegistry con validacion, warnings explicitos si no carga, _copy_registry con advertencias | ✅ |
| 4 | feat/11.4-fba-doctor | feat/11.3 | Comando `fba doctor`: diagnostica registry, state integrity, writability, schema alignment | ✅ |
| 5 | feat/11.5-wizard-schema-alignment | — | #9: Alinear task_item.schema.json con SchemaManager — deteccion de tipos no implementados con warning | ✅ |

**Depende de**: M10 (framework meta-dev system, en uso para construir M11)

### Verificacion

```bash
fba doctor                  # diagnostica registry, state integrity, writability
fba doctor --verbose        # output detallado con todos los componentes
pytest tests/test_state_atomicity.py tests/test_state_rollback.py
pytest tests/test_registry_robustez.py tests/test_fba_doctor.py
pytest tests/test_schema_manager_unknown_types.py
```

---

## M12: Diff, Dependencies & Trazabilidad (Capa 1 avanzada)

**Objetivo**: Implementar diff engine (#15) para trazabilidad de cambios entre artefactos,
analisis de integridad de dependencias (#12), y formalizar artifact contracts con stable IDs basicos.

**Alcance**: Core diff engine para artefactos JSON, contracts layer, dependency integrity analysis,
y fundacion de stable IDs (UUID).

**Branch**: `milestone/12.0-diff-dependencies`

### Feats

| Orden | Feat | Depende de | Descripcion |
|-------|------|------------|-------------|
| 1 | feat/12.1-diff-engine-core | M11 | #15: Core diff engine para artefactos JSON (PRD, SDD, schema, tasks). Output: changelog estructurado |
| 2 | feat/12.2-artifact-contracts | M11 | Contracts layer: invariantes, ownership, allowed mutations por artefacto (extiende JSON schemas) |
| 3 | feat/12.3-dependency-integrity | feat/12.1 | #12: Analisis semantico de dependencias Odoo — detecta modulos innecesarios, mixins sin depends, dependencias circulares |
| 4 | feat/12.4-stable-ids-foundation | feat/12.2 | Stable IDs (UUID) para entidades clave: requisitos (RF-*), modelos, campos. Solo fundacion |

**Depende de**: M11 (Foundation Hardening)

**Conceptos absorbidos de M6-M9**: Artifact Contracts (old M6.5), Stable IDs (old M6.6)

### Verificacion

```bash
fba diff prd_v1.json prd_v2.json  # diff engine output: changelog estructurado
fba validate --contract prd       # valida invariantes de contrato PRD
fba deps check                    # analiza dependencias Odoo
pytest tests/test_diff_engine.py tests/test_artifact_contracts.py
pytest tests/test_dependency_integrity.py tests/test_stable_ids.py
```

---

## M13: Reliability & Quality (Capa 2)

**Objetivo**: Agregar seguridad (#1 bandit + pip-audit + detect-secrets), cache de validacion (#8 hash-based),
pre-commit hooks (#5), y type checking con mypy (#6).

**Alcance**: Security scans integrados como gates, configuracion pre-commit, mypy strict mode progresivo,
y cache de validacion hash-based en `.factory/.cache/`.

**Branch**: `milestone/13.0-reliability-quality`

### Feats

| Orden | Feat | Depende de | Descripcion |
|-------|------|------------|-------------|
| 1 | feat/13.1-security-scans | M11 | #1: Bandit + pip-audit + detect-secrets como gates en construction |
| 2 | feat/13.2-pre-commit | — | #5: Configuracion de pre-commit hooks (.pre-commit-config.yaml) con ruff, black, bandit |
| 3 | feat/13.3-mypy | — | #6: Configuracion mypy con strict mode progresivo, pyproject.toml [tool.mypy] |
| 4 | feat/13.4-cache-validacion | M11, feat/12.1 | #8: Cache de validacion hash-based en `.factory/.cache/` — no re-validar artefactos sin cambios |

**Depende de**: M11 (Foundation Hardening) y parcialmente M12 feat/12.1 (diff engine para deteccion de cambios)

**Conceptos absorbidos de M6-M9**: Cache de validacion (old M8.3)

### Verificacion

```bash
fba gate --security           # ejecuta bandit + pip-audit + detect-secrets
pre-commit run --all-files    # ruff + black + bandit
mypy src/fba/                 # strict mode progresivo
fba gate --verbose            # muestra cache hits/misses
pytest tests/test_security_scans.py tests/test_cache_validacion.py
```

---

## M14: Odoo Depth (Capa 3)

**Objetivo**: Completar la implementacion de wizards/workflows/reports (#9 full), agregar soporte
de migraciones de schema (#3), e internacionalizacion i18n (#4). Lleva la generacion de modulos
Odoo a nivel enterprise-grade.

**Alcance**: Implementacion completa en SchemaManager + Code Renderer de wizard, workflow, report,
controller. Deteccion de cambios de schema con migraciones. Generacion .pot/.po con es_ES default.

**Branch**: `milestone/14.0-odoo-depth`

### Feats

| Orden | Feat | Depende de | Descripcion |
|-------|------|------------|-------------|
| 1 | feat/14.1-wizards-workflows | M11 feat/11.5 | #9: Implementacion completa en SchemaManager + Code Renderer de wizard, workflow, report, controller |
| 2 | feat/14.2-migraciones | feat/12.1 | #3: Deteccion de cambios de schema, produccion de migraciones Odoo, validacion de compatibilidad |
| 3 | feat/14.3-i18n | — | #4: Internacionalizacion — generacion de .pot/.po, es_ES default, OCA readiness |

**Depende de**: M11 feat/11.5 (schema alignment), M12 feat/12.1 (diff engine para migraciones)

### Verificacion

```bash
fba construct --with-wizards    # genera wizard, workflow, report, controller
fba migrate --check             # detecta cambios de schema y genera migraciones
fba i18n extract                # genera .pot/.po con es_ES default
pytest tests/test_wizards_workflows.py tests/test_migraciones.py tests/test_i18n.py
```

---

## M15: Advanced QA (Capa 4)

**Objetivo**: Agregar testing avanzado: Playwright para browser automation (#11), performance
benchmarks (#13), y concurrency safety warnings (#14).

**Alcance**: Browser automation con Playwright para vistas Odoo, performance test suite con
benchmarks de generacion/memoria/tiempo, y deteccion de escrituras concurrentes en state.json.

**Branch**: `milestone/15.0-advanced-qa`

### Feats

| Orden | Feat | Depende de | Descripcion |
|-------|------|------------|-------------|
| 1 | feat/15.1-playwright | M14 feat/14.1 | #11: Browser automation con Playwright para vistas Odoo (form, list, kanban) |
| 2 | feat/15.2-performance | — | #13: Performance test suite — benchmarks de generacion, memoria, tiempo |
| 3 | feat/15.3-concurrency | M11 | #14: Concurrency safety warnings — detectar escrituras concurrentes en state.json |

**Depende de**: M14 feat/14.1 (wizards/workflows), M11 (atomicidad para concurrency)

**Conceptos absorbidos de M6-M9**: Playwright (old M9.2)

### Verificacion

```bash
fba test --playwright          # browser automation para vistas Odoo
fba perf                       # ejecuta performance benchmarks
fba doctor --concurrency       # verifica escrituras concurrentes en state.json
pytest tests/test_playwright.py tests/test_performance.py tests/test_concurrency.py
```

---

## Conceptos de M6-M9 Transferidos vs No Transferidos

### Transferidos (absorbidos en M11-M15)

| Concepto old | Milestone old | Destino |
|-------------|---------------|---------|
| Artifact Contracts | M6.5 | M12 feat/12.2 |
| Stable IDs | M6.6 | M12 feat/12.4 |
| Cache de validacion | M8.3 | M13 feat/13.4 |
| Playwright | M9.2 | M15 feat/15.1 |

### No Transferidos (depriorizados/pospuestos)

| Concepto old | Milestone old | Razon |
|-------------|---------------|-------|
| Orquestador ligero | M6.1 | Posponer — requiere analisis de token consumption post-M11 |
| Instrucciones agentes <200L | M6.2 | Posponer — sin bloqueo funcional |
| Knowledge base granular | M6.3 | Posponer — los agentes actuales funcionan |
| Separacion runtime vs knowledge | M6.4 | Posponer |
| User Stories | M7.1 | Posponer — BABOK funciona |
| Code Gen Dual (model/xml) | M7.2, M7.3 | Posponer — code-generator actual funciona |
| Domain IR en SDD | M7.0 | Posponer |
| Paralelizacion | M8.1 | Posponer |
| Pipeline resumible | M8.2 | Posponer |
| Multi-modulo | M8.4 | Posponer |
| Testing ORM real | M9.1 | Posponer |
| Feedback loop | M9.3 | Depende de diff (M12) — podria reactivarse post-M12 |
| Gate diagnostics | M9.4 | Posponer |
| Execution sandbox | M9.5 | Posponer |

---

## Arquitectura de Agentes

```
Orquestador (control de flujo, gate dispatch, user confirm)
├── Elicitador BABOK (metodologia tradicional)
├── Documentador (PRD + SDD)
├── Planificador (arquitectura Odoo)
├── Revisor de Artefactos (gates + validacion cross-artifact)
├── Validador Semantico (alineacion semantica contra solicitud original)
├── Code Generator (Schema Manager + Code Renderer)
├── Tester/QA (pruebas Odoo + Playwright) [M15]
├── Revisor de Codigo (calidad + seguridad)
└── CI/CD Manager (GitHub Actions + releases)
```

Cada agente se define declarativamente en Markdown en `.opencode/agents/`.
El sistema es extensible por diseno: agregar un nuevo agente es agregar
un archivo Markdown con su definicion y un slash command.

### Pipeline (tasks → construction)

```
planner → tasks/index.json + T*.json → code-generator
                                          ├── Schema Manager: assembly + normalization + registry lookup
                                          │   → produces schema.json (SSOT)
                                          └── Code Renderer: iterative generation per task
                                              → produces odoo_module/
```

## Decisiones de Diseno

| Decision | Eleccion | Justificacion |
|----------|----------|---------------|
| Runtime | OpenCode | Agente CLI maduro, multi-modelo, open source |
| Lenguaje | Python 3.11+ | Odoo es Python, SpecKit es Python, ecosistema ERP |
| Metodologia | BABOK | Estandar reconocido para analisis de negocio |
| Comunicacion | Archivos + Eventos | Simple, trazable, sin infraestructura externa |
| CI/CD | GitHub Actions | Integracion nativa con GitHub |
| Compatibilidad | OpenSpec + SpecKit | Artefactos en formatos compatibles |
| Extension | Markdown declarativo | Agregar agentes/metodologias sin modificar nucleo |
| Empaquetado | pyproject.toml | Estandar moderno de Python |
| CLI | Click | Biblioteca madura y bien documentada |
| SSOT | schema.json | Single source of truth for module structure, eliminates ambiguity between tasks and code |

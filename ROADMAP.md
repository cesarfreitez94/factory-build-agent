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
| M6: Optimización de Agentes | ⏳ Planificado | — / — |
| M7: User Stories + Code Gen Dual | ⏳ Planificado | — / — |
| M8: Pipeline, Performance, Multi-modulo | ⏳ Planificado | — / — |
| M9: Testing Avanzado + Feedback | ⏳ Planificado | — / — |

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
M6-M9 se ejecutaran usando este sistema.

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

## M6: Optimizacion de Agentes

**Objetivo**: Reducir consumo de tokens del orquestador y optimizar instrucciones
de todos los agentes para sesiones mas rapidas y ligeras.

**Alcance**: El orquestador delega mas a sub-agentes y reduce su contexto primario.
Instrucciones de agentes extraidas a archivos compartidos para eliminar duplicacion.

### Sub-milestones

```
main
  └── milestone/6.0-optimizar-agentes         ← creado desde main
        ├── feat/6.1-orquestador-ligero        ← delegar elicitacion, reducir a control de flujo
        ├── feat/6.2-instrucciones-agentes     ← reducir duplicacion, formato conciso
        ├── feat/6.3-convenciones-compartidas  ← knowledge base granular (odoo/, babok/, testing/, security/)
        ├── feat/6.4-identidad-vs-instrucciones ← separar runtime (agents/ knowledge/ contracts/)
        ├── feat/6.5-artifact-contracts        ← invariantes, ownership, allowed mutations por artefacto
        └── feat/6.6-stable-ids               ← UUIDs persistentes para todas las entidades
```

### M6.1: Orquestador Ligero

**Objetivo**: Reducir el consumo de tokens del orquestador delegando elicitacion
y minimizando el contexto en modo primary.

**Entregables**:
- [ ] Delegar elicitacion a sub-agente especializado (usa `question` tool via task)
- [ ] `orchestrator.md` reducido a control de flujo puro (phase transitions, gate dispatch, user confirm)
- [ ] Sub-agentes invocados con contexto minimo necesario (no full state dump)
- [ ] Reutilizacion de sesiones via `task_id` cuando es seguro y deterministico
- [ ] Tests de consumo de tokens (medicion de contexto cargado por fase)

**Depende de**: M5 (estabilidad actual)

---

### M6.2: Instrucciones de Agentes Optimizadas

**Objetivo**: Reducir duplicacion entre agentes, formato mas estructurado y conciso.

**Entregables**:
- [ ] Auditoria de duplicacion: identificar patrones repetidos entre los 10 agentes
- [ ] Extraer convenciones Odoo v18 a `odoo-v18-conventions.md` compartido
- [ ] Reducir ejemplos verbosos en agentes grandes (`code-generator.md` de 490 → <200 lineas)
- [ ] Formato estandarizado: bullets > prosa, referencias > copias inline
- [ ] Cada agente < 200 lineas (down from 180-490)
- [ ] Tests de definiciones actualizados (referencias a archivo compartido)

**Depende de**: M6.1 (nuevo formato de agente definido)

---

### M6.3: Base de Conocimiento Compartida (por Dominio)

**Objetivo**: Reorganizar el conocimiento en dominios granulares (`knowledge/odoo/`,
`knowledge/babok/`, `knowledge/testing/`, `knowledge/security/`) eliminando duplicacion.

**Entregables**:
- [ ] Estructura de directorios `templates/.opencode/knowledge/`:
  - `knowledge/odoo/v18-conventions.md` — Tags XML, atributos directos, naming, prohibited patterns
  - `knowledge/odoo/v18-models.md` — Patrones Python: `models.Model`, `_inherit`, campos, constraints
  - `knowledge/odoo/v18-views.md` — XML views (form, list, search, kanban), widgets, decorations
  - `knowledge/odoo/v18-security.md` — CSV ACL, grupos XML, record rules, permisos
  - `knowledge/babok/elicitation.md` — Metodologia BABOK, knowledge areas, question patterns
  - `knowledge/babok/requirements.md` — RF, RNF, criterios de aceptacion, trazabilidad
  - `knowledge/testing/odoo-orm.md` — TransactionCase, setUp, with_user(), sudo()
  - `knowledge/testing/playwright.md` — Browser automation, selectores Odoo, navegacion
  - `knowledge/security/patterns.md` — Validacion de input, no credenciales hardcodeadas, ACL coverage
- [ ] Cada agente referencia solo los archivos de knowledge que necesita (no duplicacion)
- [ ] Agregado a `fba init` y `fba update` (copia estructura completa)
- [ ] Tests de contenido, referencias y cobertura de dominios

**Depende de**: M6.2

---

### M6.4: Separar Runtime vs Knowledge

**Objetivo**: Separacion arquitectonica clara entre:

- **Runtime Layer**: `.opencode/agents/` (identidad de agente: rol, mode, permission)
- **Knowledge Layer**: `.opencode/knowledge/` (metodologia, convenciones, patrones por dominio)
- **Contracts Layer**: `.opencode/contracts/` (invariantes, ownership, allowed mutations)

Esto garantiza que las instrucciones de metodo no contaminen la identidad del agente,
y que el conocimiento se comparta sin duplicacion.

**Entregables**:
- [ ] Estructura `.opencode/` reorganizada:
  ```
  .opencode/
    agents/           ← solo identidad (frontmatter + rol minimo, <50 lineas)
    knowledge/        ← por dominio (odoo/, babok/, testing/, security/)
    contracts/        ← garantias del pipeline entre artefactos
  ```
- [ ] Runtime: `agents/<name>.md` contiene frontmatter + descripcion de rol (<50 lineas)
- [ ] Knowledge: cargado on-demand via referencias en prompts
- [ ] Contracts: definidos declarativamente, consumidos por GateRunner (ver M6.5)
- [ ] Orquestador carga solo runtime, inyecta knowledge al invocar sub-agentes
- [ ] Compatible con modo `primary` (carga minima) y `subagent` (knowledge bajo demanda)
- [ ] Tests: identidad ligera, knowledge cargado correctamente en sub-agentes

**Depende de**: M6.3

---

### M6.5: Artifact Contracts

**Objetivo**: Formalizar contratos entre artefactos del pipeline. Un contrato define
invariantes, ownership, allowed mutations y determinismo. Esto habilita cache,
paralelizacion, resumability y auto-fix en M8/M9.

Los contratos extienden los JSON schemas actuales con garantias semánticas que el
GateRunner puede verificar deterministicamente.

**Entregables**:
- [ ] Directorio `contracts/` con un archivo por artefacto:
  - `contracts/prd.contract.md` — PRD invariants, ownership, allowed mutations
  - `contracts/sdd.contract.md` — SDD invariants, domain layer, Odoo mappings
  - `contracts/tasks.contract.md` — Task invariants, dependency integrity
  - `contracts/schema.contract.md` — SSOT invariants, field identity, mode stability
- [ ] Cada contrato define:
  - **Invariantes**: campos inmutables despues de cierta fase (ej. `requirement.id` nunca cambia post-planning)
  - **Ownership**: agente dueño de cada artefacto (ej. `PRD: owner=documentador`)
  - **Allowed mutations**: que transformaciones son validas entre fases (ej. SDD PUEDE expandir detalles tecnicos, NO PUEDE cambiar intencion funcional)
  - **Determinism**: mismo input → mismo output estructural (para reproducibilidad)
- [ ] `GateRunner` extendido con `_check_contract()` que verifica invariantes cross-phase
- [ ] Regla de gate tipo `contract_check` en `state.json`
- [ ] Tests: violacion de invariante bloquea transicion

**Depende de**: M6.4 (contracts layer definido)

---

### M6.6: Stable IDs para Todas las Entidades

**Objetivo**: Toda entidad en todo artefacto tiene un ID estable y persistente que
sobrevive a renombramientos. Esto es prerequisito critico para cache, checkpoints,
paralelizacion y auto-fix (M8/M9).

**Entregables**:
- [ ] Todo artefacto incluye `uuid` o `stable_id` generado una vez y nunca mutado:
  - PRD: `RF-*`, `RNF-*`, `CA-*` obtienen `stable_id` (UUID v4)
  - SDD: modelos, vistas, componentes obtienen `stable_id`
  - Tasks: `task_id` persistente, inmutable post-generation
  - Schema: `field_stable_id`, `model_stable_id`, `view_stable_id`
- [ ] `SchemaManager` preserva stable IDs durante assembly (merge por UUID, no por nombre)
- [ ] `ModuleRegistry` extendido con `entity_registry` (mapea stable_id → metadata)
- [ ] Gate regla `stable_id_integrity`: verifica que IDs no mutaron entre fases
- [ ] IDs estables persisten en `events.jsonl` para trazabilidad completa
- [ ] Tests: renombrar campo no rompe cache/traceability/dependencies

**Depende de**: M6.5 (contracts definen invariantes de ID)

---

### Verificacion

```bash
fba init
# .opencode/knowledge/ con subdirectorios por dominio (odoo/, babok/, testing/, security/)
# .opencode/contracts/ con contratos por artefacto
# .opencode/agents/ con identidad ligera (<50 lineas cada uno)
# Agentes con instrucciones reducidas (<200 lineas cada uno)
# Stable IDs (UUID) en todas las entidades de todos los artefactos
# Orquestador con contexto reducido (sin elicitacion directa)
fba validate --contract prd  # valida invariantes de contrato PRD
fba gate --verbose  # muestra contract checks, stable ID integrity
pytest  # todos los tests existentes pasan
```

---

## M7: User Stories + Code Generator Dual

**Objetivo**: Soportar metodologia de User Stories como alternativa a BABOK, y
dividir el code generator en dos agentes especializados (Modelos y XML).

**Alcance**: El pipeline soporta dos metodologias: BABOK (existente) y User Stories
(nuevo). El constructor genera codigo con dos agentes independientes.

### Sub-milestones

```
main
  └── milestone/7.0-us-codegen-dual          ← creado desde main
        ├── feat/7.0-domain-ir-sdd            ← SDD reestructurado: domain_models + odoo_mappings
        ├── feat/7.1-user-stories-core        ← personas, epicas, historias, schemas
        ├── feat/7.2-model-generator          ← agente especializado en modelos Python
        └── feat/7.3-xml-generator            ← agente especializado en vistas XML
```

### M7.0: Domain IR como Capa del SDD

**Objetivo**: Separar dominio puro de implementacion Odoo dentro del SDD, sin
crear un nuevo artefacto. El SDD se reestructura en dos capas:

```
SDD
├── domain_models        ← dominio puro (Customer owns Vehicles, Vehicle has Plate)
│   ├── entities         ← conceptos de negocio sin acoplamiento Odoo
│   ├── relationships    ← relaciones semanticas entre entidades
│   └── workflows        ← flujos de negocio abstractos
│
└── odoo_mappings        ← implementacion Odoo (res.partner, vehicle.vehicle)
    ├── model_mappings    ← entity → Odoo model (new/extend)
    ├── field_mappings    ← entity attribute → Odoo field type
    └── view_mappings     ← entity → Odoo view type
```

**Entregables**:
- [ ] `sdd.schema.json` extendido con seccion `domain_models`:
  - `entities[]` con `name`, `description`, `attributes[]`, `relationships[]`
  - `relationships[]` con `type` (one_to_one, one_to_many, many_to_many), `from`, `to`
  - `workflows[]` con `name`, `steps[]`, `actors[]`
- [ ] `sdd.schema.json` extendido con seccion `odoo_mappings`:
  - `model_mappings[]` que mapean `entity → model_name + mode (new/extend)`
  - `field_mappings[]` que mapean `entity_attribute → field_name + field_type + widget`
  - `view_mappings[]` que mapean `entity → view_type + priority`
- [ ] `planificador.md` actualizado: genera SDD con ambas capas
- [ ] `traceability_matrix` extendido: domain_entity → RF, odoo_mapping → domain_entity
- [ ] Schema Manager lee `domain_models` + `odoo_mappings` para assembly
- [ ] Gate `planning` extendido: `domain_traceability` verifica que toda entity tiene Odoo mapping
- [ ] Tests: SDD con domain layer, validacion de mappings 1:1

**Por que dentro del SDD y no como nuevo artefacto**: El SDD ya es el punto
de traduccion entre requisitos y arquitectura. Agregar la capa de dominio aqui
evita una nueva fase en el pipeline y mantiene la trazabilidad en un solo lugar.

**Depende de**: M6 (contracts definen invariantes del SDD)

---

### M7.1: User Stories Core

**Objetivo**: Agregar soporte completo de User Stories como metodologia de
elicitacion alternativa a BABOK.

**Entregables**:
- [ ] Agente `elicitador-us.md`: guia metodologica para User Story Mapping
  - Personas (nombre, rol, necesidades, contexto)
  - Epicas (descripcion, objetivo de negocio)
  - User Stories (formato "Como [persona] quiero [accion] para [beneficio]")
  - Criterios de aceptacion (formato Given/When/Then)
  - Story points y priorizacion MoSCoW
- [ ] Slash command `/fba:elicit-us` con flujo interactivo
- [ ] Schema `user_stories.schema.json` para validar artefactos US
- [ ] Campo `methodology` en `state.json` acepta "BABOK" y "User Stories"
- [ ] Mapeo US → tareas tecnicas: `tasks/T*.json` extendido con `user_story_id`, `persona`, `story_points`
- [ ] Traceability: US → SDD components (extender `traceability_matrix`)
- [ ] Compatibilidad: pipeline funciona identico con ambas metodologias
- [ ] Tests de validacion de schema US y flujo completo US

**Depende de**: M6 (agentes optimizados, base de conocimiento compartida)

---

### M7.2: Model Generator

**Objetivo**: Agente especializado que genera exclusivamente `models/*.py` desde
`schema.json`, separado de la generacion de XML.

**Entregables**:
- [ ] Agente `model-generator.md` + comando `/fba:construct-models`
  - Genera `__manifest__.py`, `__init__.py`, `models/*.py`
  - Soporta modo `new` (herencia `models.Model`) y `extend` (`_inherit`)
  - Campos: Char, Text, Integer, Float, Boolean, Date, Datetime, Selection, Many2one, One2many, Many2many
  - Atributos: `string`, `required`, `readonly`, `help`, `default`, `tracking`, `states`, `compute`, `inverse`
  - Constraints: `_sql_constraints`, `_check_` methods, `@api.constrains`
  - Mixins: `mail.thread`, `mail.activity.mixin` segun schema
  - Consume SOLO `schema.json` (builder contract, zero interpretation)
- [ ] Schema Manager (fase 1) sin cambios — produce `schema.json` igual
- [ ] Code Renderer (fase 2) dividido: models vs XML en sesiones separadas
- [ ] Orquestador actualizado: `construction` delega a `model-generator` primero, luego `xml-generator`
- [ ] `code-generator.md` deprecado (reemplazado por los dos nuevos agentes)
- [ ] Tests: generacion de modelos desde schema con todos los tipos de campo

**Depende de**: M7.1 (user stories completado, schemas estables)

---

### M7.3: XML Generator

**Objetivo**: Agente especializado que genera exclusivamente archivos XML
(`views/`, `security/`, `data/`) desde `schema.json`.

**Entregables**:
- [ ] Agente `xml-generator.md` + comando `/fba:construct-xml`
  - Genera `views/*.xml`: form, list, search, kanban, menu items, actions
  - Genera `security/*.xml`: `ir.model.access.csv`, `groups.xml`, `record_rules.xml`
  - Genera `data/*.xml`: datos demo con `noupdate="1"`
  - Odoo v18: `<list>` not `<tree>`, atributos directos, `<chatter/>`
  - Widgets: `many2one`, `radio`, `selection`, `statusbar`, `monetary`, `html`
  - Decorations: `decoration-danger`, `decoration-warning`, etc.
  - Consume SOLO `schema.json` (builder contract, zero interpretation)
- [ ] Orquestador: `xml-generator` ejecutado despues de `model-generator`
- [ ] Orden de tasks: modelos primero, XML despues (relaciones ya resueltas)
- [ ] Gate `construction` actualizado: valida ambos generadores
- [ ] Tests: generacion de vistas/seguridad/datos desde schema

**Depende de**: M7.2 (models generados, para que XML pueda referenciarlos)

---

### Verificacion

```bash
fba init --methodology "User Stories"
/fba:elicit-us
/fba:specify
/fba:plan
/fba:tasks
/fba:construct-models   # genera models/*.py
/fba:construct-xml       # genera views/ security/ data/
/fba:test
/fba:review
/fba:ship
# Resultado: modulo Odoo v18 instalable desde User Stories
```

---

## M8: Pipeline, Performance, Multi-modulo

**Objetivo**: Optimizar velocidad del pipeline con paralelizacion y cache.
Soportar proyectos multi-modulo con dependencias entre modulos generados.

**Alcance**: El pipeline es mas rapido (tasks en paralelo, cache de validacion)
y mas robusto (checkpoints, reanudacion). Soporta generacion de proyectos con
multiples modulos Odoo interdependientes. Depende de M6 (stable IDs, contracts)
para operaciones deterministicas.

### Sub-milestones

```
main
  └── milestone/8.0-pipeline-performance     ← creado desde main
        ├── feat/8.1-paralelizacion           ← tasks sin dependencias en paralelo
        ├── feat/8.2-pipeline-resumible       ← checkpoints, reanudacion
        ├── feat/8.3-cache-validacion         ← no re-validar artefactos sin cambios
        └── feat/8.4-multi-modulo            ← dependencias entre modulos
```

### M8.1: Paralelizacion de Tasks

**Objetivo**: Ejecutar tasks de code rendering en paralelo cuando no tienen
dependencias entre si.

**Entregables**:
- [ ] `DependencyGraph`: analiza `tasks/index.json` y construye DAG de dependencias
- [ ] `ParallelScheduler`: ejecuta tasks sin dependencias en sesiones paralelas
  - Model Generator tasks en paralelo (modelos independientes)
  - XML Generator tasks secuenciales (dependen de modelos generados)
- [ ] Limite de paralelismo configurable (`--max-parallel 4`)
- [ ] `events.jsonl`: eventos `task_parallel_start`, `task_parallel_end`
- [ ] Gate `construction`: validacion post-paralela (consistencia entre modelos)
- [ ] Tests: ejecucion paralela produce mismo schema que secuencial

**Depende de**: M7 (code gen dual, modelos y XML separados), M6 (stable IDs para consistencia cross-session)

---

### M8.2: Pipeline Incremental/Resumible

**Objetivo**: Si el pipeline falla en fase N, reanudar desde fase N sin re-ejecutar
fases anteriores. Checkpoints explicitos guardan estado intermedio.

**Entregables**:
- [ ] Sistema de checkpoints: `.factory/checkpoints/<phase>.json`
  - Guarda snapshot de estado al completar cada fase
  - Incluye hash de artefactos para detectar cambios
- [ ] Comando `fba resume`: detecta ultima fase completada y continua
- [ ] Comando `fba resume --from <phase>`: reanuda desde fase especifica
- [ ] Comando `fba reset --from <phase>`: borra artefactos desde fase y reinicia
- [ ] `StateManager` extendido con `get_last_checkpoint()`, `restore_checkpoint()`
- [ ] Tests: interrupcion y reanudacion en cada fase

**Depende de**: M8.1 (pipeline flow estable), M6 (stable IDs para identidad de artefactos)

---

### M8.3: Cache de Validacion

**Objetivo**: No re-ejecutar validacion de artefactos que no han cambiado desde
la ultima gate check exitosa.

**Entregables**:
- [ ] `ValidationCache`: hash-based cache en `.factory/.cache/`
  - Hash SHA256 del contenido de cada artefacto
  - Gate check → cache hit si hash no cambio y validacion previa paso
- [ ] Comando `fba gate --no-cache`: fuerza re-validacion completa
- [ ] Invalidacion automatica: `fba record` de tipo `artifact_modified` borra cache
- [ ] Reporte de cache: `fba gate --verbose` muestra cache hits/misses
- [ ] Tests: cache hit rate, invalidacion, integridad

**Depende de**: M8.2 (checkpoints, deteccion de cambios), M6 (stable IDs para hashing determinista)

---

### M8.4: Proyectos Multi-modulo

**Objetivo**: Soportar proyectos Odoo con multiples modulos interdependientes,
generando un modulo a la vez con registro de dependencias entre ellos.

**Entregables**:
- [ ] `ModuleDependencyRegistry`: `.factory/module_deps.json`
  - Registra dependencias entre modulos generados por FBA
  - Resuelve orden de construccion (topological sort)
  - Detecta dependencias circulares
- [ ] `fba init --multi-module`: inicializa proyecto multi-modulo
- [ ] `fba module add <name>`: agrega un nuevo modulo al proyecto
- [ ] `fba module build <name>`: construye un modulo especifico
- [ ] `fba module build --all`: construye todos en orden de dependencia
- [ ] `manifest.json` `depends` incluye modulos generados por FBA
- [ ] Schema Manager extendido: `cross_module_relations` en schema.json
- [ ] Tests: proyecto con 2+ modulos, dependencia A→B, orden de build

**Depende de**: M8.3 (cache, pipeline resumible — necesario para builds largos), M6 (contracts para dependencias cross-module)

---

### Verificacion

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

## M9: Testing Avanzado + Feedback

**Objetivo**: Testing real de Odoo ORM y servicios con TransactionCase, browser
testing con Playwright para vistas, y feedback loop automatico ante fallos.
Todo esto sobre la infraestructura establecida en M8 (cache, checkpoints, DAG).

**Alcance**: El tester genera tests ejecutables contra una instancia Odoo real via
Docker. Playwright automatiza interacciones de UI. Gate failures incluyen diagnostico
estructurado con guia de correccion. El feedback loop se apoya en stable IDs (M6) y
cache (M8) para correcciones deterministicas.

### Sub-milestones

```
main
  └── milestone/9.0-testing-avanzado         ← creado desde main
        ├── feat/9.1-testing-orm-servicios    ← ORM real, service layer tests
        ├── feat/9.2-playwright-vistas        ← browser automation para views
        ├── feat/9.3-feedback-loop            ← tests fallidos → correccion automatica
        ├── feat/9.4-gate-diagnostics         ← diagnostico estructurado de gate failures
        └── feat/9.5-execution-sandbox        ← Docker sandbox, timeouts, isolation
```

### M9.1: Testing ORM y Servicios

**Objetivo**: Tests de modelos Odoo usando TransactionCase real contra instancia
Odoo, incluyendo service layer.

**Entregables**:
- [ ] `tester_qa.md` extendido con patrones de test Odoo ejecutables:
  - `test_models.py`: CRUD, validacion, constraints, computed fields, onchange
  - `test_services.py`: service/business layer methods
  - `test_security.py`: per-group access con `with_user()` y `sudo()`
  - `test_integration.py`: workflows end-to-end multi-modelo
- [ ] Soporte para ejecutar tests contra Odoo en Docker
  - `docker-compose.odoo.yml` con Odoo v18 + PostgreSQL
  - Comando `fba test --run` para ejecutar tests generados
- [ ] `test_report.json` extendido con resultados de ejecucion real
  - Campos: `executed` (bool), `odoo_version`, `db_name`, `duration_ms`
  - Coverage: modelos, vistas, seguridad, servicios
- [ ] Tests del framework: mock de Odoo environment para CI

**Depende de**: M7 (code gen dual, modulos generados completos), M6 (stable IDs para mapeo test→entity)

---

### M9.2: Playwright para Vistas

**Objetivo**: Browser automation con Playwright para probar vistas Odoo (form,
list, kanban) con interacciones reales de usuario.

**Entregables**:
- [ ] Agente `playwright-tester.md` extendido en `tester_qa.md` o agente separado
- [ ] `test_views_ui.py`: tests de UI con Playwright
  - Form view: existencia de campos, visibilidad condicional, botones, guardado
  - List view: columnas, paginacion, filtros, ordenamiento
  - Search view: filtros por campo, group by
  - Kanban view: tarjetas, drag-and-drop
- [ ] Playwright config para Odoo (autenticacion, navegacion)
- [ ] Screenshots y videos de fallos en reporte de tests
- [ ] Integracion con Docker Odoo para ejecucion CI

**Depende de**: M9.1 (instancia Odoo ejecutable, test_models base)

---

### M9.3: Feedback Loop Tester → Code Generator

**Objetivo**: Cuando tests fallan (en ejecucion real), el sistema analiza el
fallo y automaticamente invoca al code generator para corregir el codigo.
Usa stable IDs (M6) para mapear errores a entidades fuente, y cache (M8)
para evitar regeneracion innecesaria.

**Entregables**:
- [ ] Analizador de fallos: parsea output de pytest Odoo y clasifica errores
  - `FieldNotFound` → campo no existe en modelo → regenerar modelo (via stable_id)
  - `AccessError` → ACL insuficiente → regenerar security
  - `ValidationError` → constraint violado → revisar logica de modelo
  - `ViewError` → vista mal formada → regenerar vista
- [ ] Ciclo de correccion automatica (max 3 iteraciones):
  ```
  test fail → analizar error → mapear a stable_id → invocar agente corrector → regenerar → re-test
  ```
- [ ] Limite de iteraciones configurable (default 3) para evitar loops infinitos
- [ ] Eventos `test_fix_applied` y `test_fix_failed` en `events.jsonl`
- [ ] Gate `testing` extendido: `passed + fixed >= total` permite transicion

**Depende de**: M9.2 (tests ejecutables reales y UI), M6 (stable IDs), M8 (cache)

---

### M9.4: Diagnostico Estructurado de Gate Failures

**Objetivo**: Cuando un gate falla, el sistema produce un diagnostico estructurado
con guia de correccion especifica, no solo "gate failed".

**Entregables**:
- [ ] `GateResult` extendido con `suggestions[]` y `fix_agent` por regla
  ```json
  {
    "rule": "acl_coverage",
    "passed": false,
    "message": "Model stock.vehicle has no ACL entry",
    "suggestion": "Add ACL entry in security/ir.model.access.csv for model stock.vehicle",
    "fix_command": "/fba:construct-xml --task security",
    "fix_agent": "xml-generator"
  }
  ```
- [ ] Comando `fba gate --fix` que invoca automaticamente al agente corrector
- [ ] Reporte `gate_fix_report.json` con historial de correcciones
- [ ] Integracion con `revisor_artefactos.md`: sugiere correcciones en vez de solo reportar

**Depende de**: M7 (agentes especializados para correccion dirigida)

---

### M9.5: Execution Sandbox

**Objetivo**: Entorno de ejecucion aislado para correr codigo generado y tests
de forma segura y reproducible. Formaliza Docker runtime, timeouts, quotas,
retry policies e isolation.

**Entregables**:
- [ ] Directorio `runtime/` con configuracion de sandbox:
  - `runtime/docker/docker-compose.odoo.yml` — Odoo v18 + PostgreSQL
  - `runtime/docker/Dockerfile.odoo` — imagen base con dependencias
  - `runtime/sandbox/execution.py` — `ExecutionSandbox` class
  - `runtime/sandbox/policies.py` — timeout, quota, retry, isolation
- [ ] `ExecutionSandbox` class:
  - `run_tests(module_path)`: ejecuta pytest Odoo en contenedor
  - `run_playwright(module_path)`: ejecuta Playwright en contenedor
  - `run_auto_fix(module_path, error)`: ejecuta correccion en contenedor
  - Timeouts configurables por tipo de operacion
  - Resource quotas (CPU, memoria)
  - Retry policies con exponential backoff
- [ ] `fba sandbox up/down`: gestiona ciclo de vida del sandbox
- [ ] `fba sandbox status`: verifica estado del sandbox
- [ ] Eventos `sandbox_start`, `sandbox_error`, `sandbox_timeout` en events.jsonl
- [ ] Cleanup automatico post-ejecucion (contenedores, volumenes temporales)
- [ ] Tests: timeouts, quotas, retry, isolation entre ejecuciones

**Depende de**: M9.1 (Docker Odoo), M9.3 (auto-fix necesita sandbox aislado)

---

### Verificacion (M9)

```bash
# Iniciar sandbox
fba sandbox up

# Testing real con Docker Odoo
fba test --run        # ejecuta tests generados contra instancia real
fba test --run --playwright  # incluye tests de UI con Playwright

# Feedback loop
fba test --run --auto-fix  # fallo → analiza (via stable_id) → corrige → re-testa (max 3 ciclos)

# Gate diagnostics
fba gate --fix        # fallo → diagnostico → sugerencia → correccion automatica

# Limpiar sandbox
fba sandbox down
pytest                # todos los tests del framework pasan
```

---

## Arquitectura de Agentes

```
Orquestador (control de flujo, gate dispatch, user confirm)
├── Elicitador BABOK (metodologia tradicional)
├── Elicitador US (User Story Mapping) [M7]
├── Documentador (PRD + SDD)
├── Planificador (arquitectura Odoo)
├── Revisor de Artefactos (gates + validacion cross-artifact)
├── Validador Semantico (alineacion semantica contra solicitud original)
├── Model Generator (modelos Python desde schema.json) [M7]
├── XML Generator (vistas, seguridad, datos desde schema.json) [M7]
├── Tester/QA (pruebas Odoo + Playwright) [M9]
├── Revisor de Codigo (calidad + seguridad)
└── CI/CD Manager (GitHub Actions + releases)
```

Cada agente se define declarativamente en Markdown en `.opencode/agents/`.
El sistema es extensible por diseno: agregar un nuevo agente es agregar
un archivo Markdown con su definicion y un slash command.

### Pipeline (tasks → construction, con code gen dual)

```
planner → tasks/index.json + T*.json → code-generator
                                          ├── Schema Manager: assembly + normalization + registry lookup
                                          │   → produces schema.json (SSOT)
                                          └── Code Renderer [dual en M7]:
                                              ├── Model Generator: models/*.py
                                              └── XML Generator: views/ security/ data/
                                              → produces odoo_module/
```

## Decisiones de Diseno

| Decision | Eleccion | Justificacion |
|----------|----------|---------------|
| Runtime | OpenCode | Agente CLI maduro, multi-modelo, open source |
| Lenguaje | Python 3.11+ | Odoo es Python, SpecKit es Python, ecosistema ERP |
| Metodologia v1 | BABOK | Estandar reconocido para analisis de negocio |
| Metodologia v2 | User Stories | Alternativa agil con personas, epicas, historias [M7] |
| Comunicacion | Archivos + Eventos | Simple, trazable, sin infraestructura externa |
| CI/CD | GitHub Actions | Integracion nativa con GitHub |
| Compatibilidad | OpenSpec + SpecKit | Artefactos en formatos compatibles |
| Extension | Markdown declarativo | Agregar agentes/metodologias sin modificar nucleo |
| Empaquetado | pyproject.toml | Estandar moderno de Python |
| CLI | Click | Biblioteca madura y bien documentada |
| Arquitectura Runtime | Agents + Knowledge + Contracts | Separacion de identidad, conocimiento y garantias [M6] |
| Estabilidad | Artifact Contracts | Invariantes, ownership, allowed mutations por artefacto [M6] |
| Identidad | Stable IDs (UUID) | Entidades con identidad persistente cross-phase [M6] |
| Dominio | Domain IR en SDD | Separacion dominio puro vs implementacion Odoo [M7] |
| Code Gen | Dual (Models + XML) | Agentes especializados, menos tokens, mas mantenibles [M7] |
| Testing UI | Playwright | Browser automation para vistas Odoo [M9] |
| Execution | Docker Sandbox | Entorno aislado con timeouts, quotas, retry [M9] |
| Performance | Cache + Paralelizacion + DAG | No re-validar sin cambios, tasks en paralelo [M8] |
| Escalabilidad | Multi-modulo | Proyectos con dependencias entre modulos generados [M8] |

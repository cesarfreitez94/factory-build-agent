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
| M3: Construccion + MVP | 🚧 En Progreso | 2026-05-05 |

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

### Verificacion

```bash
fba init  # genera estructura completa en un proyecto vacio
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
- [x] Comando `/fba:build` rediseñado: flujo iterativo task-por-task con sesiones frescas
- [x] Orquestador actualizado con nueva tabla de fases
- [x] Tests unitarios del nuevo sistema de tasks
- [x] Documentacion de testing: `docs/testing/m3-tasks-files.md`

**Depende de**: M2 (SDD + plan)

---

### M3.1: Constructor Core — Schema Manager + Modulo Skeleton + Modelos
**Objetivo**: Introducir el Schema Manager como capa de determinismo entre tasks
y codigo. Producir `schema.json` (SSOT) y generar `__manifest__.py`, `__init__.py`,
y modelos Odoo v18 funcionales.

**Arquitectura interna del constructor**:
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
- [ ] Agente `constructor.md` con Schema Manager + Code Renderer
- [ ] Schema `schema.schema.json` para validar el SSOT deterministico
- [ ] Module Registry (`module_registry.json`) con modulos core de Odoo v18
- [ ] Normalizacion de nombres: many2one → `*_id`, many2many → `*_ids`, etc.
- [ ] Comando `/fba:build` con flujo: assembly schema → validate → render iterativo
- [ ] Gate `schema` validando schema.json contra schema.schema.json
- [ ] Gate `construction` extendido con validacion de consistencia schema ↔ codigo
- [ ] Builder contract: code renderer no interpreta, no renombra, no reestructura
- [ ] Tests unitarios del Schema Manager, Module Registry, y Code Renderer
- [ ] Prueba manual: modulo minimo instalable en Odoo v18

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
- [ ] Agente `tester_qa.md` + comando `/fba:test`
  - Genera tests Odoo TestCase: modelos, vistas, seguridad
  - Ejecuta tests y genera `test_report.md`
  - Gate `testing`
- [ ] Agente `revisor_codigo.md` + comando `/fba:review`
  - Revisa calidad (PEP8, Odoo conventions)
  - Revisa seguridad (ACL, validacion, datos sensibles)
  - Revisa adherencia a specs (PRD/SDD)
  - Genera `review_report.md`
  - Gate `review`
- [ ] Tests de los agentes tester y revisor
- [ ] Integracion con el orquestador

**Depende de**: M3.2 (constructor completo — necesita codigo generado)

---

### M3.4: CI/CD Manager + Integracion E2E + Docs
**Objetivo**: Framework completo E2E funcionando, probado y documentado.

**Entregables**:
- [ ] Agente `ci_cd_manager.md` + comando `/fba:ship`
  - Genera GitHub Actions workflow para el modulo Odoo
  - Gate `ci_cd`
- [ ] Flujo E2E completo con modulo "Registro de Vehiculos":
  ```
  fba init → /fba:elicit → /fba:specify → /fba:plan → /fba:tasks
  → /fba:build → /fba:test → /fba:review → /fba:ship
  ```
- [ ] Tests E2E del framework completo
- [ ] Documentacion de usuario final: `docs/testing/m3-construccion.md`
- [ ] Actualizacion de ROADMAP, CHANGELOG, version (bump a 0.5.0)

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
/fba:build
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

## Arquitectura de Agentes

```
Orquestador (fase actual, validacion, transiciones)
├── Elicitador (BABOK)
├── Documentador (PRD + SDD)
├── Planificador (arquitectura Odoo)
├── Revisor de Artefactos (gates + validacion cross-artifact)
├── Validador Semantico (alineacion semantica contra solicitud original)
├── Constructor (generacion de codigo)
├── Tester/QA (pruebas)
├── Revisor de Codigo (calidad + seguridad)
└── CI/CD Manager (GitHub Actions + releases)
```

Cada agente se define declarativamente en Markdown en `.opencode/agents/`.
El sistema es extensible por diseno: agregar un nuevo agente es agregar
un archivo Markdown con su definicion y un slash command.

## Decisiones de Diseno

| Decision | Eleccion | Justificacion |
|----------|----------|---------------|
| Runtime | OpenCode | Agente CLI maduro, multi-modelo, open source |
| Lenguaje | Python 3.11+ | Odoo es Python, SpecKit es Python, ecosistema ERP |
| Metodologia v1 | BABOK | Estandar reconocido para analisis de negocio |
| Comunicacion | Archivos + Eventos | Simple, trazable, sin infraestructura externa |
| CI/CD | GitHub Actions | Integracion nativa con GitHub |
| Compatibilidad | OpenSpec + SpecKit | Artefactos en formatos compatibles |
| Extension | Markdown declarativo | Agregar agentes/metodologias sin modificar nucleo |
| Empaquetado | pyproject.toml | Estandar moderno de Python |
| CLI | Click | Biblioteca madura y bien documentada |

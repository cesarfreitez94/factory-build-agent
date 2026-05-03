# Roadmap - Factory Build Agent

Ver tambien: [README.md](README.md) | [AGENTS.md](AGENTS.md) | [docs/PRD.md](docs/PRD.md)

---

## Estado General

| Milestone | Estado | Inicio |
|-----------|--------|--------|
| M0: Fundacion | ✅ Completado | 2026-05-02 / 2026-05-02 |
| M1: Elicitacion + Documentacion | ✅ Completado | 2026-05-03 / 2026-05-03 |
| M2: Planificacion + SDD | ⬜ Pendiente | - |
| M3: Construccion + MVP | ⬜ Pendiente | - |

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

- [ ] Sub-agente Planificador (arquitectura Odoo v18)
- [ ] Slash command `/fba:plan`
- [ ] Template SDD.md (Arquitectura, Modelos, Vistas, Seguridad, Dependencias, API)
- [ ] Template plan.md (Stack, Fases, Riesgos, Estimaciones)
- [ ] Schema JSON para validar SDD
- [ ] Trazabilidad PRD -> SDD (cada requisito mapeado a componente de diseno)
- [ ] Tests

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

### Tareas

- [ ] Sub-agente Constructor: genera codigo Odoo v18
  - `__manifest__.py`
  - Modelos (`models/`)
  - Vistas (`views/`)
  - Seguridad (`security/ir.model.access.csv`)
  - Datos demo (`data/`)
- [ ] Slash command `/fba:build`
- [ ] Sub-agente Tester/QA: genera tests Odoo (Odoo TestCase)
- [ ] Slash command `/fba:test`
- [ ] Sub-agente Revisor de Codigo: calidad, seguridad, adherencia a specs
- [ ] Slash command `/fba:review`
- [ ] Sub-agente CI/CD Manager: genera workflow GitHub Actions
- [ ] Slash command `/fba:ship`
- [ ] Prueba E2E: modulo CRUD "Registro de Vehiculos"
- [ ] Tests E2E del framework
- [ ] Documentacion de usuario final

### Verificacion

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

## Arquitectura de Agentes

```
Orquestador (fase actual, validacion, transiciones)
├── Elicitador (BABOK)
├── Documentador (PRD + SDD)
├── Planificador (arquitectura Odoo)
├── Constructor (generacion de codigo)
├── Tester/QA (pruebas)
├── Revisor de Codigo (calidad + seguridad)
└── CI/CD Manager (GitHub Actions + releases)
```

Cada agente se define declarativamente en YAML en `.opencode/agents/`.
El sistema es extensible por diseno: agregar un nuevo agente es agregar
un archivo YAML con su definicion y un slash command.

## Decisiones de Diseno

| Decision | Eleccion | Justificacion |
|----------|----------|---------------|
| Runtime | OpenCode | Agente CLI maduro, multi-modelo, open source |
| Lenguaje | Python 3.11+ | Odoo es Python, SpecKit es Python, ecosistema ERP |
| Metodologia v1 | BABOK | Estandar reconocido para analisis de negocio |
| Comunicacion | Archivos + Eventos | Simple, trazable, sin infraestructura externa |
| CI/CD | GitHub Actions | Integracion nativa con GitHub |
| Compatibilidad | OpenSpec + SpecKit | Artefactos en formatos compatibles |
| Extension | YAML declarativo | Agregar agentes/metodologias sin modificar nucleo |
| Empaquetado | pyproject.toml | Estandar moderno de Python |
| CLI | Click | Biblioteca madura y bien documentada |

# Changelog

Todas las cambios notables del proyecto Factory Build Agent se documentan en este archivo.

El formato esta basado en [Keep a Changelog](https://keepachangelog.com/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/).

---

## [0.4.0] - Pendiente

### Agregado

- M4: Sistema de Gates con Agente Revisor de Artefactos (planificado)
  - `src/fba/gate.py`: GateRunner con validaciones declarativas por fase
  - Integracion de gates en `StateManager.transition_to()`: bloquea transiciones invalidas
  - Comando `fba gate` para diagnostico manual
  - Agente Revisor de Artefactos: validacion cross-artifact (schema + trazabilidad + coherencia)
  - Slash command `/fba:gate`
  - Gates definidos en `state.json`, extensibles sin modificar codigo

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

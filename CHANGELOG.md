# Changelog

Todas las cambios notables del proyecto Factory Build Agent se documentan en este archivo.

El formato esta basado en [Keep a Changelog](https://keepachangelog.com/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/).

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

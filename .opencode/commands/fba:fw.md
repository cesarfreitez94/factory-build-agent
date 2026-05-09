---
description: Punto de entrada para el meta-desarrollo del framework FBA. El orquestador lee el estado, presenta un resumen y espera la intencion del usuario.
agent: framework-orchestrator
---

# fba:fw

Punto de entrada del sistema de meta-agentes para el desarrollo del framework FBA.

## Pre-condiciones

- El proyecto es el repositorio del framework FBA (no un proyecto Odoo generado).
- `.factory/framework-state.json` existe. Si no existe, reportar que el sistema
  de meta-agentes no esta inicializado.

## Pasos

### 1. Leer estado actual

Leer en orden:
1. `ROADMAP.md` — milestone activo y pendientes.
2. `.factory/framework-state.json` — estado de la ultima sesion, feats pendientes, decisiones.
3. `CHANGELOG.md` — ultimos cambios realizados.
4. `CONTRIBUTING.md` — recordar las reglas del workflow.

### 2. Presentar resumen al usuario

Mostrar un resumen compacto con:
- Estado del roadmap (milestones completados / activo / planificados).
- Ultima sesion: que se hizo, por cual agente, que quedo pendiente.
- Proximo paso sugerido segun el estado actual.
- Decisiones pendientes del usuario si las hay (`pending_decisions`).

Ejemplo de resumen:

```
## Estado del Framework

Roadmap: ✅ M0-M5 | ⏳ M10 activo (2/5 feats) | 📋 M6-M9 planificados

Ultima sesion: framework-builder completo feat/10.2 el 2026-05-09
Pendiente: feat/10.3-slash-commands, feat/10.4-fw-brief-template, feat/10.5-docs

Proximo paso sugerido: feat/10.3-slash-commands
```

### 3. Esperar intencion del usuario

No asumas nada. Espera a que el usuario exprese su intencion. Ejemplos:
- "continua donde quedamos"
- "implementa el M6"
- "planifica soporte multi-modelo"
- "que falta por hacer?"

### 4. Procesar intencion

Segun la intencion del usuario, delega al agente correspondiente:

| Intencion | Delegar a |
|-----------|-----------|
| Planificar algo nuevo | `framework-planner` via task tool |
| Construir/implementar | `framework-builder` via task tool |
| Informacion/estado | Responder directamente con datos de state.json y ROADMAP.md |

### 5. Al finalizar

Actualizar `.factory/framework-state.json` con los resultados de la sesion.

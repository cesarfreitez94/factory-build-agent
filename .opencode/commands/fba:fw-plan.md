---
description: Planifica una mejora del framework FBA generando un brief ejecutable (fw-brief.md). Delega al framework-planner.
agent: framework-orchestrator
---

# fba:fw-plan

Genera un plan ejecutable para una mejora del framework FBA.

## Pre-condiciones

- `.factory/framework-state.json` existe.
- El usuario proporciona una descripcion de lo que quiere planificar.

## Pasos

### 1. Validar intencion

Si el usuario no proporciono una descripcion (ej. solo escribio `/fba:fw-plan`),
preguntarle que quiere planificar usando el `question` tool.

### 2. Delegar al planner

Invocar al `framework-planner` via task tool con la intencion del usuario:

```
task(
  description="Planificar: [intencion del usuario]",
  prompt="El usuario quiere: [intencion exacta]. Lee ROADMAP.md y .factory/framework-state.json. Genera .factory/fw-brief.md con issue, branch, archivos, tests, definicion de done. Si hay ambiguedad, preguntame a mi para escalar al usuario. NO asumas nada.",
  subagent_type="framework-planner"
)
```

### 3. Presentar resultado

Lee `.factory/fw-brief.md` generado por el planner y presentalo al usuario en un formato legible:
- Objetivo
- Feats planificados (nombre, orden, dependencias)
- Archivos a crear/modificar
- Tests requeridos
- Definicion de done
- Decisiones pendientes (si el planner las identifico)

### 4. Confirmar con el usuario

Preguntar al usuario si:
- Quiere proceder con la construccion (delegar al builder).
- Quiere ajustar el plan (re-planificar con feedback).
- Quiere guardar el plan para despues.

## Post-condiciones

- `.factory/fw-brief.md` existe con el plan detallado.
- `.factory/framework-state.json` tiene el brief registrado en `open_briefs`.

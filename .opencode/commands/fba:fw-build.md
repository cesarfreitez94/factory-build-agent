---
description: Ejecuta brief de mejora del framework FBA
agent: framework-orchestrator
subtask: true
---

# fba:fw-build

Ejecuta el plan de mejora del framework FBA contenido en `.factory/fw-brief.md`.

## Pre-condiciones

- `.factory/fw-brief.md` existe y es valido.
- `.factory/framework-state.json` existe.
- El milestone branch referenciado en el brief existe (o `framework-git` lo creara).

## Pasos

### 1. Verificar brief

Leer `.factory/fw-brief.md`. Si no existe, informar al usuario que debe ejecutar
`/fba:fw-plan` primero (o `/fba:fw` para dejar que el orchestrator decida).

### 2. Mostrar resumen del brief

Presentar al usuario lo que se va a construir:
- Objetivo
- Numero de feats a ejecutar
- Restricciones del plan
- Branch destino

### 3. Delegar al builder

Invocar al `framework-builder` via task tool:

```
task(
  description="Construir: [objetivo del brief]",
  prompt="Lee .factory/fw-brief.md COMPLETO. Ejecuta todos los feats pendientes en orden. Delega operaciones git a framework-git. Delega actualizaciones de state a framework-registry. Usa framework-explorer para contexto de CONTRIBUTING.md. Sigue ESTRICTAMENTE: crea issues, branches feat/X.Y desde el milestone, escribe tests primero, implementa, pytest, commit conventional, PR al milestone branch. NO hagas commit a main. NO abras PR a main sin confirmacion.",
  subagent_type="framework-builder"
)
```

### 4. Monitorear progreso

El builder reportara al finalizar. Si encuentra blockers, los escalara.

### 5. Presentar resultado final

Al terminar el builder:
- Mostrar resumen de feats completados.
- Listar PRs abiertos al milestone branch.
- Indicar si el milestone esta listo para revision del usuario.
- Si `ready_for_user_review: true`, preguntar al usuario si quiere revisar
  y eventualmente autorizar el PR a main.

## Post-condiciones

- Cada feat tiene su branch, commit y PR al milestone branch (via `framework-git`).
- `.factory/framework-state.json` actualizado (via `framework-registry`).
- `.factory/fw-session-report.md` generado con resumen de la sesion.
- Si el brief esta completamente ejecutado, `open_briefs` actualizado (via `framework-registry`).

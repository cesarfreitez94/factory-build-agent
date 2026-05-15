# Codex Framework Planner

## Proposito

Transformar intenciones del usuario en briefs ejecutables para el desarrollo del
framework FBA.

## Principio

El planner define que debe lograrse, restricciones, dependencias y verificaciones.
No pre-implementa la solucion ni fija detalles internos innecesarios.

## Entradas

- Intencion del usuario.
- Milestone activo en `ROADMAP.md`.
- Estado en `.factory/framework-state.json`.
- Reglas de `CONTRIBUTING.md`.
- Impacto documental esperado en `AGENTS.md`, `ROADMAP.md`, `CHANGELOG.md` y
  `docs/testing/`.

## Salida

Un brief en `.factory/` cuando la tarea sea amplia o parte de un milestone. El
brief debe incluir:

- Issue.
- Branch.
- Objetivo medible.
- Feats ordenados.
- Restricciones.
- Tests requeridos.
- Definicion de Done.
- Documentacion a actualizar.

## Criterios para preguntar

Preguntar antes de planificar si:

- Falta confirmar alcance funcional.
- No existe issue y Codex no puede crearlo.
- El cambio contradice una decision arquitectonica documentada.
- El usuario pide alterar el orden del roadmap.
- El cambio podria requerir PR a `main`.

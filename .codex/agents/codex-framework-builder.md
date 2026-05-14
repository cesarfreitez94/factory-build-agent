# Codex Framework Builder

## Proposito

Implementar cambios del framework FBA de forma acotada, verificable y alineada
con `CONTRIBUTING.md`.

## Precondiciones

- Existe issue de GitHub.
- La rama activa no es `main`.
- Para feats de milestone, la rama activa es `feat/X.Y-descripcion`.
- El alcance esta claro en el mensaje del usuario o en un brief de `.factory/`.

## Flujo

1. Leer contexto relevante antes de editar.
2. Si el cambio es de riesgo medio o alto, escribir o ajustar tests primero.
3. Implementar solo lo necesario para el objetivo.
4. Actualizar documentacion si cambia alcance, arquitectura, agentes, schemas o
   comportamiento de usuario.
5. Ejecutar verificacion relevante.
6. Reportar resultados y blockers.

## Limites

- No hacer commits sin confirmacion del usuario.
- No abrir PRs a `main`.
- No iniciar el siguiente feat secuencial del milestone si el anterior aun no
  fue mergeado, salvo instruccion explicita del usuario.
- No tocar cambios no relacionados del worktree.

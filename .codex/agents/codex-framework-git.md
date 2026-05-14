# Codex Framework Git

## Proposito

Preparar operaciones git para el meta-desarrollo de FBA respetando el flujo del
repositorio.

## Reglas criticas

- Nunca commitear en `main`.
- Nunca abrir PR a `main` sin confirmacion explicita del usuario.
- No usar `--force`, `--no-verify` ni comandos destructivos sin permiso.
- Todo commit debe referenciar issue: `tipo(#NN): descripcion`.

## Operaciones habituales

- Crear rama de milestone desde `main`: `milestone/X.0-descripcion`.
- Crear rama de feature desde milestone: `feat/X.Y-descripcion`.
- Preparar commit convencional despues de tests.
- Preparar PR de `feat/` a `milestone/`.
- Preparar PR de `milestone/` a `main` solo tras validacion manual.

## Checklist pre-commit

- `git status` revisado.
- Archivos modificados pertenecen al alcance.
- Tests/verificaciones ejecutadas.
- `CHANGELOG.md` actualizado si el cambio es notable.
- Mensaje sigue Conventional Commits con issue.

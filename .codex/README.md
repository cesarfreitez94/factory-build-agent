# Marco Codex para FBA

`.codex/` define como trabajar con Codex en el meta-desarrollo de Factory Build
Agent. Es equivalente en intencion al sistema `.opencode/`, pero no es runtime:
son guias, roles y checklists para mantener el trabajo alineado con el flujo del
repositorio.

## Fuentes de verdad

Antes de planificar o implementar, Codex debe leer o verificar:

- `AGENTS.md` para arquitectura y convenciones del proyecto.
- `CONTRIBUTING.md` para issue, branch, commit, PR y validacion.
- `ROADMAP.md` para el milestone activo y dependencias.
- `CHANGELOG.md` para registrar cambios notables.
- `.factory/framework-state.json` para estado del meta-desarrollo.

## Roles

Los archivos en `.codex/agents/` no son agentes ejecutables. Son perfiles de
trabajo que Codex usa como lentes segun la tarea:

- `codex-framework-orchestrator.md`: coordina la sesion y protege el flujo.
- `codex-framework-planner.md`: convierte intenciones en briefs ejecutables.
- `codex-framework-builder.md`: implementa cambios acotados con tests.
- `codex-framework-reviewer.md`: revisa riesgos, bugs y cobertura.
- `codex-framework-git.md`: prepara operaciones git segun `CONTRIBUTING.md`.

## Flujo de sesion

1. Confirmar rama actual y estado del worktree.
2. Verificar o crear issue antes de editar archivos.
3. Trabajar desde una rama `feat/` derivada del milestone activo.
4. Si la tarea es amplia, crear o actualizar un brief en `.factory/`.
5. Implementar una sub-tarea por vez, con tests cuando aplique.
6. Ejecutar verificacion relevante antes de cerrar.
7. Registrar cambios notables en `CHANGELOG.md`.
8. No abrir PR a `main` sin confirmacion explicita del usuario.

## M16

Para M16, el marco debe mantener separados:

- Preparacion del entorno de colaboracion Codex: cambios en `.codex/`.
- Implementacion del milestone: `feat/16.1`, `feat/16.2`, `feat/16.3`.

La implementacion funcional de M16 empieza despues de tener issue, branch, brief
y alcance confirmados.

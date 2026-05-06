# Contributing to Factory Build Agent

> **IMPORTANTE**: Este documento es la fuente de verdad del proceso de desarrollo.
> Todo contribuidor (humano o AI) debe seguir este flujo sin excepcion.

---

## Reglas Fundamentales

> ⛔ **main es SOLO-LECTURA. Cero commits directos. Cero excepciones.**
> Toda modificacion al codigo se hace en branches y entra a main exclusivamente via Pull Request mergeado.

1. **NUNCA hacer commit directo a `main`**. Solo se mergea via Pull Request.
2. **Siempre crear un GitHub Issue antes de escribir codigo**. Nada se desarrolla sin issue.
3. **Usar la convencion de branching** descrita abajo.
4. **Referenciar el issue en cada commit**: `tipo(#XX): descripcion`.
5. **Tests deben pasar** antes de abrir PR.
6. **Un feat branch por sub-tarea**. Secuencial: no empezar `feat/X.Y+1` hasta que `feat/X.Y` este mergeado.
7. **Si un feat ya mergeado necesita fix**: crear `feat/X.Y.Z` donde Z es fix/mejora.
8. **Todos los PRs requieren 1 aprobacion** antes de merge.
9. **Cada milestone incluye `docs/testing/`** con instrucciones para el usuario.
10. **PR de milestone a `main` requiere validacion manual del usuario.**
    El agente debe solicitar confirmacion explicita al usuario antes de abrir el PR.
    Sin esta confirmacion, el PR a `main` no se abre.
11. **Cambios de alcance o arquitectura requieren actualizar documentacion.**
    Si un feature agrega, modifica o elimina: agentes, fases del pipeline,
    artefactos, schemas, o componentes arquitectonicos — se DEBE actualizar
    AGENTS.md (seccion Architecture), ROADMAP.md (descripcion del milestone),
    CHANGELOG.md, y los archivos de templates/docs/testing/ afectados.
    Esto es parte del feature, no un afterthought.

---

## Estrategia de Branching

### Estructura

```
main (PROTEGIDO - solo PR merge)
│
├── milestone/1.0-elicitacion-babok ──────────► PR → main
│   ├── feat/1.1-elicitacion-prompt ──► PR → milestone/1.0
│   ├── feat/1.1.1-fix-stakeholders ──► PR → milestone/1.0
│   ├── feat/1.2-flujo-preguntas ─────► PR → milestone/1.0
│   └── feat/1.3-...
│
├── milestone/2.0-planificacion-sdd ───────────► PR → main
│   └── feat/2.x-...
│
└── milestone/3.0-construccion-mvp ────────────► PR → main
    └── feat/3.x-...
```

### Convencion de Nombres

| Rama | Proposito | Ejemplo |
|------|-----------|---------|
| `milestone/X.0-descripcion` | Branch principal del milestone | `milestone/1.0-elicitacion-babok` |
| `feat/X.Y-descripcion` | Sub-tarea del milestone X | `feat/1.3-slash-command` |
| `feat/X.Y.Z-descripcion` | Fix/mejora de feat X.Y ya mergeado | `feat/1.3.1-ajustar-output` |

### Reglas

- Solo `feat/` branches mergean a `milestone/` branches.
- Solo `milestone/` branches mergean a `main`.
- Los `feat/X.Y.Z` (fixes) tambien mergean al milestone branch via PR.
- `feat/X.Y` y `feat/X.Y+1` NO pueden trabajarse en paralelo (secuencial por milestone).

---

## Ciclo de Vida de un Issue

### Sub-tarea (`feat/X.Y`)

```
1. Crear Issue con template "Feature / Sub-tarea"
2. Asignar label de fase (phase/elicitacion, phase/docs, etc.)
3. Asignar label de tipo (type/feature, type/test, etc.)
4. Vincular al Epic Issue del milestone
5. Al iniciar: crear branch feat/X.Y-descripcion desde el milestone branch
6. Desarrollar en commits atomico: "tipo(#XX): descripcion"
7. Al finalizar: abrir PR del feat branch al milestone branch
8. CI debe pasar
9. Solicitar review (1 aprobador requerido)
10. Merge → squash merge al milestone branch
11. El PR debe cerrar el Issue automaticamente con "Closes #XX"
```

### Milestone (`milestone/X.0`)

```
1. Crear Epic Issue con template "Epic / Milestone"
2. Crear branch: milestone/X.0-descripcion (desde main)
3. Crear sub-issues para cada tarea del milestone
4. Completar todas las sub-issues via PRs al milestone branch
5. Actualizar ROADMAP.md y CHANGELOG.md
6. Verificar que docs/testing/mX-descripcion.md existe
7. **Validar el milestone branch manualmente**:
   a. Ejecutar `pytest` y confirmar 0 fallos
   b. Seguir los pasos en `docs/testing/mX-*.md`
   c. Probar los comandos slash en un proyecto limpio
   d. El usuario debe dar confirmacion explicita
   e. ⛔ El agente NO PUEDE abrir PR a main sin esta confirmacion
8. Abrir PR del milestone branch a main
9. Revisar checklist de completitud
10. Merge a main
11. Cerrar Epic Issue
```

---

## Convencion de Commits

[Conventional Commits](https://www.conventionalcommits.org/) con referencia al issue:

```
feat(#XX): descripcion    # nueva feature
fix(#XX): descripcion     # bug fix
docs(#XX): descripcion    # documentacion
test(#XX): descripcion    # tests
chore(#XX): descripcion   # mantenimiento
refactor(#XX): descripcion # refactor sin cambio funcional
```

Ejemplo:
```
feat(#5): implementar flujo de preguntas BABOK para elicitacion
fix(#8): corregir validacion de campo stakeholders en PRD
docs(#10): agregar guia de testing para M1
```

---

## Checklist Pre-PR

Antes de abrir un Pull Request, verificar:

- [ ] Todos los tests pasan: `pytest`
- [ ] El codigo nuevo tiene tests (si aplica)
- [ ] La documentacion esta actualizada (AGENTS.md, ROADMAP.md, CHANGELOG.md, docs/testing/ si aplica)
- [ ] El PR referencia el Issue que cierra (`Closes #XX`)
- [ ] Los commits siguen conventional commits con referencia al issue
- [ ] El branch esta al dia con su parent (milestone o main)

---

## Labels de GitHub

| Label | Uso |
|-------|-----|
| `epic` | Issue padre de milestone |
| `milestone/0` | Fase fundacion |
| `milestone/1` | Fase elicitacion BABOK |
| `milestone/2` | Fase planificacion + SDD |
| `milestone/3` | Fase construccion + MVP |
| `phase/elicitacion` | Agente elicitador |
| `phase/docs` | Agente documentador |
| `phase/planning` | Agente planificador |
| `phase/build` | Agente constructor |
| `phase/test` | Agente tester/QA |
| `phase/review` | Agente revisor de codigo |
| `phase/cicd` | Agente CI/CD manager |
| `type/feature` | Nueva funcionalidad |
| `type/test` | Tests |
| `type/docs` | Documentacion |
| `type/chore` | Tareas de mantenimiento |
| `priority/high` | Critico |
| `priority/medium` | Normal |
| `priority/low` | Puede esperar |

---

## Documentacion de Testing

Cada milestone debe incluir un archivo en `docs/testing/` que explique al usuario
como probar la funcionalidad entregada:

```
docs/testing/
├── m0-fundacion.md          # Como probar fba init
├── m1-elicitacion.md        # Como probar la elicitacion BABOK
├── m2-planificacion.md      # Como probar plan y SDD
└── m3-construccion.md       # Como probar el flujo E2E
```

### Estructura del Documento de Testing

```markdown
# Testing - M[X]: [Nombre del Milestone]

## Requisitos Previos
- Python 3.11+, OpenCode, etc.

## Pasos para Probar

### 1. [Nombre del test]
**Objetivo**: [Que se prueba]
**Comando**:
```
[comando a ejecutar]
```
**Resultado esperado**:
```
[output esperado]
```

## Troubleshooting
[Problemas comunes y soluciones]
```

---

## Referencias

- [AGENTS.md](AGENTS.md) - Contexto tecnico para OpenCode
- [ROADMAP.md](ROADMAP.md) - Estado actual y plan de hitos
- [README.md](README.md) - Vision general del proyecto
- [docs/PRD.md](docs/PRD.md) - PRD del framework

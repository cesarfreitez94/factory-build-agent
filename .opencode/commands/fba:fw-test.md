---
description: Ejecuta tests del framework FBA con scope especifico
agent: framework-orchestrator
subtask: true
---

# fba:fw-test

Permite probar cambios de forma parcial, sin ejecutar todo el pipeline de tests.

## Uso

```
/fba:fw-test unit                    # tests unitarios de src/fba/
/fba:fw-test cli                     # tests del CLI
/fba:fw-test agents                  # tests de los agentes framework
/fba:fw-test integration             # tests E2E del flujo completo
/fba:fw-test feat/12.3               # tests de feat especifico
/fba:fw-test all                     # todos los tests (pipeline completo)
```

## Parametros

- `$ARGUMENTS` contiene el scope a probar
- Si vacio, muestra los scopes disponibles

## Scopes disponibles

| Scope | Ejecuta | Descripcion |
|-------|---------|-------------|
| `unit` | `pytest tests/test_*.py -k "not e2e"` | Tests unitarios excluyendo E2E |
| `cli` | `pytest tests/test_cli*.py` | Tests del CLI (fba init, fba doctor, etc.) |
| `agents` | `pytest tests/test_agents*.py` | Tests de los agentes framework |
| `integration` | `pytest tests/test_e2e*.py` | Tests end-to-end del flujo completo |
| `feat/X.Y` | `pytest tests/ -k "X_Y"` | Tests especificos de un feat |
| `all` | `pytest` | Todos los tests del framework |

## Flujo

1. Parsear scope de `$ARGUMENTS`
2. Si scope esta vacio, presentar menu de scopes disponibles
3. Si scope es valido, presentar al usuario que se va a ejecutar
4. Ejecutar pytest con los filtros apropiados
5. Mostrar resultados (pass/fail, coverage si disponible)

## Nota

Este comando NO usa un agente framework-test separado. Ejecuta pytest directamente
via orchestrator que tiene `bash: deny` pero puede delegar la ejecucion al builder
o可以直接 ejecutar si tiene permisos.

Si el orchestrator no tiene permisos de bash, delega la ejecucion a framework-builder
con el scope especifico para testing.
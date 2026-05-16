# Testing - M24: Meta-Framework Builders

## Estado

M24 estructura completada. El testing detallado de los componentes builders
(schema contracts, workflow v2, policy constraints, context bundle, task packet,
plan builder, roadmap slice builder, intent builder) sera cubierto en M25
junto con la nueva arquitectura de agentes meta.

## Estructura Creada

- **Schema contracts**: `schemas/meta/policy_constraints.schema.json` y demas schemas v2
- **Workflow v2 migration**: `src/fba/meta_workflow_migration.py` con drift detection
- **Builders**:
  - `src/fba/meta_policy_constraints.py` — Policy constraints generator
  - `src/fba/meta_context_broker.py` — Context bundle broker
  - `src/fba/meta_task_packet_builder.py` — Task packet builder
  - `src/fba/meta_plan_builder.py` — Plan builder
  - `src/fba/meta_roadmap_slice_builder.py` — Roadmap slice builder
  - `src/fba/meta_intent_builder.py` — Intent builder

## Verificacion Rapida

```bash
pytest tests/test_meta_*.py -v --tb=short
```

## Siguiente Paso

M25: Meta-Framework v2 Agents — implementacion de la nueva arquitectura de
agentes meta con los builders de M24 como base.

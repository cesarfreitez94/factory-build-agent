# Agent V2 Handoff

Objetivo:
Migrar .opencode/agents hacia arquitectura V2 basada en contratos.

Ya implementado y commiteado:
- schemas/meta/*
- src/fba/meta_workflow_migration.py
- src/fba/meta_policy_constraints.py
- src/fba/meta_context_broker.py
- src/fba/meta_task_packet_builder.py
- src/fba/meta_plan_builder.py
- src/fba/meta_roadmap_slice_builder.py
- src/fba/meta_intent_builder.py
- tests correspondientes

Pipeline V2 actual:
user_message
→ intent
→ policy_constraints
→ roadmap_slice
→ plan
→ task_packet
→ context_bundle

Estado:
- V1 sigue siendo autoridad.
- V2 es shadow/no intrusivo.
- No se han modificado agentes ni comandos.
- No se ha activado V2 como runtime.

Siguiente fase:
Diseñar transición desde agentes actuales .opencode/agents hacia agentes V2 contract-driven.

Prompt inicial:
Diseña la transición desde los agentes actuales de .opencode/agents hacia una arquitectura V2 basada en contratos.

Contexto:
Ya existen utilities:
- intent_builder
- policy_constraints
- roadmap_slice_builder
- plan_builder
- task_packet_builder
- context_broker
- migration V1→V2

Problema:
Los agentes actuales leen demasiado contexto, mezclan responsabilidades y gastan tokens.

Objetivo:
Diseñar:
1. Qué agentes actuales deben desaparecer.
2. Cuáles sobreviven.
3. Cuáles cambian de responsabilidad.
4. Nuevos agentes necesarios.
5. Nuevo framework-orchestrator.
6. Flujo:
   user
   → orchestrator
   → intent
   → policy
   → roadmap
   → plan
   → packet
   → context
   → implementer
   → review
   → git
7. Cómo coexistir con V1.
8. Estrategia de migración incremental.
9. Riesgos.

Restricciones:
- No implementar.
- No modificar agentes.
- Solo diseño.

Pendientes conocidos:
- Working tree puede tener cambios previos no relacionados:
  .factory/framework-state.json
  .gitignore
  .opencode/plugins/fba-agent-observer.ts
- No mezclar esos cambios con la fase agentes.

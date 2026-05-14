# Roadmap - Factory Build Agent

Ver tambien: [README.md](README.md) | [AGENTS.md](AGENTS.md) | [docs/PRD.md](docs/PRD.md)

---

## Estado General

| Milestone | Estado | Inicio |
|-----------|--------|--------|
| M0: Fundacion | ✅ Completado | 2026-05-02 / 2026-05-02 |
| M1: Elicitacion + Documentacion | ✅ Completado | 2026-05-03 / 2026-05-03 |
| M2: Planificacion + SDD | ✅ Completado | 2026-05-04 / 2026-05-04 |
| M4: Sistema de Gates | ✅ Completado | 2026-05-05 / 2026-05-05 |
| M3: Construccion + MVP | ✅ Completado | 2026-05-05 / 2026-05-06 |
| M5: Bug Fixes & Stability | ✅ Completado | 2026-05-06 / 2026-05-08 |
| M10: Framework Meta-Development | ✅ Completado | 2026-05-09 / 2026-05-09 |
| M11: Foundation Hardening | ✅ Completado | 2026-05-09 / 2026-05-12 |
| M12: Diff, Dependencies & Trazabilidad | ✅ Completado | 2026-05-12 / 2026-05-13 |
| M13: Reliability & Quality | ✅ Completado | 2026-05-13 / 2026-05-13 |
| M14: Odoo Depth | ✅ Completado | 2026-05-13 / 2026-05-13 |
| M15: Advanced QA | ✅ Completado | 2026-05-13 / 2026-05-13 |
| M16: Foundation Intelligence | ✅ Completado | 2026-05-14 / 2026-05-14 |
| M17: Semantic Core | ⏳ Planificado | Pendiente |
| M18: Input & Extension Layer | ⏳ Planificado | Pendiente |
| M19: Governance & Observability | ⏳ Planificado | Pendiente |
| M20: Graph Enforcement Gates | ⏳ Planificado | Pendiente |
| M21: Learning Loop | ⏳ Planificado | Pendiente |
| M22: Sustainability & Cost Control | ⏳ Planificado | Pendiente |

---

## Milestones completados

El detalle historico de M0-M15 esta archivado en [ROADMAP_CHECK.md](ROADMAP_CHECK.md).

---

## Roadmap Post-M15: Evolucion por Dependencias

**Fuente**: [fba-mejoras-post-roadmap.md](fba-mejoras-post-roadmap.md)

**Criterio de integracion**: los bloques del documento se convierten en milestones futuros
sin marcar completitud prematura. La secuencia prioriza prerrequisitos arquitectonicos:
primero conocimiento versionado de Odoo, luego grafo semantico, despues ingesta externa,
gobernanza humana, gates sobre grafo, aprendizaje y control de costo.

### M16: Foundation Intelligence

**Estado**: Completado.

**Objetivo**: Dar al framework una base de conocimiento version-aware antes de pedirle
decisiones mas complejas. El Constructor y el Planificador deben saber que existe en un
modulo Odoo antes de generar o extender codigo.

**Alcance**: ModuleRegistry autoindexado, Odoo Pattern Knowledge Base, y aislamiento inicial
de conocimiento por version de Odoo.

**Branch sugerido**: `milestone/16.0-foundation-intelligence`

### Feats

| Orden | Feat | Depende de | Descripcion | Estado |
|-------|------|------------|-------------|--------|
| 1 | feat/16.1-module-registry-autoindexado | M15 | Indexar modulos Odoo existentes: modelos, vistas, controllers, reportes, seguridad, data, crons, wizards y OWL | ✅ |
| 2 | feat/16.2-odoo-version-layer | feat/16.1 | Separar conocimiento `base/`, `v18/`, `v17/` para patrones, deprecaciones y novedades | ✅ |
| 3 | feat/16.3-pattern-knowledge-base | feat/16.2 | JSON estructurado de patrones Odoo, ejemplos, naming conventions y anti-patrones consultables por agentes | ✅ |

**Verificacion esperada**

```bash
fba registry index addons/my_module --odoo-version 18.0
fba registry inspect my_module
test -f .factory/registry_index.json
fba patterns query wizard.confirmation --odoo-version 18.0
pytest tests/test_registry_autoindex.py tests/test_odoo_version_layer.py tests/test_knowledge_schema_validation.py
```

---

### M17: Semantic Core

**Estado**: Planificado.

**Objetivo**: Introducir el grafo semantico como memoria compartida y trazable del sistema,
sin infraestructura externa en la primera iteracion.

**Alcance**: Ontologia tipada, persistencia en `.factory/graph.json`, queries fundamentales,
y emision gradual desde agentes existentes.

**Branch sugerido**: `milestone/17.0-semantic-core`

### Feats

| Orden | Feat | Depende de | Descripcion | Estado |
|-------|------|------------|-------------|--------|
| 1 | feat/17.1-graph-ontology | M16 | NodeType y EdgeType para BABOK, Impact Mapping, Event Storming, Example Mapping, Odoo, integraciones y calidad | ⏳ |
| 2 | feat/17.2-graph-store-queries | feat/17.1 | Persistencia JSON + queries: impact_of, is_covered, orphan_nodes, dependents, governing_adrs, full_trace | ⏳ |
| 3 | feat/17.3-agent-graph-emission | feat/17.2 | Protocolo para que Elicitador, Documentador, Planificador, Constructor, Tester y Revisores emitan nodos/aristas | ⏳ |
| 4 | feat/17.4-elicitation-method-stack | feat/17.3 | Encadenar BABOK + Impact Mapping + Event Storming + Example Mapping dentro de `/fba:elicit` | ⏳ |

**Verificacion esperada**

```bash
fba graph validate
fba graph trace req_001
fba graph impact req_001
pytest tests/test_semantic_graph.py tests/test_graph_emission.py
```

---

### M18: Input & Extension Layer

**Estado**: Planificado.

**Objetivo**: Permitir que FBA consuma conocimiento externo y trabaje tanto sobre modulos
nuevos como sobre modulos Odoo existentes.

**Alcance**: Connector Specification Layer, Connector Knowledge Model (CKM), modo `CREATE`
versus `EXTEND`, y compatibilidad de generacion incremental sobre `_inherit`.

**Branch sugerido**: `milestone/18.0-input-extension-layer`

### Feats

| Orden | Feat | Depende de | Descripcion | Estado |
|-------|------|------------|-------------|--------|
| 1 | feat/18.1-connector-spec-layer | M17 | Ingesta OpenAPI/Swagger, Postman, GraphQL SDL, HTML/PDF docs, cURL y SDK docs con confidence_score | ⏳ |
| 2 | feat/18.2-connector-knowledge-model | feat/18.1 | CKM tipado: auth, entities, endpoints, flows, errors, rate limits y retry policy | ⏳ |
| 3 | feat/18.3-create-extend-mode | M16, feat/18.2 | Detectar `CREATE`/`EXTEND`, indexar modulo base y generar deltas seguros con `_inherit` | ⏳ |

**Verificacion esperada**

```bash
fba connector ingest openapi.yaml
fba init --extend sale
fba construct --mode extend
pytest tests/test_connector_ingest.py tests/test_extend_mode.py
```

---

### M19: Governance & Observability

**Estado**: Planificado.

**Objetivo**: Formalizar los puntos donde el humano decide y registrar por que los agentes
toman decisiones relevantes.

**Alcance**: Checkpoints POST-ELICIT, POST-SPECIFY, POST-PLAN y PRE-SHIP; registro
`.factory/decisions.jsonl`; exposicion de decisiones para revisores y usuarios.

**Branch sugerido**: `milestone/19.0-governance-observability`

### Feats

| Orden | Feat | Depende de | Descripcion | Estado |
|-------|------|------------|-------------|--------|
| 1 | feat/19.1-human-checkpoints | M17 | Modelo HumanCheckpoint con resumen, decisiones, riesgos, gaps, accion requerida e impacto estimado | ⏳ |
| 2 | feat/19.2-agent-decision-log | feat/19.1 | AgentDecision JSONL con rationale, alternativas, nodos del grafo y confidence | ⏳ |
| 3 | feat/19.3-checkpoint-cli | feat/19.2 | Comandos para presentar/aprobar/corregir checkpoints sin obligar al usuario a leer artefactos completos | ⏳ |

**Verificacion esperada**

```bash
fba checkpoint show POST-PLAN
fba checkpoint approve POST-PLAN
fba decisions list --agent planificador
pytest tests/test_checkpoints.py tests/test_agent_decisions.py
```

---

### M20: Graph Enforcement Gates

**Estado**: Planificado.

**Objetivo**: Evolucionar los gates actuales hacia validaciones ejecutables sobre grafo
semantico, codigo y resultados de calidad.

**Alcance**: Architectural Gates, Semantic Gates y Delivery Gates. Estos gates bloquean
transiciones cuando falta trazabilidad, cobertura, estructura Odoo o confianza suficiente.

**Branch sugerido**: `milestone/20.0-graph-enforcement-gates`

### Feats

| Orden | Feat | Depende de | Descripcion | Estado |
|-------|------|------------|-------------|--------|
| 1 | feat/20.1-architectural-gates | M17, M18 | Dependencias circulares, estructura de modulo, bounded contexts, naming y encapsulacion | ⏳ |
| 2 | feat/20.2-semantic-gates | feat/20.1 | Cobertura requisito-test, criterio-test, riesgo-test y codigo sin trazabilidad | ⏳ |
| 3 | feat/20.3-delivery-gates | feat/20.2, M19 | Quality score, regression risk e indicadores de baja confianza del agente | ⏳ |

**Verificacion esperada**

```bash
fba gate --graph
fba gate --quality-score
fba graph orphan-nodes SOURCE_CODE
pytest tests/test_graph_gates.py tests/test_delivery_gates.py
```

---

### M21: Learning Loop

**Estado**: Planificado.

**Objetivo**: Capturar fallos como senales estructuradas y convertir patrones recurrentes
en restricciones futuras para Planificador y Constructor.

**Alcance**: FailureSignal, FailurePattern, persistencia en `.factory/failure_patterns.json`,
reduccion/restauracion de confidence y uso de patrones como contexto de regeneracion.

**Branch sugerido**: `milestone/21.0-learning-loop`

### Feats

| Orden | Feat | Depende de | Descripcion | Estado |
|-------|------|------------|-------------|--------|
| 1 | feat/21.1-failure-signals | M20 | Emitir fallos desde tests, gates, compilacion y revision con contexto y version Odoo | ⏳ |
| 2 | feat/21.2-failure-patterns | feat/21.1 | Consolidar fallos recurrentes con frecuencia, last_seen y mitigacion inyectable | ⏳ |
| 3 | feat/21.3-regeneration-feedback | feat/21.2 | Planificador y Constructor consultan failure_patterns antes de ejecutar | ⏳ |

**Verificacion esperada**

```bash
fba failures list
fba failures explain pattern_001
fba construct --use-failure-patterns
pytest tests/test_failure_signals.py tests/test_learning_loop.py
```

---

### M22: Sustainability & Cost Control

**Estado**: Planificado.

**Objetivo**: Evitar que el framework colapse por costo, tokens o complejidad interna.

**Alcance**: Estimacion previa de tokens/costo, politica de asignacion de modelos por agente,
presupuestos por fase, y reglas anti-complejidad verificables en documentacion y templates.

**Branch sugerido**: `milestone/22.0-sustainability-cost-control`

### Feats

| Orden | Feat | Depende de | Descripcion | Estado |
|-------|------|------------|-------------|--------|
| 1 | feat/22.1-token-cost-estimator | M19 | Estimar tokens/costo antes de ejecutar fases y mostrarlo en checkpoints | ⏳ |
| 2 | feat/22.2-model-routing-policy | feat/22.1 | Politica configurable por agente: modelos pesados para decisiones, ligeros para tareas repetitivas | ⏳ |
| 3 | feat/22.3-anti-complexity-contracts | feat/22.2 | Reglas: progressive disclosure, contratos minimos de agentes, YAML para config y Python para logica | ⏳ |

**Verificacion esperada**

```bash
fba cost estimate --phase all
fba models policy validate
fba doctor --complexity
pytest tests/test_cost_estimator.py tests/test_model_policy.py
```

---

## Conceptos de M6-M9 Transferidos vs No Transferidos

### Transferidos (absorbidos en M11-M15)

| Concepto old | Milestone old | Destino |
|-------------|---------------|---------|
| Artifact Contracts | M6.5 | M12 feat/12.2 |
| Stable IDs | M6.6 | M12 feat/12.4 |
| Cache de validacion | M8.3 | M13 feat/13.4 |
| Playwright | M9.2 | M15 feat/15.1 |

### Reactivados en Roadmap Post-M15

| Concepto old | Milestone old | Razon |
|-------------|---------------|-------|
| Knowledge base granular | M6.3 | Reactivado en M16 como Odoo Pattern Knowledge Base version-aware |
| Separacion runtime vs knowledge | M6.4 | Reactivado en M16 mediante `odoo_versions/base` y capas por version |
| User Stories | M7.1 | Reactivado en M17 como nodo del grafo semantico |
| Domain IR en SDD | M7.0 | Replanteado en M17 como Semantic Graph + ontologia compartida |
| Multi-modulo | M8.4 | Reactivado parcialmente en M18 y M20 mediante `CREATE`/`EXTEND`, dependencias y bounded contexts |
| Feedback loop | M9.3 | Reactivado en M21 sobre FailureSignal y FailurePattern |
| Gate diagnostics | M9.4 | Reactivado en M19-M20 via checkpoints, decisions log y graph gates |

### Siguen Pospuestos

| Concepto old | Milestone old | Razon |
|-------------|---------------|-------|
| Orquestador ligero | M6.1 | Se evaluara despues de M22 con datos reales de costo/tokens |
| Instrucciones agentes <200L | M6.2 | No bloquea funcionalidad; se mantiene como criterio de sostenibilidad, no como milestone aislado |
| Code Gen Dual (model/xml) | M7.2, M7.3 | El code-generator actual sigue siendo suficiente; M20 cubrira calidad via gates |
| Paralelizacion | M8.1 | Pospuesto hasta medir impacto real despues de M22 |
| Pipeline resumible | M8.2 | Pospuesto; M19 checkpoints y M21 learning reducen primero el riesgo operativo |
| Testing ORM real | M9.1 | Sigue fuera del alcance inmediato; requiere entorno Odoo real y decision de infraestructura |
| Execution sandbox | M9.5 | Sigue fuera del alcance del framework core |

---

## Arquitectura de Agentes

```
Orquestador (control de flujo, gate dispatch, user confirm)
├── Elicitador BABOK (metodologia tradicional)
├── Documentador (PRD + SDD)
├── Planificador (arquitectura Odoo)
├── Revisor de Artefactos (gates + validacion cross-artifact)
├── Validador Semantico (alineacion semantica contra solicitud original)
├── Code Generator (Schema Manager + Code Renderer)
├── Tester/QA (pruebas Odoo + Playwright) [M15]
├── Revisor de Codigo (calidad + seguridad)
└── CI/CD Manager (GitHub Actions + releases)
```

Cada agente se define declarativamente en Markdown en `.opencode/agents/`.
El sistema es extensible por diseno: agregar un nuevo agente es agregar
un archivo Markdown con su definicion y un slash command.

### Pipeline (tasks → construction)

```
planner → tasks/index.json + T*.json → code-generator
                                          ├── Schema Manager: assembly + normalization + registry lookup
                                          │   → produces schema.json (SSOT)
                                          └── Code Renderer: iterative generation per task
                                              → produces odoo_module/
```

## Decisiones de Diseno

| Decision | Eleccion | Justificacion |
|----------|----------|---------------|
| Runtime | OpenCode | Agente CLI maduro, multi-modelo, open source |
| Lenguaje | Python 3.11+ | Odoo es Python, SpecKit es Python, ecosistema ERP |
| Metodologia | BABOK | Estandar reconocido para analisis de negocio |
| Comunicacion | Archivos + Eventos | Simple, trazable, sin infraestructura externa |
| CI/CD | GitHub Actions | Integracion nativa con GitHub |
| Compatibilidad | OpenSpec + SpecKit | Artefactos en formatos compatibles |
| Extension | Markdown declarativo | Agregar agentes/metodologias sin modificar nucleo |
| Empaquetado | pyproject.toml | Estandar moderno de Python |
| CLI | Click | Biblioteca madura y bien documentada |
| SSOT | schema.json | Single source of truth for module structure, eliminates ambiguity between tasks and code |

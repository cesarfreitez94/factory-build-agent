# FBA — Mejoras Post-Roadmap

> Documento de arquitectura y evolución del framework.
> Secuencia ordenada por dependencias: cada bloque es prerequisito del siguiente.

---

## Bloque 1 — Foundation Layer
*Prerequisito de todo lo demás. Sin esto, los agentes operan a ciegas.*

### 1.1 ModuleRegistry Autoindexado (version-aware)

El registry debe construirse automáticamente pasando el path de un módulo Odoo existente,
sin intervención manual. Debe ser consciente de la versión de Odoo para que la migración
futura (v18 → v19) no requiera reescritura.

**Qué indexa:**
- Modelos: campos, tipos, herencia (`_inherit`, `_inherits`), constraints
- Vistas: form, tree, kanban, search, pivot, graph, calendar
- Controllers: rutas, métodos HTTP, autenticación
- Reportes: QWeb templates, paper formats
- Seguridad: `ir.model.access`, record rules, grupos
- Data: archivos XML/CSV de datos iniciales y demo
- Crons: intervalos, métodos, activos/inactivos
- Wizards: modelos transient, vistas asociadas
- OWL Components: componentes JS, props, hooks

**Contrato de salida:**
```python
@dataclass
class IndexedModule:
    name: str
    odoo_version: str           # "18.0", "17.0", etc.
    models: list[ModelMeta]
    views: list[ViewMeta]
    dependencies: list[str]     # otros módulos requeridos
    registry_version: int       # para invalidación de caché
```

**Regla:** Cada agente del framework consulta el registry antes de generar.
Nunca genera sin saber qué existe.

---

### 1.2 Odoo Pattern Knowledge Base

Base de conocimiento interna que describe cómo se construye cada artefacto Odoo.
Es el "libro de reglas" que alimenta al Constructor y al Planificador.

**Patrones indexados:**
- Cómo heredar un modelo sin romper compatibilidad
- Patrones de vista por tipo de caso de uso (wizard de confirmación, dashboard, etc.)
- Estructura correcta de `security/` por tipo de módulo
- Patrones de integración entre módulos (Many2one, delegation inheritance)
- Convenciones de naming por tipo de artefacto
- Anti-patrones conocidos que el Revisor debe detectar

**Formato:** YAML estructurado + ejemplos de código por patrón, accesible via query
semántico desde los agentes.

---

## Bloque 2 — Semantic Core
*La fundación arquitectónica del framework. Habilita todo lo de los bloques 3-6.*

### 2.1 Semantic Graph + Ontología

El grafo semántico es la memoria compartida del sistema. Los agentes no se comunican
solo via archivos — emiten y consultan el grafo como efecto secundario de su trabajo.
Cada nodo y arista tiene tipo explícito, lo que habilita razonamiento, no solo almacenamiento.

**Implementación:** Pydantic (nodos tipados) + NetworkX (traversal). Sin infraestructura
externa en fase inicial. Serialización a JSON para persistencia en `.factory/graph.json`.

#### Ontología — Tipos de Nodo

Los nodos están organizados por capa. Cada metodología de elicitación aporta
su propia capa de nodos; todas convergen en el grafo compartido.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAPA 1 — BABOK (elicitación estructurada)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIREMENT         Requisito funcional o no funcional
USER_STORY          Historia de usuario derivada del requisito
DOMAIN_CAPABILITY   Capacidad de negocio que agrupa historias
ACCEPTANCE_CRITERIA Criterio de aceptación de una historia
RISK                Riesgo identificado asociado a un requisito o decisión
ADR                 Architecture Decision Record

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAPA 2 — Impact Mapping (objetivos y actores)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUSINESS_GOAL       Objetivo de negocio medible ("reducir cierre contable 30%")
ACTOR               Rol o persona que interactúa con el sistema ("Contador")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAPA 3 — Event Storming (modelo de dominio)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOMAIN_EVENT        Algo que ocurrió en el dominio ("Factura confirmada")
COMMAND             Intención que produce un evento ("Confirmar factura")
AGGREGATE           Conjunto de modelos con consistencia propia
POLICY              Reacción automática a un evento ("Cuando X, hacer Y")
READ_MODEL          Proyección de datos para lectura (vistas, dashboards, reportes)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAPA 4 — Example Mapping (criterios y tests)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUSINESS_RULE       Regla de negocio concreta ("Factura sin líneas no puede confirmarse")
EXAMPLE             Escenario concreto que ilustra una regla (dado/cuando/entonces)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAPA 5 — Artefactos Odoo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ODOO_MODULE         Módulo Odoo completo
ODOO_MODEL          Modelo (_name, campos, herencia)
ODOO_FIELD          Campo individual de un modelo
ODOO_VIEW           Vista (form/tree/kanban/etc.)
ODOO_CONTROLLER     Endpoint HTTP
ODOO_REPORT         Reporte QWeb
ODOO_WIZARD         Modelo transient + vista
ODOO_OWL_COMPONENT  Componente JavaScript OWL
ODOO_CRON           Trabajo programado (→ derivado de POLICY)
ODOO_AUTOMATION     Automated action de Odoo (→ derivado de POLICY)
ODOO_RULE           Record rule de seguridad
ODOO_ACCESS         Línea de ir.model.access

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAPA 6 — Integraciones externas
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API_CONTRACT        Contrato de integración externa
ENDPOINT            Endpoint individual de una API
SCHEMA_ENTITY       Entidad de datos de una API externa
CONNECTOR_SPEC      Especificación fuente (OpenAPI, Swagger, PDF, etc.)
CONNECTOR_KM        Connector Knowledge Model derivado

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAPA 7 — Calidad y código
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST_CASE           Caso de prueba (→ derivado de EXAMPLE)
TEST_RESULT         Resultado de ejecución de un test
SOURCE_CODE         Archivo de código fuente generado
```

#### Ontología — Tipos de Arista

```
# ── Impact Mapping ────────────────────────────────────────────
PURSUES             Actor pursues BusinessGoal
IMPACTS             UserStory impacts BusinessGoal
OWNS                Actor owns Requirement

# ── Event Storming ────────────────────────────────────────────
TRIGGERS            Command triggers DomainEvent
REACTS_TO           Policy reacts_to DomainEvent
PRODUCES            DomainEvent produces ReadModel
EMITTED_BY          DomainEvent emitted_by Aggregate
HANDLED_BY          Command handled_by Aggregate
MAPS_TO_MODULE      Aggregate maps_to OdooModule
MAPS_TO_VIEW        Command maps_to OdooView
MAPS_TO_CRON        Policy maps_to OdooCron
MAPS_TO_AUTOMATION  Policy maps_to OdooAutomation

# ── Example Mapping ───────────────────────────────────────────
GOVERNS_STORY       BusinessRule governs_story UserStory
ILLUSTRATES         Example illustrates BusinessRule
BECOMES             Example becomes TestCase

# ── Trazabilidad descendente (BABOK) ──────────────────────────
IMPLEMENTS          UserStory implements Requirement
DERIVES_FROM        UserStory derives_from DomainCapability
SATISFIES           SourceCode satisfies Requirement
TRACES_TO           SourceCode traces_to UserStory
REFINES             AcceptanceCriteria refines UserStory

# ── Cobertura de calidad ──────────────────────────────────────
VALIDATES           TestCase validates AcceptanceCriteria
VALIDATES_RULE      TestCase validates_rule BusinessRule
COVERS              TestCase covers Risk
VERIFIES            TestResult verifies TestCase

# ── Estructura Odoo ───────────────────────────────────────────
BELONGS_TO          OdooModel belongs_to OdooModule
CONTAINS            OdooModel contains OdooField
RENDERS             OdooView renders OdooModel
DEPENDS_ON          OdooModule depends_on OdooModule
INHERITS            OdooModel inherits OdooModel

# ── Decisiones arquitectónicas ────────────────────────────────
MOTIVATED_BY        ADR motivated_by Risk
GOVERNS             ADR governs OdooModule
VIOLATES            SourceCode violates ADR

# ── Generación por agentes ────────────────────────────────────
GENERATES           Agent generates SourceCode / OdooModel
PLANNED_BY          OdooModel planned_by ADR

# ── Integraciones externas ────────────────────────────────────
PARSED_FROM         ConnectorKM parsed_from ConnectorSpec
IMPLEMENTS_CONTRACT OdooModule implements_contract APIContract
MAPS_TO             SchemaEntity maps_to OdooField
```

#### Queries fundamentales que habilita

```python
# ¿Qué se rompe si cambio este requisito?
graph.impact_of("req_facturacion_electronica")

# ¿Este requisito tiene tests asociados?
graph.is_covered("req_001", via=EdgeType.VALIDATES)

# ¿Qué código no tiene trazabilidad a ningún requisito? (drift)
graph.orphan_nodes(type=NodeType.SOURCE_CODE)

# ¿Qué módulos dependen de este modelo?
graph.dependents("odoo_model_account_move")

# ¿Qué decisiones arquitectónicas gobiernan este módulo?
graph.governing_adrs("odoo_module_facturacion")

# ¿Qué requisitos no tienen ningún test case?
graph.uncovered_nodes(NodeType.REQUIREMENT, EdgeType.VALIDATES)

# ── Nuevas queries habilitadas por la ontología extendida ──

# ¿Qué historias de usuario impactan este objetivo de negocio?
graph.predecessors("goal_cierre_contable", via=EdgeType.IMPACTS)

# ¿Qué reglas de negocio no tienen ejemplos concretos? (riesgo de ambigüedad)
graph.uncovered_nodes(NodeType.BUSINESS_RULE, EdgeType.ILLUSTRATES)

# ¿Qué ejemplos no se convirtieron en tests aún? (gap de cobertura)
graph.uncovered_nodes(NodeType.EXAMPLE, EdgeType.BECOMES)

# ¿Qué políticas del dominio no tienen implementación Odoo?
graph.uncovered_nodes(NodeType.POLICY, EdgeType.MAPS_TO_AUTOMATION)

# ¿Qué eventos de dominio no producen ningún read model?
graph.uncovered_nodes(NodeType.DOMAIN_EVENT, EdgeType.PRODUCES)

# ¿Qué actor no tiene ningún requisito asignado? (stakeholder ignorado)
graph.uncovered_nodes(NodeType.ACTOR, EdgeType.OWNS)

# Trazabilidad completa de un objetivo al código:
# BusinessGoal → UserStory → BusinessRule → Example → TestCase → SourceCode
graph.full_trace("goal_cierre_contable")
```

#### Protocolo de emisión por agente

Cada agente emite al grafo como efecto secundario de su trabajo.
El Elicitador conduce internamente 4 fases metodológicas; para el usuario es una sola conversación.

```
Elicitador
  Fase 1 — BABOK        → emite: Requirement, Risk, AcceptanceCriteria
  Fase 2 — Impact Map   → emite: BusinessGoal, Actor
                          aristas: pursues, impacts, owns
  Fase 3 — Event Storm  → emite: DomainEvent, Command, Aggregate, Policy, ReadModel
                          aristas: triggers, reacts_to, produces, emitted_by
  Fase 4 — Example Map  → emite: UserStory, BusinessRule, Example
                          aristas: governs_story, illustrates, implements

Documentador  → emite: DomainCapability, ADR
                aristas: derives_from, motivated_by

Planificador  → emite: OdooModule, OdooModel
                aristas: depends_on, planned_by, maps_to_module, maps_to_cron

Constructor   → emite: SourceCode, OdooField, OdooView, OdooAutomation, OdooCron
                aristas: traces_to, generates, maps_to_view, maps_to_automation

Tester        → emite: TestCase (desde Example via BECOMES), TestResult
                aristas: validates, validates_rule, covers, verifies, becomes

Revisor       → emite: aristas violates cuando detecta incumplimientos

CI/CD Manager → actualiza TestResult con resultados reales de pipeline
```

### 2.2 Capa de Metodologías de Elicitación

El agente Elicitador no usa una sola metodología — combina cuatro de forma encadenada.
El usuario no necesita conocerlas; el agente las conduce como una conversación única.

```
┌─────────────────────────────────────────────────────────────────┐
│  CONVERSACIÓN CON EL USUARIO (una sola sesión /fba:elicit)      │
├──────────┬──────────────┬───────────────┬───────────────────────┤
│  BABOK   │ Impact Map   │ Event Storming│   Example Mapping     │
├──────────┼──────────────┼───────────────┼───────────────────────┤
│ ¿Qué     │ ¿Para qué    │ ¿Qué eventos  │ ¿Qué reglas gobiernan │
│ necesitas?│ objetivo?   │ ocurren en    │ cada historia?        │
│ ¿Qué no  │ ¿Quién lo   │ el dominio?   │ Dame un ejemplo       │
│ funciona?│ necesita?   │ ¿Qué lo       │ concreto de cada      │
│          │             │ dispara?      │ regla.                │
├──────────┼──────────────┼───────────────┼───────────────────────┤
│Requirement│BusinessGoal │DomainEvent    │BusinessRule           │
│UserStory  │Actor        │Command        │Example                │
│Risk       │             │Aggregate      │  → TestCase           │
│Criteria   │             │Policy         │                       │
└──────────┴──────────────┴───────────────┴───────────────────────┘
```

**Mapeo Event Storming → Odoo** (lo que hace el Planificador automáticamente):

```
Aggregate   →  OdooModule (o conjunto de modelos con _name relacionados)
Command     →  OdooView con botón de acción (button type="object")
DomainEvent →  mail.thread tracking / trigger de automated action
Policy      →  OdooAutomation (ir.actions.server) o OdooCron
ReadModel   →  OdooView tree/kanban/pivot o OdooReport QWeb
```

Este mapeo es la razón por la que Event Storming es la técnica más valiosa
para Odoo en particular: el modelo interno de Odoo ya es event-driven.

---

## Bloque 3 — Input Layer
*Cómo el framework consume conocimiento externo.*

### 3.1 Connector Specification Layer

El framework puede ingerir documentación de APIs externas en múltiples formatos
y convertirla en un Connector Knowledge Model (CKM) tipado, que luego se registra
en el grafo semántico como nodo `CONNECTOR_KM`.

**Formatos de entrada soportados:**
- OpenAPI 3.x / Swagger 2.x (JSON + YAML)
- Postman Collections v2.x
- Documentación HTML scrapeada
- PDFs de documentación técnica
- GraphQL schemas (SDL)
- Ejemplos cURL anotados
- SDK docs (Python, JS)

**Modelo de confianza variable:** No todos los inputs generan el mismo nivel de contrato.
Cada fuente tiene un `confidence_score` que se propaga al CKM.

```
OpenAPI/Swagger   → confidence: HIGH   (schema formal)
GraphQL SDL       → confidence: HIGH
Postman           → confidence: MEDIUM (ejemplos sin schema completo)
HTML/PDF docs     → confidence: LOW    (parseado heurístico)
cURL examples     → confidence: LOW
```

**Salida — Connector Knowledge Model:**
```python
@dataclass
class ConnectorKnowledgeModel:
    id: str
    source_format: str
    confidence: float
    base_url: str
    auth: AuthSpec           # oauth2, apikey, basic, bearer
    entities: list[SchemaEntity]
    endpoints: list[EndpointSpec]
    flows: list[FlowSpec]    # secuencias de llamadas documentadas
    error_codes: dict[int, str]
    rate_limits: RateLimitSpec
    retry_policy: RetrySpec
```

**Derivaciones automáticas desde el CKM:**
- Contratos tipados (Pydantic models por entidad)
- Adaptadores de integración Odoo (mapeo campo a campo)
- Políticas de sincronización (webhook vs polling, estrategia de conflicto)
- Flows de autenticación listos para implementar

---

## Bloque 4 — Process Layer
*Cómo el sistema interactúa con humanos y se hace auditable.*

### 4.1 Human-in-the-Loop Checkpoints Formalizados

El flujo de agentes no debe asumir autonomía total. Hay puntos donde la decisión
humana es necesaria, y el sistema debe presentar contexto suficiente para decidir rápido.

**Checkpoints obligatorios:**

```
POST-ELICIT    → Validar que los requisitos capturados son correctos
               Presenta: lista de requirements + riesgos identificados
               Acción: aprobar / corregir / agregar

POST-SPECIFY   → Validar PRD y SDD antes de planificar
               Presenta: resumen de capacidades + decisiones de diseño
               Acción: aprobar / rechazar sección / modificar

POST-PLAN      → Validar arquitectura Odoo antes de construir
               Presenta: módulos a crear, dependencias, ADRs tomadas
               Acción: aprobar / cambiar decisión arquitectónica

PRE-SHIP       → Gate final antes de merge/deploy
               Presenta: score de calidad, cobertura, riesgos residuales
               Acción: aprobar / forzar revisión adicional
```

**Formato de presentación de cada checkpoint:**
```python
@dataclass
class HumanCheckpoint:
    phase: str
    summary: str                    # qué hicieron los agentes
    decisions_made: list[str]       # decisiones que tomaron
    risks_identified: list[Risk]    # riesgos del grafo
    gaps: list[str]                 # qué falta según el grafo
    required_action: str            # qué necesita el humano
    estimated_impact: str           # si no se interviene, qué pasa
```

---

### 4.2 Agent Decision Observability

El sistema debe registrar no solo qué generó cada agente, sino por qué tomó
cada decisión relevante. Esto es distinto a la trazabilidad de artefactos.

**Qué se registra:**
```python
@dataclass
class AgentDecision:
    agent: str
    timestamp: str
    decision: str           # "Usar Many2one en lugar de Many2many"
    rationale: str          # "Porque la relación es N:1 según el requisito REQ-042"
    alternatives: list[str] # "Many2many si la relación fuera N:M"
    graph_nodes: list[str]  # nodos del grafo que motivaron la decisión
    confidence: float
```

Almacenado en `.factory/decisions.jsonl`. Accesible para el Revisor y para el humano
en cualquier checkpoint. Permite entender el sistema sin leer el código generado.

---

## Bloque 5 — Quality Layer
*Donde el framework pasa de asistente a sistema operativo de ingeniería.*

### 5.1 Enforcement Gates Automáticos

Los gates son queries sobre el grafo semántico + validaciones estáticas del código.
No son sugerencias — bloquean el avance en el flujo.

#### Architectural Gates
```python
# Valida que no haya dependencias circulares entre módulos
def gate_no_circular_deps(graph) -> GateResult:
    cycles = list(nx.simple_cycles(graph.module_subgraph()))
    return GateResult(passed=len(cycles)==0, violations=cycles)

# Valida que los módulos Odoo sigan la estructura de directorios correcta
def gate_module_structure(module_path) -> GateResult: ...

# Valida bounded contexts: un modelo no puede pertenecer a dos módulos
def gate_bounded_contexts(graph) -> GateResult: ...

# Valida naming conventions por tipo de artefacto
def gate_naming_conventions(source_code) -> GateResult: ...

# Valida que no se acceda a campos privados de otros módulos
def gate_encapsulation(graph) -> GateResult: ...
```

#### Semantic Gates
```python
# Todo requisito debe tener al menos un test case
def gate_requirement_coverage(graph) -> GateResult:
    uncovered = graph.uncovered_nodes(NodeType.REQUIREMENT, EdgeType.VALIDATES)
    return GateResult(passed=len(uncovered)==0, violations=uncovered)

# Todo código generado debe tener trazabilidad a un requisito
def gate_traceability(graph) -> GateResult:
    orphans = graph.orphan_nodes(type=NodeType.SOURCE_CODE)
    return GateResult(passed=len(orphans)==0, violations=orphans)

# Todo criterio de aceptación debe estar cubierto por un test
def gate_criteria_coverage(graph) -> GateResult: ...

# Todo riesgo identificado debe tener al menos un test que lo cubra
def gate_risk_coverage(graph) -> GateResult: ...
```

#### Delivery Gates
```python
# Score de calidad mínimo antes de ship
def gate_quality_score(test_results) -> GateResult:
    score = calculate_quality_score(test_results)
    return GateResult(passed=score >= 0.85, score=score)

# Análisis de regresión: cambios que afectan módulos existentes
def gate_regression_risk(graph, changed_nodes) -> GateResult:
    impacted = [graph.impact_of(n) for n in changed_nodes]
    return GateResult(passed=True, warnings=impacted)  # warning, no blocker

# Confianza del agente constructor en el código generado
def gate_agent_confidence(decisions) -> GateResult:
    low_confidence = [d for d in decisions if d.confidence < 0.7]
    return GateResult(passed=len(low_confidence)==0, warnings=low_confidence)
```

---

## Bloque 6 — Learning Layer
*Lo que convierte el sistema en uno que mejora con el tiempo.*

### 6.1 Feedback Loop desde Fallos

Cuando el código generado falla (tests, validación, gate), el sistema debe capturar
esa señal de forma estructurada y usarla en la próxima generación del mismo tipo
de artefacto. Sin esto, el objetivo de largo plazo (self-improving system) no es alcanzable.

**Ciclo de aprendizaje:**
```
Fallo detectado
    → FailureSignal emitido (tipo, agente, artefacto, contexto)
    → nodo de grafo actualizado (confidence reducida)
    → FailurePattern registrado si es recurrente
    → Pattern inyectado como restricción al agente en próxima ejecución
    → Éxito posterior → confidence restaurada
```

```python
@dataclass
class FailureSignal:
    agent: str
    artifact_node_id: str       # nodo del grafo que falló
    failure_type: str           # "test_failure", "gate_violation", "compile_error"
    error_message: str
    context: dict               # inputs que llevaron al fallo
    odoo_version: str

@dataclass
class FailurePattern:
    pattern_id: str
    failure_type: str
    frequency: int
    last_seen: str
    mitigation: str             # instrucción que se inyecta al agente
```

Almacenado en `.factory/failure_patterns.json`. El Planificador y Constructor
consultan este archivo antes de ejecutar.

---

### 6.2 Estrategia de Versión Odoo

El framework debe sobrevivir a cambios de versión sin reescritura completa.
El conocimiento específico de versión debe estar aislado del core.

**Estructura:**
```
fba/
  odoo_versions/
    v18/
      patterns.yaml       # patrones específicos de v18
      deprecated.yaml     # lo que ya no funciona en v18
      new_features.yaml   # novedades de v18 vs v17
    v17/
      patterns.yaml
    base/
      patterns.yaml       # patrones comunes a todas las versiones
```

El ModuleRegistry, el Planificador y el Constructor resuelven la versión al inicio
del proyecto y cargan solo el conocimiento de esa versión + base.

---

### 6.3 Estrategia Módulo Nuevo vs Módulo Existente

El flujo actual asume creación desde cero. En proyectos Odoo reales, la modificación
y extensión de módulos existentes es igualmente frecuente.

**Dos modos de operación:**

```
MODE: CREATE    → flujo actual completo (elicit → build → ship)

MODE: EXTEND    → flujo adaptado:
                  1. Registry indexa módulo existente
                  2. Elicitador trabaja sobre delta (qué cambia, no qué hay)
                  3. Planificador verifica compatibilidad con el módulo base
                  4. Constructor genera solo artefactos de extensión
                     (_inherit en lugar de nuevos modelos cuando corresponde)
                  5. Gates validan que la extensión no rompe el módulo base
```

El modo se detecta automáticamente si el registry encuentra un módulo con el mismo
nombre técnico, o se especifica explícitamente con `fba init --extend nombre_modulo`.

---

## Bloque 7 — Sustainability
*Cómo evitar que el framework colapse bajo su propio peso.*

### 7.1 Gestión de Costo y Tokens

Con 7 agentes en un ciclo completo, el costo por módulo puede ser prohibitivo sin
una estrategia explícita de cuándo usar modelos pesados vs ligeros.

**Política de asignación:**
```
claude-opus / gpt-4o    → Elicitador, Planificador (decisiones de alto impacto)
claude-sonnet           → Documentador, Constructor, Revisor (generación intensiva)
claude-haiku / gpt-4o-mini → Tester (generación repetitiva de tests)
                           CI/CD Manager (plantillas predecibles)
```

**Estimación previa a ejecución:**
- El sistema estima tokens antes de iniciar el flujo
- Muestra costo estimado al usuario en el checkpoint `POST-ELICIT`
- Permite al usuario reducir scope o cambiar política de modelos

---

### 7.2 Principios Anti-Complejidad

El riesgo más alto del framework es volverse imposible de mantener.
Estas reglas son no negociables:

**Progressive Disclosure:** El usuario no necesita entender el grafo para usar el framework.
Los gates se muestran como resultados simples (pass/fail + qué falta), no como queries.

**Contract mínimo de agentes:** Cada agente tiene exactamente una responsabilidad,
un formato de input, y un formato de output definido en schema. No hay lógica compartida
no declarada entre agentes.

**YAML para configuración, Python para lógica:** El YAML define qué agentes existen
y qué comandos exponen. La lógica de razonamiento, gates y queries vive en Python.
Nunca al revés.

**Lo que el framework NO hace (explícito):**
- No gestiona infraestructura Odoo (eso es odoo-deploy, Kubernetes, etc.)
- No reemplaza revisión humana de requisitos de negocio complejos
- No garantiza código libre de bugs, garantiza trazabilidad y cobertura

---

## Roadmap Reordenado por Dependencias

```
CORTO PLAZO (prerequisitos del resto)
├── 1.1 ModuleRegistry autoindexado (version-aware)
├── 1.2 Odoo Pattern Knowledge Base
├── 2.1 Semantic Graph + Ontología (fundación)
└── 4.2 Agent Decision Observability (auditoría básica)

MEDIANO PLAZO (habilitan calidad)
├── 3.1 Connector Specification Layer
├── 4.1 Human-in-the-Loop Checkpoints
├── 5.1 Enforcement Gates (Architectural + Semantic + Delivery)
├── 6.3 Estrategia módulo nuevo vs existente
└── 6.2 Estrategia de versión Odoo

LARGO PLAZO (diferencian el framework)
├── 6.1 Feedback Loop desde fallos
├── 7.1 Gestión de costo y tokens
├── Impact analysis automático (query sobre grafo)
├── Auto-review reasoning (Revisor usa grafo, no heurísticas)
├── Architectural governance (gates + ADRs)
├── Change propagation (grafo + checkpoints)
└── Organizational memory / self-improving system
```

---

*Versión 1.1 — ontología extendida con Event Storming, Example Mapping e Impact Mapping*

# M6: Optimizacion de Agentes — Plan de Implementacion

> Arquitectura y especificacion tecnica del milestone 6.
> Branch: `milestone/6.0-optimizar-agentes`
> Fecha: 2026-05-09

---

## Arquitectura General

```
┌──────────────────────────────────────────────────────────────────┐
│                    ORQUESTADOR (~80 lineas)                       │
│                                                                    │
│  while fase != "complete":                                        │
│    accion = fba session query(current_phase)                       │
│                                                                    │
│    if accion == "elicit_round":              ← Camino B            │
│      leer elicit_questions.json                                   │
│      para cada pregunta: usar question tool (clickable)            │
│      guardar respuestas en elicit_answers.json                    │
│                                                                    │
│    if accion == "invoke_agent":                                    │
│      task(agente, comando)                                        │
│                                                                    │
│    if accion == "transition":                                      │
│      fba transition <fase>                                        │
│                                                                    │
│  fba record(evento)                                               │
└───────┬──────────────┬──────────────┬─────────────────────────────┘
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌───────────┐ ┌──────────────────────────┐
│ SESSION MGR  │ │ GATE/TX   │ │ ARCHIVOS                  │
│ (CLI Python) │ │ (CLI)     │ │                            │
│              │ │           │ │ state.json                 │
│ stateless    │ │ transition│ │ events.jsonl               │
│ lee state.json│ │ + gates  │ │ elicit_questions.json      │
│ responde JSON│ │           │ │ elicit_answers.json        │
└──────────────┘ └───────────┘ │ elicit_output.json         │
                               └──────────────────────────┘
```

### Decisiones Clave

| Decision | Eleccion | Justificacion |
|----------|----------|---------------|
| Session Manager | CLI Python determinista | Zero tokens, 100% testeable, la info ya esta en state.json |
| Elicitacion | Camino B (JSON protocol) | Elicitador disena preguntas, orquestador las renderiza con question tool. Clickable, misma UX |
| Knowledge loading | Read tool bajo demanda | Sub-agentes cargan knowledge files solo cuando necesitan |
| Contracts | Markdown + YAML frontmatter | Legible por humanos/agentes, parseable por GateRunner |
| Stable IDs | UUID v4, merge por UUID (fallback a nombre) | Backward compatible, inmutable cross-phase |
| Deploy | `fba init` / `fba update` copian knowledge/ y contracts/ | Cero cambios en runtime del proyecto destino |

### Arquitectura de Capas (M6.4)

```
.opencode/
├── agents/        ← solo identidad (frontmatter + rol, <50 lineas c/u)
├── knowledge/     ← metodologia, convenciones, patrones por dominio
├── contracts/     ← garantias entre artefactos
├── commands/      ← slash commands
└── protocols/     ← protocolos compartidos
```

---

## feat/6.0: Session Manager

### Archivos Nuevos

#### `src/fba/session_manager.py`

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json

class ActionType(str, Enum):
    INVOKE_AGENT = "invoke_agent"
    ELICIT_ROUND = "elicit_round"
    TRANSITION = "transition"
    ASK_USER = "ask_user"
    COMPLETE = "complete"

@dataclass
class SessionQuery:
    query: str              # "next_action" | "gate_failure" | "user_decision"
    current_phase: str
    phase_status: str | None = None
    gate_result: dict | None = None
    user_choice: str | None = None

@dataclass
class SessionResponse:
    action: ActionType
    agent: str | None = None
    command: str | None = None
    input_files: list[str] | None = None
    questions_file: str | None = None
    answers_file: str | None = None
    to_phase: str | None = None
    gates_required: list[str] | None = None
    user_question: dict | None = None
    summary: str | None = None

class SessionManager:
    def __init__(self, project_dir: Path): ...
    def query(self, q: SessionQuery) -> SessionResponse: ...
    def _determine_action(self, state, q) -> SessionResponse: ...
    def _handle_interactive_phase(self, state, q) -> SessionResponse: ...
    def _handle_batch_phase(self, state, q) -> SessionResponse: ...
    def _find_valid_transition(self, state, phase) -> str | None: ...
```

**Logica de `_determine_action`**:

| Estado | Accion |
|---|---|
| Fase `interactive` + status `pending` + no hay answers | `invoke_agent` (elicitador produce preguntas) |
| Fase `interactive` + hay `questions_file` sin `answers_file` | `elicit_round` (orquestador presenta preguntas) |
| Fase `interactive` + hay `answers_file` + no hay `output_file` | `invoke_agent` (elicitador procesa respuestas) |
| Fase `interactive` + hay `output_file` (elicit_output.json) | `transition` |
| Fase `batch` + status `pending` | `invoke_agent` |
| Fase `batch` + status `completed` + gate OK | `transition` |
| Fase `batch` + status `completed` + gate FAIL | `ask_user` |
| Fase == `complete` | `complete` |

#### `schemas/session_query.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "query": { "enum": ["next_action", "gate_failure", "user_decision"] },
    "current_phase": { "type": "string" },
    "phase_status": { "type": "string" },
    "gate_result": { "type": "object" },
    "user_choice": { "type": "string" }
  },
  "required": ["query", "current_phase"]
}
```

#### `schemas/session_response.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "action": { "enum": ["invoke_agent", "elicit_round", "transition", "ask_user", "complete"] },
    "agent": { "type": "string" },
    "command": { "type": "string" },
    "input_files": { "type": "array", "items": {"type": "string"} },
    "questions_file": { "type": "string" },
    "answers_file": { "type": "string" },
    "to_phase": { "type": "string" },
    "gates_required": { "type": "array", "items": {"type": "string"} },
    "user_question": { "type": "object" },
    "summary": { "type": "string" }
  },
  "required": ["action"]
}
```

### Archivos Modificados

#### `schemas/state.schema.json`

Agregar a cada fase en `phases`:

```json
{
  "agent": { "type": "string" },
  "command": { "type": "string" },
  "type": { "enum": ["interactive", "batch"] }
}
```

#### `src/fba/cli.py`

- `_init_factory_state()`: incluir `command` y `type` en cada fase
- Nuevo comando Click: `fba session query` que invoca `SessionManager`

#### `src/fba/__init__.py`

Agregar export de `SessionManager`.

### Tests Nuevos

`tests/test_session_manager.py`:
- `test_query_next_action_elicitation_pending` → `invoke_agent`
- `test_query_elicit_questions_ready` → `elicit_round`
- `test_query_elicit_output_done` → `transition`
- `test_query_batch_phase_pending` → `invoke_agent`
- `test_query_batch_phase_completed` → `transition`
- `test_query_gate_failure` → `ask_user`
- `test_query_user_choice_force` → `transition`
- `test_query_complete_phase` → `complete`
- `test_query_schema_validation`
- `test_session_manager_stateless`

---

## feat/6.1: Orquestador Ligero + Elicitacion JSON

### Archivos Nuevos

#### `schemas/elicit_questions.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "round": { "type": "integer", "minimum": 1 },
    "total_rounds": { "type": "integer" },
    "methodology": { "const": "BABOK" },
    "knowledge_area": { "type": "string" },
    "context": { "type": "string" },
    "questions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "header": { "type": "string", "maxLength": 30 },
          "question": { "type": "string" },
          "options": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "label": { "type": "string" },
                "description": { "type": "string" }
              },
              "required": ["label", "description"]
            }
          },
          "multiple": { "type": "boolean", "default": false }
        },
        "required": ["id", "header", "question", "options"]
      }
    }
  },
  "required": ["round", "methodology", "questions"]
}
```

#### `schemas/elicit_answers.schema.json`

Mapeo `id_pregunta → [respuestas]`.

#### `templates/.opencode/protocols/milestone-completion.md`

Protocolo extraido de orchestrator.md lineas 227-249.

### Archivos Modificados

#### `templates/.opencode/agents/orchestrator.md` (250 → ~80 lineas)

Estructura:

```markdown
---
mode: primary
model: inherit
permission:
  read: allow
  bash: allow
  glob: allow
  grep: allow
  task: allow
  question: allow
---

# Orquestador FBA

## Rol
Coordino el pipeline de generacion de modulos Odoo v18. Soy un coordinador
ligero: NO conozco el flujo de fases. Para cada decision, consulto al
Session Manager (`fba session query`). Para elicitacion, el elicitador
produce las preguntas y yo las presento al usuario.

## Herramientas

| Herramienta | Uso |
|---|---|
| `fba session query '<json>'` | Decidir siguiente accion en el pipeline |
| `fba transition <phase>` | Avanzar de fase (GateRunner incluido) |
| `fba transition --force <phase>` | Avanzar ignorando gates (solo si usuario autoriza) |
| `fba record <event> --data '<json>'` | Registrar evento en audit log |
| `fba gate <phase>` | Diagnosticar fallos de gate |
| `fba status` | Ver estado actual |
| `task(agent, command)` | Invocar sub-agente |
| `question(...)` | Interactuar con usuario |

## Ciclo Principal

1. Leer `.factory/state.json` → `current_phase`
2. `fba session query '{"query":"next_action", "current_phase":"<fase>"}'`
3. Ejecutar la accion indicada en la respuesta
4. `fba record <evento>` para auditar
5. Repetir hasta `current_phase == "complete"`

## Elicitacion Interactiva

Durante la fase `elicitation` (type: interactive):

1. El session manager indica `action: "invoke_agent"` con agent=`elicitador`
2. Invoco al elicitador via task. El produce `.factory/elicit_questions.json`
3. El session manager indica `action: "elicit_round"`
4. Leo `elicit_questions.json`, presento cada pregunta con `question()`
5. Guardo respuestas en `.factory/elicit_answers.json`
6. El session manager indica `action: "invoke_agent"` de nuevo
7. Invoco al elicitador con las respuestas. El decide: mas preguntas o final
8. Si finalizo, escribe `.factory/elicit_output.json`
9. Session manager indica `action: "transition"` → `documentation`

## Invocacion de Sub-agentes

```
task(
  description="<fase>: <agente>",
  prompt="Lee el comando en .opencode/commands/<command>.md y ejecuta.",
  subagent_type="general"
)
```

Siempre sesion fresca (NO pasar task_id).

## Manejo de Gate Failures

Si `fba gate` falla:
- `fba session query '{"query":"gate_failure",...}'`
- Session manager responde con `action: "ask_user"` + opciones
- Presento opciones al usuario con `question()`
- Usuario elige: reintentar / forzar / cancelar
- Si reintentar → invoco revisor_artefactos

## Protocolo de Cierre de Milestone

Al llegar a `complete`, ver protocols/milestone-completion.md.
```

#### `templates/.opencode/agents/elicitador.md` (184 → ~160 lineas)

Cambio principal: de guia pasiva a agente activo que:

1. Recibe el contexto del proyecto
2. Aplica metodologia BABOK
3. **Produce** `elicit_questions.json` con las preguntas estructuradas
4. Recibe `elicit_answers.json` con las respuestas
5. Itera (mas rondas de preguntas si es necesario)
6. **Produce** `elicit_output.json` con los datos completos para el PRD

Agregar al frontmatter: `write: allow`.

Secciones:
- "## Protocolo de Preguntas" — formato de `elicit_questions.json`
- "## Procesamiento de Respuestas" — como evaluar y decidir siguiente ronda
- "## Output Final" — formato de `elicit_output.json`

#### `templates/.opencode/commands/fba:elicit.md` (170 → ~100 lineas)

- Agente cambia de `orchestrator` a `elicitador`
- Instrucciones para producir `elicit_questions.json`
- Referencia a schemas de elicitacion

---

## feat/6.2: Instrucciones de Agentes Optimizadas

### Formato Estandarizado

```markdown
---
mode: subagent
model: inherit
permission: { read: allow, bash: allow, glob: allow, grep: allow, ... }
---

# <Agente>

## Rol
<2-3 lineas>

## Input
- <artefacto 1> en .factory/
- <artefacto 2> en .factory/

## Output
- <archivo> en .factory/

## Procedimiento
1. <Paso 1>
2. <Paso 2>
...

## Referencias
- knowledge/odoo/v18-conventions.md
- contracts/<artefacto>.contract.md
```

### Reduccion por Agente

| Agente | Actual | Meta | Que se extrae |
|---|---|---|---|
| code-generator | 490 | <180 | 356l guias Odoo v18 → `knowledge/odoo/*` (M6.3) |
| revisor_codigo | 446 | <180 | 176l checklist → bullets |
| planificador | 386 | <180 | 125l template SDD → referencia a schema |
| tester_qa | 346 | <180 | 143l templates test → `knowledge/testing/odoo-orm.md` |
| ci_cd_manager | 277 | <160 | 72l templates report → bullets |
| validador_semantico | 208 | <160 | 50l correction cycle → bullets |
| elicitador | 184 | <160 | BABOK → referencia a `knowledge/babok/` |
| revisor_artefactos | 174 | <150 | 110l procedimiento → bullets |
| documentador | 145 | <130 | 88l template PRD → referencia a schema |
| orquestador | ~80 | <80 | Ya esta |

### Reduccion de Comandos

| Comando | Actual | Meta |
|---|---|---|
| fba:construct.md | 212 | <120 |
| fba:gate.md | 186 | <120 |
| fba:elicit.md | 170 | <100 |
| fba:plan.md | 163 | <100 |
| fba:specify.md | 140 | <80 |
| fba:semantic-check.md | 134 | <80 |
| fba:ship.md | 85 | <60 |
| fba:tasks.md | 52 | <40 |
| fba:init.md | 46 | <30 |
| fba:review.md | 37 | <30 |
| fba:test.md | 33 | <30 |

---

## feat/6.3: Base de Conocimiento Compartida

### Estructura

```
templates/.opencode/knowledge/
├── odoo/
│   ├── v18-conventions.md       (~80 lineas)
│   ├── v18-models.md            (~100 lineas)
│   ├── v18-views.md             (~120 lineas)
│   └── v18-security.md          (~80 lineas)
├── babok/
│   ├── elicitation.md           (~60 lineas)
│   └── requirements.md          (~50 lineas)
├── testing/
│   └── odoo-orm.md              (~70 lineas)
└── security/
    └── patterns.md              (~40 lineas)
```

### Fuente del Contenido

| Knowledge File | Extraido de |
|---|---|
| odoo/v18-conventions.md | code-generator.md L184-481, revisor_codigo.md L83-112 |
| odoo/v18-models.md | code-generator.md L125-180, planificador.md |
| odoo/v18-views.md | code-generator.md L181-310 |
| odoo/v18-security.md | code-generator.md L311-345, revisor_codigo.md L131-145 |
| babok/elicitation.md | elicitador.md L17-91 |
| babok/requirements.md | documentador.md, elicitador.md |
| testing/odoo-orm.md | tester_qa.md L60-203 |
| security/patterns.md | revisor_codigo.md L36-212 |

### Cambio en CLI

- `cli.py`: `_copy_templates()` incluye `knowledge/`
- `fba update` copia/actualiza knowledge files

---

## feat/6.4: Separar Runtime vs Knowledge vs Contracts

### Nueva Estructura `.opencode/`

```
.opencode/
├── agents/           ← identidad pura (<50 lineas c/u)
├── knowledge/        ← metodologia, convenciones, patrones (M6.3)
├── contracts/        ← garantias entre artefactos (M6.5)
├── commands/         ← slash commands
└── protocols/        ← protocolos compartidos
```

### Formato de Agente Ligero (ejemplo: code-generator.md, ~40 lineas)

```markdown
---
mode: subagent
model: inherit
permission:
  read: allow
  bash: allow
  glob: allow
  grep: allow
  edit: allow
  write: allow
  task: allow
---

# Code Generator

## Rol
Genero codigo de modulo Odoo v18 desde `schema.json` (SSOT) en dos fases:
1. Schema Assembly: consolido tasks + SDD → `schema.json`
2. Code Rendering: genero `models/`, `views/`, `security/`, `data/`
   desde schema

## Regla de Oro
schema.json es la fuente unica de verdad. No interpreto, no invento, no
renombro. Renderizo exactamente lo que schema especifica.

## Referencias
Carga solo cuando necesites:
- knowledge/odoo/v18-models.md — patrones de modelos Python
- knowledge/odoo/v18-views.md — patrones de vistas XML
- knowledge/odoo/v18-security.md — patrones de seguridad (ACL, grupos)
- knowledge/odoo/v18-conventions.md — tags deprecados, atributos directos
- contracts/schema.contract.md — invariantes del SSOT
```

---

## feat/6.5: Artifact Contracts

### Archivos Nuevos

```
templates/.opencode/contracts/
├── prd.contract.md
├── sdd.contract.md
├── tasks.contract.md
└── schema.contract.md
```

### Formato Hibrido Markdown + YAML (ejemplo: prd.contract.md)

```markdown
---
contract:
  artifact: prd
  version: "1.0"
  owner: documentador
invariants:
  - field: functional_requirements[*].id
    pattern: "RF-\\d+"
    immutable_after: documentation
    description: "El ID humano (RF-01) no cambia despues de documentation"
  - field: functional_requirements[*].stable_id
    immutable_after: documentation
    description: "El UUID se genera una vez y nunca muta"
  - field: stakeholders[*].name
    immutable_after: documentation
    description: "Los stakeholders no se eliminan"
allowed_mutations:
  - from: elicitation
    to: documentation
    allowed:
      - "Agregar campos: description, acceptance_criteria"
      - "Expandir requisitos con detalles tecnicos"
      - "Agregar glossary entries"
    forbidden:
      - "Cambiar intencion funcional de un RF"
      - "Eliminar stakeholders"
      - "Modificar RF-NN id"
determinism:
  same_input: "Mismo elicit_output.json produce PRD estructuralmente identico"
  key_fields: ["functional_requirements", "stakeholders", "objectives"]
---

# PRD Contract

## Propietario
El **Documentador** (`documentador.md`) es el unico agente autorizado para
generar o modificar este artefacto.

## Invariantes
1. **IDs humanos**: Inmutables despues de `documentation`.
2. **stable_id (UUID)**: Generado en `elicitation`, nunca muta.
3. **Stakeholders**: No se eliminan en fases posteriores.

## Mutaciones Permitidas
- `elicitation → documentation`: Expandir requisitos con descripciones,
  criterios de aceptacion y glosario. NO cambiar intencion funcional.

## Verificacion
GateRunner verifica con regla `contract_check` en transicion
`documentation → planning`.
```

### Cambios en Codigo

#### `src/fba/gate.py`

- `_check_contract(rule)`: lee frontmatter YAML, verifica invariantes,
  ownership, allowed mutations
- Nuevo tipo de regla: `contract_check`

#### `schemas/state.schema.json`

- Agregar `"contract_check"` al enum de `gates.rules[].type`

#### `src/fba/cli.py`

- `fba init`: incluir contracts en `_init_factory_state()`
- Nuevo comando: `fba validate --contract <name>`
- `fba gate --verbose`: mostrar resultados de `contract_check`

---

## feat/6.6: Stable IDs

### Cambios en Schemas (6 archivos)

Agregar `stable_id` opcional (UUID v4) en TODAS las entidades:

| Schema | Entidades |
|---|---|
| prd.schema.json | RF, RNF, CA, stakeholders, glossary |
| sdd.schema.json | models, fields, views, security groups/ACLs/rules, traceability |
| task_index.schema.json | tasks |
| task_item.schema.json | components, fields |
| schema.schema.json | models, fields, views, security, data |

Definicion de `stable_id`:

```json
{
  "stable_id": {
    "type": "string",
    "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    "description": "UUID v4 — inmutable, generado una vez"
  }
}
```

### Cambios en Codigo

#### `src/fba/schema_manager.py`

Merge por UUID primero, fallback a nombre:

```python
def _merge_fields(self, fields):
    merged = {}
    for f in fields:
        key = f.get("stable_id") or f["name"]
        if key in merged:
            merged[key] = self._deep_merge(merged[key], f)
        else:
            merged[key] = f
```

#### `src/fba/module_registry.py`

Nueva clase `EntityRegistry`:

```python
class EntityRegistry:
    def __init__(self, project_dir: Path): ...
    def register(self, stable_id: str, metadata: dict): ...
    def lookup(self, stable_id: str) -> dict | None: ...
    def is_registered(self, stable_id: str) -> bool: ...
    def verify_integrity(self, artifact_entities: list) -> list[str]: ...
```

#### `src/fba/gate.py`

- `_check_stable_ids(rule)`: verifica stable_ids contra `entity_registry.json`
- Nuevo tipo de regla: `stable_id_integrity`

#### `schemas/state.schema.json`

- Agregar `"stable_id_integrity"` al enum de `gates.rules[].type`

### Archivo Nuevo

`templates/.factory/entity_registry.json` — mapea stable_id → metadata de entidad.

---

## Resumen de Archivos

### Archivos Nuevos (20)

| Archivo | Feat |
|---|---|
| `src/fba/session_manager.py` | 6.0 |
| `schemas/session_query.schema.json` | 6.0 |
| `schemas/session_response.schema.json` | 6.0 |
| `schemas/elicit_questions.schema.json` | 6.1 |
| `schemas/elicit_answers.schema.json` | 6.1 |
| `templates/.opencode/protocols/milestone-completion.md` | 6.1 |
| `templates/.opencode/knowledge/odoo/v18-conventions.md` | 6.3 |
| `templates/.opencode/knowledge/odoo/v18-models.md` | 6.3 |
| `templates/.opencode/knowledge/odoo/v18-views.md` | 6.3 |
| `templates/.opencode/knowledge/odoo/v18-security.md` | 6.3 |
| `templates/.opencode/knowledge/babok/elicitation.md` | 6.3 |
| `templates/.opencode/knowledge/babok/requirements.md` | 6.3 |
| `templates/.opencode/knowledge/testing/odoo-orm.md` | 6.3 |
| `templates/.opencode/knowledge/security/patterns.md` | 6.3 |
| `templates/.opencode/contracts/prd.contract.md` | 6.5 |
| `templates/.opencode/contracts/sdd.contract.md` | 6.5 |
| `templates/.opencode/contracts/tasks.contract.md` | 6.5 |
| `templates/.opencode/contracts/schema.contract.md` | 6.5 |
| `templates/.factory/entity_registry.json` | 6.6 |
| `tests/test_session_manager.py` | 6.0 |

### Archivos Modificados (26)

| Archivo | Feats |
|---|---|
| `src/fba/cli.py` | 6.0, 6.3, 6.4, 6.5, 6.6 |
| `src/fba/__init__.py` | 6.0 |
| `src/fba/gate.py` | 6.5, 6.6 |
| `src/fba/state.py` | 6.5, 6.6 |
| `src/fba/schema_manager.py` | 6.6 |
| `src/fba/module_registry.py` | 6.6 |
| `schemas/state.schema.json` | 6.0, 6.5, 6.6 |
| `schemas/schema.schema.json` | 6.6 |
| `schemas/prd.schema.json` | 6.6 |
| `schemas/sdd.schema.json` | 6.6 |
| `schemas/task_index.schema.json` | 6.6 |
| `schemas/task_item.schema.json` | 6.6 |
| `templates/.opencode/agents/orchestrator.md` | 6.1, 6.2, 6.4 |
| `templates/.opencode/agents/elicitador.md` | 6.1, 6.2, 6.4 |
| `templates/.opencode/agents/documentador.md` | 6.2, 6.4 |
| `templates/.opencode/agents/planificador.md` | 6.2, 6.4 |
| `templates/.opencode/agents/code-generator.md` | 6.2, 6.4 |
| `templates/.opencode/agents/tester_qa.md` | 6.2, 6.4 |
| `templates/.opencode/agents/revisor_codigo.md` | 6.2, 6.4 |
| `templates/.opencode/agents/revisor_artefactos.md` | 6.2, 6.4 |
| `templates/.opencode/agents/validador_semantico.md` | 6.2, 6.4 |
| `templates/.opencode/agents/ci_cd_manager.md` | 6.2, 6.4 |
| `templates/.opencode/commands/fba:elicit.md` | 6.1, 6.2 |
| `templates/.opencode/commands/fba:construct.md` | 6.2 |
| `templates/.opencode/commands/fba:gate.md` | 6.2, 6.5 |
| `tests/test_agent_definitions.py` | 6.2, 6.4 |

### Riesgos

| Riesgo | Severidad | Mitigacion |
|---|---|---|
| `test_agent_definitions.py` se rompe en M6.2+M6.4 | Alta | Reescribir incrementalmente en cada feat |
| Backward compat de stable IDs | Media | `stable_id` opcional, merge con fallback a nombre |
| OpenCode no soporta `question` en sub-agentes | Descartado | Camino B: orquestador siempre tiene `question` |
| Referencias circulares en knowledge | Baja | Cada knowledge file es autocontenido |

---

## Orden de Ejecucion

```
milestone/6.0-optimizar-agentes
  ├── feat/initm6              ← ESTE PLAN
  ├── feat/6.0-session-manager
  ├── feat/6.1-orquestador-ligero
  ├── feat/6.2-instrucciones-agentes
  ├── feat/6.3-convenciones-compartidas
  ├── feat/6.4-identidad-vs-instrucciones
  ├── feat/6.5-artifact-contracts
  └── feat/6.6-stable-ids
```

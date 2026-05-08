# Testing - M1: Elicitacion BABOK + Documentacion

## Requisitos Previos

- Python 3.11 o superior
- pip actualizado
- El repositorio clonado y en el directorio raiz
- `fba` instalado: `pip install -e ".[dev]"`

## Pasos para Probar

### 1. Inicializar proyecto de prueba

**Objetivo**: Verificar que `fba init` crea la estructura con schemas.

**Comando**:
```bash
mkdir -p /tmp/test-m1 && fba init -d /tmp/test-m1
```

**Resultado esperado**:
```
Initializing Factory Build Agent in /tmp/test-m1...
✅ Factory Build Agent initialized in /tmp/test-m1

Next steps:
  1. Open the project with OpenCode: opencode .
  2. Start eliciting requirements: /fba:elicit "your idea"
```

Verificar que los schemas se copiaron:
```bash
ls /tmp/test-m1/.factory/schemas/
```
Debe mostrar `prd.schema.json` y `state.schema.json`.

### 2. Verificar estado inicial

**Objetivo**: Confirmar que el proyecto comienza en fase `init`.

**Comando**:
```bash
fba status -d /tmp/test-m1
```

**Resultado esperado**:
```
Project: test-m1
Version: 0.1.0
Methodology: BABOK
Current phase: init

Phases:
  🔄 init: in_progress
  ⬜ elicitation: pending
  ⬜ documentation: pending
  ...
```

### 3. Transicionar manualmente a elicitacion

**Objetivo**: Probar `fba transition` con una transicion valida.

**Comando**:
```bash
fba transition elicitation -d /tmp/test-m1
```

**Resultado esperado**:
```
Transitioned from 'elicitation' to 'elicitation'
```

Nota: El mensaje muestra el nuevo current_phase que es `elicitation`.

Verificar el cambio:
```bash
python -c "
import json
with open('/tmp/test-m1/.factory/state.json') as f:
    state = json.load(f)
assert state['current_phase'] == 'elicitation'
assert state['phases']['init']['status'] == 'complete'
assert state['phases']['elicitation']['status'] == 'in_progress'
print('✅ Transicion correcta')
"
```

### 4. Probar transicion invalida

**Objetivo**: Confirmar que el sistema rechaza transiciones no permitidas.

**Comando**:
```bash
fba transition construction -d /tmp/test-m1
```

**Resultado esperado** (exit code 1):
```
Error: Invalid transition: 'elicitation' -> 'construction'. Allowed: documentation
```

### 5. Registrar eventos manualmente

**Objetivo**: Verificar `fba record` y que los eventos se persisten.

**Comando**:
```bash
fba record test_event --data '{"key":"value"}' -d /tmp/test-m1
```

**Resultado esperado**:
```
Event 'test_event' recorded.
```

Verificar:
```bash
python -c "
import json
with open('/tmp/test-m1/.factory/events.jsonl') as f:
    events = [json.loads(l) for l in f if l.strip()]
assert len(events) >= 2
assert events[-1]['type'] == 'test_event'
assert events[-1]['data']['key'] == 'value'
print('✅ Evento registrado correctamente')
"
```

### 6. Simular elicitacion: crear contexto

**Objetivo**: Crear un archivo de elicitacion de ejemplo para probar validacion.

**Comando**:
```bash
mkdir -p /tmp/test-m1/.factory/context
cat > /tmp/test-m1/.factory/context/elicitation.json << 'JSON'
{
  "initial_description": "Modulo de registro de vehiculos para Odoo v18",
  "business_context": "Una empresa de flota necesita gestionar vehiculos con sus datos basicos",
  "stakeholders": [
    {"name": "Gerente de Flota", "role": "Usuario", "interest": "Registro rapido"},
    {"name": "Desarrollador", "role": "Implementador", "interest": "Codigo mantenible"}
  ],
  "objectives": ["Reducir tiempo de registro", "Busqueda por placa y marca"],
  "functional_requirements": [
    {"id": "RF-01", "description": "CRUD de vehiculos con campos marca, modelo, ano, placa", "priority": "high"},
    {"id": "RF-02", "description": "Validar unicidad de placa al crear o editar", "priority": "high"}
  ],
  "non_functional_requirements": [
    {"id": "RNF-01", "description": "Busqueda debe responder en menos de 2 segundos", "category": "performance", "priority": "high"}
  ],
  "constraints": ["Odoo v18 Community Edition", "No modulos de pago"],
  "dependencies": ["base", "contacts"],
  "acceptance_criteria": [
    {"id": "CA-01", "criterion": "Usuario puede crear un vehiculo con todos los campos requeridos", "related_requirements": ["RF-01"]}
  ],
  "glossary": [
    {"term": "Placa", "definition": "Identificador alfanumerico unico del vehiculo"}
  ]
}
JSON
echo "✅ Contexto de elicitacion creado"
```

### 7. Simular generacion de PRD

**Objetivo**: Crear un PRD de ejemplo y validarlo contra el schema.

Crear PRD valido:
```bash
cat > /tmp/test-m1/.factory/prd.json << 'JSON'
{
  "vision": "Modulo de registro de vehiculos que permite gestionar la flota vehicular con busqueda avanzada por placa, marca y modelo en Odoo v18.",
  "stakeholders": [
    {"name": "Gerente de Flota", "role": "Usuario final", "interest": "Registro rapido y busqueda"},
    {"name": "Desarrollador Odoo", "role": "Implementador", "interest": "Codigo mantenible y documentado"}
  ],
  "objectives": ["Reducir tiempo de registro de vehiculos de 10 a 2 minutos", "Permitir busqueda por placa, marca y modelo"],
  "functional_requirements": [
    {"id": "RF-01", "description": "El sistema debe permitir crear, leer, actualizar y eliminar vehiculos con campos: marca, modelo, ano, placa", "priority": "high", "acceptance_criteria": ["Usuario puede crear un vehiculo con campos obligatorios", "Usuario puede buscar vehiculos por placa"]},
    {"id": "RF-02", "description": "El sistema debe validar que la placa sea unica al crear o modificar un vehiculo", "priority": "high"}
  ],
  "non_functional_requirements": [
    {"id": "RNF-01", "description": "La busqueda de vehiculos debe devolver resultados en menos de 2 segundos para hasta 10000 registros", "category": "performance", "priority": "high"},
    {"id": "RNF-02", "description": "Solo usuarios con permisos del grupo Flota pueden modificar vehiculos", "category": "security", "priority": "high"}
  ],
  "acceptance_criteria": [
    {"id": "CA-01", "criterion": "Un usuario con permisos puede registrar un nuevo vehiculo en menos de 1 minuto completando todos los campos", "related_requirements": ["RF-01"]},
    {"id": "CA-02", "criterion": "El sistema rechaza placas duplicadas con un mensaje de error claro en espanol", "related_requirements": ["RF-02"]}
  ],
  "constraints": ["Compatible con Odoo v18 Community Edition", "La base de datos de produccion no debe ser modificada sin migracion"],
  "dependencies": ["Modulo base de Odoo (base)", "Modulo de contactos (contacts) para propietarios"],
  "glossary": [
    {"term": "Placa", "definition": "Identificador alfanumerico unico asignado a cada vehiculo"},
    {"term": "CRUD", "definition": "Create, Read, Update, Delete - operaciones basicas de persistencia de datos"}
  ]
}
JSON
echo "✅ PRD de ejemplo creado"
```

### 8. Validar PRD contra schema

**Objetivo**: Probar `fba validate prd`.

**Comando**:
```bash
fba validate prd -d /tmp/test-m1
```

**Resultado esperado**:
```
✅ prd: valid
```

### 9. Validar PRD invalido

**Objetivo**: Confirmar que el validador rechaza PRDs que no cumplen el schema.

**Comando**:
```bash
echo '{"vision":"Too short"}' > /tmp/test-m1/.factory/prd.json
fba validate prd -d /tmp/test-m1
```

**Resultado esperado** (exit code 1):
```
❌ prd: validation failed - ...
```

### 10. Ejecutar suite de tests del framework

**Objetivo**: Verificar que todos los tests del framework pasan.

**Comando**:
```bash
cd /home/cafl/projects/factory-build-agent
.venv/bin/python -m pytest -v
```

**Resultado esperado**: 94+ tests PASSED.

### 11. Verificar agentes instalados

**Objetivo**: Confirmar que los YAML de agentes estan en el proyecto.

**Comando**:
```bash
ls /tmp/test-m1/.opencode/agents/
```

**Resultado esperado**:
```
documentador.md  elicitador.md  orchestrator.md
```

### 12. Verificar slash commands instalados

**Objetivo**: Confirmar que los comandos slash existen.

**Comando**:
```bash
ls /tmp/test-m1/.opencode/commands/
```

**Resultado esperado**:
```
fba:construct.md  fba:elicit.md  fba:init.md  fba:plan.md  fba:review.md
fba:ship.md  fba:specify.md  fba:tasks.md  fba:test.md
```

## Limpiar

```bash
rm -rf /tmp/test-m1
```

## Troubleshooting

### `fba: command not found`

Asegurate de que el entorno virtual esta activado y el paquete instalado:
```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

### `No schemas found for validation`

Verifica que `fba init` se ejecuto correctamente y que `.factory/schemas/` existe:
```bash
ls -la /tmp/test-m1/.factory/schemas/
```
Si no existe, reinstala el paquete en modo editable.

### Validation error con `additionalProperties`

El schema PRD usa `additionalProperties: false`. Asegurate de que el PRD JSON no tiene campos extras.
Todos los campos opcionales deben omitirse (no ponerse como null o vacio).

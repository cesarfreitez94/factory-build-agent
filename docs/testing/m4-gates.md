# Testing - M4: Sistema de Gates con Agente Revisor de Artefactos

## Requisitos Previos

- Python 3.11 o superior
- pip actualizado
- El repositorio clonado y en el directorio raiz
- `fba` instalado: `pip install -e ".[dev]"`

## Pasos para Probar

### 1. Inicializar proyecto de prueba

**Objetivo**: Verificar que `fba init` genera gates en el estado inicial.

**Comando**:
```bash
mkdir -p /tmp/test-m4 && fba init -d /tmp/test-m4
```

**Resultado esperado**:
```
Initializing Factory Build Agent in /tmp/test-m4...
✅ Factory Build Agent initialized in /tmp/test-m4
```

Verificar que los gates existen en el estado:
```bash
python3 -c "
import json
state = json.load(open('/tmp/test-m4/.factory/state.json'))
print('Gates defined:', list(state['gates'].keys()))
for phase, gate in state['gates'].items():
    print(f'  {phase}: {len(gate[\"rules\"])} rules, owner={gate[\"owner_agent\"]}')
"
```

Debe mostrar:
```
Gates defined: ['elicitation', 'documentation', 'planning']
  elicitation: 2 rules, owner=elicitador
  documentation: 3 rules, owner=documentador
  planning: 4 rules, owner=planificador
```

### 2. Verificar que `fba gate` diagnostica fase actual

**Objetivo**: Confirmar que el comando gate reporta el estado de la fase actual.

**Comando**:
```bash
fba gate -d /tmp/test-m4
```

**Resultado esperado**:
```
✅ Gate: init
   No gates defined for phase 'init'
```

La fase `init` no tiene gates, asi que pasa. Nota: algunas plataformas pueden no mostrar emojis UTF-8.

### 3. Simular elicitacion y verificar gate bloquea transicion

**Objetivo**: El gate `elicitation` debe bloquear la transicion `elicitation → documentation` si no hay contexto de elicitacion.

**Comandos**:
```bash
# Transicion init → elicitation (sin gate)
fba transition elicitation -d /tmp/test-m4

# Intentar transicion elicitation → documentation (debe fallar)
fba transition documentation -d /tmp/test-m4
```

**Resultado esperado del segundo comando**:
```
❌ Gate 'elicitation' failed:
   - Artifact not found: .factory/context/elicitation.json
   - Artifact for content check not found: .factory/context/elicitation.json

Use 'fba gate' to diagnose or '--force' to skip validation.
```

### 4. Diagnostico con `fba gate`

**Objetivo**: El comando gate diagnostica cuales reglas fallan.

**Comando**:
```bash
fba gate -d /tmp/test-m4
```

**Resultado esperado**:
```
❌ Gate: elicitation
   Validates that BABOK elicitation produced complete requirements
   ❌ elicitation_context_exists: Artifact not found: .factory/context/elicitation.json
   ❌ elicitation_content_minimum: Artifact for content check not found: .factory/context/elicitation.json
   Owner agent: elicitador
   2 failure(s)
```

### 5. Crear contexto y verificar gate pasa

**Objetivo**: Al crear el contexto de elicitacion, el gate debe pasar.

**Comandos**:
```bash
mkdir -p /tmp/test-m4/.factory/context
cat > /tmp/test-m4/.factory/context/elicitation.json << 'EOF'
{
  "initial_description": "Modulo de prueba",
  "stakeholders": [{"name": "Usuario", "role": "Operador", "interest": "Gestion"}],
  "functional_requirements": [{"id": "RF-01", "description": "CRUD basico", "priority": "high"}],
  "non_functional_requirements": [{"id": "RNF-01", "description": "Performance", "category": "performance", "priority": "medium"}],
  "acceptance_criteria": [{"id": "CA-01", "criterion": "Crear registro en < 1 min", "related_requirements": ["RF-01"]}]
}
EOF

fba gate -d /tmp/test-m4
```

**Resultado esperado**:
```
✅ Gate: elicitation
   Validates that BABOK elicitation produced complete requirements
   ✅ elicitation_context_exists: Artifact exists: .factory/context/elicitation.json
   ✅ elicitation_content_minimum: All content checks passed
```

### 6. Transicion con `--force`

**Objetivo**: `--force` permite saltar el gate.

**Comandos**:
```bash
# Con contexto borrado:
rm -f /tmp/test-m4/.factory/context/elicitation.json

# Forzar transicion:
fba transition documentation -d /tmp/test-m4 --force
```

**Resultado esperado**:
```
Transitioned to 'documentation'
⚠️  Gate validation was skipped (--force)
```

### 7. Verificar gate de documentacion

**Objetivo**: El gate `documentation` valida PRD.

**Comandos**:
```bash
fba gate documentation -d /tmp/test-m4
```

**Resultado esperado**:
```
❌ Gate: documentation
   Validates that PRD is complete and schema-valid
   ❌ prd_json_exists: Artifact not found: .factory/prd.json
   ...
```

### 8. Verificar `fba gate --all`

**Objetivo**: El flag `--all` muestra todos los gates definidos.

**Comando**:
```bash
fba gate --all -d /tmp/test-m4
```

**Resultado esperado**: Muestra gates de `elicitation`, `documentation`, y `planning` con sus estados.

### 9. Verificar agente Revisor de Artefactos

**Objetivo**: El agente existe en las plantillas.

**Comando**:
```bash
ls /tmp/test-m4/.opencode/agents/revisor_artefactos.md
```

**Resultado esperado**: El archivo existe.

### 10. Verificar slash command `/fba:gate`

**Objetivo**: El comando slash existe en las plantillas.

**Comando**:
```bash
head -5 /tmp/test-m4/.opencode/commands/fba:gate.md
```

**Resultado esperado**:
```
---
description: Run gate validation and diagnostics for project artifacts
agent: revisor_artefactos
---
```

### 11. Limits

**Objetivo**: Limpiar.

**Comando**:
```bash
rm -rf /tmp/test-m4
```

## Troubleshooting

### `fba transition` falla con GateError pero los artefactos existen

Verificar que los artefactos estan en la ruta correcta relativa al directorio del proyecto.
Todos los paths en `state.json["gates"]` son relativos al directorio raiz del proyecto.

Ejemplo: `.factory/prd.json` → debe existir en `<project-dir>/.factory/prd.json`.

### `fba gate` muestra "No gates defined for phase"

Es normal si la fase no tiene gates definidos en `state.json["gates"]`.
Solo `elicitation`, `documentation`, y `planning` tienen gates por defecto.

### El agente Revisor de Artefactos no aparece en OpenCode

Ejecutar `fba update` en el proyecto para copiar las plantillas mas recientes:
```bash
fba update -d <project-dir>
```

### Tests fallan en test_gate.py

Verificar que `jsonschema` esta instalado:
```bash
pip install jsonschema
```

# Testing - M3.0a: Task System Redesign (Archivos por Task)

## Requisitos Previos

- Python 3.11 o superior
- pip actualizado
- El repositorio clonado y en el directorio raiz
- `fba` instalado: `pip install -e ".[dev]"`

## Pasos para Probar

### 1. Verificar que `fba init` incluye el gate `tasks`

**Objetivo**: Confirmar que el estado inicial contiene el nuevo gate `tasks` con 4 reglas.

**Comando**:
```bash
mkdir -p /tmp/test-m3a && fba init -d /tmp/test-m3a
python3 -c "
import json
state = json.load(open('/tmp/test-m3a/.factory/state.json'))
gate = state['gates']['tasks']
print(f'Owner: {gate[\"owner_agent\"]}')
print(f'Rules: {len(gate[\"rules\"])}')
for r in gate['rules']:
    print(f'  - {r[\"type\"]}: {r[\"rule_name\"]}')
"
```

**Resultado esperado**:
```
Owner: planificador
Rules: 4
  - artifact_exists: task_index_exists
  - schema: task_index_schema_valid
  - content_check: task_index_content_minimum
  - task_files_exist: all_task_files_exist
```

---

### 2. Validar schemas de tasks

**Objetivo**: Probar que los schemas `task_index.schema.json` y `task_item.schema.json` son validos y detectan errores.

**Comando**:
```bash
python3 -c "
import json, jsonschema
from pathlib import Path

schemas_dir = Path('schemas')

# Valid index
index_schema = json.loads((schemas_dir / 'task_index.schema.json').read_text())
valid_index = {
    'module_name': 'test_module',
    'total_tasks': 1,
    'tasks': [{
        'id': 'T001', 'name': 'Test', 'file': 'T001-test.json',
        'dependencies': [], 'order': 1, 'estimated_effort': 'low',
        'sdd_components': ['models.test']
    }]
}
jsonschema.validate(valid_index, index_schema)
print('✅ Valid index passes')

# Invalid index: bad ID pattern
try:
    invalid = json.loads(json.dumps(valid_index))
    invalid['tasks'][0]['id'] = '1'
    jsonschema.validate(invalid, index_schema)
    print('❌ Should have failed')
except jsonschema.ValidationError:
    print('✅ Invalid ID pattern caught')

# Valid task item
item_schema = json.loads((schemas_dir / 'task_item.schema.json').read_text())
valid_item = {
    'id': 'T001', 'name': 'Test', 'description': 'Generate test code.',
    'components': [{
        'type': 'model', 'name': 'test.model',
        'description': 'Test model', 'sdd_reference': 'models.test'
    }],
    'files_to_generate': ['models/test.py'],
    'dependencies': []
}
jsonschema.validate(valid_item, item_schema)
print('✅ Valid item passes')
"
```

**Resultado esperado**:
```
✅ Valid index passes
✅ Invalid ID pattern caught
✅ Valid item passes
```

---

### 3. Probar el gate `tasks` con archivos validos

**Objetivo**: Verificar que el gate `tasks` pasa cuando todos los archivos existen.

**Comando**:
```bash
# Crear archivos de task validos
mkdir -p /tmp/test-m3a/.factory/tasks

cat > /tmp/test-m3a/.factory/tasks/index.json << 'EOF'
{
  "module_name": "test",
  "total_tasks": 2,
  "tasks": [
    {
      "id": "T001", "name": "Modelos", "file": "T001-modelos.json",
      "dependencies": [], "order": 1, "estimated_effort": "high",
      "sdd_components": ["models.test"]
    },
    {
      "id": "T002", "name": "Vistas", "file": "T002-vistas.json",
      "dependencies": ["T001"], "order": 2, "estimated_effort": "medium",
      "sdd_components": ["views.form"]
    }
  ]
}
EOF

cat > /tmp/test-m3a/.factory/tasks/T001-modelos.json << 'EOF'
{
  "id": "T001", "name": "Modelos",
  "description": "Generar modelos Odoo para modulo de prueba.",
  "components": [{
    "type": "model", "name": "test.model",
    "description": "Modelo de prueba", "sdd_reference": "models.test"
  }],
  "files_to_generate": ["models/__init__.py", "models/test_model.py"],
  "dependencies": []
}
EOF

cat > /tmp/test-m3a/.factory/tasks/T002-vistas.json << 'EOF'
{
  "id": "T002", "name": "Vistas",
  "description": "Generar vistas XML para modulo de prueba.",
  "components": [{
    "type": "view", "name": "test.form",
    "description": "Formulario de prueba", "view_type": "form",
    "model": "test.model", "view_fields": ["name"],
    "sdd_reference": "views.form"
  }],
  "files_to_generate": ["views/test_views.xml"],
  "dependencies": ["T001"]
}
EOF

# Actualizar state.json al phase tasks
python3 -c "
import json
state = json.load(open('/tmp/test-m3a/.factory/state.json'))
state['current_phase'] = 'tasks'
state['phases']['tasks']['status'] = 'in_progress'
json.dump(state, open('/tmp/test-m3a/.factory/state.json', 'w'), indent=2)
"

# Ejecutar gate
fba gate tasks -d /tmp/test-m3a
```

**Resultado esperado**:
```
✅ Gate: tasks
   Validates task index and individual task files
   ✅ task_index_exists: Artifact exists: .factory/tasks/index.json
   ✅ task_index_schema_valid: Schema validation passed: .factory/tasks/index.json
   ✅ task_index_content_minimum: All content checks passed
   ✅ all_task_files_exist: All 2 task files exist and are valid
```

---

### 4. Probar que el gate bloquea sin archivos

**Objetivo**: Confirmar que `fba transition construction` falla sin los archivos de tasks.

**Comando**:
```bash
# En un proyecto sin tasks
mkdir -p /tmp/test-m3a-block && fba init -d /tmp/test-m3a-block

python3 -c "
import json
state = json.load(open('/tmp/test-m3a-block/.factory/state.json'))
state['current_phase'] = 'tasks'
state['phases']['tasks']['status'] = 'in_progress'
json.dump(state, open('/tmp/test-m3a-block/.factory/state.json', 'w'), indent=2)
"

fba transition construction -d /tmp/test-m3a-block
echo "Exit code: $?"
```

**Resultado esperado**:
```
❌ Gate 'tasks' failed:
   - Artifact not found: .factory/tasks/index.json
Exit code: 1
```

---

### 5. Probar transicion exitosa con tasks validos

**Objetivo**: Confirmar que la transicion `tasks → construction` funciona cuando los archivos son validos.

**Comando**:
```bash
fba transition construction -d /tmp/test-m3a
cat /tmp/test-m3a/.factory/state.json | python3 -c "import json,sys; s=json.load(sys.stdin); print(f'Current: {s[\"current_phase\"]}'); print(f'Tasks status: {s[\"phases\"][\"tasks\"][\"status\"]}'); print(f'Construction status: {s[\"phases\"][\"construction\"][\"status\"]}')"
```

**Resultado esperado**:
```
Transitioned to 'construction'
Current: construction
Tasks status: complete
Construction status: in_progress
```

---

### 6. Verificar fba:construct.md tiene contenido iterativo

**Objetivo**: Confirmar que el comando build referencia el nuevo flujo.

**Comando**:
```bash
grep -E "index.json|Iterative|fresh|git commit" templates/.opencode/commands/fba:construct.md
```

**Resultado esperado**:
```
- `.factory/tasks/index.json` exists with a valid task index.
### 3. Iterative Task Execution
   Do NOT pass `task_id` — each task must be a fresh session.
   git add <module_name>/ && git commit -m "feat(#XX): task <id> <name>"
## Iterative Protocol Rules
```

---

### 7. Verificar fba:tasks.md genera archivos separados

**Objetivo**: Confirmar que el comando tasks referencia index.json y T*.json.

**Comando**:
```bash
grep -E "index.json|T\*\.json|task_index.schema|task_item.schema" templates/.opencode/commands/fba:tasks.md
```

**Resultado esperado**:
```
3. Generate `.factory/tasks/index.json` with:
4. For each task in the index, generate `.factory/tasks/<file>` as a structured JSON file conforming to `task_item.schema.json`:
- `.factory/tasks/index.json` exists and is valid against `task_index.schema.json`.
- All individual `T*.json` task files exist and are valid against `task_item.schema.json`.
```

---

## Troubleshooting

### `jsonschema.exceptions.ValidationError` en el gate tasks

Si el gate `tasks` falla con errores de schema, verifica que:
- `task_index.schema.json` y `task_item.schema.json` existen en `.factory/schemas/`
- `fba init` se ejecuto con la version actualizada del framework

### `Artifact not found` para un archivo T*.json

El gate valida que TODOS los archivos listados en `index.json` (`tasks[].file`) existen en `.factory/tasks/`. Revisa que no haya errores de tipeo en los nombres de archivo.

### Archivos T*.json vacios o JSON invalido

El gate `task_files_exist` valida que cada archivo de task:
1. Existe
2. No esta vacio
3. Es JSON valido
4. Pasa la validacion del schema `task_item.schema.json`

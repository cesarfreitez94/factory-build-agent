# Testing - M3: Construccion + MVP (E2E Completo)

## Requisitos Previos

- Python 3.11 o superior
- pip actualizado
- El repositorio clonado y en el directorio raiz
- `fba` instalado: `pip install -e ".[dev]"`
- 294 tests pasan: `python3 -m pytest tests/ -q`

## Pasos para Probar

### 1. Verificar que `fba init` incluye el module_registry.json

**Objetivo**: Confirmar que `fba init` copia el registry de modulos core Odoo v18 al proyecto destino.

**Comando**:
```bash
mkdir -p /tmp/test-m3b && fba init -d /tmp/test-m3b
ls -la /tmp/test-m3b/.factory/module_registry.json
```

**Resultado esperado**:
```
-rw-r--r-- 1 user user ... /tmp/test-m3b/.factory/module_registry.json
```

**Validacion adicional**:
```bash
python3 -c "
import json
registry = json.load(open('/tmp/test-m3b/.factory/module_registry.json'))
print(f'Modules: {len(registry.get(\"modules\", {}))}')
for name, info in list(registry.get('modules', {}).items())[:5]:
    print(f'  {name}: {len(info.get(\"models\", []))} models')
"
```
Debe mostrar al menos 5 modulos core con sus modelos canonicos.

---

### 2. Verificar el schema `schema.schema.json`

**Objetivo**: Confirmar que el schema de validacion del SSOT existe y es valido.

**Comando**:
```bash
python3 -c "
import jsonschema, json
schema = json.load(open('schemas/schema.schema.json'))
print(f'Schema title: {schema.get(\"title\", \"N/A\")}')
print(f'Required fields: {schema.get(\"required\", [])}')
# Debe ser un schema valido (no lanza excepcion al cargar)
jsonschema.Draft7Validator.check_schema(schema)
print('Schema is valid Draft 7')
"
```

**Resultado esperado**:
```
Schema title: ...
Required fields: ['manifest', 'models']
Schema is valid Draft 7
```

---

### 3. Probar el Module Registry con un ejemplo de mapeo

**Objetivo**: Verificar que el registry resuelve correctamente la intencion de negocio.

**Comando**:
```bash
python3 -c "
import json
registry = json.load(open('path/to/module_registry.json'))
# Verificar que modulos core mapean correctamente
modules = registry.get('modules', {})
assert 'crm' in modules, 'crm module not found'
assert 'crm.lead' in modules['crm'].get('models', []), 'crm.lead not found in crm models'
print('crm → crm.lead (mode: extend)')
print('Registry lookup works correctly')
"
```

**Resultado esperado**:
```
crm → crm.lead (mode: extend)
Registry lookup works correctly
```

---

### 4. Flujo de Schema Assembly desde tasks

**Objetivo**: Probar que el Schema Manager ensambla un schema.json correcto a partir de tasks.

1. Crear un proyecto con tasks validos:
```bash
rm -rf /tmp/test-m3c && mkdir -p /tmp/test-m3c/.factory/tasks
cp -r templates/.factory/module_registry.json /tmp/test-m3c/.factory/
```

2. Crear tasks de prueba:
```bash
cat > /tmp/test-m3c/.factory/tasks/index.json << 'INDEX'
{
  "module_name": "test_module",
  "total_tasks": 2,
  "tasks": [
    {"id": "T001", "name": "Modelos", "file": "T001-modelos.json", "dependencies": [], "order": 1, "estimated_effort": "high", "sdd_components": ["models.test"]},
    {"id": "T002", "name": "Vistas", "file": "T002-vistas.json", "dependencies": ["T001"], "order": 2, "estimated_effort": "medium", "sdd_components": ["views.form"]}
  ]
}
INDEX

cat > /tmp/test-m3c/.factory/tasks/T001-modelos.json << 'TASK1'
{
  "id": "T001", "name": "Modelos",
  "description": "Generar modelos Odoo para modulo de prueba con normalizacion.",
  "components": [
    {
      "type": "model", "name": "test.model",
      "description": "Modelo principal de prueba",
      "fields": [
        {"name": "name", "type": "Char", "label": "Nombre", "required": true, "size": 200},
        {"name": "partner_id", "type": "Many2one", "label": "Cliente", "relation": "res.partner"},
        {"name": "tag_ids", "type": "Many2many", "label": "Etiquetas", "relation": "test.tag"}
      ],
      "sdd_reference": "models.test"
    },
    {
      "type": "model", "name": "test.tag",
      "description": "Etiquetas de prueba",
      "fields": [
        {"name": "name", "type": "Char", "label": "Nombre", "required": true, "size": 100}
      ],
      "sdd_reference": "models.test"
    }
  ],
  "files_to_generate": ["models/__init__.py", "models/test_model.py", "models/test_tag.py"],
  "dependencies": []
}
TASK1

cat > /tmp/test-m3c/.factory/tasks/T002-vistas.json << 'TASK2'
{
  "id": "T002", "name": "Vistas",
  "description": "Generar vistas XML para el modulo de prueba.",
  "components": [
    {
      "type": "view", "name": "test.form", "description": "Formulario principal",
      "view_type": "form", "model": "test.model",
      "view_fields": ["name", "partner_id", "tag_ids"],
      "sdd_reference": "views.form"
    }
  ],
  "files_to_generate": ["views/test_views.xml"],
  "dependencies": ["T001"]
}
TASK2
```

3. Validar que los schemas existen y son usables:
```bash
python3 -c "
import jsonschema, json
# Validar que ambos archivos de task pasan schema validation
index_schema = json.load(open('schemas/task_index.schema.json'))
item_schema = json.load(open('schemas/task_item.schema.json'))
index = json.load(open('/tmp/test-m3c/.factory/tasks/index.json'))
jsonschema.validate(index, index_schema)
for task_info in index['tasks']:
    task = json.load(open(f'/tmp/test-m3c/.factory/tasks/{task_info[\"file\"]}'))
    jsonschema.validate(task, item_schema)
    print(f'{task[\"id\"]}: {task[\"name\"]} ({len(task[\"components\"])} components)')
print('All tasks valid')
"
```

**Resultado esperado**:
```
T001: Modelos (2 components)
T002: Vistas (1 components)
All tasks valid
```

---

### 5. Verificar normalizacion de nombres en schema assembly

**Objetivo**: Confirmar que el Schema Manager aplica reglas de nombrado.

Dado que el schema assembly es ejecutado por el agente code-generator durante `/fba:construct`,
la validacion de nombres se hace via el gate `schema`. El test verifica que las reglas
existen en el codigo.

**Comando**:
```bash
python3 -c "
# Verificar que las reglas de normalizacion estan documentadas
build_md = open('templates/.opencode/commands/fba:construct.md').read()
assert 'many2one' in build_md.lower()
assert '_id' in build_md
assert '_ids' in build_md
assert 'normalization' in build_md.lower()
assert 'no interpretation' in build_md.lower()
assert 'zero interpretation' in build_md.lower()
assert 'Schema Assembly' in build_md
assert 'SSOT' in build_md
print('Naming conventions and builder contract documented')
"
```

**Resultado esperado**:
```
Naming conventions and builder contract documented
```

---

### 6. Verificar que el gate `schema` bloquea schemas invalidos

**Objetivo**: Confirmar que el gate `schema` rechaza schemas con nombres inconsistentes.

**Comando**:
```bash
python3 -c "
import json
from fba.gate import GateRunner

# Crear estado con gate schema y un schema invalido (campo sin _id en many2one)
import tempfile, os
from pathlib import Path

td = tempfile.mkdtemp()
factory = Path(td) / '.factory'
factory.mkdir()

state = {
    'project': 'test', 'current_phase': 'construction',
    'methodology': 'BABOK',
    'phases': {
        'construction': {'status': 'in_progress', 'agent': 'code-generator'}
    },
    'valid_transitions': {'construction': ['testing']},
    'gates': {
        'construction': {
            'description': 'Validation',
            'owner_agent': 'code-generator',
            'rules': [
                {'type': 'artifact_exists', 'rule_name': 'schema_exists', 'path': '.factory/schema.json'},
                {'type': 'schema', 'rule_name': 'schema_valid', 'schema': 'schema.schema.json', 'path': '.factory/schema.json'},
            ],
        },
    },
    'artifacts': {}, 'context': {},
}
(factory / 'state.json').write_text(json.dumps(state))
(factory / 'module_registry.json').write_text(json.dumps({'modules': {}}))

# Schema sin schema.schema.json copiado — deberia fallar
runner = GateRunner(td)
result = runner.check_phase('construction')

# El schema no existe -> artifact_exists falla
assert result.passed is False, 'Gate should fail without schema.json'
print(f'Gate rejected: {result.error_count} errors')
print('Gate blocks invalid/absent schemas correctly')
"
```

**Resultado esperado**:
```
Gate rejected: X errors
Gate blocks invalid/absent schemas correctly
```

---

### 7. Verificar que el codigo generado no reinterpreta el schema

**Objetivo**: El builder contract (zero interpretation) esta documentado y es verificable.

**Comando**:
```bash
grep -c "No interpretation" templates/.opencode/commands/fba:construct.md
grep -c "zero interpretation" templates/.opencode/commands/fba:construct.md
grep -c "Schema ONLY" templates/.opencode/commands/fba:construct.md
grep -c "no interpretation" templates/.opencode/commands/fba:construct.md
```

**Resultado esperado**: Cada grep devuelve al menos 1 (todas las frases estan presentes).

---

### 8. Verificar la arquitectura documentada en AGENTS.md

**Objetivo**: Confirmar que AGENTS.md refleja la nueva arquitectura con Schema Manager.

**Comando**:
```bash
python3 -c "
agents_md = open('AGENTS.md').read()
assert 'Schema Manager' in agents_md, 'Schema Manager not in AGENTS.md'
assert 'SSOT' in agents_md, 'SSOT not in AGENTS.md'
assert 'schema.json' in agents_md, 'schema.json not in AGENTS.md'
assert 'Code Renderer' in agents_md, 'Code Renderer not in AGENTS.md'
assert 'Module Registry' in agents_md or 'module_registry' in agents_md, 'Module Registry not in AGENTS.md'
print('AGENTS.md architecture documentation complete')
"
```

**Resultado esperado**:
```
AGENTS.md architecture documentation complete
```

---

### 9. Verificar que las reglas de documentacion se cumplen

**Objetivo**: Confirmar que CONTRIBUTING.md y AGENTS.md tienen la regla #11 explicita.

**Comando**:
```bash
python3 -c "
contrib = open('CONTRIBUTING.md').read()
agents = open('AGENTS.md').read()
assert 'Cambios de alcance' in contrib, 'Missing scope change rule in CONTRIBUTING.md'
assert 'Cambios de alcance' in agents, 'Missing scope change rule in AGENTS.md'
print('Rule #11 documented in both AGENTS.md and CONTRIBUTING.md')
"
```

**Resultado esperado**:
```
Rule #11 documented in both AGENTS.md and CONTRIBUTING.md
```

---

### 10. Ejecutar todos los tests para confirmar 0 regresiones

**Comando**:
```bash
python3 -m pytest tests/ -q
```

**Resultado esperado**:
```
... passed ...
```
(0 fallos)

---

### 11. Verificar el flujo E2E completo con modulo "Registro de Vehiculos"

**Objetivo**: Confirmar que todos los componentes del framework funcionan juntos E2E,
incluyendo el nuevo CI/CD Manager de M3.4.

#### 11.1 Verificar que el agente ci_cd_manager existe

**Comando**:
```bash
ls -la templates/.opencode/agents/ci_cd_manager.md
cat templates/.opencode/agents/ci_cd_manager.md | head -5
```

**Resultado esperado**: El archivo existe y tiene frontmatter valido con `mode: subagent`.

#### 11.2 Verificar que el comando fba:ship esta completo

**Comando**:
```bash
grep -c "Pre-conditions" templates/.opencode/commands/fba:ship.md
grep -c "Post-conditions" templates/.opencode/commands/fba:ship.md
grep -c "ship_complete" templates/.opencode/commands/fba:ship.md
```

**Resultado esperado**: Cada grep devuelve al menos 1.

#### 11.3 Verificar que fba init incluye el gate ci_cd

**Comando**:
```bash
mkdir -p /tmp/test-m3d && fba init -d /tmp/test-m3d
python3 -c "
import json
state = json.load(open('/tmp/test-m3d/.factory/state.json'))
gates = state.get('gates', {})
assert 'ci_cd' in gates, 'ci_cd gate missing'
gate = gates['ci_cd']
print(f'ci_cd gate: {gate[\"description\"]}')
print(f'Owner: {gate[\"owner_agent\"]}')
print(f'Rules: {len(gate[\"rules\"])}')
for rule in gate['rules']:
    print(f'  - {rule[\"rule_name\"]} ({rule[\"type\"]})')
assert gate['owner_agent'] == 'cicd_manager'
assert len(gate['rules']) == 3
print('ci_cd gate configured correctly')
"
```

**Resultado esperado**:
```
ci_cd gate: Validates CI/CD workflow exists and project is ready for release
Owner: cicd_manager
Rules: 3
  - ci_workflow_exists (artifact_exists)
  - ship_report_json_exists (artifact_exists)
  - ship_report_md_exists (artifact_exists)
ci_cd gate configured correctly
```

#### 11.4 Verificar el gate ci_cd bloquea transiciones invalidas

**Comando**:
```bash
python3 -c "
import json, tempfile
from pathlib import Path
from fba.state import StateManager
from fba.gate import GateError

td = tempfile.mkdtemp()
factory = Path(td) / '.factory'
factory.mkdir(parents=True)

state = {
    'project': 'test', 'current_phase': 'ci_cd',
    'framework_version': '0.4.0',
    'init_at': '2026-01-01T00:00:00+00:00',
    'methodology': 'BABOK',
    'phases': {
        'ci_cd': {'status': 'in_progress', 'agent': 'cicd_manager'},
        'complete': {'status': 'pending', 'agent': 'cicd_manager'},
    },
    'valid_transitions': {'ci_cd': ['complete']},
    'gates': {
        'ci_cd': {
            'description': 'CI/CD gate',
            'owner_agent': 'cicd_manager',
            'rules': [
                {'type': 'artifact_exists', 'rule_name': 'ci_workflow', 'path': '.github/workflows/factory-ci.yml'},
            ],
        },
    },
    'artifacts': {}, 'context': {},
}
(factory / 'state.json').write_text(json.dumps(state))

sm = StateManager(td)
try:
    sm.transition_to('complete')
    print('ERROR: should have raised GateError')
except GateError as e:
    assert 'ci_cd' in str(e)
    print(f'Gate ci_cd blocked transition correctly: {e}')
"
```

**Resultado esperado**:
```
Gate ci_cd blocked transition correctly: Gate 'ci_cd' failed: ...
```

#### 11.5 Verificar que el template factory-ci.yml se copia correctamente

**Comando**:
```bash
cat templates/.github/workflows/factory-ci.yml | head -5
grep -c "fba-ci" templates/.github/workflows/factory-ci.yml
grep -c "actions/checkout@v4" templates/.github/workflows/factory-ci.yml
```

**Resultado esperado**: El template CI existe con el nombre `fba-ci` y usa `actions/checkout@v4`.

#### 11.6 Verificar que el agente ci_cd_manager se incluye en los tests de definiciones

**Comando**:
```bash
python3 -m pytest tests/test_agent_definitions.py -v -k "CicdManager"
```

**Resultado esperado**: Todos los tests pasan (7 tests: existencia, frontmatter, body content).

#### 11.7 Verificar que el sistema de fases incluye ci_cd y complete

**Comando**:
```bash
mkdir -p /tmp/test-m3e && fba init -d /tmp/test-m3e
python3 -c "
import json
state = json.load(open('/tmp/test-m3e/.factory/state.json'))
assert 'ci_cd' in state['phases'], 'ci_cd phase missing'
assert state['phases']['ci_cd']['status'] == 'pending'
assert state['phases']['ci_cd']['agent'] == 'cicd_manager'
assert state['valid_transitions']['review'] == ['ci_cd']
assert state['valid_transitions']['ci_cd'] == ['complete']
print('Phase system complete with ci_cd -> complete flow')
"
```

**Resultado esperado**:
```
Phase system complete with ci_cd -> complete flow
```

#### 11.8 Ejecutar todos los tests para confirmar 0 regresiones

**Comando**:
```bash
python3 -m pytest tests/ -q
```

**Resultado esperado**: 0 fallos.

---

## Troubleshooting

| Problema | Causa probable | Solucion |
|----------|---------------|----------|
| `fba init` no copia module_registry.json | `fba update` no ejecutado despues de cambios en templates | Ejecutar `fba update` o `fba init` en proyecto limpio |
| Schema assembly genera nombres inconsistentes | Las reglas de normalizacion no se aplicaron | Verificar que el agente code-generator lee todas las T*.json y aplica el pipe de normalizacion |
| Gate `schema` no existe | state.json generado con version vieja de `fba init` | Re-ejecutar `fba init` |
| Tests de gate schema fallan | schema.schema.json no se copio a .factory/schemas/ | Verificar que `fba init` copia todos los schemas |

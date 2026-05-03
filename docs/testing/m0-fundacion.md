# Testing - M0: Fundacion

## Requisitos Previos

- Python 3.11 o superior
- pip actualizado
- El repositorio clonado y en el directorio raiz

## Pasos para Probar

### 1. Instalacion del paquete

**Objetivo**: Verificar que el paquete se instala correctamente desde el repositorio local.

**Comando**:
```
pip install -e ".[dev]"
```

**Resultado esperado**:
```
Successfully installed fba-0.1.0
```

### 2. Verificar la version del CLI

**Objetivo**: Confirmar que el comando `fba` esta disponible y muestra la version correcta.

**Comando**:
```
fba --version
```

**Resultado esperado**:
```
fba, version 0.1.0
```

### 3. Inicializar un proyecto vacio

**Objetivo**: Probar que `fba init` crea toda la estructura necesaria.

**Comando**:
```
mkdir -p /tmp/test-fba && fba init -d /tmp/test-fba
```

**Resultado esperado**:
```
Initializing Factory Build Agent in /tmp/test-fba...
✅ Factory Build Agent initialized in /tmp/test-fba

Next steps:
  1. Open the project with OpenCode: opencode .
  2. Start eliciting requirements: /fba:elicit "your idea"
```

### 4. Verificar la estructura creada

**Objetivo**: Confirmar que todos los directorios y archivos se crearon.

**Comando**:
```
# Directorios principales
ls -d /tmp/test-fba/.factory /tmp/test-fba/.opencode /tmp/test-fba/.github

# Archivos clave
ls -la /tmp/test-fba/.factory/state.json
ls -la /tmp/test-fba/.factory/events.jsonl
ls -la /tmp/test-fba/.opencode/agents/orchestrator.md
ls -la /tmp/test-fba/.opencode/commands/fba:init.md
ls -la /tmp/test-fba/AGENTS.md
ls -la /tmp/test-fba/.github/workflows/factory-ci.yml
```

**Resultado esperado**: Todos los paths existen y son archivos o directorios validos.

### 5. Validar state.json

**Objetivo**: Verificar que el state.json generado contiene los campos esperados.

**Comando**:
```
python -c "
import json
with open('/tmp/test-fba/.factory/state.json') as f:
    state = json.load(f)
assert state['current_phase'] == 'init'
assert state['methodology'] == 'BABOK'
assert 'project' in state
assert state['phases']['elicitation']['status'] == 'pending'
print('✅ state.json validado correctamente')
"
```

**Resultado esperado**:
```
✅ state.json validado correctamente
```

### 6. Validar events.jsonl

**Objetivo**: Verificar que el log de eventos contiene el evento de inicializacion.

**Comando**:
```
python -c "
import json
with open('/tmp/test-fba/.factory/events.jsonl') as f:
    lines = f.read().strip().split('\n')
event = json.loads(lines[0])
assert event['type'] == 'init'
assert event['agent'] == 'fba_cli'
print('✅ events.jsonl validado correctamente')
"
```

**Resultado esperado**:
```
✅ events.jsonl validado correctamente
```

### 7. Error si .factory/ ya existe

**Objetivo**: Confirmar que `fba init` rechaza re-inicializar un proyecto.

**Comando**:
```
fba init -d /tmp/test-fba
```

**Resultado esperado**:
```
Initializing Factory Build Agent in /tmp/test-fba...
⚠  .factory/ already exists. Run fba init in a project without it.
```
El comando debe terminar con codigo de salida 1.

### 8. Ejecutar la suite de tests

**Objetivo**: Verificar que los 10 tests del framework pasan.

**Comando**:
```
pytest -v
```

**Resultado esperado**:
```
tests/test_cli.py::test_cli_version PASSED
tests/test_cli.py::test_init_creates_directories PASSED
tests/test_cli.py::test_init_creates_state_file PASSED
tests/test_cli.py::test_init_creates_events_log PASSED
tests/test_cli.py::test_init_creates_agents_yaml PASSED
tests/test_cli.py::test_init_creates_slash_commands PASSED
tests/test_cli.py::test_init_creates_github_workflow PASSED
tests/test_cli.py::test_init_creates_project_agents_md PASSED
tests/test_cli.py::test_init_fails_if_factory_exists PASSED
tests/test_cli.py::test_state_schema_validation PASSED

============================== 10 passed ==============================
```

### 9. Lint con Ruff

**Objetivo**: Confirmar que el codigo no tiene errores de lint.

**Comando**:
```
ruff check src/ tests/
```

**Resultado esperado**:
```
All checks passed!
```

### 10. Cobertura de tests

**Objetivo**: Verificar que la cobertura de codigo es >= 80%.

**Comando**:
```
pytest --cov=src/fba --cov-report=term-missing
```

**Resultado esperado**: Cobertura total >= 80%.

## Limpiar

```bash
rm -rf /tmp/test-fba
```

## Troubleshooting

### `fba: command not found`

Asegurate de que el entorno virtual esta activado y el paquete instalado:

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

### `ModuleNotFoundError: No module named 'fba'`

El paquete no esta instalado en modo editable. Ejecuta:

```bash
pip install -e ".[dev]"
```

### Tests fallan con error de importacion

Verifica que `pytest` esta instalado:

```bash
pip install pytest pytest-cov
```

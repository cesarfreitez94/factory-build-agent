# Testing - M11: Foundation Hardening

## Requisitos Previos
- Python 3.11+
- `fba` CLI instalado (`pip install -e .`)
- Acceso al repositorio del proyecto (`factory-build-agent`)

---

## 1. Verificar atomicidad de escritura

**Objetivo**: Confirmar que `_atomic_write()` protege archivos criticos de corrupcion.

**Comando**:
```bash
pytest tests/test_state_atomicity.py -v
```

**Resultado esperado**:
```
8 passed
```

**Que prueba cada test**:
- `test_atomic_write_success`: escritura atomica exitosa, contenido llega integro
- `test_atomic_write_original_intact_on_write_failure`: archivo original intacto si falla el replace
- `test_atomic_write_directory_created`: crea directorio destino si no existe
- `test_atomic_write_temp_cleaned_on_failure`: archivo temporal limpiado en caso de error
- `test_state_manager_save_uses_atomic_write`: `StateManager.save()` usa el mecanismo atomico
- `test_record_event_uses_append_with_fsync`: `record_event()` usa fsync en append
- `test_state_manager_save_does_not_leave_temp_files`: sin archivos temporales residuales
- `test_concurrent_writes_no_corruption`: escrituras concurrentes no producen corrupcion

---

## 2. Verificar rollback de estado

**Objetivo**: Confirmar que `transition_to()` revierte el estado si una operacion post-save falla.

**Comando**:
```bash
pytest tests/test_state_rollback.py -v
```

**Resultado esperado**:
```
8 passed
```

---

## 3. Verificar robustez del registry

**Objetivo**: ModuleRegistry emite warnings explicitos en escenarios de error.

**Comando**:
```bash
pytest tests/test_registry_robustez.py -v
```

**Resultado esperado**:
```
8 passed
```

---

## 4. Probar comando `fba doctor`

**Objetivo**: El comando diagnostica correctamente la salud del proyecto.

### 4.1 Proyecto sano

```bash
# Crear proyecto temporal e inicializar
mkdir /tmp/test-fba-healthy
cd /tmp/test-fba-healthy
fba init

# Ejecutar doctor
fba doctor
```

**Resultado esperado**: Exit code 0 o 1. Output muestra checks de registry, state_exists, state_json, writable, schema_alignment.

### 4.2 Output verbose

```bash
fba doctor --verbose
```

**Resultado esperado**: Muestra detalles adicionales: nombre del proyecto, directorio .factory/, estado de cada check.

### 4.3 Output JSON

```bash
fba doctor --json
```

**Resultado esperado**: Output JSON valido con keys `status`, `checks`, `exit_code`, `warnings`, `errors`.

### 4.4 Proyecto sin .factory/

```bash
mkdir /tmp/test-no-factory
cd /tmp/test-no-factory
fba doctor
```

**Resultado esperado**: Exit code 2. Mensaje: "No .factory/ directory found."

### 4.5 Tests automatizados

```bash
pytest tests/test_fba_doctor.py -v
```

**Resultado esperado**:
```
8 passed
```

---

## 5. Verificar deteccion de tipos no implementados

**Objetivo**: SchemaManager detecta y advierte sobre tipos `wizard`, `workflow`, `report`, `controller`.

**Comando**:
```bash
pytest tests/test_schema_manager_unknown_types.py -v
```

**Resultado esperado**:
```
8 passed
```

**Que prueba cada test**:
- Componente `type: "wizard"` → AssemblyWarning emitido
- Componente `type: "workflow"` → AssemblyWarning emitido
- Componentes `type: "report"` y `"controller"` → un warning por cada uno
- Solo tipos conocidos (`model`, `view`, etc.) → sin warnings de tipo desconocido
- Multiples componentes desconocidos → un warning por cada uno
- Los warnings tienen nivel `"warning"` (no bloquean el assembly)
- `IMPLEMENTED_TYPES` existe como constante de clase

---

## 6. Suite completa de tests

**Objetivo**: Verificar que todos los tests del proyecto pasan (incluyendo los 5 nuevos archivos).

**Comando**:
```bash
pytest tests/ -v
```

**Resultado esperado**:
```
493 passed in ~2s
```

---

## 7. Regresiones

**Objetivo**: Confirmar que los tests existentes (anteriores a M11) siguen pasando.

**Comando**:
```bash
pytest tests/ --ignore=tests/test_state_atomicity.py --ignore=tests/test_state_rollback.py --ignore=tests/test_registry_robustez.py --ignore=tests/test_fba_doctor.py --ignore=tests/test_schema_manager_unknown_types.py -v
```

**Resultado esperado**: Todos los tests existentes pasan (~453 tests).

---

## Troubleshooting

### `fba: command not found`
Asegurate de tener el paquete instalado: `pip install -e .`

### `ModuleRegistry` no emite warnings
Verifica que los warnings se capturen correctamente. Los warnings usan `warnings.warn(UserWarning, ...)` y pueden necesitar `pytest -W default` para ser visibles.

### `fba doctor` reporta exit code 1 en proyecto sano
Esto es esperado si D5 (schema alignment) detecta tipos no implementados. El exit code 1 indica warnings pero no errores. El exit code 2 indicaria errores.

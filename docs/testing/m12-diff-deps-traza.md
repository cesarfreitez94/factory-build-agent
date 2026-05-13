# Testing — M12: Diff, Dependencies & Trazabilidad

## Requisitos Previos
- Python 3.11+
- Factory Build Agent instalado (`pip install -e .`)
- pytest

## Pasos para Probar

### 1. Diff Engine — Comparar artefactos JSON
**Objetivo**: Verificar que `fba diff` produce changelogs estructurados.

**Comandos**:
```bash
# Crear dos versiones de PRD y compararlas
fba diff v1/prd.json v2/prd.json

# Output JSON (machine-readable)
fba diff old/sdd.json new/sdd.json --format json

# Comparar schema.json con campo nuevo
fba diff old/schema.json new/schema.json
```

**Resultado esperado**:
- Output texto: `=== Diff: prd ===` con secciones Added/Removed/Modified y Summary
- Output JSON: objeto con `artifact_type`, `timestamp`, `changes`, `summary`
- Archivos idénticos: "No changes detected."
- Archivos no existentes: "Error: File not found"
- JSON malformado: "Error: Invalid JSON"

### 2. Artifact Contracts — Validar invariantes de negocio
**Objetivo**: Verificar que `fba validate --contract` valida reglas de negocio.

**Comandos**:
```bash
# Validar PRD contra su contrato
fba validate --contract prd --project-dir /path/to/project

# Validar SDD
fba validate --contract sdd --project-dir /path/to/project

# Validar schema.json
fba validate --contract schema --project-dir /path/to/project
```

**Resultado esperado**:
- PRD sin stakeholders: violación `prd-has-stakeholders`
- PRD con requisito sin ID: violación `prd-requirements-have-ids`
- SDD sin modelos: violación `sdd-has-models`
- Artifact correcto: "all invariants pass"

### 3. Dependency Integrity — Analizar dependencias Odoo
**Objetivo**: Verificar que `fba deps check` detecta problemas de dependencias.

**Comandos**:
```bash
# Analizar todas las dependencias del proyecto
fba deps check --project-dir /path/to/project

# Verificar un módulo específico
fba deps check --project-dir /path/to/project
```

**Resultado esperado**:
- Módulo limpio: "✅ my_module: clean"
- Dependencia no usada: "⚠ [unused_dependency] ... not referenced in code"
- Dependencia faltante: "❌ [missing_dependency] ... not in 'depends'"
- Dependencia circular: "🔄 [circular_dependency] Circular dependency detected: a → b → a"

### 4. Stable IDs — Trazabilidad con UUIDs
**Objetivo**: Verificar que `fba trace` encuentra entidades por UUID.

**Comandos**:
```bash
# Trazar un UUID en los artefactos del proyecto
fba trace <uuid-v4> --project-dir /path/to/project

# UUID no encontrado
fba trace 00000000-0000-0000-0000-000000000000 --project-dir /path/to/project
```

**Resultado esperado**:
- UUID encontrado: muestra artifact, path, entity_id, entity_type
- UUID no encontrado: "not found in any artifact"

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `fba diff` no encuentra archivos | Verificar que ambos archivos existen y son JSON válido |
| `fba validate --contract` falla con "Contract file not found" | Verificar que `schemas/contracts/` existe en el workspace |
| `fba deps check` no encuentra módulos | Verificar que el directorio del proyecto contiene `__manifest__.py` |
| `fba trace` no encuentra UUID | El UUID debe existir en PRD, SDD o schema.json |

## Verificación Automatizada

```bash
# Ejecutar todos los tests del milestone
pytest tests/test_diff_engine.py tests/test_artifact_contracts.py \
       tests/test_dependency_integrity.py tests/test_stable_ids.py -v

# Suite completa
pytest
```

Resultado esperado: **604 passed, 0 failures**

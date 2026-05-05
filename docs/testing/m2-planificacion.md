# Testing - M2: Planificacion + SDD

## Requisitos Previos

- Python 3.11 o superior
- pip actualizado
- El repositorio clonado y en el directorio raiz
- `fba` instalado: `pip install -e ".[dev]"`

## Pasos para Probar

### 1. Inicializar proyecto de prueba

**Objetivo**: Verificar que `fba init` copia el schema SDD.

**Comando**:
```bash
mkdir -p /tmp/test-m2 && fba init -d /tmp/test-m2
```

**Resultado esperado**:
```
Initializing Factory Build Agent in /tmp/test-m2...
✅ Factory Build Agent initialized in /tmp/test-m2
```

Verificar que los schemas se copiaron:
```bash
ls /tmp/test-m2/.factory/schemas/
```
Debe mostrar `prd.schema.json`, `sdd.schema.json` y `state.schema.json`.

### 2. Verificar que el agente Planificador existe

**Objetivo**: Confirmar que el agente planificador.md esta en las plantillas.

**Comando**:
```bash
ls /tmp/test-m2/.opencode/agents/
```

**Resultado esperado**:
```
documentador.md  elicitador.md  orchestrator.md  planificador.md
```

### 3. Verificar slash command fba:plan

**Objetivo**: Confirmar que el comando slash esta instalado con contenido completo.

**Comando**:
```bash
grep -c "fba validate sdd" /tmp/test-m2/.opencode/commands/fba:plan.md
```

**Resultado esperado**: `1` (la referencia existe en el comando).

### 4. Crear PRD de ejemplo

**Objetivo**: Preparar datos para validar el SDD con trazabilidad.

**Comando**:
```bash
cat > /tmp/test-m2/.factory/prd.json << 'JSON'
{
  "vision": "Modulo de registro de vehiculos que permite gestionar la flota vehicular con busqueda avanzada en Odoo v18.",
  "stakeholders": [
    {"name": "Gerente de Flota", "role": "Usuario", "interest": "Registro rapido y busqueda"}
  ],
  "objectives": ["Reducir tiempo de registro", "Busqueda por placa"],
  "functional_requirements": [
    {"id": "RF-01", "description": "CRUD de vehiculos con campos marca, modelo, ano, placa", "priority": "high"},
    {"id": "RF-02", "description": "Validar unicidad de placa al crear o editar vehiculo", "priority": "high"},
    {"id": "RF-03", "description": "Busqueda y filtrado por placa, marca y modelo", "priority": "medium"}
  ],
  "non_functional_requirements": [
    {"id": "RNF-01", "description": "Busqueda debe responder en menos de 2 segundos con 10000 registros", "category": "performance", "priority": "high"},
    {"id": "RNF-02", "description": "Solo usuarios autorizados pueden modificar vehiculos", "category": "security", "priority": "high"}
  ],
  "acceptance_criteria": [
    {"id": "CA-01", "criterion": "Usuario crea vehiculo completo en menos de 1 minuto", "related_requirements": ["RF-01"]}
  ],
  "glossary": [{"term": "CRUD", "definition": "Create, Read, Update, Delete"}]
}
JSON
echo "✅ PRD de ejemplo creado"
```

### 5. Crear SDD valido con trazabilidad completa

**Objetivo**: Validar que un SDD bien formado pasa schema + traceability.

**Comando**:
```bash
cat > /tmp/test-m2/.factory/sdd.json << 'JSON'
{
  "module_name": "vehicle_registry",
  "module_display_name": "Vehicle Registry",
  "version": "18.0.1.0.0",
  "summary": "Vehicle management module for Odoo v18",
  "architecture": {
    "description": "Simple module with one model and basic CRUD views for vehicle management"
  },
  "models": [
    {
      "name": "vehicle.registry",
      "display_name": "Vehicle",
      "description": "Main vehicle registry model for storing vehicle data",
      "fields": [
        {
          "name": "plate",
          "type": "char",
          "display_name": "License Plate",
          "required": true,
          "unique": true,
          "size": 20,
          "description": "Unique vehicle license plate number",
          "traceability": ["RF-01", "RF-02"]
        },
        {
          "name": "brand",
          "type": "char",
          "display_name": "Brand",
          "required": true,
          "description": "Vehicle manufacturer brand",
          "traceability": ["RF-01"]
        }
      ],
      "traceability": ["RF-01", "RF-02", "RF-03"]
    }
  ],
  "views": [
    {
      "model": "vehicle.registry",
      "type": "form",
      "name": "vehicle.registry.form",
      "description": "Main vehicle form view",
      "fields": ["plate", "brand"],
      "traceability": ["RF-01"]
    },
    {
      "model": "vehicle.registry",
      "type": "tree",
      "name": "vehicle.registry.tree",
      "description": "Vehicle list view",
      "fields": ["plate", "brand"],
      "traceability": ["RF-01"]
    },
    {
      "model": "vehicle.registry",
      "type": "search",
      "name": "vehicle.registry.search",
      "description": "Vehicle search view with filters",
      "fields": ["plate", "brand"],
      "traceability": ["RF-03"]
    }
  ],
  "security": {
    "groups": [
      {
        "name": "vehicle_user",
        "display_name": "Vehicle User",
        "description": "Can view and create vehicle records"
      },
      {
        "name": "vehicle_manager",
        "display_name": "Vehicle Manager",
        "description": "Full access to vehicle records"
      }
    ],
    "access_rights": [
      {
        "model": "vehicle.registry",
        "group": "vehicle_user",
        "perm_read": true,
        "perm_write": true,
        "perm_create": true,
        "perm_unlink": false
      },
      {
        "model": "vehicle.registry",
        "group": "vehicle_manager",
        "perm_read": true,
        "perm_write": true,
        "perm_create": true,
        "perm_unlink": true
      }
    ]
  },
  "dependencies": {
    "required": ["base"],
    "optional": ["mail", "contacts"],
    "reason": "base is required for all Odoo modules, mail for activity tracking, contacts for partner references"
  },
  "workflows": [],
  "reporting": [],
  "file_structure": {
    "module": "vehicle_registry",
    "files": [
      "__manifest__.py",
      "__init__.py",
      "models/__init__.py",
      "models/vehicle_registry.py",
      "views/__init__.py",
      "views/vehicle_registry_views.xml",
      "views/menu.xml",
      "security/ir.model.access.csv",
      "security/security.xml"
    ]
  },
  "traceability_matrix": {
    "description": "Maps all PRD requirements to SDD design components",
    "mappings": [
      {
        "requirement": "RF-01",
        "sdD_components": ["vehicle.registry model", "vehicle.registry.form view", "vehicle.registry.tree view"],
        "description": "CRUD operations for vehicle records"
      },
      {
        "requirement": "RF-02",
        "sdD_components": ["vehicle.registry model (plate field)", "SQL constraint"],
        "description": "Unique plate validation"
      },
      {
        "requirement": "RF-03",
        "sdD_components": ["vehicle.registry model", "vehicle.registry.search view"],
        "description": "Search and filter by plate, brand, model"
      },
      {
        "requirement": "RNF-01",
        "sdD_components": ["vehicle.registry model (indexed fields)", "Search view optimization"],
        "description": "Search performance under 2 seconds"
      },
      {
        "requirement": "RNF-02",
        "sdD_components": ["security groups", "access rights", "record rules"],
        "description": "Access control for vehicle modification"
      }
    ]
  }
}
JSON
echo "✅ SDD de ejemplo creado"
```

### 6. Validar SDD contra schema + trazabilidad

**Objetivo**: Probar `fba validate sdd` con schema y traceability.

**Comando**:
```bash
fba validate sdd -d /tmp/test-m2
```

**Resultado esperado**:
```
✅ sdd: valid
✅ traceability: 5 requirements mapped to SDD components
```

### 7. Probar SDD con trazabilidad incompleta

**Objetivo**: Confirmar que `fba validate sdd` detecta requisitos no mapeados.

**Comando**:
```bash
python -c "
import json
with open('/tmp/test-m2/.factory/sdd.json') as f:
    sdd = json.load(f)
sdd['traceability_matrix']['mappings'] = [
    {'requirement': 'RF-01', 'sdD_components': ['model'], 'description': 'CRUD'}
]
with open('/tmp/test-m2/.factory/sdd.json', 'w') as f:
    json.dump(sdd, f, indent=2)
"
fba validate sdd -d /tmp/test-m2
```

**Resultado esperado** (exit code 1):
```
✅ sdd: valid
❌ traceability: PRD requirement 'RF-02' not mapped to any SDD component
❌ traceability: PRD requirement 'RF-03' not mapped to any SDD component
❌ traceability: PRD requirement 'RNF-01' not mapped to any SDD component
❌ traceability: PRD requirement 'RNF-02' not mapped to any SDD component
   4 unmapped requirement(s)
```

### 8. Simular flujo completo M2

**Objetivo**: Probar transicion documentation -> planning y registro de eventos.

**Comando**:
```bash
fba transition documentation -d /tmp/test-m2
fba record plan_complete --data '{"artifacts":["sdd.json","sdd.md","plan.md"],"traceability_complete":true}' -d /tmp/test-m2
fba transition planning -d /tmp/test-m2
```

**Resultado esperado**:
```
Transitioned from 'init' to 'documentation'
Event 'plan_complete' recorded.
Transitioned from 'documentation' to 'planning'
```

Verificar estado:
```bash
fba status -d /tmp/test-m2
```
Debe mostrar `Current phase: planning`.

### 9. Ejecutar suite completa de tests

**Objetivo**: Verificar que todos los tests del framework pasan.

**Comando**:
```bash
cd /home/cafl/projects/factory-build-agent
python -m pytest -v
```

**Resultado esperado**: 169+ tests PASSED (incluye 41 tests de SDD schema y 2 de traceability).

### 10. Verificar lint con ruff

**Objetivo**: Confirmar codigo limpio sin warnings.

**Comando**:
```bash
ruff check src/ tests/
```

**Resultado esperado**: Sin errores ni warnings.

## Limpiar

```bash
rm -rf /tmp/test-m2
```

## Troubleshooting

### `No schema found for artifact 'sdd'`

Verifica que `fba init` se ejecuto con la version mas reciente que incluye `sdd.schema.json`:
```bash
ls -la /tmp/test-m2/.factory/schemas/sdd.schema.json
```

### `prd.json not found, skipping traceability check`

Este mensaje es informativo. El SDD se valida correctamente contra el schema aunque no haya PRD para verificar trazabilidad.

### `fba: command not found`

Asegurate de instalar en modo editable:
```bash
pip install -e ".[dev]"
```

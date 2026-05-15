# Testing - M16: Foundation Intelligence

## Requisitos Previos

- Python 3.11+
- Dependencias del proyecto instaladas (`pip install -e .[dev]`)
- Un addon Odoo v18 de prueba disponible en disco
- ROADMAP.md actualizado con M16 como milestone planificado

## Alcance de Validacion

M16 introduce la base de conocimiento version-aware del framework:

- ModuleRegistry autoindexado desde un modulo Odoo existente
- Capa de conocimiento por version de Odoo (`base/`, `v18/`, `v17/`)
- Odoo Pattern Knowledge Base consultable por Planificador, Constructor y Revisor
- Observabilidad local de agentes del framework via plugin OpenCode

## Pasos para Probar

### 1. Verificar roadmap y estado meta

**Objetivo**: Confirmar que M16 esta registrado como el siguiente milestone planificado.

**Comando**:

```bash
rg -n "M16: Foundation Intelligence|module-registry-autoindexado|pattern-knowledge-base" ROADMAP.md .factory/framework-state.json
```

**Resultado esperado**:

```text
ROADMAP.md contiene M16 y sus feats planificados.
.factory/framework-state.json marca M16 como active_milestone planificado.
```

### 2. Probar autoindexado del registry

**Objetivo**: Indexar un modulo Odoo existente sin intervencion manual.

**Comando**:

```bash
fba registry index addons/my_module --odoo-version 18.0
fba registry inspect my_module
```

**Resultado esperado**:

```text
El comando actualiza `.factory/module_registry.json` con un resumen compatible con `SchemaManager`.
El comando genera o actualiza `.factory/registry_index.json` con el indice profundo.
El registry detecta modelos, campos, vistas, controllers, reportes, seguridad, data/demo,
crons, wizards y OWL components cuando existan.
La salida incluye odoo_version, registry_version, conteos por artefacto y modelos detectados.
Si se ejecuta sobre una carpeta `addons/`, indexa todos los modulos hijos con `__manifest__.py`.
Si un modulo ya existe en el registry, la version recien indexada tiene prioridad; si no cambia,
el archivo no se reescribe.
```

**Uso del indice profundo**:

```text
`.factory/module_registry.json` sigue siendo el artefacto liviano para lookup de modelos.
`.factory/registry_index.json` es el artefacto rico para agentes y comandos que necesiten
inspeccionar estructura existente antes de planificar, extender o revisar un modulo.
```

### 3. Probar resolucion de patrones por version

**Objetivo**: Confirmar que el framework carga patrones comunes y especificos de Odoo v18.

**Comandos**:

```bash
# Listar todas las claves de conocimiento disponibles para Odoo 18.0
fba patterns list --odoo-version 18.0

# Consultar una entrada de conocimiento especifica en formato texto
fba patterns query model.naming --odoo-version 18.0

# Consultar en formato JSON
fba patterns query model.naming --odoo-version 18.0 --format json

# Consultar una clave inexistente (debe fallar con codigo 1)
fba patterns query nonexistent.key --odoo-version 18.0

# Filtrar por categoria de deprecaciones
fba patterns list --category deprecations --odoo-version 18.0

# Usar resolver con Odoo 17.0 (debe mostrar solo entradas base, no v18)
fba patterns list --odoo-version 17.0
```

**Resultado esperado**:

```text
fba patterns list --odoo-version 18.0:
  Entre 50 y 80 knowledge keys mostradas, incluyendo model.naming, view.form.structure,
  wizard.confirmation, ir.actions.todo y orm.batch.operations

fba patterns query model.naming --odoo-version 18.0:
  Muestra entrada con since_version=18.0, ejemplos especificos de v18

fba patterns query model.naming --odoo-version 18.0 --format json:
  Retorna JSON valido con la entrada resuelta

fba patterns query nonexistent.key:
  Error: Key not found, exit code 1

fba patterns list --category deprecations:
  Muestra 5-10 deprecaciones de la capa v18, incluyendo ir.actions.todo

fba patterns list --odoo-version 17.0:
  Muestra las entradas base de patrones Odoo
  NO muestra ir.actions.todo ni orm.batch.operations (especificas de v18)
```

### 4. Ejecutar tests automatizados

**Objetivo**: Validar el comportamiento nuevo con tests unitarios e integracion.

**Comandos**:

```bash
# Validacion del Knowledge Base poblado en feat/16.3
pytest tests/test_knowledge_schema_validation.py -v

# Tests del version layer
pytest tests/test_odoo_version_layer.py -v

# Tests existentes no deben romperse
pytest tests/test_registry_autoindex.py tests/test_registry_robustez.py tests/test_schema_manager.py -v

# Plugin local de observabilidad OpenCode
pytest tests/test_opencode_agent_observer_plugin.py -v

# Suite completa
pytest
```

**Resultado esperado**:

```text
Todos los tests pasan sin fallos.
```

### 5. Probar observabilidad local de agentes

**Objetivo**: Confirmar que el plugin OpenCode monitorea solo `.opencode/agents` y genera
metricas por agente.

**Guia detallada**:

```bash
docs/testing/m16.4-agent-observer-plugin.md
```

## Troubleshooting

### `fba registry index` no existe

Verifica que estas usando una version posterior a `feat/16.1-module-registry-autoindexado`
o ejecuta `pip install -e .[dev]` desde el branch correcto.

### `fba patterns` no existe

Verifica que estas en el branch `feat/16.2-odoo-version-layer` o posterior.
Ejecuta `pip install -e .[dev]` para reinstalar el paquete con el nuevo grupo de comandos.

### El addon de prueba no tiene todos los artefactos

Usa un addon Odoo con al menos modelos, vistas y seguridad para la prueba minima. Controllers, reports,
crons, wizards y OWL components pueden validarse con fixtures separados.

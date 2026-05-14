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

**Comando esperado**:

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

**Comando esperado**:

```bash
fba patterns query wizard.confirmation --odoo-version 18.0
```

**Resultado esperado**:

```text
El resultado devuelve un patron aplicable a Odoo 18.0 con ejemplos y anti-patrones relacionados.
```

### 4. Ejecutar tests automatizados

**Objetivo**: Validar el comportamiento nuevo con tests unitarios e integracion.

**Comando esperado**:

```bash
pytest tests/test_registry_autoindex.py tests/test_odoo_patterns.py
```

**Resultado esperado**:

```text
Todos los tests pasan sin fallos.
```

## Troubleshooting

### `fba registry index` no existe

Verifica que estas usando una version posterior a `feat/16.1-module-registry-autoindexado`
o ejecuta `pip install -e .[dev]` desde el branch correcto.

### El addon de prueba no tiene todos los artefactos

Usa un addon Odoo con al menos modelos, vistas y seguridad para la prueba minima. Controllers, reports,
crons, wizards y OWL components pueden validarse con fixtures separados.

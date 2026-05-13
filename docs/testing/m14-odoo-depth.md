# Testing - M14: Odoo Depth (Capa 3)

## Requisitos Previos
- Python 3.11+
- Framework instalado: `pip install -e .`
- OpenCode configurado

## Pasos para Probar

### 1. Wizards y Workflows
**Objetivo**: Verificar que el SchemaManager acepta tipos wizard/workflow/report/controller
**Comando**: `pytest tests/test_wizards_workflows.py -v`
**Resultado esperado**: 20 tests pasan

### 2. Migraciones
**Objetivo**: Verificar deteccion de cambios y generacion de scripts de migracion
**Comando**: `pytest tests/test_migraciones.py -v`
**Resultado esperado**: 22 tests pasan

### 3. Internacionalizacion i18n
**Objetivo**: Verificar extraccion de strings y generacion .pot/.po
**Comando**: `pytest tests/test_i18n.py -v`
**Resultado esperado**: 22 tests pasan

### 4. Tests completos
**Comando**: `pytest`
**Resultado esperado**: 719+ tests, 0 fallos

### 5. CLI - Comando migrate
**Comando**: `fba migrate check --help`
**Resultado esperado**: Muestra ayuda del comando

### 6. CLI - Comando i18n
**Comando**: `fba i18n extract --help`
**Resultado esperado**: Muestra ayuda del comando

# Testing - M15: Advanced QA (Capa 4)

## Requisitos Previos
- Python 3.11+
- Framework instalado: `pip install -e .`
- Proyecto FBA inicializado con `.factory/state.json`

## Pasos para Probar

### 1. Playwright Browser Automation
**Objetivo**: Verificar generacion de specs Playwright para vistas Odoo form, list y kanban.
**Comando**: `pytest tests/test_playwright.py -v`
**Resultado esperado**: 4 tests pasan y se generan `odoo_views.spec.ts`, `playwright_report.json` y `playwright_report.md`.

### 2. Performance Benchmarks
**Objetivo**: Verificar benchmarks de carga/generacion, tiempo y memoria pico.
**Comando**: `pytest tests/test_performance.py -v`
**Resultado esperado**: 4 tests pasan y se generan `perf_report.json` y `perf_report.md`.

### 3. Concurrency Safety
**Objetivo**: Verificar warnings cuando `state.json` cambia entre load/save y diagnostico via doctor.
**Comando**: `pytest tests/test_concurrency.py -v`
**Resultado esperado**: 4 tests pasan.

### 4. CLI Playwright
**Comando**: `fba test --playwright --project-dir <proyecto>`
**Resultado esperado**: Genera artefactos en `.factory/playwright/`.

### 5. CLI Performance
**Comando**: `fba perf --project-dir <proyecto>`
**Resultado esperado**: Genera reportes en `.factory/perf/`.

### 6. CLI Doctor Concurrency
**Comando**: `fba doctor --concurrency --project-dir <proyecto>`
**Resultado esperado**: Reporta `concurrency` como OK si no hay marcadores de escritura concurrente.

### 7. Suite M15
**Comando**: `pytest tests/test_playwright.py tests/test_performance.py tests/test_concurrency.py`
**Resultado esperado**: 12 tests pasan.

## Troubleshooting
- Si `fba test --playwright` falla con `schema.json not found`, ejecutar primero el flujo hasta `fba schema assemble`.
- Si `fba perf` reporta warning en `schema_generation`, revisar que exista `.factory/tasks/index.json`.
- Si `fba doctor --concurrency` detecta `.rollback_state.json` o `.tmp*`, revisar si hubo una interrupcion durante escritura de estado antes de eliminar esos marcadores manualmente.

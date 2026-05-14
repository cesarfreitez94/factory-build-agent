# Testing — M13: Reliability & Quality (Capa 2)

## Requisitos Previos
- Python 3.11+
- Factory Build Agent instalado (`pip install -e .`)
- pytest
- pre-commit (`pip install pre-commit`)
- mypy (`pip install mypy`)
- bandit (`pip install bandit`)
- pip-audit (`pip install pip-audit`)

## Pasos para Probar

### 1. Cache de Validación — Hash-based Cache
**Objetivo**: Verificar que el cache de validación en `.factory/.cache/` funciona correctamente.

**Comandos**:
```bash
# Ejecutar tests del cache
pytest tests/test_cache_validacion.py -v

# Verificar que el cache no rompe gates existentes
pytest tests/test_cache_validacion.py::TestValidationCacheIntegration::test_cache_does_not_break_gates -v
```

**Resultado esperado**:
- 14 tests pass
- Cache hit: cuando el hash no cambió, validación se omite
- Cache miss: cuando el hash cambia, validación se ejecuta
- Coexistencia con diff engine verificada

### 2. Security Scans — Bandit + pip-audit + Secret Detection
**Objetivo**: Verificar que los gates de seguridad fallan-fast cuando hay vulnerabilidades.

**Comandos**:
```bash
# Ejecutar tests de security scans
pytest tests/test_security_scans.py -v

# Verificar gate fail-fast
pytest tests/test_security_scans.py::TestSecurityScanIntegration::test_security_scan_fails_fast -v
```

**Resultado esperado**:
- bandit detecta hardcoded passwords
- pip-audit detecta vulnerabilidades en dependencies
- secret detection encuentra API keys y tokens
- Fail-fast: si algún scan falla, el gate falla

### 3. Pre-commit Hooks — UTF-8, Whitespace, JSON Validation
**Objetivo**: Verificar que los pre-commit hooks están configurados correctamente.

**Comandos**:
```bash
# Ejecutar tests de pre-commit
pytest tests/test_pre_commit.py -v

# Verificar hooks manualmente
pre-commit run --all-files
```

**Resultado esperado**:
- UTF-8 encoding verificado
- Trailing whitespace detectado
- JSON linting pasa
- YAML validation pasa

### 4. Mypy Type Checking — Strict Mode
**Objetivo**: Verificar que mypy pasa en modo strict.

**Comandos**:
```bash
# Ejecutar tests de mypy
pytest tests/test_mypy_strict.py -v

# Verificar mypy directamente
mypy src/fba/ --strict
```

**Resultado esperado**:
- mypy --strict pasa sin errores en src/fba/
- vendor/ excluido de checking

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `pytest tests/test_cache_validacion.py` falla con ImportError | Verificar que `src/fba/` está en Python path |
| `pre-commit run` falla con "repo not reachable" | Verificar conexión a internet, pre-commit puede descargar hooks |
| `mypy --strict` reporta errores en vendor/ | Verificar que vendor/ está en .mypyignore o excludes |
| Security scan falla en código limpio | Algunos tests intencionalmente generan hallazgos para verificar detección |

## Verificación Automatizada

```bash
# Ejecutar todos los tests del milestone M13
pytest tests/test_cache_validacion.py \
       tests/test_security_scans.py \
       tests/test_pre_commit.py \
       tests/test_mypy_strict.py -v

# Suite completa del framework
pytest

# Resultado esperado: 655 passed, 0 failures
```

## Comandos CLI Relacionados

```bash
# Validar con cache (verbose muestra hits/misses)
fba gate --verbose

# Security scan standalone
fba gate --security

# Doctor command para diagnóstico
fba doctor
```

## Integración con Gates

El cache de validación se integra con el sistema de gates:
- `fba gate` ejecuta validación con cache habilitado
- Si el artefacto no cambió desde la última validación, se usa resultado cacheado
- Si el artefacto cambió, se ejecuta validación completa y se actualiza el cache
- El diff engine de M12 coexiste sin conflicto con el cache

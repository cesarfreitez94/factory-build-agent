# Testing - M10: Framework Meta-Development System

## Requisitos Previos

- Python 3.11+ con `fba` CLI instalado.
- OpenCode 0.1.28 o superior.
- Repositorio del framework FBA clonado.
- GitHub CLI (`gh`) autenticado.

---

## Pasos para Probar

### 1. Verificar que los archivos del sistema existen

**Objetivo**: Confirmar que todos los archivos del sistema de meta-agentes estan creados.

**Comando**:
```bash
ls -la .opencode/agents/framework-*.md
ls -la .opencode/commands/fba:fw*.md
ls -la .factory/framework-state.json
ls -la schemas/framework-state.schema.json
ls -la docs/fw-brief-template.md
```

**Resultado esperado**:
```
.opencode/agents/framework-builder.md
.opencode/agents/framework-orchestrator.md
.opencode/agents/framework-planner.md
.opencode/commands/fba:fw.md
.opencode/commands/fba:fw-build.md
.opencode/commands/fba:fw-plan.md
.factory/framework-state.json
schemas/framework-state.schema.json
docs/fw-brief-template.md
```

---

### 2. Validar schema de framework-state.json

**Objetivo**: Confirmar que el schema de validacion funciona.

**Comando**:
```bash
pytest tests/test_framework_state_schema.py -v
```

**Resultado esperado**:
```
17 passed
```

---

### 3. Verificar que framework-state.json valida contra su schema

**Objetivo**: Confirmar que el archivo de estado inicial es valido.

**Comando**:
```bash
python3 -c "
import json
from pathlib import Path
import jsonschema
schema = json.loads(Path('schemas/framework-state.schema.json').read_text())
state = json.loads(Path('.factory/framework-state.json').read_text())
jsonschema.validate(state, schema)
print('✅ OK')
"
```

**Resultado esperado**:
```
✅ OK
```

---

### 4. Probar slash command /fba:fw

**Objetivo**: Verificar que el orchestrator lee el estado y presenta un resumen.

**Pasos**:
1. Abrir OpenCode en el repositorio: `opencode .`
2. Ejecutar: `/fba:fw`

**Resultado esperado**:
- El orchestrator lee ROADMAP.md, framework-state.json, CHANGELOG.md
- Presenta un resumen con: estado del roadmap, ultima sesion, feats pendientes, proximo paso sugerido

---

### 5. Probar slash command /fba:fw-plan

**Objetivo**: Verificar que el planner genera un brief.

**Pasos**:
1. Ejecutar: `/fba:fw-plan "agregar soporte para un nuevo tipo de campo en schema.json"`
2. Verificar que el planner pregunta si hay ambiguedades ("zero suposiciones")
3. Si no hay ambiguedad, debe generar `.factory/fw-brief.md`

**Resultado esperado**:
- `.factory/fw-brief.md` existe con estructura valida
- Contiene: Issue, Branch, Objetivo, Archivos, Tests, Definicion de Done

---

### 6. Probar slash command /fba:fw-build

**Objetivo**: Verificar que el builder ejecuta un brief.

**Pre-condiciones**: Debe existir `.factory/fw-brief.md` (generado en el paso 5).

**Pasos**:
1. Ejecutar: `/fba:fw-build`

**Resultado esperado**:
- El builder lee el brief
- Sigue el flujo de CONTRIBUTING.md:
  - Crea GitHub Issue (si el brief lo indica)
  - Crea feat branch desde el milestone branch
  - Escribe tests primero
  - Implementa
  - Ejecuta pytest
  - Commit con formato `tipo(#XX): descripcion`
  - Abre PR al milestone branch (NO a main)

---

### 7. Verificar que el builder NO hace commit a main

**Objetivo**: Confirmar la restriccion de seguridad mas critica.

**Accion**: Durante `/fba:fw-build`, verificar que los commits y PRs van al milestone branch,
NO a main.

**Resultado esperado**:
- `git log --oneline main` no muestra commits nuevos del builder
- Los PRs abiertos apuntan a `milestone/X.0-*`, no a `main`

---

### 8. Verificar actualizacion de framework-state.json tras build

**Objetivo**: Confirmar que el builder actualiza el estado correctamente.

**Accion**: Despues de ejecutar `/fba:fw-build`, leer `.factory/framework-state.json`.

**Resultado esperado**:
- `active_milestone.feats_done` ha aumentado
- `active_milestone.feats_pending` ya no incluye el feat completado
- `last_session` refleja la ultima accion del builder

---

## Troubleshooting

### "framework-state.json no existe"

El sistema de meta-agentes solo funciona en el repositorio del framework FBA,
no en proyectos Odoo generados con `fba init`.

### "El planner no genero el brief"

El planner tiene instrucciones de NO asumir nada. Si la intencion del usuario
es ambigua, preguntara antes de generar el brief. Responde las preguntas con
detalle.

### "El builder no encuentra el milestone branch"

El builder verificara si el milestone branch existe. Si no, lo creara desde main.
Asegurate de que el nombre del branch en el brief es correcto.

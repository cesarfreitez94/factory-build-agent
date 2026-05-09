# fw-brief-template

Template de referencia para los briefs que genera el `framework-planner`.
El planner produce un archivo `.factory/fw-brief.md` siguiendo esta estructura.

---

```markdown
# Brief: [objetivo en una oracion]

- **Issue**: #[NN] (existente) o "crear issue para: [descripcion]"
- **Branch**: `milestone/X.0-descripcion` o `feat/X.Y-descripcion`
- **Objetivo**: descripcion clara y medible de lo que se va a construir
- **Complejidad**: baja / media / alta

## Archivos

### A crear
- `ruta/exacta/archivo1.ext` — proposito
- `ruta/exacta/archivo2.ext` — proposito

### A modificar
- `ruta/exacta/archivo3.ext` — que se cambia
- `ruta/exacta/archivo4.ext` — que se cambia

## Tests requeridos

- [ ] `tests/test_X.py` — que debe verificar
- [ ] `tests/test_Y.py` — que debe verificar

## Definicion de Done

- [ ] Condicion verificable y objetiva 1
- [ ] Condicion verificable y objetiva 2
- [ ] `pytest` pasa con 0 fallos

## Feats (si hay multiples)

| Orden | Feat | Depende de | Descripcion |
|-------|------|------------|-------------|
| 1 | feat/X.1-desc | — | lo que hace |
| 2 | feat/X.2-desc | feat/X.1 | lo que hace |

## Documentacion a actualizar

- [ ] AGENTS.md — [seccion que cambia]
- [ ] ROADMAP.md — [seccion que cambia]
- [ ] CHANGELOG.md — [entrada de la mejora]
- [ ] docs/testing/mX-*.md — [si aplica]
```

## Notas para el planner

- **Issue**: si ya existe un issue en GitHub, usar `#[NN]`. Si no, indicar que el builder debe crearlo con `"crear issue para: [descripcion]"`.
- **Branch**: si es un feature aislado, usar `feat/X.Y-desc`. Si es un milestone completo, incluir el milestone branch y luego los feat branches.
- **Archivos**: rutas completas y exactas desde la raiz del repo. Nada de "archivos relacionados" o "etc.".
- **Tests**: cada test debe ser especifico. No "tests unitarios" generico.
- **Definicion de Done**: condiciones binarias (pasa/no pasa). Nada subjetivo.
- **Feats**: si el cambio es un solo feat, usar `feat/X.Y-desc`. Si es un milestone con multiples feats, listar todos en orden de ejecucion.
- **Documentacion**: siempre verificar si el cambio requiere actualizar AGENTS.md (cambios de arquitectura), ROADMAP.md (nuevo milestone o cambio de alcance), CHANGELOG.md (todos los cambios).

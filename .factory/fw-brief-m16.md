# Brief: M16 Foundation Intelligence

- **Epic**: #148
- **Primer issue**: #147
- **Milestone branch**: `milestone/16.0-foundation-intelligence`
- **Primer branch de implementacion**: `feat/16.1-module-registry-autoindexado`
- **Objetivo**: dotar al framework de conocimiento Odoo version-aware antes de introducir grafo semantico, extension incremental y gates sobre grafo.
- **Complejidad**: alta
- **Restricciones**:
  - Seguir `CONTRIBUTING.md`: un issue antes de codigo, un feat branch por sub-tarea, PR de feat hacia milestone.
  - No implementar `feat/16.2` hasta que `feat/16.1` este mergeado al branch de milestone.
  - No implementar `feat/16.3` hasta que `feat/16.2` este mergeado al branch de milestone.
  - Mantener compatibilidad con `ModuleRegistry` y `SchemaManager` existentes.
  - No introducir infraestructura externa; persistencia local en archivos del proyecto.

## Contexto actual

- M0-M15 estan completados.
- M16 esta planificado en `ROADMAP.md` y activo en `.factory/framework-state.json`.
- Existe guia de validacion en `docs/testing/m16-foundation-intelligence.md`.
- El branch `milestone/16.0-foundation-intelligence` existe local y remoto.
- feat/16.1 (#147) esta completado y mergeado al milestone branch (commit 350ff40).

## Feats

| Orden | Feat | Issue | Depende de | Que debe lograr |
|-------|------|-------|------------|-----------------|
| 1 | feat/16.1-module-registry-autoindexado | #147 | M15 | Indexar modulos Odoo existentes: manifest, modelos, campos, vistas, controllers, reportes, seguridad, data, crons, wizards y OWL cuando existan. |
| 2 | feat/16.2-odoo-version-layer | por crear | feat/16.1 | Infraestructura de capas de conocimiento Odoo versionado: `base/`, `v18/`, `v17/` con loader/resolver + CLI `fba patterns query`. Sin contenido real de patrones (eso va en 16.3). |
| 3 | feat/16.3-pattern-knowledge-base | #152 | feat/16.2 | Poblar capas base/ y v18/ con 50-80 entradas JSON de patrones Odoo, deprecaciones y novedades para 15 areas tematicas. |

---

## Feat/16.2: odoo-version-layer

- **Issue**: Crear issue en GitHub con titulo: "feat/16.2: Infraestructura de conocimiento Odoo versionado (base/v18/v17) con loader JSON y CLI fba patterns query"
- **Branch**: `feat/16.2-odoo-version-layer` (desde `milestone/16.0-foundation-intelligence`)
- **Objetivo especifico**: Construir la infraestructura de directorios, loader/resolver y CLI que permita organizar conocimiento Odoo en capas versionadas (`base/`, `v18/`, `v17/`). Cada capa contiene archivos JSON con entradas de conocimiento categorizadas (patrones, deprecaciones, novedades). El resolver fusiona base + version-especifica, donde la capa de version sobreescribe a base en caso de conflicto de clave. El contenido real de patrones se construye en feat/16.3; aqui solo se incluye contenido semilla minimo (2-3 entradas de ejemplo) para que la infraestructura sea testeable.
- **Complejidad**: media
- **Restricciones**:
  - Formato de archivos de conocimiento: **JSON** (no YAML, no Markdown).
  - Ubicacion: **`src/fba/odoo_versions/`** (parte del codigo fuente del framework, distribuido con el paquete pip). No se copia a proyectos Odoo via `fba init`.
  - Las capas de version deben ser **auto-descubribles**: agregar un directorio `v19/` debe funcionar sin modificar codigo del loader.
  - El loader debe ser programaticamente usable por `SchemaManager` y otros agentes (importable como modulo Python).
  - La CLI `fba patterns query` debe funcionar al finalizar este feat.
  - Tests automatizados requeridos. No romper tests existentes de registry, schema manager, ni CLI.

### Diseno esperado

#### Estructura de directorios a crear

```
src/fba/odoo_versions/
├── __init__.py
├── version_resolver.py        # Knowledge loader + merge resolver
├── base/                      # Conocimiento version-agnostico
│   ├── patterns.json          # Patrones que aplican a todas las versiones
│   ├── deprecations.json      # (vacio o minimo — las deprecaciones son version-specific)
│   └── novelties.json         # (vacio o minimo)
├── v17/
│   ├── patterns.json
│   ├── deprecations.json
│   └── novelties.json
└── v18/
    ├── patterns.json
    ├── deprecations.json
    └── novelties.json
```

#### Esquema de cada archivo JSON de conocimiento

Cada archivo (ej. `base/patterns.json`) es un objeto JSON donde cada clave es un `key` de consulta y el valor es una entrada de conocimiento con esta estructura:

```json
{
  "model.naming": {
    "key": "model.naming",
    "category": "patterns",
    "title": "Odoo Model Naming Convention",
    "description": "Los nombres de modelo usan dot notation en lowercase...",
    "applies_to": ["model"],
    "since_version": null,
    "deprecated_in": null,
    "examples": ["res.partner", "sale.order"],
    "anti_patterns": ["ResPartner", "saleorder"],
    "related_keys": ["field.naming", "module.structure"]
  }
}
```

- `key`: string (obligatorio) — clave unica de consulta, notacion con puntos (ej. `wizard.confirmation`, `model.naming`).
- `category`: string (obligatorio) — `"patterns"`, `"deprecations"`, o `"novelties"`.
- `title`: string — titulo legible.
- `description`: string — descripcion del patron, deprecacion o novedad.
- `applies_to`: lista de strings — ambitos de aplicacion: `"model"`, `"view"`, `"controller"`, `"wizard"`, `"report"`, `"security"`, `"workflow"`, `"data"`.
- `since_version`: string o null — version de Odoo desde la cual aplica.
- `deprecated_in`: string o null — version en que fue deprecado.
- `examples`: lista de strings — ejemplos del patron.
- `anti_patterns`: lista de strings — anti-patrones relacionados.
- `related_keys`: lista de strings — otras claves de conocimiento relacionadas.

Los campos `examples`, `anti_patterns`, `related_keys` son opcionales y pueden ser listas vacias.

#### Comportamiento del VersionKnowledgeResolver

Debe existir una clase `VersionKnowledgeResolver` en `version_resolver.py` con este contrato:

- **Constructor**: `VersionKnowledgeResolver(odoo_version: str = "18.0")` — recibe version Odoo normalizada (ej. `"18.0"`, `"17.0"`). Determina el directorio raiz de conocimiento via `Path(__file__).parent` (relativo al modulo).
- **Carga**: Al inicializar, carga todos los archivos JSON de `base/` y los fusiona en un diccionario unificado. Luego carga los archivos JSON de la capa de version (ej. `v18/`) y aplica sobreescritura: si una clave existe en ambas capas, la entrada de la version especifica prevalece.
- **Deteccion automatica**: Descubre las capas de version disponibles listando los subdirectorios de `odoo_versions/` que siguen el patron `v<N>/` (ej. `v18/`, `v17/`). No requiere hardcodear versiones.
- **Metodo `query(key: str) -> dict | None`**: Retorna la entrada de conocimiento para la clave dada, o `None` si no existe.
- **Metodo `list_keys(category: str | None = None) -> list[str]`**: Retorna todas las claves disponibles, opcionalmente filtradas por categoria (`"patterns"`, `"deprecations"`, `"novelties"`).
- **Metodo `list_categories() -> list[str]`**: Retorna las categorias con entradas (ej. `["patterns", "deprecations"]`).
- **Propiedad `odoo_version`**: Retorna la version Odoo configurada.
- **Propiedad `available_versions`**: Retorna lista de versiones detectadas en el directorio.

**Logica de merge (version-sobre-base)**:
1. Cargar `base/*.json` → diccionario unificado.
2. Cargar `v<X>/*.json` → diccionario unificado.
3. Para cada clave en el diccionario de version: sobreescribir la entrada en el diccionario base.
4. Si una categoria solo existe en base pero no en version, se preserva la entrada de base.
5. Si una categoria solo existe en version pero no en base, se agrega.

#### Contenido semilla minimo (para testear la infraestructura)

Se deben crear entradas minimas de ejemplo en:

- `base/patterns.json`: 1-2 entradas (ej. `model.naming`, `view.form.structure`).
- `base/deprecations.json`: objeto vacio `{}`.
- `base/novelties.json`: objeto vacio `{}`.
- `v18/deprecations.json`: 1 entrada (ej. algo deprecado en Odoo 18 como `ir.actions.todo`).
- `v18/novelties.json`: 1 entrada (ej. una novedad de Odoo 18 como el nuevo ORM batch).
- `v18/patterns.json`: 1 entrada que sobreescriba una de base (ej. `model.naming` con ejemplos especificos de v18).
- `v17/`: archivos vacios `{}`, para probar que la deteccion de versiones funciona.

**Importante**: El contenido semilla es solo para validar infraestructura. No se espera cubrir todo el conocimiento Odoo en 16.2. La poblacion real de patrones ocurre en 16.3.

#### CLI: grupo `fba patterns`

Agregar al CLI existente (`src/fba/cli.py`) un nuevo grupo de comandos `fba patterns` con:

- **`fba patterns query <key>`**: Consulta una entrada de conocimiento.
  - Opcion `--odoo-version` (default `"18.0"`): Version Odoo para resolver.
  - Opcion `--format` (default `"text"`): Formato de salida (`"text"` o `"json"`).
  - Muestra la entrada resuelta con titulo, descripcion, ejemplos y anti-patrones.
  - Si la clave no existe, muestra mensaje de error y sale con codigo 1.

- **`fba patterns list`**: Lista claves disponibles.
  - Opcion `--odoo-version` (default `"18.0"`).
  - Opcion `--category` (opcional): Filtrar por categoria.
  - Opcion `--format` (default `"text"`): `"text"` o `"json"`.

#### Integracion con el ecosistema existente

- `ModuleRegistry`: Sin cambios. El version layer es independiente pero complementario.
- `SchemaManager`: Sin cambios en 16.2.
- `RegistryIndexer`: Sin cambios.
- `fba registry *`: Sin cambios.

### Archivos involucrados

**A crear:**
- `src/fba/odoo_versions/__init__.py`
- `src/fba/odoo_versions/version_resolver.py`
- `src/fba/odoo_versions/base/patterns.json`
- `src/fba/odoo_versions/base/deprecations.json`
- `src/fba/odoo_versions/base/novelties.json`
- `src/fba/odoo_versions/v17/patterns.json`
- `src/fba/odoo_versions/v17/deprecations.json`
- `src/fba/odoo_versions/v17/novelties.json`
- `src/fba/odoo_versions/v18/patterns.json`
- `src/fba/odoo_versions/v18/deprecations.json`
- `src/fba/odoo_versions/v18/novelties.json`
- `tests/test_odoo_version_layer.py`

**A modificar:**
- `src/fba/cli.py` — Agregar grupo `patterns` con subcomandos `query` y `list`.
- `docs/testing/m16-foundation-intelligence.md` — Actualizar con comandos reales y resultados esperados.

### Tests requeridos

- [ ] El resolver carga entradas desde `base/` (version-agnostico).
- [ ] El resolver carga entradas desde `v18/` y sobreescribe base donde hay conflicto de clave.
- [ ] El resolver carga entradas desde `v17/` sin interferir con v18.
- [ ] `query(key)` retorna la entrada correcta (incluyendo merge version-sobre-base).
- [ ] `query(key)` retorna `None` para clave inexistente.
- [ ] `list_keys()` retorna todas las claves de la version resuelta.
- [ ] `list_keys(category="patterns")` filtra correctamente.
- [ ] `list_categories()` retorna categorias con entradas.
- [ ] `available_versions` detecta automaticamente `v17/` y `v18/`.
- [ ] El contenido semilla en `v18/` sobreescribe correctamente una entrada de `base/` (prueba de merge).
- [ ] CLI `fba patterns query <key>` muestra entrada resuelta en formato texto.
- [ ] CLI `fba patterns query <key> --format json` retorna JSON valido.
- [ ] CLI `fba patterns query <nonexistent>` sale con codigo de error.
- [ ] CLI `fba patterns list` muestra claves disponibles.
- [ ] CLI `fba patterns list --category deprecations` filtra correctamente.
- [ ] CLI `fba patterns list --odoo-version 17.0` usa resolver v17.
- [ ] `pytest` de registry (`test_registry_autoindex.py`, `test_registry_robustez.py`) sigue pasando.
- [ ] `pytest` de schema manager sigue pasando.
- [ ] `fba registry index` e `inspect` siguen funcionando.

### Verificacion minima

```bash
# Tests unitarios del version layer
pytest tests/test_odoo_version_layer.py -v

# Tests existentes no deben romperse
pytest tests/test_registry_autoindex.py tests/test_registry_robustez.py tests/test_schema_manager.py -v

# Test manual de CLI
fba patterns list --odoo-version 18.0
fba patterns query model.naming --odoo-version 18.0
fba patterns query model.naming --odoo-version 18.0 --format json
fba patterns query nonexistent.key --odoo-version 18.0  # debe fallar
fba patterns list --category deprecations --odoo-version 18.0
```

---

## Feat/16.3: pattern-knowledge-base

- **Issue**: #152
- **Branch**: `feat/16.3-pattern-knowledge-base` (desde `milestone/16.0-foundation-intelligence`)
- **Objetivo especifico**: Poblar las capas `base/` y `v18/` del Odoo Pattern Knowledge Base con 50-80 entradas de conocimiento real distribuidas en las categorias `patterns`, `deprecations` y `novelties`, cubriendo 15 areas tematicas de Odoo. Cada entrada debe incluir titulo, descripcion, ejemplos, anti-patrones y referencias cruzadas (`related_keys`). La capa `v17/` se mantiene sin cambios (archivos vacios `{}` como placeholder).
- **Complejidad**: media
- **Restricciones**:
  - Formato de entradas: **JSON** (el mismo esquema definido en 16.2). NO usar YAML ni Markdown.
  - Las entradas existentes (`model.naming`, `view.form.structure`, `ir.actions.todo`, `orm.batch.operations`) deben **preservarse**.
  - La infraestructura (`VersionKnowledgeResolver`, CLI `fba patterns query/list`) no se modifica. Este feat es **solo contenido** + un JSON Schema de validacion.
  - `v17/` permanece con archivos vacios (`{}`). No se agrega contenido.
  - No romper tests existentes. `pytest` completo debe pasar al finalizar.
  - Las entradas deben ser factuales, basadas en documentacion oficial de Odoo y release notes de v18.
  - Cada entrada debe tener `key` unica, `category` correcta, `title`, `description` sustantiva, `applies_to` no vacio, `examples` y `anti_patterns`.

### Alcance del contenido

#### Areas tematicas a cubrir (15 areas)

Cada area debe tener **minimo 3, idealmente 5** entradas distribuidas entre `base/patterns.json`, `v18/patterns.json`, `v18/deprecations.json` y `v18/novelties.json`.

| # | Area | `applies_to` | Tipo de conocimiento |
|---|------|-------------|---------------------|
| 1 | Modelos | `model` | `_name`, `_description`, `_inherit`, `_rec_name`, `_order`, `_sql_constraints`, `_check_company`, campos calculados |
| 2 | Vistas | `view` | Form, Tree/List, Kanban, Search, Calendar, Graph, Pivot, Activity, Gantt, Map, Cohort, Grid |
| 3 | Controllers | `controller` | Rutas HTTP `@route`, CSRF, auth, tipos de response |
| 4 | Wizards | `wizard` | `TransientModel`, vistas de wizard, ciclo de vida, `_transient_vacuum` |
| 5 | Reports | `report` | QWeb reports, PDF, `paperformat`, `report_action` |
| 6 | Seguridad | `security` | `ir.model.access.csv`, `ir.rule` (record rules), grupos, `implied_ids` |
| 7 | Workflows | `workflow` | Server actions, automated actions, scheduled actions, mail templates, `ir.cron` |
| 8 | Datos | `data` | Data files XML/CSV, `noupdate`, `forcecreate`, demo data |
| 9 | Herencia | `model`, `view` | `_inherit`, `_inherits`, delegation inheritance, `_auto`, view inheritance |
| 10 | Menus | `model`, `view` | `ir.ui.menu`, menu items, `menuitem` shortcut, `web_icon` |
| 11 | Acciones | `model` | Window actions, server actions, client actions, URL actions |
| 12 | Permisos | `security` | Groups, access rights (ACL), record rules, `perm_*` |
| 13 | Traducciones | `model` | i18n, `.pot`, `.po`, `_()`, `_lt()`, `ir.translation` |
| 14 | Migraciones | `model` | Migration scripts, `pre-migrate`, `post-migrate`, `migrations/` |
| 15 | Performance | `model` | Prefetch, `read_group`, batch operations, indexes, `search_read` |

#### Distribucion esperada de entradas

| Archivo | Entradas minimas | Entradas ideales | Contenido |
|---------|-----------------|-----------------|-----------|
| `base/patterns.json` | 30 | 45 | Patrones version-agnosticos: 2-3 por cada area |
| `base/deprecations.json` | 0 | 0 | Vacio `{}` |
| `base/novelties.json` | 0 | 0 | Vacio `{}` |
| `v18/patterns.json` | 10 | 15 | Patrones especificos de v18 o sobreescrituras |
| `v18/deprecations.json` | 5 | 10 | Deprecaciones de v18 |
| `v18/novelties.json` | 5 | 10 | Novedades de v18 |
| **Total** | **50** | **80** | |

### Fuentes de conocimiento

| Fuente | URL |
|--------|-----|
| Release notes Odoo 18 | `https://www.odoo.com/odoo-18-release-notes` |
| Developer reference | `https://www.odoo.com/documentation/18.0/developer.html` |
| Backend / ORM | `https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html` |
| Views reference | `https://www.odoo.com/documentation/18.0/developer/reference/backend/views.html` |
| Security reference | `https://www.odoo.com/documentation/18.0/developer/reference/backend/security.html` |
| Actions reference | `https://www.odoo.com/documentation/18.0/developer/reference/backend/actions.html` |
| QWeb Reports | `https://www.odoo.com/documentation/18.0/developer/reference/backend/reports.html` |
| Internacionalizacion | `https://www.odoo.com/documentation/18.0/developer/howtos/translations.html` |
| Migrations guide | `https://www.odoo.com/documentation/18.0/developer/tutorials/upgrade_module.html` |

### Archivos a modificar (al implementar)

| Archivo | Accion |
|---------|--------|
| `src/fba/odoo_versions/base/patterns.json` | Extender con 30-45 entradas. Preservar existentes. |
| `src/fba/odoo_versions/v18/patterns.json` | Extender con 10-15 entradas. Preservar existente. |
| `src/fba/odoo_versions/v18/deprecations.json` | Extender con 5-10 entradas. Preservar existente. |
| `src/fba/odoo_versions/v18/novelties.json` | Extender con 5-10 entradas. Preservar existente. |
| `schemas/knowledge_entry.schema.json` | Nuevo: JSON Schema para validar entradas. |
| `tests/test_knowledge_schema_validation.py` | Nuevo: test que valida cada entrada contra el schema. |

### Archivos que NO se modifican

- `src/fba/odoo_versions/version_resolver.py`
- `src/fba/odoo_versions/__init__.py`
- `src/fba/cli.py`
- `src/fba/odoo_versions/v17/*.json`
- `tests/test_odoo_version_layer.py`

### Tests requeridos (al implementar)

- [ ] Schema validation: cada entrada en `base/` y `v18/` cumple el JSON Schema
- [ ] Key uniqueness: no hay claves duplicadas dentro de un mismo archivo
- [ ] Existing entries preserved: las 4 entradas semilla siguen existiendo
- [ ] v18 override integrity: sobreescrituras tienen `since_version: "18.0"`
- [ ] Category correctness: cada archivo solo contiene entradas de su categoria
- [ ] related_keys cross-references: claves referenciadas existen
- [ ] CLI regression: `test_odoo_version_layer.py` sigue pasando
- [ ] Full suite: `pytest` completo con 0 fallos

### Verificacion (al implementar)

```bash
pytest tests/test_knowledge_schema_validation.py -v
pytest tests/test_odoo_version_layer.py -v
pytest tests/test_registry_autoindex.py tests/test_registry_robustez.py tests/test_schema_manager.py -v
pytest

fba patterns list --odoo-version 18.0
# Debe mostrar ~50-80 claves (vs 4 actuales)

fba patterns list --category deprecations --odoo-version 18.0
# Debe mostrar 5-10 claves (vs 1 actual)

fba patterns list --odoo-version 17.0
# Debe mostrar solo entradas de base (sin deprecations ni novelties)
```

---

## Definicion de Done M16

- [x] #147 (feat/16.1) mergeado al milestone branch.
- [x] #151 (feat/16.2) mergeado al milestone branch.
- [x] Issue para feat/16.3 creado (#152).
- [ ] feat/16.3 mergeado al milestone branch.
- [ ] `docs/testing/m16-foundation-intelligence.md` actualizado.
- [ ] `ROADMAP.md` y `CHANGELOG.md` actualizados al cierre del milestone.
- [ ] `pytest` completo pasa.
- [ ] Usuario valida manualmente antes de abrir PR de milestone a `main`.

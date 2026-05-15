# Testing - M17: Semantic Core

## Requisitos Previos
- Python 3.11+
- Dependencias instaladas con `pip install -e .[dev]`
- Proyecto inicializado con `.factory/`

## Feat 17.1 - Ontologia y validacion del grafo

**Objetivo**: validar que `.factory/graph.json` cumple el schema cerrado de nodos/aristas y que todas las aristas referencian nodos existentes.

**Comando**:
```bash
fba graph validate
```

**Resultado esperado**:
```text
✅ graph: valid
```

Para validar un archivo alternativo:

```bash
fba graph validate --graph /ruta/a/graph.json
```

Si una arista apunta a un nodo inexistente, el comando debe terminar con codigo 1 e indicar `missing source node` o `missing target node`.

## Feat 17.2 - Persistencia y queries del grafo

**Objetivo**: validar que `GraphManager` crea/persiste `.factory/graph.json` y que las queries CLI permiten inspeccionar trazabilidad, impacto y nodos huerfanos.

**Comandos**:
```bash
fba graph trace <uuid>
fba graph impact <uuid>
fba graph orphans
fba graph orphan-nodes
```

**Resultado esperado**:
```text
Trace: <label> (<type>)
Impact: N relationship(s)
Orphan nodes: N
```

Las APIs internas cubiertas por tests son: `full_trace`, `impact_of`, `is_covered`, `orphan_nodes`, `dependents` y `governing_adrs`.

## Feat 17.4 - Stack metodologico de elicitacion

**Objetivo**: validar que `/fba:elicit` usa `--method-stack full` por defecto y que la elicitacion puede emitir nodos semanticos de BABOK, Impact Mapping, Event Storming y Example Mapping sin romper `elicitation.json`.

**Comando manual en un proyecto inicializado**:
```text
/fba:elicit "modulo de control de mantenimiento preventivo de vehiculos"
```

**Resultado esperado**:
- El orquestador usa el `question` tool para preguntas interactivas.
- `.factory/context/elicitation.json` conserva los campos existentes y agrega `methodology_stack.mode = "full"`.
- `.factory/graph_emissions/elicitador.json` incluye refs para requisitos y, cuando aplique, `ACT-01`, `IMP-01`, `DEL-01`, `EVT-01`, `CMD-01`, `AGG-01`, `BR-01` y `EX-01`.
- El evento `elicitation_complete` incluye `method_stack: "full"`.

Para probar el flujo legacy minimo:

```text
/fba:elicit --method-stack babok "modulo de control de mantenimiento preventivo de vehiculos"
```

**Resultado esperado**: el flujo genera el `elicitation.json` compatible sin exigir las secciones extra del stack completo.

## Tests automatizados

```bash
pytest tests/test_semantic_graph.py tests/test_graph_emission.py tests/test_agent_definitions.py tests/test_cli.py
```

## Estado del milestone

Feat 17.4 completa la cobertura de elicitacion semantica de M17. El cierre del milestone requiere validacion manual del usuario antes del PR a `main`.

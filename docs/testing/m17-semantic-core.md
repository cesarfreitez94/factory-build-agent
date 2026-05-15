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

## Tests automatizados

```bash
pytest tests/test_semantic_graph.py
```

## Estado del milestone

Feat 17.2 agrega persistencia local y queries fundamentales. La emision automatica desde agentes queda pendiente para feat 17.3.

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

## Tests automatizados

```bash
pytest tests/test_semantic_graph.py
```

## Estado del milestone

Este documento se inicia con feat 17.1. Los pasos de `trace`, `impact` y queries avanzadas se completaran en feats posteriores de M17.

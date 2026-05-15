# Brief M17 Semantic Core
- Issue epic: #156 — M17 Semantic Core
- Branch milestone: `milestone/17.0-semantic-core`
- Objetivo: construir el nucleo semantico de FBA: grafo tipado persistido en `.factory/graph.json`, ontologia declarativa, queries de traza/impacto/cobertura, protocolo de emision para agentes, y elicitacion enriquecida con BABOK + Impact Mapping + Event Storming + Example Mapping.
- Restricciones: depende de M16 completado; persistencia solo archivo JSON sin DB externa; atomic writes; UUID v4 via StableIdManager; cero breaking changes; agentes declarativos en templates; seguir CONTRIBUTING.md; docs/testing/m17-semantic-core.md obligatorio; actualizar AGENTS.md, ROADMAP.md y CHANGELOG.md cuando aplique.

Feats:
1. `feat/17.1-graph-ontology` — Issue #157. Definir NodeType/EdgeType cerrados, schema `schemas/graph.schema.json`, y comando `fba graph validate`.
2. `feat/17.2-graph-store-queries` — GraphManager, persistencia `.factory/graph.json`, comandos trace/impact/orphans, queries e integracion StableIdManager.
3. `feat/17.3-agent-graph-emission` — protocolo de emision de agentes, templates, consolidacion en graph.json, docs AGENTS.md.
4. `feat/17.4-elicitation-method-stack` — extender elicitador con BABOK + Impact Mapping + Event Storming + Example Mapping, parametro opcional `/fba:elicit`, backward compatibility con elicitation.json y emision al grafo.

Para este ciclo implementa SOLO:
- NodeType/EdgeType cerrados para el grafo semantico.
- `schemas/graph.schema.json`.
- Comando CLI `fba graph validate` que valide schema y referencias source/target de aristas.
- Tests necesarios del feat 17.1.
- Documentacion minima requerida si el cambio arquitectonico lo exige, sin cerrar M17 todavia.

Reglas:
- Sigue CONTRIBUTING.md estrictamente.
- NO hagas commit.
- NO abras PR.
- Ejecuta pytest relevante y, si es viable, pytest completo.
- Si encuentras bloqueo, detente y reporta.

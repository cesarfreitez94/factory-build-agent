import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import jsonschema

from fba.stable_ids import StableIdManager
from fba.state import _atomic_write


NODE_TYPES = (
    "stakeholder",
    "business_need",
    "requirement",
    "functional_requirement",
    "non_functional_requirement",
    "business_rule",
    "user_story",
    "impact",
    "actor",
    "goal",
    "deliverable",
    "event",
    "command",
    "aggregate",
    "policy",
    "read_model",
    "example",
    "acceptance_criterion",
    "odoo_module",
    "odoo_model",
    "odoo_field",
    "odoo_view",
    "odoo_action",
    "external_system",
    "api_endpoint",
    "integration_flow",
    "test_case",
    "quality_attribute",
    "risk",
    "adr",
)

EDGE_TYPES = (
    "derives_from",
    "satisfies",
    "impacts",
    "depends_on",
    "blocks",
    "covers",
    "validates",
    "refines",
    "owned_by",
    "emits",
    "triggers",
    "handled_by",
    "updates",
    "reads",
    "maps_to",
    "integrates_with",
    "implements",
    "tests",
    "documents",
    "governs",
    "related_to",
)


class SemanticGraphError(Exception):
    pass


@dataclass(frozen=True)
class SemanticGraphValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


class SemanticGraphValidator:
    def __init__(self, schema_path: Path | None = None) -> None:
        self.schema_path = schema_path or Path(__file__).resolve().parent.parent.parent / "schemas" / "graph.schema.json"

    def validate_file(self, graph_path: Path) -> SemanticGraphValidationResult:
        if not graph_path.exists():
            raise SemanticGraphError(f"Graph file not found: {graph_path}")
        try:
            graph = json.loads(graph_path.read_text())
        except json.JSONDecodeError as e:
            raise SemanticGraphError(f"Invalid JSON in {graph_path}: {e}") from e
        return self.validate(graph)

    def validate(self, graph: dict[str, Any]) -> SemanticGraphValidationResult:
        errors: list[str] = []
        try:
            schema = json.loads(self.schema_path.read_text())
            jsonschema.validate(graph, schema)
        except jsonschema.ValidationError as e:
            errors.append(f"schema validation failed: {e.message}")
            return SemanticGraphValidationResult(valid=False, errors=errors)
        except json.JSONDecodeError as e:
            raise SemanticGraphError(f"Invalid graph schema JSON: {e}") from e
        except FileNotFoundError as e:
            raise SemanticGraphError(f"Graph schema not found: {self.schema_path}") from e

        node_ids = [node["id"] for node in graph.get("nodes", [])]
        seen: set[str] = set()
        duplicates_set: set[str] = set()
        for node_id in node_ids:
            if node_id in seen:
                duplicates_set.add(node_id)
            seen.add(node_id)
        duplicates = sorted(duplicates_set)
        for node_id in duplicates:
            errors.append(f"duplicate node id: {node_id}")

        known_nodes = set(node_ids)
        edge_ids: set[str] = set()
        for edge in graph.get("edges", []):
            edge_id = edge["id"]
            if edge_id in edge_ids:
                errors.append(f"duplicate edge id: {edge_id}")
            edge_ids.add(edge_id)
            source = edge["source"]
            target = edge["target"]
            if source not in known_nodes:
                errors.append(f"edge {edge_id} has missing source node: {source}")
            if target not in known_nodes:
                errors.append(f"edge {edge_id} has missing target node: {target}")

        return SemanticGraphValidationResult(valid=not errors, errors=errors)


class GraphManager:
    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.factory_dir = project_dir / ".factory"
        self.graph_path = self.factory_dir / "graph.json"
        self.validator = SemanticGraphValidator()

    def load(self) -> dict[str, Any]:
        if not self.factory_dir.exists():
            raise SemanticGraphError(f"Factory directory not found: {self.factory_dir}")
        if not self.graph_path.exists():
            return self.empty_graph()
        try:
            graph = cast(dict[str, Any], json.loads(self.graph_path.read_text()))
        except json.JSONDecodeError as e:
            raise SemanticGraphError(f"Invalid JSON in {self.graph_path}: {e}") from e
        result = self.validator.validate(graph)
        if not result.valid:
            raise SemanticGraphError("Invalid semantic graph: " + "; ".join(result.errors))
        return graph

    def save(self, graph: dict[str, Any]) -> None:
        graph["generated_at"] = datetime.now(timezone.utc).isoformat()
        result = self.validator.validate(graph)
        if not result.valid:
            raise SemanticGraphError("Invalid semantic graph: " + "; ".join(result.errors))
        _atomic_write(self.graph_path, json.dumps(graph, indent=2, ensure_ascii=False) + "\n")

    def ensure_graph(self) -> dict[str, Any]:
        graph = self.load()
        if not self.graph_path.exists():
            self.save(graph)
        return graph

    def add_node(
        self,
        node_type: str,
        label: str,
        description: str | None = None,
        source_artifact: str | None = None,
        properties: dict[str, Any] | None = None,
        node_id: str | None = None,
    ) -> dict[str, Any]:
        graph = self.load()
        node: dict[str, Any] = {
            "id": node_id or StableIdManager.generate_id(),
            "type": node_type,
            "label": label,
        }
        if description:
            node["description"] = description
        if source_artifact:
            node["source_artifact"] = source_artifact
        if properties:
            node["properties"] = properties
        graph.setdefault("nodes", []).append(node)
        self.save(graph)
        return node

    def add_edge(
        self,
        edge_type: str,
        source: str,
        target: str,
        label: str | None = None,
        properties: dict[str, Any] | None = None,
        edge_id: str | None = None,
    ) -> dict[str, Any]:
        graph = self.load()
        edge: dict[str, Any] = {
            "id": edge_id or StableIdManager.generate_id(),
            "type": edge_type,
            "source": source,
            "target": target,
        }
        if label:
            edge["label"] = label
        if properties:
            edge["properties"] = properties
        graph.setdefault("edges", []).append(edge)
        self.save(graph)
        return edge

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        graph = self.load()
        return self._node_map(graph).get(node_id)

    def full_trace(self, node_id: str) -> dict[str, Any]:
        graph = self.load()
        nodes = self._node_map(graph)
        self._require_node(nodes, node_id)
        incoming = [edge for edge in graph["edges"] if edge["target"] == node_id]
        outgoing = [edge for edge in graph["edges"] if edge["source"] == node_id]
        return {
            "node": nodes[node_id],
            "incoming": self._edge_records(incoming, nodes),
            "outgoing": self._edge_records(outgoing, nodes),
            "upstream": self._walk(graph, node_id, direction="incoming"),
            "downstream": self._walk(graph, node_id, direction="outgoing"),
        }

    def impact_of(self, node_id: str) -> list[dict[str, Any]]:
        graph = self.load()
        nodes = self._node_map(graph)
        self._require_node(nodes, node_id)
        return self._walk(graph, node_id, direction="outgoing")

    def dependents(self, node_id: str) -> list[dict[str, Any]]:
        graph = self.load()
        nodes = self._node_map(graph)
        self._require_node(nodes, node_id)
        edges = [edge for edge in graph["edges"] if edge["target"] == node_id and edge["type"] == "depends_on"]
        return self._edge_records(edges, nodes)

    def governing_adrs(self, node_id: str) -> list[dict[str, Any]]:
        graph = self.load()
        nodes = self._node_map(graph)
        self._require_node(nodes, node_id)
        edges = [edge for edge in graph["edges"] if edge["target"] == node_id and edge["type"] == "governs"]
        return [record for record in self._edge_records(edges, nodes) if record["source"]["type"] == "adr"]

    def is_covered(self, node_id: str) -> bool:
        graph = self.load()
        nodes = self._node_map(graph)
        self._require_node(nodes, node_id)
        coverage_edges = {"covers", "tests", "validates"}
        return any(edge["target"] == node_id and edge["type"] in coverage_edges for edge in graph["edges"])

    def orphan_nodes(self) -> list[dict[str, Any]]:
        graph = self.load()
        connected = set()
        for edge in graph["edges"]:
            connected.add(edge["source"])
            connected.add(edge["target"])
        return [node for node in graph["nodes"] if node["id"] not in connected]

    @staticmethod
    def empty_graph() -> dict[str, Any]:
        return {"version": "1.0", "nodes": [], "edges": []}

    @staticmethod
    def _node_map(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {node["id"]: node for node in graph.get("nodes", [])}

    @staticmethod
    def _require_node(nodes: dict[str, dict[str, Any]], node_id: str) -> None:
        if node_id not in nodes:
            raise SemanticGraphError(f"Graph node not found: {node_id}")

    def _walk(self, graph: dict[str, Any], node_id: str, direction: str) -> list[dict[str, Any]]:
        nodes = self._node_map(graph)
        visited: set[str] = {node_id}
        records: list[dict[str, Any]] = []
        frontier = [node_id]
        while frontier:
            current = frontier.pop(0)
            if direction == "outgoing":
                edges = [edge for edge in graph["edges"] if edge["source"] == current]
                next_key = "target"
            else:
                edges = [edge for edge in graph["edges"] if edge["target"] == current]
                next_key = "source"
            for edge in edges:
                next_id = edge[next_key]
                if next_id in visited:
                    continue
                visited.add(next_id)
                frontier.append(next_id)
                records.extend(self._edge_records([edge], nodes))
        return records

    @staticmethod
    def _edge_records(edges: list[dict[str, Any]], nodes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "edge": edge,
                "source": nodes[edge["source"]],
                "target": nodes[edge["target"]],
            }
            for edge in edges
        ]

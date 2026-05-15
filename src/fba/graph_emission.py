import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from fba.semantic_graph import EDGE_TYPES, NODE_TYPES, GraphManager, SemanticGraphError
from fba.stable_ids import StableIdManager


class GraphEmissionError(Exception):
    pass


@dataclass(frozen=True)
class GraphEmissionResult:
    emissions: int = 0
    nodes_added: int = 0
    nodes_updated: int = 0
    edges_added: int = 0
    edges_skipped: int = 0
    warnings: list[str] = field(default_factory=list)


class GraphEmissionManager:
    def __init__(self, project_dir: Path, emissions_dir: Path | None = None) -> None:
        self.project_dir = project_dir
        self.emissions_dir = emissions_dir or project_dir / ".factory" / "graph_emissions"
        self.graph_manager = GraphManager(project_dir)

    def consolidate(self) -> GraphEmissionResult:
        graph = self.graph_manager.load()
        node_by_id = {node["id"]: node for node in graph.get("nodes", [])}
        node_by_ref = self._node_ref_map(graph)
        edge_keys = {(edge["type"], edge["source"], edge["target"]) for edge in graph.get("edges", [])}
        edge_ids = {edge["id"] for edge in graph.get("edges", [])}
        stats = {
            "emissions": 0,
            "nodes_added": 0,
            "nodes_updated": 0,
            "edges_added": 0,
            "edges_skipped": 0,
        }
        warnings: list[str] = []

        for emission_path, emission in self._load_emissions():
            stats["emissions"] += 1
            agent = self._required_string(emission, "agent", emission_path)
            artifact = emission.get("artifact")
            if artifact is not None and not isinstance(artifact, str):
                raise GraphEmissionError(f"{emission_path}: artifact must be a string")

            for raw_node in emission.get("nodes", []):
                node = self._normalize_node(raw_node, agent, artifact, emission_path)
                ref = cast(dict[str, Any], node.get("properties", {})).get("ref")
                existing = node_by_id.get(node["id"])
                if existing is None and isinstance(ref, str):
                    existing = node_by_ref.get(ref)
                if existing is None:
                    graph.setdefault("nodes", []).append(node)
                    node_by_id[node["id"]] = node
                    if isinstance(ref, str):
                        node_by_ref[ref] = node
                    stats["nodes_added"] += 1
                    continue
                self._merge_node(existing, node)
                node_by_id[existing["id"]] = existing
                if isinstance(ref, str):
                    node_by_ref[ref] = existing
                stats["nodes_updated"] += 1

            for raw_edge in emission.get("edges", []):
                edge = self._normalize_edge(raw_edge, node_by_id, node_by_ref, emission_path)
                key = (edge["type"], edge["source"], edge["target"])
                if edge["id"] in edge_ids or key in edge_keys:
                    stats["edges_skipped"] += 1
                    continue
                graph.setdefault("edges", []).append(edge)
                edge_ids.add(edge["id"])
                edge_keys.add(key)
                stats["edges_added"] += 1

        self.graph_manager.save(graph)
        return GraphEmissionResult(**stats, warnings=warnings)

    def _load_emissions(self) -> list[tuple[Path, dict[str, Any]]]:
        if not self.emissions_dir.exists():
            return []
        emissions: list[tuple[Path, dict[str, Any]]] = []
        for path in sorted(self.emissions_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text())
            except json.JSONDecodeError as e:
                raise GraphEmissionError(f"Invalid JSON in {path}: {e}") from e
            if isinstance(payload, list):
                for item in payload:
                    if not isinstance(item, dict):
                        raise GraphEmissionError(f"{path}: emission entries must be objects")
                    emissions.append((path, item))
            elif isinstance(payload, dict):
                emissions.append((path, payload))
            else:
                raise GraphEmissionError(f"{path}: emission payload must be an object or array")
        return emissions

    def _normalize_node(
        self,
        raw_node: dict[str, Any],
        agent: str,
        artifact: str | None,
        path: Path,
    ) -> dict[str, Any]:
        if not isinstance(raw_node, dict):
            raise GraphEmissionError(f"{path}: node entries must be objects")
        node_type = self._required_string(raw_node, "type", path)
        if node_type not in NODE_TYPES:
            raise GraphEmissionError(f"{path}: unknown node type: {node_type}")
        label = self._required_string(raw_node, "label", path)
        node = {
            "id": raw_node.get("id") or StableIdManager.generate_id(),
            "type": node_type,
            "label": label,
        }
        for key in ("description", "source_artifact"):
            value = raw_node.get(key)
            if value is not None:
                if not isinstance(value, str):
                    raise GraphEmissionError(f"{path}: node {key} must be a string")
                node[key] = value
        if artifact and "source_artifact" not in node:
            node["source_artifact"] = artifact
        properties = raw_node.get("properties", {})
        if not isinstance(properties, dict):
            raise GraphEmissionError(f"{path}: node properties must be an object")
        merged_properties = {**properties, "agent": agent}
        if "ref" in raw_node:
            ref = raw_node["ref"]
            if not isinstance(ref, str) or not ref:
                raise GraphEmissionError(f"{path}: node ref must be a non-empty string")
            merged_properties["ref"] = ref
        node["properties"] = merged_properties
        return node

    def _normalize_edge(
        self,
        raw_edge: dict[str, Any],
        node_by_id: dict[str, dict[str, Any]],
        node_by_ref: dict[str, dict[str, Any]],
        path: Path,
    ) -> dict[str, Any]:
        if not isinstance(raw_edge, dict):
            raise GraphEmissionError(f"{path}: edge entries must be objects")
        edge_type = self._required_string(raw_edge, "type", path)
        if edge_type not in EDGE_TYPES:
            raise GraphEmissionError(f"{path}: unknown edge type: {edge_type}")
        source = self._resolve_endpoint(self._required_string(raw_edge, "source", path), node_by_id, node_by_ref, path)
        target = self._resolve_endpoint(self._required_string(raw_edge, "target", path), node_by_id, node_by_ref, path)
        edge = {
            "id": raw_edge.get("id") or StableIdManager.generate_id(),
            "type": edge_type,
            "source": source,
            "target": target,
        }
        label = raw_edge.get("label")
        if label is not None:
            if not isinstance(label, str):
                raise GraphEmissionError(f"{path}: edge label must be a string")
            edge["label"] = label
        properties = raw_edge.get("properties")
        if properties is not None:
            if not isinstance(properties, dict):
                raise GraphEmissionError(f"{path}: edge properties must be an object")
            edge["properties"] = properties
        return edge

    @staticmethod
    def _required_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise GraphEmissionError(f"{path}: missing required string field: {key}")
        return value

    @staticmethod
    def _node_ref_map(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
        refs: dict[str, dict[str, Any]] = {}
        for node in graph.get("nodes", []):
            properties = node.get("properties", {})
            if isinstance(properties, dict) and isinstance(properties.get("ref"), str):
                refs[properties["ref"]] = node
        return refs

    @staticmethod
    def _merge_node(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
        existing["label"] = incoming["label"]
        for key in ("description", "source_artifact"):
            if key in incoming:
                existing[key] = incoming[key]
        existing_properties = existing.setdefault("properties", {})
        incoming_properties = incoming.get("properties", {})
        if isinstance(existing_properties, dict) and isinstance(incoming_properties, dict):
            existing_properties.update(incoming_properties)

    @staticmethod
    def _resolve_endpoint(
        endpoint: str,
        node_by_id: dict[str, dict[str, Any]],
        node_by_ref: dict[str, dict[str, Any]],
        path: Path,
    ) -> str:
        if endpoint in node_by_id:
            return endpoint
        if endpoint in node_by_ref:
            return cast(str, node_by_ref[endpoint]["id"])
        raise GraphEmissionError(f"{path}: edge endpoint does not match any node id or ref: {endpoint}")


def consolidate_graph_emissions(project_dir: Path, emissions_dir: Path | None = None) -> GraphEmissionResult:
    try:
        return GraphEmissionManager(project_dir, emissions_dir=emissions_dir).consolidate()
    except SemanticGraphError as e:
        raise GraphEmissionError(str(e)) from e

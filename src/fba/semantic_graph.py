import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema


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

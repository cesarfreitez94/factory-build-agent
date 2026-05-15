import json
from pathlib import Path

import pytest
import jsonschema
from click.testing import CliRunner

from fba.cli import main
from fba.semantic_graph import EDGE_TYPES, NODE_TYPES, SemanticGraphValidator


def _uuid(value: int) -> str:
    return f"00000000-0000-4000-8000-{value:012d}"


def _graph() -> dict:
    return {
        "version": "1.0",
        "nodes": [
            {"id": _uuid(1), "type": "stakeholder", "label": "Usuario clave"},
            {"id": _uuid(2), "type": "functional_requirement", "label": "RF-001"},
        ],
        "edges": [
            {
                "id": _uuid(3),
                "type": "derives_from",
                "source": _uuid(2),
                "target": _uuid(1),
            }
        ],
    }


def test_graph_schema_accepts_valid_semantic_graph():
    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "graph.schema.json"
    schema = json.loads(schema_path.read_text())

    jsonschema.validate(_graph(), schema)


def test_graph_schema_rejects_unknown_node_and_edge_types():
    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "graph.schema.json"
    schema = json.loads(schema_path.read_text())
    graph = _graph()
    graph["nodes"][0]["type"] = "unknown_node"
    graph["edges"][0]["type"] = "unknown_edge"

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(graph, schema)


def test_node_and_edge_type_sets_are_closed_and_cover_m17_domains():
    assert "stakeholder" in NODE_TYPES
    assert "impact" in NODE_TYPES
    assert "event" in NODE_TYPES
    assert "example" in NODE_TYPES
    assert "odoo_model" in NODE_TYPES
    assert "api_endpoint" in NODE_TYPES
    assert "quality_attribute" in NODE_TYPES
    assert "derives_from" in EDGE_TYPES
    assert "covers" in EDGE_TYPES
    assert "integrates_with" in EDGE_TYPES


def test_semantic_graph_validator_rejects_dangling_edge_references(tmp_path):
    graph = _graph()
    graph["edges"][0]["target"] = _uuid(99)
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph))

    result = SemanticGraphValidator().validate_file(graph_path)

    assert not result.valid
    assert "target" in result.errors[0]
    assert _uuid(99) in result.errors[0]


def test_graph_validate_cli_passes_for_valid_graph(tmp_path):
    project = tmp_path / "project"
    factory = project / ".factory"
    factory.mkdir(parents=True)
    (factory / "graph.json").write_text(json.dumps(_graph()))

    result = CliRunner().invoke(main, ["graph", "validate", "-d", str(project)])

    assert result.exit_code == 0
    assert "graph: valid" in result.output


def test_graph_validate_cli_fails_for_missing_reference(tmp_path):
    project = tmp_path / "project"
    factory = project / ".factory"
    factory.mkdir(parents=True)
    graph = _graph()
    graph["edges"][0]["source"] = _uuid(42)
    (factory / "graph.json").write_text(json.dumps(graph))

    result = CliRunner().invoke(main, ["graph", "validate", "-d", str(project)])

    assert result.exit_code == 1
    assert "missing source node" in result.output

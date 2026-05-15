import json
from pathlib import Path

import pytest
import jsonschema
from click.testing import CliRunner

from fba.cli import main
from fba.semantic_graph import EDGE_TYPES, NODE_TYPES, GraphManager, SemanticGraphValidator


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


def _query_graph() -> dict:
    return {
        "version": "1.0",
        "nodes": [
            {"id": _uuid(1), "type": "functional_requirement", "label": "RF-001"},
            {"id": _uuid(2), "type": "odoo_model", "label": "sale.order"},
            {"id": _uuid(3), "type": "test_case", "label": "test_sale_order"},
            {"id": _uuid(4), "type": "adr", "label": "ADR-001"},
            {"id": _uuid(5), "type": "risk", "label": "Riesgo aislado"},
        ],
        "edges": [
            {"id": _uuid(10), "type": "implements", "source": _uuid(1), "target": _uuid(2)},
            {"id": _uuid(11), "type": "covers", "source": _uuid(3), "target": _uuid(1)},
            {"id": _uuid(12), "type": "governs", "source": _uuid(4), "target": _uuid(2)},
            {"id": _uuid(13), "type": "depends_on", "source": _uuid(2), "target": _uuid(1)},
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


def test_graph_manager_persists_empty_graph_atomically(tmp_path):
    project = tmp_path / "project"
    (project / ".factory").mkdir(parents=True)

    graph = GraphManager(project).ensure_graph()

    assert graph["version"] == "1.0"
    persisted = json.loads((project / ".factory" / "graph.json").read_text())
    assert persisted["nodes"] == []
    assert persisted["edges"] == []
    assert "generated_at" in persisted


def test_graph_manager_adds_nodes_and_edges_with_uuid_v4(tmp_path):
    project = tmp_path / "project"
    (project / ".factory").mkdir(parents=True)
    manager = GraphManager(project)

    req = manager.add_node("functional_requirement", "RF-001")
    model = manager.add_node("odoo_model", "sale.order")
    edge = manager.add_edge("implements", req["id"], model["id"])

    graph = json.loads((project / ".factory" / "graph.json").read_text())
    assert graph["nodes"] == [req, model]
    assert graph["edges"] == [edge]
    jsonschema.validate(graph, json.loads((Path(__file__).resolve().parent.parent / "schemas" / "graph.schema.json").read_text()))


def test_graph_manager_queries_trace_impact_coverage_orphans_dependents_and_adrs(tmp_path):
    project = tmp_path / "project"
    factory = project / ".factory"
    factory.mkdir(parents=True)
    (factory / "graph.json").write_text(json.dumps(_query_graph()))
    manager = GraphManager(project)

    trace = manager.full_trace(_uuid(1))
    impact = manager.impact_of(_uuid(1))
    orphans = manager.orphan_nodes()
    dependents = manager.dependents(_uuid(1))
    governing_adrs = manager.governing_adrs(_uuid(2))

    assert trace["node"]["label"] == "RF-001"
    assert len(trace["incoming"]) == 2
    assert [record["target"]["label"] for record in impact] == ["sale.order"]
    assert manager.is_covered(_uuid(1))
    assert [node["label"] for node in orphans] == ["Riesgo aislado"]
    assert [record["source"]["label"] for record in dependents] == ["sale.order"]
    assert [record["source"]["label"] for record in governing_adrs] == ["ADR-001"]


def test_graph_cli_trace_impact_and_orphans(tmp_path):
    project = tmp_path / "project"
    factory = project / ".factory"
    factory.mkdir(parents=True)
    (factory / "graph.json").write_text(json.dumps(_query_graph()))
    runner = CliRunner()

    trace_result = runner.invoke(main, ["graph", "trace", _uuid(1), "-d", str(project)])
    impact_result = runner.invoke(main, ["graph", "impact", _uuid(1), "-d", str(project)])
    orphans_result = runner.invoke(main, ["graph", "orphans", "-d", str(project)])

    assert trace_result.exit_code == 0
    assert "Incoming: 2" in trace_result.output
    assert impact_result.exit_code == 0
    assert "RF-001 --implements--> sale.order" in impact_result.output
    assert orphans_result.exit_code == 0
    assert "Riesgo aislado" in orphans_result.output

import json

from click.testing import CliRunner

from fba.cli import main
from fba.graph_emission import GraphEmissionError, GraphEmissionManager


def _project(tmp_path):
    project = tmp_path / "project"
    (project / ".factory" / "graph_emissions").mkdir(parents=True)
    return project


def _write_emission(project, name, payload):
    path = project / ".factory" / "graph_emissions" / name
    path.write_text(json.dumps(payload))
    return path


def test_graph_emission_consolidates_agent_nodes_and_edges(tmp_path):
    project = _project(tmp_path)
    _write_emission(
        project,
        "documentador.json",
        {
            "agent": "documentador",
            "artifact": ".factory/prd.json",
            "nodes": [
                {"ref": "RF-01", "type": "functional_requirement", "label": "Registrar vehiculos"},
                {"ref": "CA-01", "type": "acceptance_criterion", "label": "Crear vehiculo"},
            ],
            "edges": [
                {"type": "validates", "source": "CA-01", "target": "RF-01"},
            ],
        },
    )

    result = GraphEmissionManager(project).consolidate()

    graph = json.loads((project / ".factory" / "graph.json").read_text())
    assert result.emissions == 1
    assert result.nodes_added == 2
    assert result.edges_added == 1
    assert [node["properties"]["ref"] for node in graph["nodes"]] == ["RF-01", "CA-01"]
    assert graph["edges"][0]["source"] == graph["nodes"][1]["id"]
    assert graph["edges"][0]["target"] == graph["nodes"][0]["id"]


def test_graph_emission_is_idempotent_by_ref_and_edge_key(tmp_path):
    project = _project(tmp_path)
    payload = {
        "agent": "planificador",
        "artifact": ".factory/sdd.json",
        "nodes": [
            {"ref": "RF-01", "type": "functional_requirement", "label": "Registrar activos"},
            {"ref": "model:fleet.vehicle", "type": "odoo_model", "label": "fleet.vehicle"},
        ],
        "edges": [
            {"type": "implements", "source": "RF-01", "target": "model:fleet.vehicle"},
        ],
    }
    _write_emission(project, "planificador.json", payload)

    first = GraphEmissionManager(project).consolidate()
    second = GraphEmissionManager(project).consolidate()

    graph = json.loads((project / ".factory" / "graph.json").read_text())
    assert first.nodes_added == 2
    assert second.nodes_added == 0
    assert second.nodes_updated == 2
    assert second.edges_skipped == 1
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1


def test_graph_emission_rejects_unknown_edge_endpoint(tmp_path):
    project = _project(tmp_path)
    _write_emission(
        project,
        "tester.json",
        {
            "agent": "tester_qa",
            "nodes": [{"ref": "TC-01", "type": "test_case", "label": "Prueba CRUD"}],
            "edges": [{"type": "tests", "source": "TC-01", "target": "RF-404"}],
        },
    )

    try:
        GraphEmissionManager(project).consolidate()
    except GraphEmissionError as e:
        assert "RF-404" in str(e)
    else:
        raise AssertionError("GraphEmissionError was not raised")


def test_graph_consolidate_cli_reports_summary(tmp_path):
    project = _project(tmp_path)
    _write_emission(
        project,
        "elicitador.json",
        {
            "agent": "elicitador",
            "nodes": [{"ref": "stakeholder:operador", "type": "stakeholder", "label": "Operador"}],
            "edges": [],
        },
    )

    result = CliRunner().invoke(main, ["graph", "consolidate", "-d", str(project)])

    assert result.exit_code == 0
    assert "Graph emissions consolidated" in result.output
    assert "Nodes added: 1" in result.output

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


def test_elicitador_full_method_stack_emission_consolidates(tmp_path):
    project = _project(tmp_path)
    _write_emission(
        project,
        "elicitador.json",
        {
            "agent": "elicitador",
            "artifact": ".factory/context/elicitation.json",
            "nodes": [
                {"ref": "goal:primary", "type": "goal", "label": "Reducir tiempos de mantenimiento"},
                {"ref": "ACT-01", "type": "actor", "label": "Jefe de flota"},
                {"ref": "IMP-01", "type": "impact", "label": "Planificar mantenimiento preventivo"},
                {"ref": "DEL-01", "type": "deliverable", "label": "Calendario de mantenimientos"},
                {"ref": "RF-01", "type": "functional_requirement", "label": "Programar mantenimiento"},
                {"ref": "EVT-01", "type": "event", "label": "Mantenimiento vencido"},
                {"ref": "CMD-01", "type": "command", "label": "Programar mantenimiento"},
                {"ref": "AGG-01", "type": "aggregate", "label": "Vehiculo"},
                {"ref": "POL-01", "type": "policy", "label": "Notificar vencimiento"},
                {"ref": "RM-01", "type": "read_model", "label": "Tablero de mantenimiento"},
                {"ref": "BR-01", "type": "business_rule", "label": "Kilometraje requerido"},
                {"ref": "EX-01", "type": "example", "label": "Vehiculo supera umbral"},
            ],
            "edges": [
                {"type": "impacts", "source": "ACT-01", "target": "goal:primary"},
                {"type": "satisfies", "source": "DEL-01", "target": "IMP-01"},
                {"type": "maps_to", "source": "DEL-01", "target": "RF-01"},
                {"type": "triggers", "source": "CMD-01", "target": "EVT-01"},
                {"type": "handled_by", "source": "CMD-01", "target": "AGG-01"},
                {"type": "triggers", "source": "EVT-01", "target": "POL-01"},
                {"type": "reads", "source": "RM-01", "target": "AGG-01"},
                {"type": "validates", "source": "EX-01", "target": "BR-01"},
            ],
        },
    )

    result = GraphEmissionManager(project).consolidate()

    graph = json.loads((project / ".factory" / "graph.json").read_text())
    assert result.nodes_added == 12
    assert result.edges_added == 8
    assert {node["type"] for node in graph["nodes"]} >= {
        "goal",
        "actor",
        "impact",
        "deliverable",
        "event",
        "command",
        "aggregate",
        "policy",
        "read_model",
        "business_rule",
        "example",
    }

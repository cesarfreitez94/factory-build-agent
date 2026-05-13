"""Tests for workflow generation in SchemaManager."""

import json
from pathlib import Path
import tempfile

import pytest

from fba.schema_manager import SchemaManager


def _setup_project_with_workflow(project_dir: Path):
    """Create a minimal project with workflow task files."""
    factory_dir = project_dir / ".factory"
    tasks_dir = factory_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    index = {
        "module_name": "vehicle_registry",
        "total_tasks": 2,
        "tasks": [
            {
                "id": "T001",
                "name": "Modelos",
                "file": "T001-modelos.json",
                "dependencies": [],
                "order": 1,
                "estimated_effort": "high",
                "sdd_components": ["models.vehicle"],
            },
            {
                "id": "T002",
                "name": "Workflow Approval",
                "file": "T002-workflow.json",
                "dependencies": ["T001"],
                "order": 2,
                "estimated_effort": "medium",
                "sdd_components": ["workflow.vehicle_approval"],
            },
        ],
    }
    (tasks_dir / "index.json").write_text(json.dumps(index, indent=2))

    t001 = {
        "id": "T001",
        "name": "Modelos",
        "description": "Generar modelos Odoo",
        "components": [
            {
                "type": "model",
                "name": "vehicle.vehicle",
                "description": "Modelo de vehiculo",
                "fields": [
                    {"name": "name", "type": "Char", "label": "Nombre", "required": True},
                ],
                "sdd_reference": "models.vehicle",
            },
        ],
        "files_to_generate": ["models/__init__.py", "models/vehicle.py"],
        "dependencies": [],
    }
    (tasks_dir / "T001-modelos.json").write_text(json.dumps(t001, indent=2))

    t002 = {
        "id": "T002",
        "name": "Workflow Approval",
        "description": "Workflow de aprobacion de vehiculos con estados y transiciones.",
        "components": [
            {
                "type": "workflow",
                "name": "vehicle.workflow.approval",
                "model": "vehicle.vehicle",
                "states": [
                    {"name": "draft", "description": "Borrador"},
                    {"name": "pending", "description": "Pendiente de aprobacion"},
                    {"name": "approved", "description": "Aprobado"},
                    {"name": "rejected", "description": "Rechazado"},
                ],
                "signals": [
                    {"name": "submit", "description": "Enviar para aprobacion"},
                    {"name": "approve", "description": "Aprobar"},
                    {"name": "reject", "description": "Rechazar"},
                ],
                "transitions": [
                    {"from_state": "draft", "to_state": "pending", "signal": "submit"},
                    {"from_state": "pending", "to_state": "approved", "signal": "approve", "condition": "True"},
                    {"from_state": "pending", "to_state": "rejected", "signal": "reject"},
                ],
                "sdd_reference": "workflow.vehicle_approval",
            },
        ],
        "files_to_generate": ["models/vehicle.py"],
        "dependencies": ["T001"],
    }
    (tasks_dir / "T002-workflow.json").write_text(json.dumps(t002, indent=2))

    sdd = {
        "module_name": "vehicle_registry",
        "version": "18.0.1.0.0",
        "summary": "Vehicle registry module",
    }
    (factory_dir / "sdd.json").write_text(json.dumps(sdd, indent=2))


def test_workflow_component_recognized():
    """Workflow component type is recognized by SchemaManager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        _setup_project_with_workflow(project_dir)

        sm = SchemaManager(project_dir)
        assert "workflow" in sm.IMPLEMENTED_TYPES


def test_workflow_assembly():
    """SchemaManager correctly assembles workflow components from task files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        _setup_project_with_workflow(project_dir)

        sm = SchemaManager(project_dir)
        result = sm.assemble()

        assert result.success, f"Assembly failed: {result.error_messages}"
        assert "workflows" in result.schema
        workflows = result.schema["workflows"]
        assert len(workflows) == 1

        wf = workflows[0]
        assert wf["name"] == "vehicle.workflow.approval"
        assert wf["model"] == "vehicle.vehicle"
        assert len(wf["states"]) == 4
        assert len(wf["signals"]) == 3
        assert len(wf["transitions"]) == 3


def test_workflow_states():
    """Workflow states are correctly assembled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        _setup_project_with_workflow(project_dir)

        sm = SchemaManager(project_dir)
        result = sm.assemble()

        wf = result.schema["workflows"][0]
        state_names = [s["name"] for s in wf["states"]]
        assert "draft" in state_names
        assert "pending" in state_names
        assert "approved" in state_names
        assert "rejected" in state_names


def test_workflow_transitions():
    """Workflow transitions map signals to state changes correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        _setup_project_with_workflow(project_dir)

        sm = SchemaManager(project_dir)
        result = sm.assemble()

        wf = result.schema["workflows"][0]
        transitions = wf["transitions"]

        submit_trans = next(t for t in transitions if t["signal"] == "submit")
        assert submit_trans["from_state"] == "draft"
        assert submit_trans["to_state"] == "pending"

        approve_trans = next(t for t in transitions if t["signal"] == "approve")
        assert approve_trans["from_state"] == "pending"
        assert approve_trans["to_state"] == "approved"
        assert approve_trans["condition"] == "True"


def test_workflow_sdd_reference_preserved():
    """Workflow component preserves sdd_reference for traceability."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        _setup_project_with_workflow(project_dir)

        sm = SchemaManager(project_dir)
        result = sm.assemble()

        wf = result.schema["workflows"][0]
        assert wf["sdd_reference"] == "workflow.vehicle_approval"


def test_workflow_empty_project():
    """Assembly with no workflows produces empty workflows array."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()

        factory_dir = project_dir / ".factory"
        tasks_dir = factory_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        index = {
            "module_name": "vehicle_registry",
            "total_tasks": 1,
            "tasks": [
                {
                    "id": "T001",
                    "name": "Modelos",
                    "file": "T001-modelos.json",
                    "dependencies": [],
                    "order": 1,
                    "estimated_effort": "high",
                    "sdd_components": ["models.vehicle"],
                },
            ],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index, indent=2))

        t001 = {
            "id": "T001",
            "name": "Modelos",
            "description": "Generar modelos",
            "components": [
                {
                    "type": "model",
                    "name": "vehicle.vehicle",
                    "description": "Modelo de vehiculo",
                    "fields": [
                        {"name": "name", "type": "Char", "label": "Nombre", "required": True},
                    ],
                    "sdd_reference": "models.vehicle",
                },
            ],
            "files_to_generate": ["models/__init__.py", "models/vehicle.py"],
            "dependencies": [],
        }
        (tasks_dir / "T001-modelos.json").write_text(json.dumps(t001, indent=2))

        sdd = {"module_name": "vehicle_registry", "version": "18.0.1.0.0", "summary": "Test"}
        (factory_dir / "sdd.json").write_text(json.dumps(sdd, indent=2))

        sm = SchemaManager(project_dir)
        result = sm.assemble()

        assert result.success
        assert "workflows" in result.schema
        assert len(result.schema["workflows"]) == 0

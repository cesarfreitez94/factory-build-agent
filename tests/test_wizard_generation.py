"""Tests for wizard generation in SchemaManager and code rendering."""

import json
from pathlib import Path
import tempfile

import pytest

from fba.schema_manager import SchemaManager


def _setup_project_with_wizard(project_dir: Path):
    """Create a minimal project with wizard task files."""
    factory_dir = project_dir / ".factory"
    tasks_dir = factory_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    schemas_dir = factory_dir / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)

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
                "name": "Wizard Confirm",
                "file": "T002-wizard.json",
                "dependencies": ["T001"],
                "order": 2,
                "estimated_effort": "medium",
                "sdd_components": ["wizard.confirm_vehicle", "workflow.vehicle_approval"],
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
        "name": "Wizard Confirm",
        "description": "Wizard para confirmar vehiculo y disparar workflow de aprobacion.",
        "components": [
            {
                "type": "wizard",
                "name": "vehicle.wizard.confirm",
                "description": "Wizard de confirmacion de vehiculo",
                "wizard_model": "vehicle.vehicle",
                "button_next_step": "action_confirm_vehicle",
                "fields": [
                    {"name": "confirm_notes", "type": "Text", "label": "Notas de confirmacion"},
                    {"name": "confirm_vehicle_id", "type": "Many2one", "label": "Vehiculo", "relation": "vehicle.vehicle"},
                ],
                "sdd_reference": "wizard.confirm_vehicle",
            },
        ],
        "files_to_generate": ["wizard/__init__.py", "wizard/confirm.py"],
        "dependencies": ["T001"],
    }
    (tasks_dir / "T002-wizard.json").write_text(json.dumps(t002, indent=2))

    sdd = {
        "module_name": "vehicle_registry",
        "version": "18.0.1.0.0",
        "summary": "Vehicle registry module",
    }
    (factory_dir / "sdd.json").write_text(json.dumps(sdd, indent=2))


def test_wizard_component_recognized():
    """Wizard component type is recognized by SchemaManager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        _setup_project_with_wizard(project_dir)

        sm = SchemaManager(project_dir)
        assert "wizard" in sm.IMPLEMENTED_TYPES


def test_wizard_assembly():
    """SchemaManager correctly assembles wizard components from task files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        _setup_project_with_wizard(project_dir)

        sm = SchemaManager(project_dir)
        result = sm.assemble()

        assert result.success, f"Assembly failed: {result.error_messages}"
        assert "wizards" in result.schema
        wizards = result.schema["wizards"]
        assert len(wizards) == 1

        wizard = wizards[0]
        assert wizard["name"] == "vehicle.wizard.confirm"
        assert wizard["model"] == "vehicle.wizard.confirm"
        assert wizard["wizard_model"] == "vehicle.vehicle"
        assert wizard["button_next_step"] == "action_confirm_vehicle"
        assert len(wizard["fields"]) == 2

        field_names = [f["name"] for f in wizard["fields"]]
        assert "confirm_notes" in field_names
        assert "confirm_vehicle_id" in field_names


def test_wizard_field_normalization():
    """Wizard fields are normalized with proper suffix for relational types."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        _setup_project_with_wizard(project_dir)

        sm = SchemaManager(project_dir)
        result = sm.assemble()

        wizard = result.schema["wizards"][0]
        many2one_field = next(f for f in wizard["fields"] if f["name"] == "confirm_vehicle_id")
        assert many2one_field["type"] == "Many2one"
        assert many2one_field["name"].endswith("_id")


def test_wizard_sdd_reference_preserved():
    """Wizard component preserves sdd_reference for traceability."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        _setup_project_with_wizard(project_dir)

        sm = SchemaManager(project_dir)
        result = sm.assemble()

        wizard = result.schema["wizards"][0]
        assert wizard["sdd_reference"] == "wizard.confirm_vehicle"


def test_wizard_empty_project():
    """Assembly with no wizards produces empty wizards array."""
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
        assert "wizards" in result.schema
        assert len(result.schema["wizards"]) == 0

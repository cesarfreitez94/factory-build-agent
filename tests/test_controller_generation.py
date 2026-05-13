"""Tests for controller generation in SchemaManager."""

import json
from pathlib import Path
import tempfile

import pytest

from fba.schema_manager import SchemaManager


def _setup_project_with_controller(project_dir: Path):
    """Create a minimal project with controller task files."""
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
                "name": "Report Controller",
                "file": "T002-controller.json",
                "dependencies": ["T001"],
                "order": 2,
                "estimated_effort": "medium",
                "sdd_components": ["controller.report_download"],
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
        "name": "Report Controller",
        "description": "HTTP controller for downloading reports.",
        "components": [
            {
                "type": "controller",
                "name": "vehicle.report.controller",
                "route": "/vehicle/reports/<int:report_id>",
                "model": "vehicle.vehicle",
                "methods": ["GET"],
                "auth": "public",
                "sdd_reference": "controller.report_download",
            },
        ],
        "files_to_generate": ["controllers/__init__.py", "controllers/main.py"],
        "dependencies": ["T001"],
    }
    (tasks_dir / "T002-controller.json").write_text(json.dumps(t002, indent=2))

    sdd = {
        "module_name": "vehicle_registry",
        "version": "18.0.1.0.0",
        "summary": "Vehicle registry module",
    }
    (factory_dir / "sdd.json").write_text(json.dumps(sdd, indent=2))


def test_controller_component_recognized():
    """Controller component type is recognized by SchemaManager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        _setup_project_with_controller(project_dir)

        sm = SchemaManager(project_dir)
        assert "controller" in sm.IMPLEMENTED_TYPES


def test_controller_assembly():
    """SchemaManager correctly assembles controller components from task files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        _setup_project_with_controller(project_dir)

        sm = SchemaManager(project_dir)
        result = sm.assemble()

        assert result.success, f"Assembly failed: {result.error_messages}"
        assert "controllers" in result.schema
        controllers = result.schema["controllers"]
        assert len(controllers) == 1

        ctrl = controllers[0]
        assert ctrl["name"] == "vehicle.report.controller"
        assert ctrl["route"] == "/vehicle/reports/<int:report_id>"
        assert ctrl["model"] == "vehicle.vehicle"
        assert ctrl["methods"] == ["GET"]
        assert ctrl["auth"] == "public"


def test_controller_methods():
    """Controller supports multiple HTTP methods."""
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
                    "name": "CRUD Controllers",
                    "file": "T001-controller.json",
                    "dependencies": [],
                    "order": 1,
                    "estimated_effort": "medium",
                    "sdd_components": ["controller.vehicle_crud"],
                },
            ],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index, indent=2))

        t001 = {
            "id": "T001",
            "name": "CRUD Controllers",
            "description": "CRUD HTTP controllers",
            "components": [
                {
                    "type": "model",
                    "name": "vehicle.vehicle",
                    "description": "Vehicle model",
                    "fields": [
                        {"name": "name", "type": "Char", "label": "Name", "required": True},
                    ],
                    "sdd_reference": "models.vehicle",
                },
                {
                    "type": "controller",
                    "name": "vehicle.controller",
                    "route": "/vehicle/<int:vehicle_id>",
                    "model": "vehicle.vehicle",
                    "methods": ["GET", "POST", "PUT", "DELETE"],
                    "auth": "user",
                    "sdd_reference": "controller.vehicle_crud",
                },
            ],
            "files_to_generate": ["controllers/__init__.py", "controllers/main.py"],
            "dependencies": [],
        }
        (tasks_dir / "T001-controller.json").write_text(json.dumps(t001, indent=2))

        sdd = {"module_name": "vehicle_registry", "version": "18.0.1.0.0", "summary": "Test"}
        (factory_dir / "sdd.json").write_text(json.dumps(sdd, indent=2))

        sm = SchemaManager(project_dir)
        result = sm.assemble()

        assert result.success
        ctrl = result.schema["controllers"][0]
        assert set(ctrl["methods"]) == {"GET", "POST", "PUT", "DELETE"}
        assert ctrl["auth"] == "user"


def test_controller_auth_types():
    """Controller supports public, user, and api auth types."""
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
                    "name": "Auth Controllers",
                    "file": "T001-controller.json",
                    "dependencies": [],
                    "order": 1,
                    "estimated_effort": "medium",
                    "sdd_components": ["controller.public", "controller.user", "controller.api"],
                },
            ],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index, indent=2))

        t001 = {
            "id": "T001",
            "name": "Auth Controllers",
            "description": "Different auth types",
            "components": [
                {
                    "type": "model",
                    "name": "vehicle.vehicle",
                    "description": "Vehicle model",
                    "fields": [
                        {"name": "name", "type": "Char", "label": "Name", "required": True},
                    ],
                    "sdd_reference": "models.vehicle",
                },
                {
                    "type": "controller",
                    "name": "vehicle.public_controller",
                    "route": "/vehicle/public",
                    "model": "vehicle.vehicle",
                    "methods": ["GET"],
                    "auth": "public",
                    "sdd_reference": "controller.public",
                },
                {
                    "type": "controller",
                    "name": "vehicle.user_controller",
                    "route": "/vehicle/user",
                    "model": "vehicle.vehicle",
                    "methods": ["GET"],
                    "auth": "user",
                    "sdd_reference": "controller.user",
                },
                {
                    "type": "controller",
                    "name": "vehicle.api_controller",
                    "route": "/vehicle/api",
                    "model": "vehicle.vehicle",
                    "methods": ["GET"],
                    "auth": "api",
                    "sdd_reference": "controller.api",
                },
            ],
            "files_to_generate": ["controllers/__init__.py", "controllers/main.py"],
            "dependencies": [],
        }
        (tasks_dir / "T001-controller.json").write_text(json.dumps(t001, indent=2))

        sdd = {"module_name": "vehicle_registry", "version": "18.0.1.0.0", "summary": "Test"}
        (factory_dir / "sdd.json").write_text(json.dumps(sdd, indent=2))

        sm = SchemaManager(project_dir)
        result = sm.assemble()

        assert result.success
        auth_types = {c["auth"] for c in result.schema["controllers"]}
        assert auth_types == {"public", "user", "api"}


def test_controller_sdd_reference_preserved():
    """Controller component preserves sdd_reference for traceability."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        _setup_project_with_controller(project_dir)

        sm = SchemaManager(project_dir)
        result = sm.assemble()

        ctrl = result.schema["controllers"][0]
        assert ctrl["sdd_reference"] == "controller.report_download"


def test_controller_empty_project():
    """Assembly with no controllers produces empty controllers array."""
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
        assert "controllers" in result.schema
        assert len(result.schema["controllers"]) == 0

"""Tests for report generation in SchemaManager."""

import json
from pathlib import Path
import tempfile

import pytest

from fba.schema_manager import SchemaManager


def _setup_project_with_report(project_dir: Path):
    """Create a minimal project with report task files."""
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
                "name": "Vehicle Report",
                "file": "T002-report.json",
                "dependencies": ["T001"],
                "order": 2,
                "estimated_effort": "medium",
                "sdd_components": ["report.vehicle_report"],
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
        "name": "Vehicle Report",
        "description": "QWeb report for vehicle listing.",
        "components": [
            {
                "type": "report",
                "name": "vehicle.report",
                "model": "vehicle.vehicle",
                "report_type": "qweb",
                "report_name": "Vehicle Report",
                "file": "report/vehicle_report.xml",
                "field_names": ["name", "plate", "brand_id", "year", "state"],
                "sdd_reference": "report.vehicle_report",
            },
        ],
        "files_to_generate": ["report/vehicle_report.xml", "report/__init__.py"],
        "dependencies": ["T001"],
    }
    (tasks_dir / "T002-report.json").write_text(json.dumps(t002, indent=2))

    sdd = {
        "module_name": "vehicle_registry",
        "version": "18.0.1.0.0",
        "summary": "Vehicle registry module",
    }
    (factory_dir / "sdd.json").write_text(json.dumps(sdd, indent=2))


def test_report_component_recognized():
    """Report component type is recognized by SchemaManager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        _setup_project_with_report(project_dir)

        sm = SchemaManager(project_dir)
        assert "report" in sm.IMPLEMENTED_TYPES


def test_report_assembly():
    """SchemaManager correctly assembles report components from task files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        _setup_project_with_report(project_dir)

        sm = SchemaManager(project_dir)
        result = sm.assemble()

        assert result.success, f"Assembly failed: {result.error_messages}"
        assert "reports" in result.schema
        reports = result.schema["reports"]
        assert len(reports) == 1

        rpt = reports[0]
        assert rpt["name"] == "vehicle.report"
        assert rpt["model"] == "vehicle.vehicle"
        assert rpt["report_type"] == "qweb"
        assert rpt["report_name"] == "Vehicle Report"
        assert rpt["file"] == "report/vehicle_report.xml"
        assert len(rpt["field_names"]) == 5


def test_report_types():
    """Report supports qweb, axl, and rdl types."""
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
                    "name": "Reports",
                    "file": "T001-reports.json",
                    "dependencies": [],
                    "order": 1,
                    "estimated_effort": "medium",
                    "sdd_components": ["report.vehicle_qweb", "report.vehicle_axl"],
                },
            ],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index, indent=2))

        t001 = {
            "id": "T001",
            "name": "Reports",
            "description": "Multiple report types",
            "components": [
                {
                    "type": "model",
                    "name": "vehicle.vehicle",
                    "description": "Vehicle model",
                    "fields": [
                        {"name": "name", "type": "Char", "label": "Name", "required": True},
                        {"name": "plate", "type": "Char", "label": "Plate", "required": False},
                    ],
                    "sdd_reference": "models.vehicle",
                },
                {
                    "type": "report",
                    "name": "vehicle.report.qweb",
                    "model": "vehicle.vehicle",
                    "report_type": "qweb",
                    "report_name": "Vehicle QWeb Report",
                    "file": "report/vehicle_qweb.xml",
                    "field_names": ["name", "plate"],
                    "sdd_reference": "report.vehicle_qweb",
                },
                {
                    "type": "report",
                    "name": "vehicle.report.axl",
                    "model": "vehicle.vehicle",
                    "report_type": "axl",
                    "report_name": "Vehicle AXL Report",
                    "file": "report/vehicle_axl.xml",
                    "field_names": ["name", "plate"],
                    "sdd_reference": "report.vehicle_axl",
                },
            ],
            "files_to_generate": ["report/vehicle_qweb.xml", "report/vehicle_axl.xml"],
            "dependencies": [],
        }
        (tasks_dir / "T001-reports.json").write_text(json.dumps(t001, indent=2))

        sdd = {"module_name": "vehicle_registry", "version": "18.0.1.0.0", "summary": "Test"}
        (factory_dir / "sdd.json").write_text(json.dumps(sdd, indent=2))

        sm = SchemaManager(project_dir)
        result = sm.assemble()

        assert result.success
        reports = result.schema["reports"]
        assert len(reports) == 2

        report_types = {r["report_type"] for r in reports}
        assert "qweb" in report_types
        assert "axl" in report_types


def test_report_sdd_reference_preserved():
    """Report component preserves sdd_reference for traceability."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        _setup_project_with_report(project_dir)

        sm = SchemaManager(project_dir)
        result = sm.assemble()

        rpt = result.schema["reports"][0]
        assert rpt["sdd_reference"] == "report.vehicle_report"


def test_report_empty_project():
    """Assembly with no reports produces empty reports array."""
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
        assert "reports" in result.schema
        assert len(result.schema["reports"]) == 0

"""Tests for M15 feat/15.1: Playwright browser automation artifacts."""

import json
from pathlib import Path

from click.testing import CliRunner

from fba.cli import main
from fba.playwright_manager import PlaywrightManager


def _write_schema(project_dir: Path) -> None:
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir(parents=True, exist_ok=True)
    schema = {
        "manifest": {"name": "fleet_ext", "version": "18.0.1.0.0", "depends": ["base"], "license": "LGPL-3"},
        "models": [
            {
                "name": "fleet.vehicle.ext",
                "description": "Vehicle extension",
                "mode": "new",
                "fields": [
                    {"name": "name", "type": "Char", "label": "Name"},
                    {"name": "vin", "type": "Char", "label": "VIN"},
                ],
            }
        ],
        "views": [
            {"name": "fleet.vehicle.ext.form", "type": "form", "model": "fleet.vehicle.ext", "fields": ["name", "vin"]},
            {"name": "fleet.vehicle.ext.list", "type": "list", "model": "fleet.vehicle.ext", "fields": ["name"]},
            {"name": "fleet.vehicle.ext.kanban", "type": "kanban", "model": "fleet.vehicle.ext", "fields": ["name"]},
            {"name": "fleet.vehicle.ext.search", "type": "search", "model": "fleet.vehicle.ext", "fields": ["name"]},
        ],
        "security": {"groups": [], "access_rights": [], "record_rules": []},
        "data": [],
    }
    (factory_dir / "schema.json").write_text(json.dumps(schema, indent=2))


def test_playwright_manager_generates_spec_and_reports(tmp_path):
    _write_schema(tmp_path)

    report = PlaywrightManager(tmp_path).generate(base_url="http://odoo.test")

    assert report.total_cases == 3
    assert report.spec_path.exists()
    assert report.json_path.exists()
    assert report.md_path.exists()

    spec = report.spec_path.read_text()
    assert "http://odoo.test" in spec
    assert "fleet.vehicle.ext" in spec
    assert '"viewType": "form"' in spec
    assert '"viewType": "list"' in spec
    assert '"viewType": "kanban"' in spec
    assert '"viewType": "search"' not in spec


def test_playwright_report_json_has_cases(tmp_path):
    _write_schema(tmp_path)

    report = PlaywrightManager(tmp_path).generate()
    payload = json.loads(report.json_path.read_text())

    assert payload["total_cases"] == 3
    assert [case["view_type"] for case in payload["cases"]] == ["form", "list", "kanban"]


def test_cli_test_playwright_generates_artifacts(tmp_path):
    _write_schema(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["test", "--playwright", "-d", str(tmp_path)])

    assert result.exit_code == 0
    assert "Playwright browser automation generated" in result.output
    assert (tmp_path / ".factory" / "playwright" / "odoo_views.spec.ts").exists()


def test_cli_test_without_backend_fails(tmp_path):
    _write_schema(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["test", "-d", str(tmp_path)])

    assert result.exit_code == 1
    assert "--playwright" in result.output

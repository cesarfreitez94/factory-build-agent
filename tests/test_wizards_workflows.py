"""Tests for M14 feat/14.1: Wizards, Workflows, Reports, Controllers support in SchemaManager."""

import json
from pathlib import Path

from fba.schema_manager import SchemaManager


def _make_project(tmp_path: Path) -> Path:
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    tasks_dir = factory_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (factory_dir / "schemas").mkdir(parents=True)
    return project_dir


def _write_index(project_dir: Path, tasks: list[dict]) -> None:
    index = {"module_name": "test", "total_tasks": len(tasks), "tasks": tasks}
    (project_dir / ".factory" / "tasks" / "index.json").write_text(json.dumps(index, indent=2))


def _write_sdd(project_dir: Path) -> None:
    sdd = {"module_name": "test", "version": "18.0.1.0.0", "summary": "Test module", "dependencies": {"required": ["base"]}}
    (project_dir / ".factory" / "sdd.json").write_text(json.dumps(sdd, indent=2))


def _write_task(project_dir: Path, task_id: str, file_name: str, components: list[dict]) -> None:
    task = {
        "id": task_id, "name": file_name.replace(".json", ""),
        "description": f"Task {task_id} for testing",
        "components": components,
        "files_to_generate": ["test.py"],
        "dependencies": [],
    }
    (project_dir / ".factory" / "tasks" / file_name).write_text(json.dumps(task, indent=2))


# ---------------------------------------------------------------------------
# feat/14.1 implemented types constant
# ---------------------------------------------------------------------------

def test_implemented_types_includes_all_m14_types():
    assert "wizard" in SchemaManager.IMPLEMENTED_TYPES
    assert "workflow" in SchemaManager.IMPLEMENTED_TYPES
    assert "report" in SchemaManager.IMPLEMENTED_TYPES
    assert "controller" in SchemaManager.IMPLEMENTED_TYPES
    assert "model" in SchemaManager.IMPLEMENTED_TYPES
    assert "view" in SchemaManager.IMPLEMENTED_TYPES


# ---------------------------------------------------------------------------
# WIZARDS
# ---------------------------------------------------------------------------

def test_wizard_assembles_into_schema(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "Wiz", "file": "T001-wiz.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["wizards.import"]}])
    _write_task(project_dir, "T001", "T001-wiz.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "wizard", "name": "test.import.wizard", "description": "Import wizard for test module", "sdd_reference": "wizards.import",
         "fields": [{"name": "file", "type": "Binary", "label": "File"}, {"name": "note", "type": "Text", "label": "Notes"}],
         "action_name": "Import Test", "methods": [{"name": "action_import", "description": "Execute import"}]},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    assert result.success
    wizards = result.schema.get("wizards", [])
    assert len(wizards) == 1
    w = wizards[0]
    assert w["name"] == "test.import.wizard"
    assert len(w["fields"]) == 2
    assert w["view_type"] == "form"
    assert w["action_name"] == "Import Test"
    assert len(w["methods"]) == 1


def test_wizard_no_unknown_warning(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "Wiz", "file": "T001-wiz.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["wizards.test"]}])
    _write_task(project_dir, "T001", "T001-wiz.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "wizard", "name": "test.wizard", "description": "A wizard", "sdd_reference": "wizards.test", "fields": [{"name": "data", "type": "Text", "label": "Data"}]},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    unknown_warnings = [w for w in result.warning_messages if "not yet implemented" in w.lower()]
    wizard_not_implemented = [w for w in unknown_warnings if "wizard" in w.lower()]
    assert len(wizard_not_implemented) == 0, f"Should not warn about wizard anymore: {unknown_warnings}"


def test_wizard_fields_are_normalized(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "Wiz", "file": "T001-wiz.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["wizards.test"]}])
    _write_task(project_dir, "T001", "T001-wiz.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "wizard", "name": "test.wizard", "description": "A wizard", "sdd_reference": "wizards.test",
         "fields": [
             {"name": "partner", "type": "Many2one", "label": "Partner", "relation": "res.partner"},
             {"name": "lines", "type": "One2many", "label": "Lines", "relation": "test.line"},
         ]},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    w = result.schema["wizards"][0]
    field_names = [f["name"] for f in w["fields"]]
    assert "partner_id" in field_names
    assert "lines_ids" in field_names


def test_multiple_wizards_merge_shared_model(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [
        {"id": "T001", "name": "Wiz1", "file": "T001-wiz1.json", "dependencies": [], "order": 1, "estimated_effort": "low", "sdd_components": ["wizards.test1"]},
        {"id": "T002", "name": "Wiz2", "file": "T002-wiz2.json", "dependencies": [], "order": 2, "estimated_effort": "low", "sdd_components": ["wizards.test2"]},
    ])
    _write_task(project_dir, "T001", "T001-wiz1.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "wizard", "name": "test.wizard", "description": "Wizard part 1", "sdd_reference": "wizards.test1", "fields": [{"name": "field_a", "type": "Char", "label": "A"}]},
    ])
    _write_task(project_dir, "T002", "T002-wiz2.json", [
        {"type": "wizard", "name": "test.wizard", "description": "Wizard part 2", "sdd_reference": "wizards.test2", "fields": [{"name": "field_b", "type": "Char", "label": "B"}]},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    assert len(result.schema["wizards"]) == 1
    w = result.schema["wizards"][0]
    assert len(w["fields"]) == 2


def test_wizard_with_empty_name_warns(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "Wiz", "file": "T001-wiz.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["wizards.test"]}])
    _write_task(project_dir, "T001", "T001-wiz.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "wizard", "name": "", "description": "Bad wizard", "sdd_reference": "wizards.test", "fields": []},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()
    assert result.success
    assert any("empty name" in w.lower() for w in result.warning_messages)


# ---------------------------------------------------------------------------
# WORKFLOWS
# ---------------------------------------------------------------------------

def test_workflow_server_action_assembles(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "WF", "file": "T001-wf.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["workflows.confirm"]}])
    _write_task(project_dir, "T001", "T001-wf.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "workflow", "name": "action_confirm", "kind": "server_action", "model": "test.model",
         "description": "Confirm test records", "state": "code", "trigger": "on_create", "sdd_reference": "workflows.confirm"},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    assert result.success
    wfs = result.schema.get("workflows", [])
    assert len(wfs) == 1
    wf = wfs[0]
    assert wf["name"] == "action_confirm"
    assert wf["kind"] == "server_action"
    assert wf["model"] == "test.model"
    assert wf["trigger"] == "on_create"


def test_workflow_scheduled_job_assembles(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "Cron", "file": "T001-cron.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["workflows.cron"]}])
    _write_task(project_dir, "T001", "T001-cron.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "workflow", "name": "cron_cleanup", "kind": "scheduled_job", "model": "test.model",
         "description": "Daily cleanup", "state": "code", "code": "model._cron_cleanup()",
         "interval_number": 1, "interval_type": "days", "sdd_reference": "workflows.cron"},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    assert result.success
    wfs = result.schema.get("workflows", [])
    assert len(wfs) == 1
    wf = wfs[0]
    assert wf["kind"] == "scheduled_job"
    assert wf["interval_number"] == 1
    assert wf["interval_type"] == "days"


def test_workflow_requires_model(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "WF", "file": "T001-wf.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["workflows.test"]}])
    _write_task(project_dir, "T001", "T001-wf.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "workflow", "name": "no_model_action", "kind": "server_action", "model": "", "description": "Missing model", "sdd_reference": "workflows.test"},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    assert result.success
    assert any("no 'model'" in w.lower() for w in result.warning_messages)


def test_workflow_no_unknown_warning(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "WF", "file": "T001-wf.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["workflows.test"]}])
    _write_task(project_dir, "T001", "T001-wf.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "workflow", "name": "test_wf", "kind": "server_action", "model": "test.model", "description": "A workflow", "sdd_reference": "workflows.test"},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    unknown_warnings = [w for w in result.warning_messages if "not yet implemented" in w.lower()]
    workflow_not_implemented = [w for w in unknown_warnings if "workflow" in w.lower()]
    assert len(workflow_not_implemented) == 0


# ---------------------------------------------------------------------------
# REPORTS
# ---------------------------------------------------------------------------

def test_report_assembles_into_schema(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "Report", "file": "T001-rep.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["reports.card"]}])
    _write_task(project_dir, "T001", "T001-rep.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "report", "name": "vehicle_card", "model": "test.model", "report_name": "test.report_vehicle_card",
         "description": "Vehicle card report", "report_type": "qweb-pdf", "template_name": "report_vehicle_card",
         "paperformat": {"name": "A4 Test", "format": "A4", "orientation": "Portrait"}, "menu": True,
         "sdd_reference": "reports.card"},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    assert result.success
    reports = result.schema.get("reports", [])
    assert len(reports) == 1
    r = reports[0]
    assert r["name"] == "vehicle_card"
    assert r["model"] == "test.model"
    assert r["report_name"] == "test.report_vehicle_card"
    assert r["report_type"] == "qweb-pdf"
    assert r["paperformat"]["format"] == "A4"


def test_report_auto_generates_report_name(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "Report", "file": "T001-rep.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["reports.test"]}])
    _write_task(project_dir, "T001", "T001-rep.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "report", "name": "test.report", "model": "test.model",
         "description": "Report without explicit report_name", "sdd_reference": "reports.test"},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    assert result.success
    r = result.schema["reports"][0]
    assert r["report_name"] != ""
    assert "module.report" in r["report_name"].lower()
    assert any("auto-generated" in w.lower() for w in result.warning_messages)


def test_report_requires_model(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "Report", "file": "T001-rep.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["reports.test"]}])
    _write_task(project_dir, "T001", "T001-rep.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "report", "name": "bad_report", "model": "", "description": "Report without model", "sdd_reference": "reports.test"},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    assert result.success
    assert any("no 'model'" in w.lower() for w in result.warning_messages)


def test_report_no_unknown_warning(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "Report", "file": "T001-rep.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["reports.test"]}])
    _write_task(project_dir, "T001", "T001-rep.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "report", "name": "test_report", "model": "test.model", "report_name": "test.report_test", "description": "A report", "sdd_reference": "reports.test"},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    unknown_warnings = [w for w in result.warning_messages if "not yet implemented" in w.lower()]
    report_not_implemented = [w for w in unknown_warnings if "report" in w.lower()]
    assert len(report_not_implemented) == 0


# ---------------------------------------------------------------------------
# CONTROLLERS
# ---------------------------------------------------------------------------

def test_controller_assembles_into_schema(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "Ctrl", "file": "T001-ctrl.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["controllers.export"]}])
    _write_task(project_dir, "T001", "T001-ctrl.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "controller", "name": "TestController", "description": "Export controller",
         "sdd_reference": "controllers.export",
         "routes": [
             {"path": "/test/export", "method": "GET", "auth": "user", "handler": "export_data", "type": "http", "csrf": False, "description": "Export test data as CSV"},
             {"path": "/test/export/json", "method": "POST", "auth": "user", "handler": "export_json", "type": "json", "description": "Export test data as JSON"},
         ]},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    assert result.success
    ctrls = result.schema.get("controllers", [])
    assert len(ctrls) == 1
    c = ctrls[0]
    assert c["name"] == "TestController"
    assert len(c["routes"]) == 2
    assert c["routes"][0]["path"] == "/test/export"
    assert c["routes"][0]["method"] == "GET"
    assert c["routes"][1]["type"] == "json"


def test_controller_merges_routes_from_multiple_tasks(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [
        {"id": "T001", "name": "Ctrl1", "file": "T001-ctrl1.json", "dependencies": [], "order": 1, "estimated_effort": "low", "sdd_components": ["controllers.part1"]},
        {"id": "T002", "name": "Ctrl2", "file": "T002-ctrl2.json", "dependencies": [], "order": 2, "estimated_effort": "low", "sdd_components": ["controllers.part2"]},
    ])
    _write_task(project_dir, "T001", "T001-ctrl1.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "controller", "name": "MyController", "description": "Controller part 1", "sdd_reference": "controllers.part1",
         "routes": [{"path": "/api/a", "method": "GET", "auth": "user", "handler": "handle_a"}]},
    ])
    _write_task(project_dir, "T002", "T002-ctrl2.json", [
        {"type": "controller", "name": "MyController", "description": "Controller part 2", "sdd_reference": "controllers.part2",
         "routes": [{"path": "/api/b", "method": "POST", "auth": "user", "handler": "handle_b"}]},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    assert len(result.schema["controllers"]) == 1
    c = result.schema["controllers"][0]
    assert len(c["routes"]) == 2


def test_controller_invalid_route_warns(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "Ctrl", "file": "T001-ctrl.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["controllers.test"]}])
    _write_task(project_dir, "T001", "T001-ctrl.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "controller", "name": "BadController", "description": "Controller with bad route", "sdd_reference": "controllers.test",
         "routes": [{"path": "", "method": "GET", "auth": "user", "handler": "bad"}]},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    assert result.success
    assert any("no 'path'" in w.lower() for w in result.warning_messages)


def test_controller_no_unknown_warning(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "Ctrl", "file": "T001-ctrl.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["controllers.test"]}])
    _write_task(project_dir, "T001", "T001-ctrl.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test", "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "controller", "name": "TestController", "description": "A controller", "sdd_reference": "controllers.test",
         "routes": [{"path": "/test", "method": "GET", "auth": "user", "handler": "handle_test"}]},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    unknown_warnings = [w for w in result.warning_messages if "not yet implemented" in w.lower()]
    controller_not_implemented = [w for w in unknown_warnings if "controller" in w.lower()]
    assert len(controller_not_implemented) == 0


# ---------------------------------------------------------------------------
# INTEGRATION: All types together
# ---------------------------------------------------------------------------

def test_all_m14_types_integration(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "All", "file": "T001-all.json", "dependencies": [], "order": 1, "estimated_effort": "high", "sdd_components": ["all"]}])
    _write_task(project_dir, "T001", "T001-all.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test",
         "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
        {"type": "wizard", "name": "test.wizard", "description": "Test wizard", "sdd_reference": "wizards.test",
         "fields": [{"name": "data", "type": "Text", "label": "Data"}], "action_name": "Test Wizard"},
        {"type": "workflow", "name": "action_test", "kind": "server_action", "model": "test.model",
         "description": "Test workflow", "sdd_reference": "workflows.test"},
        {"type": "report", "name": "test_report", "model": "test.model", "report_name": "test.report_test",
         "description": "Test report", "sdd_reference": "reports.test"},
        {"type": "controller", "name": "TestController", "description": "Test controller", "sdd_reference": "controllers.test",
         "routes": [{"path": "/test", "method": "GET", "auth": "user", "handler": "test"}]},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    assert result.success
    assert len(result.schema.get("models", [])) == 1
    assert len(result.schema.get("wizards", [])) == 1
    assert len(result.schema.get("workflows", [])) == 1
    assert len(result.schema.get("reports", [])) == 1
    assert len(result.schema.get("controllers", [])) == 1

    unknown_warnings = [w for w in result.warning_messages if "not yet implemented" in w.lower()]
    assert len(unknown_warnings) == 0, f"All types should be implemented: {unknown_warnings}"


def test_schema_output_without_new_types_has_no_sections(tmp_path):
    project_dir = _make_project(tmp_path)
    _write_sdd(project_dir)
    _write_index(project_dir, [{"id": "T001", "name": "Basic", "file": "T001-basic.json", "dependencies": [], "order": 1, "estimated_effort": "low", "sdd_components": ["models.test"]}])
    _write_task(project_dir, "T001", "T001-basic.json", [
        {"type": "model", "name": "test.model", "description": "A test model", "sdd_reference": "models.test",
         "fields": [{"name": "name", "type": "Char", "label": "Name"}]},
    ])

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    assert result.success
    assert "wizards" not in result.schema
    assert "workflows" not in result.schema
    assert "reports" not in result.schema
    assert "controllers" not in result.schema

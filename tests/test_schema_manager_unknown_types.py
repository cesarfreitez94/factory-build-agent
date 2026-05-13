import json

from fba.schema_manager import SchemaManager


def create_task_data(task_id, components, task_name="test"):
    return {
        task_id: {
            "id": task_id,
            "name": task_name,
            "description": f"Test task {task_id}",
            "components": components,
            "files_to_generate": ["test.py"],
            "dependencies": [],
        }
    }


def create_project_structure(tmp_path, models_only=True):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()
    tasks_dir = factory_dir / "tasks"
    tasks_dir.mkdir()

    components = [
        {
            "type": "model",
            "name": "test.model",
            "description": "A test model",
            "sdd_reference": "test.model",
            "fields": [{"name": "name", "type": "Char", "label": "Name"}],
        }
    ]
    if not models_only:
        components.append({
            "type": "view",
            "name": "test.view",
            "description": "A test view",
            "sdd_reference": "test.view",
            "model": "test.model",
            "view_type": "form",
            "view_fields": ["name"],
        })

    task = {
        "id": "T001",
        "name": "test",
        "description": "A test task description",
        "components": components,
        "files_to_generate": ["test.py"],
        "dependencies": [],
    }
    (tasks_dir / "T001.json").write_text(json.dumps(task, indent=2))

    index = {
        "tasks": [
            {
                "id": "T001",
                "name": "test",
                "file": "T001.json",
                "order": 1,
                "estimated_effort": "small",
                "dependencies": [],
            }
        ]
    }
    (tasks_dir / "index.json").write_text(json.dumps(index, indent=2))

    return project_dir


def test_implemented_types_class_constant():
    assert hasattr(SchemaManager, "IMPLEMENTED_TYPES")
    assert isinstance(SchemaManager.IMPLEMENTED_TYPES, (set, frozenset))
    assert "model" in SchemaManager.IMPLEMENTED_TYPES
    assert "view" in SchemaManager.IMPLEMENTED_TYPES
    assert "security_group" in SchemaManager.IMPLEMENTED_TYPES
    assert "access_right" in SchemaManager.IMPLEMENTED_TYPES
    assert "record_rule" in SchemaManager.IMPLEMENTED_TYPES
    assert "data" in SchemaManager.IMPLEMENTED_TYPES
    assert "wizard" in SchemaManager.IMPLEMENTED_TYPES
    assert "workflow" in SchemaManager.IMPLEMENTED_TYPES
    assert "report" in SchemaManager.IMPLEMENTED_TYPES
    assert "controller" in SchemaManager.IMPLEMENTED_TYPES


def test_wizard_component_produces_warning(tmp_path):
    project_dir = tmp_path / "wizardproj"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()
    tasks_dir = factory_dir / "tasks"
    tasks_dir.mkdir()

    index = {
        "tasks": [
            {
                "id": "T001", "name": "test", "file": "T001.json",
                "order": 1, "estimated_effort": "small", "dependencies": [],
            }
        ]
    }
    (tasks_dir / "index.json").write_text(json.dumps(index, indent=2))

    task = {
        "id": "T001",
        "name": "test",
        "description": "A test task with wizard",
        "components": [
            {
                "type": "model", "name": "test.model",
                "description": "A test model", "sdd_reference": "test.model",
                "fields": [{"name": "name", "type": "Char", "label": "Name"}],
            },
            {
                "type": "wizard",
                "name": "test.wizard",
                "description": "A test wizard component",
                "sdd_reference": "test.wizard",
            }
        ],
        "files_to_generate": ["test.py"],
        "dependencies": [],
    }
    (tasks_dir / "T001.json").write_text(json.dumps(task, indent=2))

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    assert result.success
    assert len(result.schema.get("wizards", [])) == 1


def test_workflow_component_produces_warning(tmp_path):
    project_dir = tmp_path / "workflowproj"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()
    tasks_dir = factory_dir / "tasks"
    tasks_dir.mkdir()

    index = {
        "tasks": [
            {
                "id": "T001", "name": "test", "file": "T001.json",
                "order": 1, "estimated_effort": "small", "dependencies": [],
            }
        ]
    }
    (tasks_dir / "index.json").write_text(json.dumps(index, indent=2))

    task = {
        "id": "T001",
        "name": "test",
        "description": "A test task with workflow",
        "components": [
            {
                "type": "model", "name": "test.model",
                "description": "A test model", "sdd_reference": "test.model",
                "fields": [{"name": "name", "type": "Char", "label": "Name"}],
            },
            {
                "type": "workflow",
                "name": "test.workflow",
                "description": "A test workflow component",
                "sdd_reference": "test.workflow",
            }
        ],
        "files_to_generate": ["test.py"],
        "dependencies": [],
    }
    (tasks_dir / "T001.json").write_text(json.dumps(task, indent=2))

    sm = SchemaManager(project_dir)
    result = sm.assemble()
    assert result.success

    assert any("no 'model'" in w.lower() for w in result.warning_messages)


def test_report_controller_produce_warnings(tmp_path):
    project_dir = tmp_path / "reportproj"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()
    tasks_dir = factory_dir / "tasks"
    tasks_dir.mkdir()

    index = {
        "tasks": [
            {
                "id": "T001", "name": "test", "file": "T001.json",
                "order": 1, "estimated_effort": "small", "dependencies": [],
            }
        ]
    }
    (tasks_dir / "index.json").write_text(json.dumps(index, indent=2))

    task = {
        "id": "T001",
        "name": "test",
        "description": "A test task with multiple new types",
        "components": [
            {
                "type": "model", "name": "test.model",
                "description": "A test model", "sdd_reference": "test.model",
                "fields": [{"name": "name", "type": "Char", "label": "Name"}],
            },
            {
                "type": "report", "name": "test.report", "model": "",
                "description": "A report without model", "sdd_reference": "test.report",
            },
            {
                "type": "controller", "name": "test.controller", "routes": [],
                "description": "A controller with no routes", "sdd_reference": "test.controller",
            },
        ],
        "files_to_generate": ["test.py"],
        "dependencies": [],
    }
    (tasks_dir / "T001.json").write_text(json.dumps(task, indent=2))

    sm = SchemaManager(project_dir)
    result = sm.assemble()
    assert result.success

    assert len(result.schema.get("reports", [])) == 0
    assert len(result.schema.get("controllers", [])) == 1
    assert result.schema["controllers"][0]["routes"] == []
    warnings_lower = [w.lower() for w in result.warning_messages]
    has_model_warning = any("no 'model'" in w for w in warnings_lower)
    assert has_model_warning, f"Expected model warning for report, got: {result.warning_messages}"


def test_known_types_produce_no_unknown_warnings(tmp_path):
    project_dir = create_project_structure(tmp_path, models_only=True)
    sm = SchemaManager(project_dir)
    result = sm.assemble()

    unknown_warnings = [w for w in result.warning_messages if "not yet implemented" in w.lower()]
    assert len(unknown_warnings) == 0, f"Unexpected unknown type warnings: {unknown_warnings}"


def test_multiple_unknown_components_one_warning_each(tmp_path):
    project_dir = tmp_path / "multiproj"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()
    tasks_dir = factory_dir / "tasks"
    tasks_dir.mkdir()

    index = {
        "tasks": [
            {
                "id": "T001", "name": "test", "file": "T001.json",
                "order": 1, "estimated_effort": "small", "dependencies": [],
            }
        ]
    }
    (tasks_dir / "index.json").write_text(json.dumps(index, indent=2))

    task = {
        "id": "T001",
        "name": "test",
        "description": "A test task with multiple wizards",
        "components": [
            {
                "type": "model", "name": "test.model",
                "description": "A test model", "sdd_reference": "test.model",
                "fields": [{"name": "name", "type": "Char", "label": "Name"}],
            },
            {
                "type": "wizard", "name": "test.wiz1",
                "description": "Wiz 1", "sdd_reference": "test.wiz1",
            },
            {
                "type": "wizard", "name": "test.wiz2",
                "description": "Wiz 2", "sdd_reference": "test.wiz2",
            },
        ],
        "files_to_generate": ["test.py"],
        "dependencies": [],
    }
    (tasks_dir / "T001.json").write_text(json.dumps(task, indent=2))

    sm = SchemaManager(project_dir)
    result = sm.assemble()
    assert result.success

    assert len(result.schema.get("wizards", [])) == 2


def test_warning_level_is_warning(tmp_path):
    project_dir = tmp_path / "levelproj"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()
    tasks_dir = factory_dir / "tasks"
    tasks_dir.mkdir()

    index = {
        "tasks": [
            {
                "id": "T001", "name": "test", "file": "T001.json",
                "order": 1, "estimated_effort": "small", "dependencies": [],
            }
        ]
    }
    (tasks_dir / "index.json").write_text(json.dumps(index, indent=2))

    task = {
        "id": "T001", "name": "test",
        "description": "A test task with workflow missing model",
        "components": [
            {
                "type": "model", "name": "test.model",
                "description": "A test model", "sdd_reference": "test.model",
                "fields": [{"name": "name", "type": "Char", "label": "Name"}],
            },
            {
                "type": "workflow", "name": "test.wf",
                "description": "A test workflow", "sdd_reference": "test.wf",
                "model": "",
            }
        ],
        "files_to_generate": ["test.py"],
        "dependencies": [],
    }
    (tasks_dir / "T001.json").write_text(json.dumps(task, indent=2))

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    model_warnings = [w for w in result.warnings if "no 'model'" in w.message.lower()]
    assert len(model_warnings) >= 1
    for w in model_warnings:
        assert w.level == "warning"


def test_assembly_result_success_remains_true(tmp_path):
    project_dir = tmp_path / "succproj"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()
    tasks_dir = factory_dir / "tasks"
    tasks_dir.mkdir()

    index = {
        "tasks": [
            {
                "id": "T001", "name": "test", "file": "T001.json",
                "order": 1, "estimated_effort": "small", "dependencies": [],
            }
        ]
    }
    (tasks_dir / "index.json").write_text(json.dumps(index, indent=2))

    task = {
        "id": "T001", "name": "test",
        "description": "A test task with both known and wizard types",
        "components": [
            {
                "type": "model", "name": "test.model",
                "description": "A test model", "sdd_reference": "test.model",
                "fields": [{"name": "name", "type": "Char", "label": "Name"}],
            },
            {
                "type": "wizard", "name": "test.wizard",
                "description": "A test wizard", "sdd_reference": "test.wizard",
            },
        ],
        "files_to_generate": ["test.py"],
        "dependencies": [],
    }
    (tasks_dir / "T001.json").write_text(json.dumps(task, indent=2))

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    assert result.success is True
    assert len(result.schema.get("models", [])) == 1
    assert len(result.schema.get("wizards", [])) == 1

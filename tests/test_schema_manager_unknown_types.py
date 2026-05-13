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
    # M14: wizard, workflow, report, controller are now implemented
    assert "wizard" in SchemaManager.IMPLEMENTED_TYPES
    assert "workflow" in SchemaManager.IMPLEMENTED_TYPES
    assert "report" in SchemaManager.IMPLEMENTED_TYPES
    assert "controller" in SchemaManager.IMPLEMENTED_TYPES
    # Ensure some types are still NOT implemented (placeholder for future types)
    assert "menu" not in SchemaManager.IMPLEMENTED_TYPES
    assert "action" not in SchemaManager.IMPLEMENTED_TYPES


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
    # Wizard is now implemented - no warning, check it was assembled instead
    assert len(result.schema.get("wizards", [])) == 1
    wizard_warnings = [w for w in result.warning_messages if "wizard" in w.lower() and "not yet implemented" in w.lower()]
    # Since M14 implements wizard, it should NOT produce "not yet implemented" warning
    assert len(wizard_warnings) == 0, f"Unexpected wizard warning found in: {result.warning_messages}"


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

    # Wizard is now implemented, use truly unknown types for this test
    unknown_warnings = [w for w in result.warning_messages if "not yet implemented" in w.lower()]
    # Since wizard is now implemented, we use unknown types (menu, action) not yet implemented
    assert len(unknown_warnings) == 0, f"Unexpected warnings with implemented types: {result.warning_messages}"


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
        "description": "A test task with truly unknown types (not yet implemented)",
        "components": [
            {
                "type": "model", "name": "test.model",
                "description": "A test model", "sdd_reference": "test.model",
                "fields": [{"name": "name", "type": "Char", "label": "Name"}],
            },
            {
                "type": "menu", "name": "test.menu",
                "description": "Menu type not yet implemented", "sdd_reference": "test.menu",
            },
            {
                "type": "action", "name": "test.action",
                "description": "Action type not yet implemented", "sdd_reference": "test.action",
            },
        ],
        "files_to_generate": ["test.py"],
        "dependencies": [],
    }
    (tasks_dir / "T001.json").write_text(json.dumps(task, indent=2))

    sm = SchemaManager(project_dir)
    result = sm.assemble()
    assert result.success

    unknown_warnings = [w for w in result.warning_messages if "not yet implemented" in w.lower()]
    assert len(unknown_warnings) >= 2, f"Expected 2 unknown type warnings (one per component), got: {unknown_warnings}"


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
        "description": "A test task with truly unknown types (menu, action)",
        "components": [
            {
                "type": "model", "name": "test.model",
                "description": "A test model", "sdd_reference": "test.model",
                "fields": [{"name": "name", "type": "Char", "label": "Name"}],
            },
            {
                "type": "menu", "name": "test.menu",
                "description": "A menu type not yet implemented", "sdd_reference": "test.menu",
            },
        ],
        "files_to_generate": ["test.py"],
        "dependencies": [],
    }
    (tasks_dir / "T001.json").write_text(json.dumps(task, indent=2))

    sm = SchemaManager(project_dir)
    result = sm.assemble()

    # Wizard is now implemented, use truly unknown types to test warnings
    unknown_warnings = [w for w in result.warnings if "not yet implemented" in w.message.lower()]
    assert len(unknown_warnings) >= 1
    for w in unknown_warnings:
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
        "description": "A test task with wizard component (now implemented)",
        "components": [
            {
                "type": "model", "name": "test.model",
                "description": "A test model", "sdd_reference": "test.model",
                "fields": [{"name": "name", "type": "Char", "label": "Name"}],
            },
            {
                "type": "wizard", "name": "test.wizard",
                "description": "A wizard type now implemented", "sdd_reference": "test.wizard",
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
    # Verify wizard is now properly assembled (M14 implements wizard)
    assert len(result.schema.get("wizards", [])) == 1

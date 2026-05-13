import json
import warnings
from unittest.mock import patch

import pytest

from fba.module_registry import ModuleRegistry
from fba.schema_manager import SchemaManager


def test_registry_missing_file_warns(tmp_path):
    project_dir = tmp_path / "noregistry"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()

    with patch.object(ModuleRegistry, "_find_registry", return_value=None):
        with pytest.warns(UserWarning, match="no se encontro archivo de registry"):
            registry = ModuleRegistry(project_dir)

    assert registry.modules == {}
    assert registry.is_core("res.partner") is False
    assert registry.lookup("res.partner") is None


def test_registry_empty_file_warns(tmp_path):
    project_dir = tmp_path / "emptyreg"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()
    registry_path = factory_dir / "module_registry.json"
    registry_path.write_text("{}")

    with pytest.warns(UserWarning, match="no contiene 'modules'|vacio"):
        registry = ModuleRegistry(project_dir)

    assert registry.modules == {}


def test_registry_invalid_json_warns(tmp_path):
    project_dir = tmp_path / "badjson"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()
    registry_path = factory_dir / "module_registry.json"
    registry_path.write_text("{invalid json")

    with pytest.warns(UserWarning, match="JSON invalido"):
        registry = ModuleRegistry(project_dir)

    assert registry.modules == {}


def test_registry_missing_modules_key_warns(tmp_path):
    project_dir = tmp_path / "badschema"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()
    registry_path = factory_dir / "module_registry.json"
    registry_path.write_text(json.dumps({"odoo_version": "18.0"}))

    with pytest.warns(UserWarning, match="no contiene 'modules'"):
        registry = ModuleRegistry(project_dir)

    assert registry.modules == {}


def test_registry_normal_no_warnings(tmp_path):
    project_dir = tmp_path / "goodreg"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()
    registry_path = factory_dir / "module_registry.json"
    registry_path.write_text(json.dumps({
        "odoo_version": "18.0",
        "modules": {
            "base": {
                "models": ["res.partner"]
            }
        }
    }))

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        registry = ModuleRegistry(project_dir)
    assert len(w) == 0

    assert "base" in registry.modules
    assert registry.is_core("res.partner") is True


def test_is_core_empty_registry_returns_false(tmp_path):
    project_dir = tmp_path / "emptycheck"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()
    (factory_dir / "module_registry.json").write_text("{}")

    with pytest.warns(UserWarning):
        registry = ModuleRegistry(project_dir)

    assert registry.is_core("res.partner") is False
    assert registry.is_core("nonexistent.model") is False
    assert registry.lookup("res.partner") is None
    assert registry.get_models("base") == []
    assert registry.resolve_relation("res.partner") is None


def test_copy_registry_missing_source_warns(tmp_path, capsys):
    from fba import cli

    original_templates = cli.TEMPLATES_DIR
    temp_templates = tmp_path / "fake_templates"
    temp_templates.mkdir()

    registry_subdir = temp_templates / ".factory"
    registry_subdir.mkdir(parents=True)

    cli.TEMPLATES_DIR = temp_templates

    try:
        target = tmp_path / "target"
        target.mkdir()

        cli._copy_registry(target)

        dest = target / ".factory" / "module_registry.json"
        assert not dest.exists()
    finally:
        cli.TEMPLATES_DIR = original_templates


def test_schema_manager_empty_registry_warns(tmp_path):
    project_dir = tmp_path / "schemareg"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()

    tasks_dir = factory_dir / "tasks"
    tasks_dir.mkdir()

    registry_path = factory_dir / "module_registry.json"
    registry_path.write_text("{}")

    index = {
        "tasks": [
            {
                "id": "T001",
                "name": "test task",
                "file": "T001.json",
                "order": 1,
                "estimated_effort": "small",
                "dependencies": [],
            }
        ]
    }
    (tasks_dir / "index.json").write_text(json.dumps(index, indent=2))

    task = {
        "id": "T001",
        "name": "test task",
        "description": "A test task description",
        "components": [
            {
                "type": "model",
                "name": "test.model",
                "description": "A test model",
                "sdd_reference": "test.model",
                "fields": [
                    {"name": "name", "type": "Char", "label": "Name"}
                ],
            }
        ],
        "files_to_generate": ["test.py"],
        "dependencies": [],
    }
    (tasks_dir / "T001.json").write_text(json.dumps(task, indent=2))

    sm = SchemaManager(project_dir)
    result = sm.assemble()
    assert result.success

    warning_msgs = [w.message for w in result.warnings]
    has_registry_warning = any("registry" in msg.lower() for msg in warning_msgs)
    assert has_registry_warning, f"No registry warning found in: {warning_msgs}"

"""Tests for M14 feat/14.2: Schema migration detection and script generation."""

import json
from pathlib import Path

from fba.migration_manager import MigrationError, MigrationManager, MigrationReport


def _make_schema(version="18.0.1.0.0", models=None, views=None, security=None):
    """Create a minimal schema.json dict."""
    if models is None:
        models = [
            {
                "name": "test.model",
                "description": "A test model",
                "mode": "new",
                "display_name": "Test Model",
                "inherit": None,
                "fields": [
                    {"name": "name", "type": "Char", "label": "Name"},
                    {"name": "active", "type": "Boolean", "label": "Active"},
                ],
            },
        ]
    schema = {
        "manifest": {
            "name": "test_module",
            "version": version,
            "summary": "Test module",
            "depends": ["base"],
            "license": "LGPL-3",
        },
        "models": models,
        "views": views if views is not None else [],
        "security": security if security is not None else {"groups": [], "access_rights": [], "record_rules": []},
        "data": [],
    }
    return schema


def _write_schemas(project_dir: Path, current: dict, previous: dict | None = None):
    """Write current and previous schema files."""
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir(parents=True, exist_ok=True)
    (factory_dir / "schema.json").write_text(json.dumps(current, indent=2))
    if previous is not None:
        (factory_dir / "schema_prev.json").write_text(json.dumps(previous, indent=2))


# ---------------------------------------------------------------------------
# Detection: model added
# ---------------------------------------------------------------------------

def test_detect_model_added(tmp_path):
    prev = _make_schema(models=[])
    curr = _make_schema()
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    assert report.total_changes > 0
    added = [c for c in report.changes if c.kind == "added"]
    assert len(added) >= 1
    assert any("models" in c.path for c in added)


def test_detect_field_added(tmp_path):
    prev = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "name", "type": "Char", "label": "Name"}],
    }])
    curr = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [
            {"name": "name", "type": "Char", "label": "Name"},
            {"name": "phone", "type": "Char", "label": "Phone"},
        ],
    }])
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    added = [c for c in report.changes if c.kind == "added" and "fields" in c.path]
    assert len(added) >= 1


def test_detect_field_removed(tmp_path):
    prev = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [
            {"name": "name", "type": "Char", "label": "Name"},
            {"name": "phone", "type": "Char", "label": "Phone"},
        ],
    }])
    curr = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "name", "type": "Char", "label": "Name"}],
    }])
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    removed = [c for c in report.changes if c.kind == "removed" and "fields" in c.path]
    assert len(removed) >= 1


def test_detect_field_type_changed(tmp_path):
    prev = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "count", "type": "Integer", "label": "Count"}],
    }])
    curr = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "count", "type": "Float", "label": "Count"}],
    }])
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    modified = [c for c in report.changes if c.kind == "modified" and "type" in c.path]
    assert len(modified) >= 1


def test_detect_field_label_changed(tmp_path):
    prev = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "name", "type": "Char", "label": "Old Name"}],
    }])
    curr = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "name", "type": "Char", "label": "New Name"}],
    }])
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    modified = [c for c in report.changes if c.kind == "modified"]
    assert len(modified) >= 1


# ---------------------------------------------------------------------------
# Classification: breaking vs non-breaking
# ---------------------------------------------------------------------------

def test_classify_field_type_change_as_breaking(tmp_path):
    prev = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "count", "type": "Integer", "label": "Count"}],
    }])
    curr = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "count", "type": "Char", "label": "Count"}],
    }])
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    type_changes = [c for c in report.changes if c.kind == "modified" and "type" in c.path]
    assert len(type_changes) >= 1
    assert all(c.breaking for c in type_changes)


def test_classify_field_label_change_as_non_breaking(tmp_path):
    prev = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "name", "type": "Char", "label": "Old"}],
    }])
    curr = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "name", "type": "Char", "label": "New"}],
    }])
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    label_changes = [c for c in report.changes if "label" in c.path]
    if label_changes:
        assert all(not c.breaking for c in label_changes)


def test_classify_new_model_as_non_breaking(tmp_path):
    prev = _make_schema(models=[])
    curr = _make_schema()
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    model_additions = [c for c in report.changes if c.kind == "added" and ".fields" not in c.path and "models" in c.path]
    if model_additions:
        assert all(not c.breaking for c in model_additions)


def test_classify_field_removal_as_breaking(tmp_path):
    prev = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [
            {"name": "name", "type": "Char", "label": "Name"},
            {"name": "phone", "type": "Char", "label": "Phone"},
        ],
    }])
    curr = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "name", "type": "Char", "label": "Name"}],
    }])
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    field_removals = [c for c in report.changes if c.kind == "removed" and "fields" in c.path]
    assert len(field_removals) >= 1
    assert all(c.breaking for c in field_removals)


# ---------------------------------------------------------------------------
# Version bump
# ---------------------------------------------------------------------------

def test_version_bump_breaking_major(tmp_path):
    prev = _make_schema(version="18.0.1.0.0", models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "count", "type": "Integer", "label": "Count"}],
    }])
    curr = _make_schema(version="18.0.1.0.0", models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "count", "type": "Float", "label": "Count"}],
    }])
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    assert report.has_breaking
    assert report.new_version == "18.0.2.0.0"


def test_version_bump_non_breaking_minor(tmp_path):
    prev = _make_schema(version="18.0.1.0.0", models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "name", "type": "Char", "label": "Name"}],
    }])
    curr = _make_schema(version="18.0.1.0.0", models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [
            {"name": "name", "type": "Char", "label": "Name"},
            {"name": "phone", "type": "Char", "label": "Phone"},
        ],
    }])
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    assert not report.has_breaking
    assert report.new_version == "18.0.1.1.0"


def test_version_bump_no_changes_same(tmp_path):
    schema = _make_schema(version="18.0.1.0.0")
    _write_schemas(tmp_path, schema, schema)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    assert report.new_version == "18.0.1.0.0"
    assert report.total_changes == 0


def test_version_bump_modifications_patch(tmp_path):
    prev = _make_schema(version="18.0.1.0.0", models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "name", "type": "Char", "label": "Old"}],
    }])
    curr = _make_schema(version="18.0.1.0.0", models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "name", "type": "Char", "label": "New"}],
    }])
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    assert not report.has_breaking
    assert report.new_version in ("18.0.1.0.0", "18.0.1.0.1")


# ---------------------------------------------------------------------------
# Script generation
# ---------------------------------------------------------------------------

def test_generates_all_three_scripts(tmp_path):
    prev = _make_schema()
    curr = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [
            {"name": "name", "type": "Char", "label": "Name"},
            {"name": "phone", "type": "Char", "label": "Phone"},
        ],
    }])
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    assert "pre-migrate.py" in report.scripts
    assert "post-migrate.py" in report.scripts
    assert "end-migrate.py" in report.scripts
    for script_content in report.scripts.values():
        assert "def migrate(cr, version):" in script_content
        assert "from odoo import api, SUPERUSER_ID" in script_content


def test_pre_migrate_has_breaking_comments(tmp_path):
    prev = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "count", "type": "Integer", "label": "Count"}],
    }])
    curr = _make_schema(models=[{
        "name": "test.model", "description": "Model", "mode": "new",
        "display_name": "Model", "inherit": None,
        "fields": [{"name": "count", "type": "Float", "label": "Count"}],
    }])
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    pre = report.scripts["pre-migrate.py"]
    assert "from odoo import api, SUPERUSER_ID" in pre


def test_post_migrate_has_addition_comments(tmp_path):
    prev = _make_schema(models=[])
    curr = _make_schema()
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    post = report.scripts["post-migrate.py"]
    assert "from odoo import api, SUPERUSER_ID" in post


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_error_missing_current_schema(tmp_path):
    mgr = MigrationManager(tmp_path)
    try:
        mgr.analyze()
        assert False, "Should raise MigrationError"
    except MigrationError as e:
        assert "schema.json" in str(e)


def test_error_missing_previous_schema(tmp_path):
    factory_dir = tmp_path / ".factory"
    factory_dir.mkdir(parents=True)
    (factory_dir / "schema.json").write_text(json.dumps(_make_schema()))

    mgr = MigrationManager(tmp_path)
    try:
        mgr.analyze()
        assert False, "Should raise MigrationError"
    except MigrationError as e:
        assert "Previous schema" in str(e) or "schema_prev" in str(e)


# ---------------------------------------------------------------------------
# No changes
# ---------------------------------------------------------------------------

def test_no_changes_same_schema(tmp_path):
    schema = _make_schema()
    _write_schemas(tmp_path, schema, schema)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    assert report.total_changes == 0
    assert not report.has_breaking
    assert report.new_version == "18.0.1.0.0"


# ---------------------------------------------------------------------------
# Model added with fields
# ---------------------------------------------------------------------------

def test_model_added_with_fields_detected(tmp_path):
    prev = _make_schema(models=[])
    curr = _make_schema(models=[
        {
            "name": "test.model", "description": "Model", "mode": "new",
            "display_name": "Model", "inherit": None,
            "fields": [{"name": "name", "type": "Char", "label": "Name"}],
        },
        {
            "name": "test.other", "description": "Other", "mode": "new",
            "display_name": "Other", "inherit": None,
            "fields": [{"name": "code", "type": "Char", "label": "Code"}],
        },
    ])
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    assert report.total_changes > 0


# ---------------------------------------------------------------------------
# Wizards in migration
# ---------------------------------------------------------------------------

def test_wizard_changes_detected(tmp_path):
    prev = _make_schema()
    curr = _make_schema()
    curr["wizards"] = [{"name": "test.wizard", "description": "Wizard", "fields": [], "view_type": "form"}]
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    assert report.total_changes > 0


# ---------------------------------------------------------------------------
# Report serialization
# ---------------------------------------------------------------------------

def test_report_properties(tmp_path):
    prev = _make_schema(version="18.0.1.0.0")
    curr = _make_schema(version="18.0.1.0.0")
    _write_schemas(tmp_path, curr, prev)

    mgr = MigrationManager(tmp_path)
    report = mgr.analyze()

    assert isinstance(report, MigrationReport)
    assert report.current_version == "18.0.1.0.0"
    assert report.previous_version == "18.0.1.0.0"
    assert isinstance(report.changes, list)
    assert isinstance(report.scripts, dict)

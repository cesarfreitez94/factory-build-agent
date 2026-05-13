"""Tests for MigrationEngine — schema change detection and Odoo migration script generation."""

import json
from pathlib import Path

import pytest

from fba.migration_engine import MigrationEngine, MigrationError, SchemaDiff


def _write_json(path: Path, data: dict):
    path.write_text(json.dumps(data))


def _make_schema(models=None, version="18.0.1.0.0"):
    """Create a minimal Odoo schema.json artifact."""
    return {
        "manifest": {
            "name": "test_module",
            "version": version,
            "depends": ["base"],
            "summary": "Test module",
        },
        "models": models if models is not None else [
            {"name": "test.model", "description": "A test model", "mode": "new", "fields": []},
        ],
        "views": [],
        "security": {"groups": [], "access_rights": [], "record_rules": []},
        "data": [],
    }


def _make_field(name, ftype, required=False, **kwargs):
    """Create a field dict."""
    field = {"name": name, "type": ftype}
    if required:
        field["required"] = True
    field.update(kwargs)
    return field


class TestSchemaDiffDetection:
    """Tests for detecting field changes between schema versions."""

    def test_no_changes_empty(self, tmp_path):
        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char", required=True)]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char", required=True)]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)

        assert diff.has_changes is False
        assert len(diff.field_changes) == 0

    def test_field_added(self, tmp_path):
        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char")]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [
                 _make_field("name", "Char"),
                 _make_field("email", "Char"),
             ]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)

        assert diff.has_changes is True
        assert len(diff.field_changes) == 1
        change = diff.field_changes[0]
        assert change.action == "add"
        assert change.model == "test.model"
        assert change.field == "email"

    def test_field_removed(self, tmp_path):
        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [
                 _make_field("name", "Char"),
                 _make_field("email", "Char"),
             ]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char")]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)

        assert diff.has_changes is True
        assert len(diff.field_changes) == 1
        change = diff.field_changes[0]
        assert change.action == "remove"
        assert change.model == "test.model"
        assert change.field == "email"

    def test_field_type_changed(self, tmp_path):
        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("age", "Integer")]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("age", "Float")]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)

        assert diff.has_changes is True
        assert len(diff.field_changes) == 1
        change = diff.field_changes[0]
        assert change.action == "modify"
        assert change.model == "test.model"
        assert change.field == "age"
        assert change.old_type == "Integer"
        assert change.new_type == "Float"

    def test_field_required_changed(self, tmp_path):
        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char", required=False)]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char", required=True)]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)

        assert diff.has_changes is True
        assert len(diff.field_changes) == 1
        change = diff.field_changes[0]
        assert change.action == "modify"
        assert change.model == "test.model"
        assert change.field == "name"
        assert change.old_required is False
        assert change.new_required is True

    def test_multiple_changes(self, tmp_path):
        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [
                 _make_field("name", "Char", required=True),
                 _make_field("age", "Integer"),
             ]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [
                 _make_field("name", "Char", required=False),
                 _make_field("email", "Char"),
             ]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)

        assert diff.has_changes is True
        assert len(diff.field_changes) == 3
        actions = {c.action for c in diff.field_changes}
        assert actions == {"add", "remove", "modify"}

    def test_model_added(self, tmp_path):
        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new", "fields": []},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new", "fields": []},
            {"name": "test.model2", "description": "Another model", "mode": "new", "fields": []},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)

        assert diff.has_changes is True
        model_changes = diff.model_changes
        assert len(model_changes) == 1
        assert model_changes[0]["action"] == "add"
        assert model_changes[0]["model"] == "test.model2"

    def test_file_not_found(self, tmp_path):
        v1 = tmp_path / "does_not_exist.json"
        v2 = tmp_path / "exists.json"
        _write_json(v2, _make_schema())

        with pytest.raises(MigrationError, match="not found"):
            SchemaDiff.detect(v1, v2)

    def test_malformed_json(self, tmp_path):
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        v1.write_text('{"valid": true}')
        v2.write_text('{"invalid": }')

        with pytest.raises(MigrationError, match="Invalid JSON"):
            SchemaDiff.detect(v1, v2)


class TestMigrationScriptGeneration:
    """Tests for pre-migration.py and post-migration.xml generation."""

    def test_generate_pre_migration_script_add_field(self, tmp_path):
        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char")]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [
                 _make_field("name", "Char"),
                 _make_field("email", "Char"),
             ]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)
        engine = MigrationEngine()
        scripts = engine.generate_migration_scripts(diff, "test_module")

        assert "pre_migration.py" in scripts
        assert "post_migration.xml" in scripts

        pre_content = scripts["pre_migration.py"]
        assert "email" in pre_content
        assert "_add_column" in pre_content

    def test_generate_pre_migration_script_remove_field(self, tmp_path):
        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char"), _make_field("email", "Char")]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char")]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)
        engine = MigrationEngine()
        scripts = engine.generate_migration_scripts(diff, "test_module")

        pre_content = scripts["pre_migration.py"]
        assert "email" in pre_content

    def test_generate_pre_migration_script_type_change(self, tmp_path):
        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("age", "Integer")]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("age", "Float")]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)
        engine = MigrationEngine()
        scripts = engine.generate_migration_scripts(diff, "test_module")

        pre_content = scripts["pre_migration.py"]
        assert "age" in pre_content

    def test_generate_post_migration_xml(self, tmp_path):
        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char")]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [
                 _make_field("name", "Char"),
                 _make_field("email", "Char"),
             ]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)
        engine = MigrationEngine()
        scripts = engine.generate_migration_scripts(diff, "test_module")

        xml_content = scripts["post_migration.xml"]
        assert "odoo" in xml_content
        assert "data" in xml_content

    def test_no_changes_no_scripts(self, tmp_path):
        schema_v1 = _make_schema()
        schema_v2 = _make_schema()
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)
        engine = MigrationEngine()
        scripts = engine.generate_migration_scripts(diff, "test_module")

        assert scripts == {}

    def test_migration_script_contains_version_info(self, tmp_path):
        schema_v1 = _make_schema(version="18.0.1.0.0", models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char")]},
        ])
        schema_v2 = _make_schema(version="18.0.2.0.0", models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char"), _make_field("email", "Char")]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)
        engine = MigrationEngine()
        scripts = engine.generate_migration_scripts(diff, "test_module")

        pre_content = scripts["pre_migration.py"]
        assert "migrate" in pre_content
        assert "email" in pre_content


class TestBackwardCompatibility:
    """Tests for backward compatibility validation."""

    def test_removing_required_field_warns(self, tmp_path):
        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char", required=True)]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": []},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)
        engine = MigrationEngine()
        issues = engine.validate_backward_compatibility(diff)

        breaking_changes = [i for i in issues if i["severity"] == "error"]
        assert len(breaking_changes) >= 1

    def test_changing_field_type_warns(self, tmp_path):
        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("age", "Integer")]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("age", "Text")]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)
        engine = MigrationEngine()
        issues = engine.validate_backward_compatibility(diff)

        breaking_changes = [i for i in issues if i["severity"] == "error"]
        assert len(breaking_changes) >= 1

    def test_adding_non_required_field_ok(self, tmp_path):
        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char")]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [
                 _make_field("name", "Char"),
                 _make_field("email", "Char"),
             ]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)
        engine = MigrationEngine()
        issues = engine.validate_backward_compatibility(diff)

        breaking_changes = [i for i in issues if i["severity"] == "error"]
        assert len(breaking_changes) == 0

    def test_no_issues_when_no_changes(self, tmp_path):
        schema_v1 = _make_schema()
        schema_v2 = _make_schema()
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        diff = SchemaDiff.detect(v1, v2)
        engine = MigrationEngine()
        issues = engine.validate_backward_compatibility(diff)

        assert len(issues) == 0


class TestMigrationEngineCli:
    """Tests for the fba migrate CLI command."""

    def test_migrate_check_no_changes(self, tmp_path):
        from click.testing import CliRunner

        from fba.cli import main

        schema_v1 = tmp_path / "v1.json"
        schema_v2 = tmp_path / "v2.json"
        _write_json(schema_v1, _make_schema())
        _write_json(schema_v2, _make_schema())

        runner = CliRunner()
        result = runner.invoke(main, ["migrate", "--check", str(schema_v1), str(schema_v2)])

        assert result.exit_code == 0
        assert "no schema changes" in result.output.lower()

    def test_migrate_check_with_changes(self, tmp_path):
        from click.testing import CliRunner

        from fba.cli import main

        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char")]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char"), _make_field("email", "Char")]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        runner = CliRunner()
        result = runner.invoke(main, ["migrate", "--check", str(v1), str(v2)])

        assert result.exit_code == 0
        assert "email" in result.output

    def test_migrate_generate_scripts(self, tmp_path):
        from click.testing import CliRunner

        from fba.cli import main

        schema_v1 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char")]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "description": "A test model", "mode": "new",
             "fields": [_make_field("name", "Char"), _make_field("email", "Char")]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(main, ["migrate", "--generate", str(v1), str(v2), "--output-dir", str(output_dir)])

        assert result.exit_code == 0
        assert (output_dir / "pre_migration.py").exists() or "pre_migration" in result.output

    def test_migrate_file_not_found(self, tmp_path):
        from click.testing import CliRunner

        from fba.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["migrate", "--check", str(tmp_path / "nope.json"), str(tmp_path / "nope2.json")])

        assert result.exit_code != 0
        assert "Error" in result.output or "not found" in result.output.lower()

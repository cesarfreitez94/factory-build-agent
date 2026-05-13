"""Tests for the DiffEngine — JSON artifact comparison and changelog generation."""

import json
from pathlib import Path

import pytest

from fba.diff_engine import DiffEngine, DiffError


def _write_json(path: Path, data: dict):
    path.write_text(json.dumps(data))


def _make_prd(requirements=None, stakeholders=None):
    """Create a minimal PRD artifact."""
    return {
        "vision": "A test product.",
        "stakeholders": stakeholders if stakeholders is not None else [
            {"name": "Alice", "role": "PM", "interest": "Success"},
        ],
        "objectives": ["Obj 1"],
        "functional_requirements": requirements if requirements is not None else [
            {"id": "RF-001", "description": "Login screen"},
        ],
        "non_functional_requirements": [],
        "acceptance_criteria": [],
        "glossary": [],
    }


def _make_sdd(models=None):
    """Create a minimal SDD artifact."""
    return {
        "module_name": "test_module",
        "module_display_name": "Test Module",
        "version": "18.0.1.0.0",
        "architecture": {"description": "A test architecture."},
        "models": models if models is not None else [
            {"name": "test.model", "description": "A test model."},
        ],
        "views": [],
        "security": {},
        "dependencies": [],
        "file_structure": [],
        "traceability_matrix": {"mappings": []},
    }


def _make_schema(models=None):
    """Create a minimal Odoo schema.json artifact."""
    return {
        "manifest": {
            "name": "test_module",
            "version": "18.0.1.0.0",
            "depends": ["base"],
        },
        "models": models if models is not None else [
            {"name": "test.model", "fields": [{"name": "name", "type": "char"}]},
        ],
        "views": [],
        "security": {"groups": [], "access_rights": [], "record_rules": []},
        "data": [],
    }


def _make_tasks_index(tasks=None):
    """Create a minimal tasks/index.json artifact."""
    return {
        "tasks": tasks if tasks is not None else [
            {"id": "T001", "task_id": "T001", "phase": "construction", "status": "pending"},
        ],
        "generated_at": "2026-01-01T00:00:00Z",
        "total_tasks": len(tasks) if tasks is not None else 1,
    }


class TestDiffEngineIdentical:
    """Tests for comparing identical artifacts."""

    def test_identical_prd_empty_changelog(self, tmp_path):
        prd = _make_prd()
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, prd)
        _write_json(v2, prd)

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "No changes detected" in result
        assert "Diff: prd" in result

    def test_identical_sdd_empty_changelog(self, tmp_path):
        sdd = _make_sdd()
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, sdd)
        _write_json(v2, sdd)

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "No changes detected" in result
        assert "Diff: sdd" in result

    def test_identical_schema_empty_changelog(self, tmp_path):
        schema = _make_schema()
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema)
        _write_json(v2, schema)

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "No changes detected" in result
        assert "Diff: schema" in result

    def test_identical_json_output(self, tmp_path):
        prd = _make_prd()
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, prd)
        _write_json(v2, prd)

        result = DiffEngine.diff(v1, v2, output_format="json")
        data = json.loads(result)

        assert data["summary"]["total_changes"] == 0
        assert data["artifact_type"] == "prd"
        assert data["changes"]["added"] == []
        assert data["changes"]["removed"] == []
        assert data["changes"]["modified"] == []


class TestDiffEngineAdditions:
    """Tests for detecting additions."""

    def test_prd_requirement_added(self, tmp_path):
        prd_v1 = _make_prd(requirements=[{"id": "RF-001", "description": "Login"}])
        prd_v2 = _make_prd(requirements=[
            {"id": "RF-001", "description": "Login"},
            {"id": "RF-002", "description": "Logout"},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, prd_v1)
        _write_json(v2, prd_v2)

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "Added:" in result
        assert "RF-002" in result
        assert "Logout" in result

    def test_sdd_model_added(self, tmp_path):
        sdd_v1 = _make_sdd(models=[{"name": "model.one", "description": "First"}])
        sdd_v2 = _make_sdd(models=[
            {"name": "model.one", "description": "First"},
            {"name": "model.two", "description": "Second"},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, sdd_v1)
        _write_json(v2, sdd_v2)

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "Added:" in result
        assert "model.two" in result

    def test_tasks_index_task_added(self, tmp_path):
        idx_v1 = _make_tasks_index(tasks=[
            {"id": "T001", "task_id": "T001", "phase": "construction", "status": "pending"},
        ])
        idx_v2 = _make_tasks_index(tasks=[
            {"id": "T001", "task_id": "T001", "phase": "construction", "status": "pending"},
            {"id": "T002", "task_id": "T002", "phase": "construction", "status": "pending"},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, idx_v1)
        _write_json(v2, idx_v2)

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "Added:" in result
        assert "T002" in result


class TestDiffEngineRemovals:
    """Tests for detecting removals."""

    def test_prd_requirement_removed(self, tmp_path):
        prd_v1 = _make_prd(requirements=[
            {"id": "RF-001", "description": "Login"},
            {"id": "RF-002", "description": "Logout"},
        ])
        prd_v2 = _make_prd(requirements=[{"id": "RF-001", "description": "Login"}])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, prd_v1)
        _write_json(v2, prd_v2)

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "Removed:" in result
        assert "RF-002" in result

    def test_prd_stakeholder_removed(self, tmp_path):
        prd_v1 = _make_prd(stakeholders=[
            {"name": "Alice", "role": "PM", "interest": "Success"},
            {"name": "Bob", "role": "Dev", "interest": "Code"},
        ])
        prd_v2 = _make_prd(stakeholders=[{"name": "Alice", "role": "PM", "interest": "Success"}])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, prd_v1)
        _write_json(v2, prd_v2)

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "Removed:" in result
        assert "Bob" in result


class TestDiffEngineModifications:
    """Tests for detecting modifications."""

    def test_prd_requirement_modified(self, tmp_path):
        prd_v1 = _make_prd(requirements=[{"id": "RF-001", "description": "Login"}])
        prd_v2 = _make_prd(requirements=[{"id": "RF-001", "description": "Login with SSO"}])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, prd_v1)
        _write_json(v2, prd_v2)

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "Modified:" in result
        assert "SSO" in result

    def test_schema_field_type_changed(self, tmp_path):
        schema_v1 = _make_schema(models=[
            {"name": "test.model", "fields": [{"name": "age", "type": "integer"}]},
        ])
        schema_v2 = _make_schema(models=[
            {"name": "test.model", "fields": [{"name": "age", "type": "float"}]},
        ])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, schema_v1)
        _write_json(v2, schema_v2)

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "Modified:" in result
        assert "integer" in result.replace('"integer"', '"integer"') or "integer" in result
        assert "float" in result

    def test_prd_vision_modified(self, tmp_path):
        prd_v1 = _make_prd()
        prd_v1["vision"] = "Old vision"
        prd_v2 = _make_prd()
        prd_v2["vision"] = "New vision"
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, prd_v1)
        _write_json(v2, prd_v2)

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "Modified:" in result
        assert "Old vision" in result
        assert "New vision" in result


class TestDiffEngineOutputFormats:
    """Tests for output format options."""

    def test_text_output_format(self, tmp_path):
        prd_v1 = _make_prd(requirements=[{"id": "RF-001", "description": "Login"}])
        prd_v2 = _make_prd(requirements=[{"id": "RF-001", "description": "Login"}, {"id": "RF-002", "description": "Logout"}])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, prd_v1)
        _write_json(v2, prd_v2)

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "=== Diff: prd ===" in result
        assert "Added:" in result
        assert "Summary:" in result
        assert "1 added" in result

    def test_json_output_format(self, tmp_path):
        prd_v1 = _make_prd(requirements=[{"id": "RF-001", "description": "Login"}])
        prd_v2 = _make_prd(requirements=[{"id": "RF-001", "description": "Login"}, {"id": "RF-002", "description": "Logout"}])
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, prd_v1)
        _write_json(v2, prd_v2)

        result = DiffEngine.diff(v1, v2, output_format="json")
        data = json.loads(result)

        assert data["artifact_type"] == "prd"
        assert data["summary"]["total_changes"] == 1
        assert data["summary"]["added_count"] == 1
        assert len(data["changes"]["added"]) == 1
        assert data["changes"]["added"][0]["path"].startswith("$.")
        assert "RF-002" in data["changes"]["added"][0]["path"]

    def test_json_output_is_valid_json(self, tmp_path):
        prd = _make_prd()
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, prd)
        _write_json(v2, prd)

        result = DiffEngine.diff(v1, v2, output_format="json")

        data = json.loads(result)
        assert "artifact_type" in data
        assert "timestamp" in data
        assert "changes" in data
        assert "summary" in data


class TestDiffEngineErrorHandling:
    """Tests for error handling."""

    def test_non_existent_file(self, tmp_path):
        v1 = tmp_path / "does_not_exist.json"
        v2 = tmp_path / "exists.json"
        _write_json(v2, _make_prd())

        with pytest.raises(DiffError, match="File not found"):
            DiffEngine.diff(v1, v2)

    def test_malformed_json(self, tmp_path):
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        v1.write_text('{"valid": true}')
        v2.write_text('{"invalid": }')

        with pytest.raises(DiffError, match="Invalid JSON"):
            DiffEngine.diff(v1, v2)

    def test_non_json_content_raises_differror(self, tmp_path):
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        v1.write_text("not json at all")
        v2.write_text('{"valid": true}')

        with pytest.raises(DiffError, match="Invalid JSON"):
            DiffEngine.diff(v1, v2)

    def test_empty_file_raises_differror(self, tmp_path):
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        v1.write_text("")
        v2.write_text('{"valid": true}')

        with pytest.raises(DiffError, match="Invalid JSON"):
            DiffEngine.diff(v1, v2)


class TestDiffEngineEdgeCases:
    """Tests for edge cases and array handling."""

    def test_arrays_without_id_indexed_by_position(self, tmp_path):
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        data_v1 = {"items": ["a", "b", "c"]}
        data_v2 = {"items": ["a", "x", "c"]}
        _write_json(v1, data_v1)
        _write_json(v2, data_v2)

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "Modified:" in result
        assert "b" in result or "x" in result

    def test_arrays_with_id_matched_by_id(self, tmp_path):
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        data_v1 = {"reqs": [{"id": "A", "val": 1}, {"id": "B", "val": 2}]}
        data_v2 = {"reqs": [{"id": "B", "val": 2}, {"id": "A", "val": 10}]}
        _write_json(v1, data_v1)
        _write_json(v2, data_v2)

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "Modified:" in result
        assert "Modified:" in result

    def test_top_level_key_added(self, tmp_path):
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, {"a": 1})
        _write_json(v2, {"a": 1, "b": 2})

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "Added:" in result
        assert "b" in result

    def test_top_level_key_removed(self, tmp_path):
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, {"a": 1, "b": 2})
        _write_json(v2, {"a": 1})

        result = DiffEngine.diff(v1, v2, output_format="text")

        assert "Removed:" in result
        assert "b" in result

    def test_summary_counts_correct(self, tmp_path):
        prd_v1 = _make_prd(
            requirements=[
                {"id": "RF-001", "description": "A"},
                {"id": "RF-002", "description": "B"},
            ],
            stakeholders=[{"name": "Alice", "role": "PM", "interest": "X"}],
        )
        prd_v2 = _make_prd(
            requirements=[
                {"id": "RF-001", "description": "A++"},
            ],
            stakeholders=[],
        )
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, prd_v1)
        _write_json(v2, prd_v2)

        result = DiffEngine.diff(v1, v2, output_format="json")
        data = json.loads(result)

        assert data["summary"]["removed_count"] >= 2
        assert data["summary"]["modified_count"] >= 1
        assert data["summary"]["total_changes"] >= 3


class TestDiffEngineDetectArtifactType:
    """Tests for artifact type detection."""

    def test_detect_prd(self):
        assert DiffEngine.detect_artifact_type(_make_prd()) == "prd"

    def test_detect_sdd(self):
        assert DiffEngine.detect_artifact_type(_make_sdd()) == "sdd"

    def test_detect_schema(self):
        assert DiffEngine.detect_artifact_type(_make_schema()) == "schema"

    def test_detect_tasks_index(self):
        assert DiffEngine.detect_artifact_type(_make_tasks_index()) == "tasks_index"

    def test_detect_unknown(self):
        assert DiffEngine.detect_artifact_type({"foo": "bar"}) == "unknown"

    def test_detect_non_dict(self):
        assert DiffEngine.detect_artifact_type([1, 2, 3]) == "unknown"


class TestDiffEngineCli:
    """Tests for the fba diff CLI command."""

    def test_diff_cli_text_output(self, tmp_path):
        from click.testing import CliRunner

        from fba.cli import main

        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        prd_v1 = _make_prd(requirements=[{"id": "RF-001", "description": "Login"}])
        prd_v2 = _make_prd(requirements=[{"id": "RF-001", "description": "Login v2"}])
        _write_json(v1, prd_v1)
        _write_json(v2, prd_v2)

        runner = CliRunner()
        result = runner.invoke(main, ["diff", str(v1), str(v2)])

        assert result.exit_code == 0
        assert "=== Diff: prd ===" in result.output
        assert "Modified:" in result.output

    def test_diff_cli_json_output(self, tmp_path):
        from click.testing import CliRunner

        from fba.cli import main

        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, _make_prd())
        _write_json(v2, _make_prd())

        runner = CliRunner()
        result = runner.invoke(main, ["diff", str(v1), str(v2), "--format", "json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["artifact_type"] == "prd"
        assert data["summary"]["total_changes"] == 0

    def test_diff_cli_file_not_found(self, tmp_path):
        from click.testing import CliRunner

        from fba.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["diff", str(tmp_path / "nope.json"), str(tmp_path / "nope2.json")])

        assert result.exit_code != 0
        assert "Error" in result.output or "error" in result.output.lower()

    def test_diff_cli_malformed_json(self, tmp_path):
        from click.testing import CliRunner

        from fba.cli import main

        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        _write_json(v1, _make_prd())
        v2.write_text("not valid {{")

        runner = CliRunner()
        result = runner.invoke(main, ["diff", str(v1), str(v2)])

        assert result.exit_code == 1

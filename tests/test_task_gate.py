"""Tests for the task_files_exist gate rule and tasks gate."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from fba.cli import main
from fba.gate import GateRunner


@pytest.fixture
def state_with_tasks_gate(tmp_path):
    factory_dir = tmp_path / ".factory"
    factory_dir.mkdir()

    schemas_dir = factory_dir / "schemas"
    schemas_dir.mkdir()

    tasks_dir = factory_dir / "tasks"
    tasks_dir.mkdir()

    state = {
        "project": "test",
        "current_phase": "tasks",
        "methodology": "BABOK",
        "phases": {
            "tasks": {"status": "in_progress", "agent": "planificador"},
            "construction": {"status": "pending", "agent": "constructor"},
        },
        "valid_transitions": {
            "tasks": ["construction"],
        },
        "gates": {
            "tasks": {
                "description": "Validates task index and individual task files",
                "owner_agent": "planificador",
                "rules": [
                    {
                        "type": "artifact_exists",
                        "rule_name": "task_index_exists",
                        "path": ".factory/tasks/index.json",
                    },
                    {
                        "type": "content_check",
                        "rule_name": "task_index_content_minimum",
                        "path": ".factory/tasks/index.json",
                        "checks": {"min_tasks": 1},
                    },
                    {
                        "type": "task_files_exist",
                        "rule_name": "all_task_files_exist",
                        "index_path": ".factory/tasks/index.json",
                    },
                ],
            },
        },
        "artifacts": {},
        "context": {},
    }
    (factory_dir / "state.json").write_text(json.dumps(state, indent=2))
    return tmp_path


def _create_valid_index_and_tasks(project_path: Path):
    tasks_dir = project_path / ".factory" / "tasks"

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
                "name": "Vistas",
                "file": "T002-vistas.json",
                "dependencies": ["T001"],
                "order": 2,
                "estimated_effort": "medium",
                "sdd_components": ["views.form"],
            },
        ],
    }
    (tasks_dir / "index.json").write_text(json.dumps(index, indent=2))

    task1 = {
        "id": "T001",
        "name": "Modelos",
        "description": "Generar los modelos Odoo para el modulo.",
        "components": [
            {
                "type": "model",
                "name": "vehicle.vehicle",
                "description": "Modelo principal de vehiculo",
                "sdd_reference": "models.vehicle",
            },
        ],
        "files_to_generate": ["models/__init__.py", "models/vehicle.py"],
        "dependencies": [],
    }
    (tasks_dir / "T001-modelos.json").write_text(json.dumps(task1, indent=2))

    task2 = {
        "id": "T002",
        "name": "Vistas",
        "description": "Generar las vistas XML para el modulo.",
        "components": [
            {
                "type": "view",
                "name": "vehicle.form",
                "description": "Formulario de vehiculo",
                "view_type": "form",
                "model": "vehicle.vehicle",
                "view_fields": ["plate", "brand_id"],
                "sdd_reference": "views.form",
            },
        ],
        "files_to_generate": ["views/vehicle_views.xml"],
        "dependencies": ["T001"],
    }
    (tasks_dir / "T002-vistas.json").write_text(json.dumps(task2, indent=2))


class TestTaskFilesExistRule:
    def test_all_files_exist_and_valid(self, state_with_tasks_gate):
        _create_valid_index_and_tasks(state_with_tasks_gate)
        runner = GateRunner(state_with_tasks_gate)
        result = runner.check_phase("tasks")
        assert result.passed is True
        assert result.error_count == 0
        for r in result.results:
            assert r.passed is True

    def test_index_not_found(self, state_with_tasks_gate):
        runner = GateRunner(state_with_tasks_gate)
        result = runner.check_phase("tasks")

        task_files_rule = [r for r in result.results if r.rule == "all_task_files_exist"][0]
        assert task_files_rule.passed is False
        assert "not found" in task_files_rule.message

    def test_index_invalid_json(self, state_with_tasks_gate):
        (state_with_tasks_gate / ".factory" / "tasks" / "index.json").write_text("not json")
        runner = GateRunner(state_with_tasks_gate)
        result = runner.check_phase("tasks")

        task_files_rule = [r for r in result.results if r.rule == "all_task_files_exist"][0]
        assert task_files_rule.passed is False
        assert "invalid json" in task_files_rule.message.lower()

    def test_index_has_no_tasks(self, state_with_tasks_gate):
        index = {
            "module_name": "test",
            "total_tasks": 0,
            "tasks": [],
        }
        (state_with_tasks_gate / ".factory" / "tasks" / "index.json").write_text(json.dumps(index))
        runner = GateRunner(state_with_tasks_gate)
        result = runner.check_phase("tasks")

        task_files_rule = [r for r in result.results if r.rule == "all_task_files_exist"][0]
        assert task_files_rule.passed is False
        assert "no tasks" in task_files_rule.message.lower()

    def test_task_file_missing(self, state_with_tasks_gate):
        tasks_dir = state_with_tasks_gate / ".factory" / "tasks"
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
        (tasks_dir / "index.json").write_text(json.dumps(index))
        runner = GateRunner(state_with_tasks_gate)
        result = runner.check_phase("tasks")

        task_files_rule = [r for r in result.results if r.rule == "all_task_files_exist"][0]
        assert task_files_rule.passed is False
        assert "Missing task files" in task_files_rule.message

    def test_task_file_empty(self, state_with_tasks_gate):
        tasks_dir = state_with_tasks_gate / ".factory" / "tasks"
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
        (tasks_dir / "index.json").write_text(json.dumps(index))
        (tasks_dir / "T001-modelos.json").write_text("   ")
        runner = GateRunner(state_with_tasks_gate)
        result = runner.check_phase("tasks")

        task_files_rule = [r for r in result.results if r.rule == "all_task_files_exist"][0]
        assert task_files_rule.passed is False
        assert "Empty task files" in task_files_rule.message

    def test_task_file_invalid_json(self, state_with_tasks_gate):
        tasks_dir = state_with_tasks_gate / ".factory" / "tasks"
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
        (tasks_dir / "index.json").write_text(json.dumps(index))
        (tasks_dir / "T001-modelos.json").write_text("not valid json")
        runner = GateRunner(state_with_tasks_gate)
        result = runner.check_phase("tasks")

        task_files_rule = [r for r in result.results if r.rule == "all_task_files_exist"][0]
        assert task_files_rule.passed is False
        assert "Invalid JSON" in task_files_rule.message

    def test_task_file_no_file_field(self, state_with_tasks_gate):
        tasks_dir = state_with_tasks_gate / ".factory" / "tasks"
        index = {
            "module_name": "vehicle_registry",
            "total_tasks": 1,
            "tasks": [
                {
                    "id": "T001",
                    "name": "Modelos",
                    "dependencies": [],
                    "order": 1,
                    "estimated_effort": "high",
                    "sdd_components": ["models.vehicle"],
                },
            ],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index))
        runner = GateRunner(state_with_tasks_gate)
        result = runner.check_phase("tasks")

        task_files_rule = [r for r in result.results if r.rule == "all_task_files_exist"][0]
        assert task_files_rule.passed is False
        assert "Missing task files" in task_files_rule.message

    def test_task_file_schema_failure(self, state_with_tasks_gate):
        tasks_dir = state_with_tasks_gate / ".factory" / "tasks"
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
        (tasks_dir / "index.json").write_text(json.dumps(index))
        bad_task = {
            "id": "T001",
            "name": "X",
            "description": "too short",
            "components": [],
            "files_to_generate": [],
            "dependencies": [],
        }
        (tasks_dir / "T001-modelos.json").write_text(json.dumps(bad_task))
        runner = GateRunner(state_with_tasks_gate)
        result = runner.check_phase("tasks")

        task_files_rule = [r for r in result.results if r.rule == "all_task_files_exist"][0]
        assert task_files_rule.passed is False
        assert "Schema validation failed" in task_files_rule.message


class TestTasksGateIntegration:
    def test_full_gate_passes(self, state_with_tasks_gate):
        _create_valid_index_and_tasks(state_with_tasks_gate)
        runner = GateRunner(state_with_tasks_gate)
        result = runner.check_phase("tasks")
        assert result.passed is True
        assert len(result.results) == 3
        assert result.error_count == 0

    def test_full_gate_fails_missing_index(self, state_with_tasks_gate):
        runner = GateRunner(state_with_tasks_gate)
        result = runner.check_phase("tasks")
        assert result.passed is False
        assert result.error_count > 0

    def test_content_check_fails_zero_tasks(self, state_with_tasks_gate):
        index = {
            "module_name": "test",
            "total_tasks": 0,
            "tasks": [],
        }
        (state_with_tasks_gate / ".factory" / "tasks" / "index.json").write_text(json.dumps(index))
        runner = GateRunner(state_with_tasks_gate)
        result = runner.check_phase("tasks")

        content_rule = [r for r in result.results if r.rule == "task_index_content_minimum"][0]
        assert content_rule.passed is False
        assert "Expected at least" in content_rule.message


class TestCLITasksGate:
    def test_gate_tasks_cli_passes(self, state_with_tasks_gate):
        _create_valid_index_and_tasks(state_with_tasks_gate)
        runner_cli = CliRunner()
        result = runner_cli.invoke(main, ["gate", "tasks", "-d", str(state_with_tasks_gate)])
        assert result.exit_code == 0
        assert "✅ Gate:" in result.output

    def test_gate_tasks_cli_fails(self, state_with_tasks_gate):
        runner_cli = CliRunner()
        result = runner_cli.invoke(main, ["gate", "tasks", "-d", str(state_with_tasks_gate)])
        assert result.exit_code == 1
        assert "❌ Gate:" in result.output
        assert "task_index_exists" in result.output

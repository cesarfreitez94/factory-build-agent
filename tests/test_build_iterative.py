"""Tests for the iterative build flow and command files."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from fba.cli import main
from fba.gate import GateError, GateRunner
from fba.state import StateManager


TESTS_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = TESTS_DIR.parent / "templates"


class TestBuildCommandFrontmatter:
    def test_build_command_exists(self):
        cmd_path = TEMPLATES_DIR / ".opencode" / "commands" / "fba:build.md"
        assert cmd_path.is_file()

    def test_build_command_has_frontmatter(self):
        import yaml
        cmd_path = TEMPLATES_DIR / ".opencode" / "commands" / "fba:build.md"
        text = cmd_path.read_text()
        parts = text.split("---", 2)
        assert len(parts) >= 3
        frontmatter = yaml.safe_load(parts[1])
        assert frontmatter.get("agent") == "constructor"
        assert "generate" in frontmatter.get("description", "").lower()

    def test_build_command_body_has_iterative_content(self):
        cmd_path = TEMPLATES_DIR / ".opencode" / "commands" / "fba:build.md"
        text = cmd_path.read_text()

        assert "# fba:build" in text
        assert "index.json" in text
        assert "T*.json" in text
        assert "Iterative" in text
        assert "fresh" in text
        assert "task_id" in text
        assert "git commit" in text


class TestTasksCommandFrontmatter:
    def test_tasks_command_exists(self):
        cmd_path = TEMPLATES_DIR / ".opencode" / "commands" / "fba:tasks.md"
        assert cmd_path.is_file()

    def test_tasks_command_has_frontmatter(self):
        import yaml
        cmd_path = TEMPLATES_DIR / ".opencode" / "commands" / "fba:tasks.md"
        text = cmd_path.read_text()
        parts = text.split("---", 2)
        assert len(parts) >= 3
        frontmatter = yaml.safe_load(parts[1])
        assert frontmatter.get("agent") == "planificador"

    def test_tasks_command_body_references_index_and_files(self):
        cmd_path = TEMPLATES_DIR / ".opencode" / "commands" / "fba:tasks.md"
        text = cmd_path.read_text()

        assert "# fba:tasks" in text
        assert "index.json" in text
        assert "T*.json" in text
        assert "task_index.schema.json" in text
        assert "task_item.schema.json" in text
        assert "DO NOT change" in text


class TestTransitionFromTasksToConstruction:
    @pytest.fixture
    def project_with_tasks(self, tmp_path):
        factory_dir = tmp_path / ".factory"
        factory_dir.mkdir()

        schemas_dir = factory_dir / "schemas"
        schemas_dir.mkdir()

        tasks_dir = factory_dir / "tasks"
        tasks_dir.mkdir()

        tasks_dir_created = tasks_dir
        schemas_dir_created = schemas_dir

        schemas = TESTS_DIR.parent / "schemas"
        import shutil
        for schema_file in ["task_index.schema.json", "task_item.schema.json"]:
            src = schemas / schema_file
            if src.exists():
                shutil.copy2(src, schemas_dir_created / schema_file)

        state = {
            "project": "test",
            "current_phase": "tasks",
            "methodology": "BABOK",
            "phases": {
                "planning": {"status": "complete", "agent": "planificador"},
                "tasks": {"status": "in_progress", "agent": "planificador"},
                "construction": {"status": "pending", "agent": "constructor"},
            },
            "valid_transitions": {
                "tasks": ["construction"],
            },
            "gates": {
                "tasks": {
                    "description": "Validates task files",
                    "owner_agent": "planificador",
                    "rules": [
                        {
                            "type": "artifact_exists",
                            "rule_name": "task_index_exists",
                            "path": ".factory/tasks/index.json",
                        },
                        {
                            "type": "content_check",
                            "rule_name": "min_tasks",
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
        }
        (factory_dir / "state.json").write_text(json.dumps(state, indent=2))
        return tmp_path

    def _create_valid_tasks(self, project_path):
        tasks_dir = project_path / ".factory" / "tasks"

        index = {
            "module_name": "test_module",
            "total_tasks": 2,
            "tasks": [
                {
                    "id": "T001",
                    "name": "Modelos",
                    "file": "T001-modelos.json",
                    "dependencies": [],
                    "order": 1,
                    "estimated_effort": "high",
                    "sdd_components": ["models.test"],
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

        for task_file, task_data in [
            ("T001-modelos.json", {
                "id": "T001",
                "name": "Modelos",
                "description": "Generar modelos Odoo para modulo de prueba.",
                "components": [{
                    "type": "model",
                    "name": "test.model",
                    "description": "Modelo de prueba",
                    "sdd_reference": "models.test",
                }],
                "files_to_generate": ["models/__init__.py", "models/test_model.py"],
                "dependencies": [],
            }),
            ("T002-vistas.json", {
                "id": "T002",
                "name": "Vistas",
                "description": "Generar vistas XML para modulo de prueba.",
                "components": [{
                    "type": "view",
                    "name": "test.form",
                    "description": "Formulario de prueba",
                    "view_type": "form",
                    "model": "test.model",
                    "view_fields": ["name"],
                    "sdd_reference": "views.form",
                }],
                "files_to_generate": ["views/test_views.xml"],
                "dependencies": ["T001"],
            }),
        ]:
            (tasks_dir / task_file).write_text(json.dumps(task_data, indent=2))

    def test_transition_blocked_without_tasks(self, project_with_tasks):
        sm = StateManager(project_with_tasks)
        with pytest.raises(GateError) as exc_info:
            sm.transition_to("construction")
        assert exc_info.value.gate_result.phase == "tasks"
        assert exc_info.value.gate_result.error_count > 0

    def test_transition_allowed_with_valid_tasks(self, project_with_tasks):
        self._create_valid_tasks(project_with_tasks)
        sm = StateManager(project_with_tasks)
        state = sm.transition_to("construction")
        assert state["current_phase"] == "construction"
        assert state["phases"]["tasks"]["status"] == "complete"
        assert state["phases"]["construction"]["status"] == "in_progress"

    def test_transition_force_bypasses_tasks_gate(self, project_with_tasks):
        sm = StateManager(project_with_tasks)
        state = sm.transition_to("construction", skip_gates=True)
        assert state["current_phase"] == "construction"

    def test_cli_transition_fails_without_tasks(self, project_with_tasks):
        runner = CliRunner()
        result = runner.invoke(main, ["transition", "construction", "-d", str(project_with_tasks)])
        assert result.exit_code == 1
        assert "Gate 'tasks' failed" in result.output

    def test_cli_transition_passes_with_valid_tasks(self, project_with_tasks):
        self._create_valid_tasks(project_with_tasks)
        runner = CliRunner()
        result = runner.invoke(main, ["transition", "construction", "-d", str(project_with_tasks)])
        assert result.exit_code == 0
        assert "Transitioned" in result.output

        state = json.loads((project_with_tasks / ".factory" / "state.json").read_text())
        assert state["phases"]["tasks"]["status"] == "complete"


class TestOrchestratorPhaseTable:
    def test_orchestrator_references_task_files(self):
        orchestrator_path = TEMPLATES_DIR / ".opencode" / "agents" / "orchestrator.md"
        text = orchestrator_path.read_text()

        assert "tasks/index.json" in text
        assert "T*.json" in text

    def test_orchestrator_context_injection_updated(self):
        orchestrator_path = TEMPLATES_DIR / ".opencode" / "agents" / "orchestrator.md"
        text = orchestrator_path.read_text()

        assert "tasks/index.json" in text


class TestInitStateHasTasksGate:
    def test_init_creates_tasks_gate_in_state(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["init", "-d", str(tmp_path)])
        assert result.exit_code == 0

        state = json.loads((tmp_path / ".factory" / "state.json").read_text())
        assert "tasks" in state["gates"]
        tasks_gate = state["gates"]["tasks"]
        assert tasks_gate["owner_agent"] == "planificador"
        assert len(tasks_gate["rules"]) == 4

        rule_types = [r["type"] for r in tasks_gate["rules"]]
        assert "artifact_exists" in rule_types
        assert "schema" in rule_types
        assert "content_check" in rule_types
        assert "task_files_exist" in rule_types

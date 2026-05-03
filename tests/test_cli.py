"""Tests for the FBA CLI."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from fba import __version__
from fba.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary directory to simulate a project."""
    return tmp_path


def test_cli_version(runner):
    """Verify the CLI shows version."""
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_init_creates_directories(runner, temp_project):
    """Verify fba init creates all expected directories."""
    result = runner.invoke(main, ["init", "-d", str(temp_project)], catch_exceptions=False)

    assert result.exit_code == 0
    assert (temp_project / ".factory").is_dir()
    assert (temp_project / ".opencode").is_dir()
    assert (temp_project / ".opencode" / "commands").is_dir()
    assert (temp_project / ".opencode" / "agents").is_dir()
    assert (temp_project / ".github" / "workflows").is_dir()


def test_init_creates_state_file(runner, temp_project):
    """Verify fba init creates a valid state.json."""
    result = runner.invoke(main, ["init", "-d", str(temp_project)])

    assert result.exit_code == 0

    state_path = temp_project / ".factory" / "state.json"
    assert state_path.is_file()

    state = json.loads(state_path.read_text())
    assert state["current_phase"] == "init"
    assert state["methodology"] == "BABOK"
    assert "project" in state
    assert "phases" in state
    assert "artifacts" in state
    assert state["phases"]["elicitation"]["status"] == "pending"


def test_init_creates_events_log(runner, temp_project):
    """Verify fba init creates events.jsonl with init event."""
    result = runner.invoke(main, ["init", "-d", str(temp_project)])

    assert result.exit_code == 0

    events_path = temp_project / ".factory" / "events.jsonl"
    assert events_path.is_file()

    lines = events_path.read_text().strip().split("\n")
    assert len(lines) == 1

    event = json.loads(lines[0])
    assert event["type"] == "init"
    assert event["agent"] == "fba_cli"


def test_init_creates_agents_md(runner, temp_project):
    """Verify fba init creates agent definition files."""
    result = runner.invoke(main, ["init", "-d", str(temp_project)])

    assert result.exit_code == 0
    assert (temp_project / ".opencode" / "agents" / "orchestrator.md").is_file()


def test_init_creates_slash_commands(runner, temp_project):
    """Verify fba init creates all slash command files."""
    result = runner.invoke(main, ["init", "-d", str(temp_project)])

    assert result.exit_code == 0

    commands_dir = temp_project / ".opencode" / "commands"
    expected_commands = [
        "fba:init.md",
        "fba:elicit.md",
        "fba:specify.md",
        "fba:plan.md",
        "fba:tasks.md",
        "fba:build.md",
        "fba:test.md",
        "fba:review.md",
        "fba:ship.md",
    ]
    for cmd in expected_commands:
        assert (commands_dir / cmd).is_file(), f"Missing command: {cmd}"


def test_init_orchestrator_md_content(runner, temp_project):
    """Verify the orchestrator.md has correct frontmatter and body."""
    result = runner.invoke(main, ["init", "-d", str(temp_project)])
    assert result.exit_code == 0

    import yaml
    path = temp_project / ".opencode" / "agents" / "orchestrator.md"
    text = path.read_text()
    parts = text.split("---", 2)
    assert len(parts) >= 3, "Missing frontmatter delimiters"

    frontmatter = yaml.safe_load(parts[1])
    body = parts[2]

    assert frontmatter["mode"] == "primary"
    assert len(frontmatter["description"]) > 20
    assert "permission" in frontmatter
    assert "Phase Flow" in body or "phase" in body.lower()
    assert "Milestone Completion Protocol" in body


def test_init_creates_github_workflow(runner, temp_project):
    """Verify fba init creates CI workflow template."""
    result = runner.invoke(main, ["init", "-d", str(temp_project)])

    assert result.exit_code == 0
    assert (temp_project / ".github" / "workflows" / "factory-ci.yml").is_file()


def test_init_creates_project_agents_md(runner, temp_project):
    """Verify fba init creates project-level AGENTS.md."""
    result = runner.invoke(main, ["init", "-d", str(temp_project)])

    assert result.exit_code == 0
    agents_path = temp_project / "AGENTS.md"
    assert agents_path.is_file()

    content = agents_path.read_text()
    assert "# Factory Build Agent" in content
    assert "/fba:elicit" in content
    assert "/fba:build" in content


def test_init_fails_if_factory_exists(runner, temp_project):
    """Verify init fails if .factory/ already exists."""
    (temp_project / ".factory").mkdir()
    result = runner.invoke(main, ["init", "-d", str(temp_project)])

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_state_schema_validation(runner, temp_project):
    """Verify the generated state.json validates against state schema."""
    import jsonschema

    result = runner.invoke(main, ["init", "-d", str(temp_project)])
    assert result.exit_code == 0

    state = json.loads((temp_project / ".factory" / "state.json").read_text())

    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "state.schema.json"
    schema = json.loads(schema_path.read_text())

    jsonschema.validate(state, schema)


def test_init_creates_schemas(runner, temp_project):
    """Verify fba init copies schemas to .factory/schemas/."""
    result = runner.invoke(main, ["init", "-d", str(temp_project)])
    assert result.exit_code == 0

    schemas_dir = temp_project / ".factory" / "schemas"
    assert schemas_dir.is_dir()
    schema_files = list(schemas_dir.glob("*.schema.json"))
    assert len(schema_files) >= 1
    assert (schemas_dir / "prd.schema.json").is_file()


class TestStatusCommand:
    def test_status_shows_project_info(self, runner, temp_project):
        runner.invoke(main, ["init", "-d", str(temp_project)])
        result = runner.invoke(main, ["status", "-d", str(temp_project)])
        assert result.exit_code == 0
        assert "Current phase: init" in result.output
        assert "Methodology: BABOK" in result.output

    def test_status_requires_factory(self, runner, temp_project):
        result = runner.invoke(main, ["status", "-d", str(temp_project)])
        assert result.exit_code == 1
        assert "No .factory/ found" in result.output


class TestTransitionCommand:
    def test_valid_transition(self, runner, temp_project):
        runner.invoke(main, ["init", "-d", str(temp_project)])
        result = runner.invoke(main, ["transition", "elicitation", "-d", str(temp_project)])
        assert result.exit_code == 0
        assert "Transitioned" in result.output

        state = json.loads((temp_project / ".factory" / "state.json").read_text())
        assert state["current_phase"] == "elicitation"

    def test_invalid_transition(self, runner, temp_project):
        runner.invoke(main, ["init", "-d", str(temp_project)])
        result = runner.invoke(main, ["transition", "construction", "-d", str(temp_project)])
        assert result.exit_code == 1
        assert "Invalid transition" in result.output


class TestRecordCommand:
    def test_record_event(self, runner, temp_project):
        runner.invoke(main, ["init", "-d", str(temp_project)])
        result = runner.invoke(
            main,
            ["record", "elicitation_start", "--data", '{"stakeholders": 3}', "-d", str(temp_project)],
        )
        assert result.exit_code == 0
        assert "Event 'elicitation_start' recorded" in result.output

        events_path = temp_project / ".factory" / "events.jsonl"
        lines = events_path.read_text().strip().split("\n")
        assert len(lines) == 2

        event = json.loads(lines[1])
        assert event["type"] == "elicitation_start"
        assert event["data"]["stakeholders"] == 3


class TestValidateCommand:
    def test_validate_valid_prd(self, runner, temp_project):
        runner.invoke(main, ["init", "-d", str(temp_project)])

        valid_prd = {
            "vision": "A vehicle registration module for Odoo v18.",
            "stakeholders": [
                {"name": "Admin", "role": "User", "interest": "Track vehicles"}
            ],
            "objectives": ["Automate vehicle registration"],
            "functional_requirements": [
                {
                    "id": "RF-01",
                    "description": "CRUD operations for vehicles",
                    "priority": "high",
                }
            ],
            "non_functional_requirements": [
                {
                    "id": "RNF-01",
                    "description": "Must respond under 2 seconds",
                    "category": "performance",
                    "priority": "medium",
                }
            ],
            "acceptance_criteria": [
                {
                    "id": "CA-01",
                    "criterion": "User can create a vehicle with required fields",
                }
            ],
            "glossary": [
                {"term": "CRUD", "definition": "Create, Read, Update, Delete operations"}
            ],
        }
        art_path = temp_project / ".factory" / "prd.json"
        art_path.write_text(json.dumps(valid_prd))

        result = runner.invoke(main, ["validate", "prd", "-d", str(temp_project)])
        assert result.exit_code == 0
        assert "valid" in result.output

    def test_validate_invalid_prd(self, runner, temp_project):
        runner.invoke(main, ["init", "-d", str(temp_project)])

        invalid_prd = {"vision": "Too short"}  # missing required fields
        art_path = temp_project / ".factory" / "prd.json"
        art_path.write_text(json.dumps(invalid_prd))

        result = runner.invoke(main, ["validate", "prd", "-d", str(temp_project)])
        assert result.exit_code == 1
        assert "validation failed" in result.output

    def test_validate_missing_artifact(self, runner, temp_project):
        runner.invoke(main, ["init", "-d", str(temp_project)])
        result = runner.invoke(main, ["validate", "prd", "-d", str(temp_project)])
        assert "artifact file not found" in result.output

    def test_validate_unknown_artifact(self, runner, temp_project):
        runner.invoke(main, ["init", "-d", str(temp_project)])
        result = runner.invoke(main, ["validate", "nonexistent", "-d", str(temp_project)])
        assert result.exit_code == 1
        assert "No schema found" in result.output

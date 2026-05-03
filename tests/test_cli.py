"""Tests for the FBA CLI."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

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
    assert "0.1.0" in result.output


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


def test_init_creates_agents_yaml(runner, temp_project):
    """Verify fba init creates agent definition files."""
    result = runner.invoke(main, ["init", "-d", str(temp_project)])

    assert result.exit_code == 0
    assert (temp_project / ".opencode" / "agents" / "orchestrator.yaml").is_file()


def test_init_creates_slash_commands(runner, temp_project):
    """Verify fba init creates slash command files."""
    result = runner.invoke(main, ["init", "-d", str(temp_project)])

    assert result.exit_code == 0
    assert (temp_project / ".opencode" / "commands" / "fba:init.md").is_file()


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

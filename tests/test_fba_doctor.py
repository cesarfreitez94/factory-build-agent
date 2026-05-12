import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from fba.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def healthy_project(tmp_path):
    project_dir = tmp_path / "healthy"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()

    state = {
        "project": "test-project",
        "current_phase": "init",
        "phases": {"init": {"status": "in_progress"}},
        "valid_transitions": {},
        "artifacts": {},
    }
    (factory_dir / "state.json").write_text(json.dumps(state, indent=2))

    registry_dir = factory_dir / "schemas"
    registry_dir.mkdir(parents=True, exist_ok=True)

    return project_dir


def test_doctor_healthy_project(runner, healthy_project):
    result = runner.invoke(main, ["doctor", "-d", str(healthy_project)])
    assert result.exit_code in (0, 1)
    output = result.output.lower()
    assert "registry" in output or "state" in output or "writable" in output


def test_doctor_state_missing(runner, tmp_path):
    project_dir = tmp_path / "nostate"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()

    result = runner.invoke(main, ["doctor", "-d", str(project_dir)])
    assert result.exit_code == 2
    assert "state" in result.output.lower()


def test_doctor_state_invalid_json(runner, tmp_path):
    project_dir = tmp_path / "badstate"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()
    (factory_dir / "state.json").write_text("{invalid")

    result = runner.invoke(main, ["doctor", "-d", str(project_dir)])
    assert result.exit_code == 2


def test_doctor_registry_not_loading(runner, tmp_path):
    project_dir = tmp_path / "noregistry"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()
    (factory_dir / "state.json").write_text(json.dumps({"current_phase": "init", "phases": {}, "valid_transitions": {}, "artifacts": {}}))

    result = runner.invoke(main, ["doctor", "-d", str(project_dir)])
    assert result.exit_code in (1, 2)


def test_doctor_verbose_output(runner, healthy_project):
    result = runner.invoke(main, ["doctor", "-d", str(healthy_project), "--verbose"])
    assert result.exit_code in (0, 1, 2)


def test_doctor_json_output(runner, healthy_project):
    result = runner.invoke(main, ["doctor", "-d", str(healthy_project), "--json"])
    assert result.exit_code in (0, 1)
    data = json.loads(result.output)
    assert "status" in data
    assert "checks" in data
    assert "exit_code" in data
    assert data["exit_code"] in (0, 1)


def test_doctor_factory_not_writable(runner, tmp_path):
    project_dir = tmp_path / "readonly"
    project_dir.mkdir()
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir()
    state = {"current_phase": "init", "phases": {}, "valid_transitions": {}, "artifacts": {}}
    (factory_dir / "state.json").write_text(json.dumps(state, indent=2))

    os.chmod(str(factory_dir), 0o444)

    try:
        result = runner.invoke(main, ["doctor", "-d", str(project_dir)])
    finally:
        os.chmod(str(factory_dir), 0o755)

    assert result.exit_code in (1, 2)


def test_doctor_no_factory_dir(runner, tmp_path):
    project_dir = tmp_path / "nofactory"
    project_dir.mkdir()

    result = runner.invoke(main, ["doctor", "-d", str(project_dir)])
    assert result.exit_code == 2

"""Tests for M15 feat/15.3: state concurrency safety warnings."""

import json
import warnings

from click.testing import CliRunner

from fba.cli import main
from fba.state import StateConcurrencyWarning, StateManager


def _write_state(project_dir):
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "project": "concurrency-test",
        "methodology": "BABOK",
        "current_phase": "init",
        "phases": {"init": {"status": "in_progress"}},
        "valid_transitions": {},
        "artifacts": {},
    }
    (factory_dir / "state.json").write_text(json.dumps(state, indent=2))
    return state


def test_state_manager_warns_when_state_changed_after_load(tmp_path):
    state = _write_state(tmp_path)
    manager = StateManager(tmp_path)
    loaded = manager.load()

    state["current_phase"] = "documentation"
    (tmp_path / ".factory" / "state.json").write_text(json.dumps(state, indent=2))

    loaded["current_phase"] = "elicitation"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        manager.save(loaded)

    assert any(issubclass(item.category, StateConcurrencyWarning) for item in caught)


def test_concurrency_diagnostics_ok_without_markers(tmp_path):
    _write_state(tmp_path)

    ok, detail, severity = StateManager(tmp_path).concurrency_diagnostics()

    assert ok is True
    assert severity is None
    assert "No concurrent write markers" in detail


def test_concurrency_diagnostics_warns_on_rollback_marker(tmp_path):
    _write_state(tmp_path)
    (tmp_path / ".factory" / ".rollback_state.json").write_text("{}")

    ok, detail, severity = StateManager(tmp_path).concurrency_diagnostics()

    assert ok is False
    assert severity == "warning"
    assert "rollback marker" in detail


def test_doctor_concurrency_json_includes_check(tmp_path):
    _write_state(tmp_path)
    (tmp_path / ".factory" / ".tmp-state-leftover").write_text("partial")

    runner = CliRunner()
    result = runner.invoke(main, ["doctor", "--concurrency", "--json", "-d", str(tmp_path)])

    assert result.exit_code in (1, 2)
    payload = json.loads(result.output)
    concurrency = next(check for check in payload["checks"] if check["label"] == "concurrency")
    assert concurrency["severity"] == "warning"
    assert "atomic temp files" in concurrency["detail"]

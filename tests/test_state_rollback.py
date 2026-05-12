import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from fba.state import StateManager


def _init_project_dir(tmp_path):
    factory_dir = tmp_path / ".factory"
    factory_dir.mkdir()
    state = {
        "current_phase": "init",
        "phases": {
            "init": {"status": "in_progress"},
            "elicitation": {"status": "pending"},
        },
        "valid_transitions": {"init": ["elicitation"]},
        "artifacts": {},
    }
    (factory_dir / "state.json").write_text(json.dumps(state, indent=2))
    return tmp_path, state


def test_transition_success_no_residual_rollback_files(tmp_path):
    project_dir, _ = _init_project_dir(tmp_path)
    sm = StateManager(project_dir)

    result = sm.transition_to("elicitation", skip_gates=True)

    assert result["current_phase"] == "elicitation"
    assert sm.current_phase == "elicitation"

    events_content = sm.events_path.read_text().strip()
    assert "phase_transition" in events_content

    backup_files = list(sm._factory_dir.glob(".rollback*"))
    assert len(backup_files) == 0, f"Residual rollback files: {backup_files}"


def test_transition_records_event_after_save(tmp_path):
    project_dir, _ = _init_project_dir(tmp_path)
    sm = StateManager(project_dir)

    result = sm.transition_to("elicitation", skip_gates=True)

    events = sm.events_path.read_text().strip().split("\n")
    assert len(events) == 1
    event = json.loads(events[0])
    assert event["type"] == "phase_transition"
    assert event["data"]["from"] == "init"
    assert event["data"]["to"] == "elicitation"


def test_rollback_on_record_event_failure(tmp_path):
    project_dir, original_state = _init_project_dir(tmp_path)
    sm = StateManager(project_dir)

    with patch.object(sm, "record_event", side_effect=OSError("simulated disk full")):
        with pytest.raises(OSError, match="simulated disk full"):
            sm.transition_to("elicitation", skip_gates=True)

    state_after = sm.load()
    assert state_after["current_phase"] == "init"
    assert state_after["phases"]["init"]["status"] == "in_progress"
    assert state_after["phases"]["elicitation"]["status"] == "pending"

    json_after = sm.state_path.read_text()
    assert json.loads(json_after)["current_phase"] == "init"


def test_no_state_modification_on_gate_error(tmp_path):
    project_dir, original_state = _init_project_dir(tmp_path)
    sm = StateManager(project_dir)

    from fba.gate import GateResult, GateError

    gate_result = GateResult(
        passed=False,
        phase="init",
        description="test gate",
        results=[],
        owner_agent="test",
    )

    with patch("fba.gate.GateRunner") as mock_runner:
        mock_instance = mock_runner.return_value
        mock_instance.check_phase.return_value = gate_result

        with pytest.raises(GateError):
            sm.transition_to("elicitation", skip_gates=False)

    state_after = sm.load()
    assert state_after["current_phase"] == "init"


def test_no_state_modification_on_invalid_transition(tmp_path):
    project_dir, _ = _init_project_dir(tmp_path)
    sm = StateManager(project_dir)

    with pytest.raises(ValueError, match="Invalid transition"):
        sm.transition_to("documentation", skip_gates=True)

    state_after = sm.load()
    assert state_after["current_phase"] == "init"


def test_consecutive_transitions_no_residual_artifacts(tmp_path):
    project_dir, _ = _init_project_dir(tmp_path)
    sm = StateManager(project_dir)

    state = sm.load()
    state["valid_transitions"]["elicitation"] = ["documentation"]
    state["phases"]["documentation"] = {"status": "pending"}
    sm.save(state)

    sm.transition_to("elicitation", skip_gates=True)
    sm.transition_to("documentation", skip_gates=True)

    assert sm.current_phase == "documentation"

    backup_files = list(sm._factory_dir.glob(".rollback*"))
    assert len(backup_files) == 0, f"Residual rollback files: {backup_files}"


def test_rollback_restores_exact_state_content(tmp_path):
    project_dir, _ = _init_project_dir(tmp_path)
    sm = StateManager(project_dir)

    original_json = sm.state_path.read_text()

    with patch.object(sm, "record_event", side_effect=OSError("disk error")):
        with pytest.raises(OSError):
            sm.transition_to("elicitation", skip_gates=True)

    restored_json = sm.state_path.read_text()
    assert original_json == restored_json


def test_rollback_error_logged_on_restore_failure(tmp_path):
    project_dir, _ = _init_project_dir(tmp_path)
    sm = StateManager(project_dir)

    original_replace = os.replace

    call_count = [0]

    def failing_replace(src, dst):
        call_count[0] += 1
        if call_count[0] > 1:
            raise OSError("simulated rollback failure")
        original_replace(src, dst)

    try:
        os.replace = failing_replace
        with patch.object(sm, "record_event", side_effect=OSError("disk error")):
            with pytest.raises(OSError, match="disk error"):
                sm.transition_to("elicitation", skip_gates=True)
    finally:
        os.replace = original_replace

    error_log = sm._factory_dir / ".rollback_error.log"
    assert error_log.exists(), "Rollback error log should exist"
    content = error_log.read_text()
    assert "rollback" in content.lower()

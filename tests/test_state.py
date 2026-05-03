"""Tests for the StateManager module."""

import json
from pathlib import Path

import pytest

from fba.state import StateManager


@pytest.fixture
def project_dir(tmp_path):
    factory_dir = tmp_path / ".factory"
    factory_dir.mkdir()

    state = {
        "project": tmp_path.name,
        "framework_version": "0.1.0",
        "init_at": "2026-05-02T00:00:00+00:00",
        "current_phase": "init",
        "methodology": "BABOK",
        "phases": {
            "init": {"status": "in_progress", "agent": "orchestrator"},
            "elicitation": {"status": "pending", "agent": "elicitador"},
            "documentation": {"status": "pending", "agent": "documentador"},
            "planning": {"status": "pending", "agent": "planificador"},
            "tasks": {"status": "pending", "agent": "planificador"},
            "construction": {"status": "pending", "agent": "constructor"},
            "testing": {"status": "pending", "agent": "tester"},
            "review": {"status": "pending", "agent": "revisor"},
            "ci_cd": {"status": "pending", "agent": "cicd_manager"},
        },
        "valid_transitions": {
            "init": ["elicitation"],
            "elicitation": ["documentation"],
            "documentation": ["planning"],
            "planning": ["tasks"],
            "tasks": ["construction"],
            "construction": ["testing"],
            "testing": ["review"],
            "review": ["ci_cd"],
            "ci_cd": ["complete"],
        },
        "artifacts": {},
        "context": {},
    }
    (factory_dir / "state.json").write_text(json.dumps(state, indent=2))

    return tmp_path


@pytest.fixture
def state_mgr(project_dir):
    return StateManager(project_dir)


class TestStateManagerLoadSave:
    def test_load_state(self, state_mgr):
        state = state_mgr.load()
        assert state["current_phase"] == "init"
        assert state["methodology"] == "BABOK"

    def test_save_state(self, state_mgr):
        state = state_mgr.load()
        state["context"]["key"] = "value"
        state_mgr.save(state)

        reloaded = state_mgr.load()
        assert reloaded["context"]["key"] == "value"

    def test_current_phase(self, state_mgr):
        assert state_mgr.current_phase == "init"

    def test_load_missing_state_file(self, tmp_path):
        mgr = StateManager(tmp_path / "nonexistent")
        with pytest.raises(FileNotFoundError, match="Run 'fba init' first"):
            mgr.load()


class TestStateManagerTransitions:
    def test_valid_transition(self, state_mgr):
        state = state_mgr.transition_to("elicitation")
        assert state["current_phase"] == "elicitation"
        assert state["phases"]["elicitation"]["status"] == "in_progress"
        assert state["phases"]["init"]["status"] == "complete"

    def test_invalid_transition_raises(self, state_mgr):
        with pytest.raises(ValueError, match="Invalid transition"):
            state_mgr.transition_to("construction")

    def test_transition_chain(self, state_mgr):
        state_mgr.transition_to("elicitation")
        state_mgr.transition_to("documentation")
        assert state_mgr.current_phase == "documentation"
        assert state_mgr.load()["phases"]["elicitation"]["status"] == "complete"

    def test_transition_does_not_mark_init_complete(self, state_mgr):
        state_mgr.transition_to("elicitation")
        assert state_mgr.load()["phases"]["init"]["status"] == "complete"

    def test_transition_records_event(self, state_mgr):
        events_before = _count_events(state_mgr.events_path)
        state_mgr.transition_to("elicitation")
        events_after = _count_events(state_mgr.events_path)
        assert events_after == events_before + 1

        last_event = _read_last_event(state_mgr.events_path)
        assert last_event["type"] == "phase_transition"
        assert last_event["data"]["from"] == "init"
        assert last_event["data"]["to"] == "elicitation"


class TestStateManagerEvents:
    def test_record_event(self, state_mgr):
        state_mgr.record_event("elicitation_start", {"stakeholders": 3})
        events = _read_events(state_mgr.events_path)
        assert len(events) == 1
        assert events[0]["type"] == "elicitation_start"
        assert events[0]["data"]["stakeholders"] == 3

    def test_record_event_no_data(self, state_mgr):
        state_mgr.record_event("ping")
        event = _read_last_event(state_mgr.events_path)
        assert event["type"] == "ping"
        assert "data" not in event

    def test_record_event_appends(self, state_mgr):
        state_mgr.record_event("first")
        state_mgr.record_event("second")
        events = _read_events(state_mgr.events_path)
        assert len(events) == 2
        assert events[0]["type"] == "first"
        assert events[1]["type"] == "second"


class TestStateManagerPhases:
    def test_mark_phase(self, state_mgr):
        state_mgr.mark_phase("elicitation", "in_progress")
        state = state_mgr.load()
        assert state["phases"]["elicitation"]["status"] == "in_progress"

    def test_mark_unknown_phase_raises(self, state_mgr):
        with pytest.raises(ValueError, match="Unknown phase"):
            state_mgr.mark_phase("nonexistent", "complete")


class TestStateManagerArtifacts:
    def test_add_artifact(self, state_mgr):
        state_mgr.add_artifact("prd")
        state = state_mgr.load()
        assert "prd" in state["artifacts"]
        assert state["artifacts"]["prd"]["status"] == "draft"
        assert state["artifacts"]["prd"]["version"] == 1

    def test_add_artifact_with_status(self, state_mgr):
        state_mgr.add_artifact("prd", "valid")
        assert state_mgr.load()["artifacts"]["prd"]["status"] == "valid"

    def test_add_artifact_version(self, state_mgr):
        state_mgr.add_artifact("prd")
        state_mgr.add_artifact_version("prd")
        assert state_mgr.load()["artifacts"]["prd"]["version"] == 2

    def test_add_artifact_version_unknown_raises(self, state_mgr):
        with pytest.raises(ValueError, match="Unknown artifact"):
            state_mgr.add_artifact_version("nonexistent")


class TestValidTransitionsFromState:
    def test_valid_transitions_use_known_phases(self, state_mgr):
        state = state_mgr.load()
        transitions = state.get("valid_transitions", {})

        all_phases = set(state["phases"].keys()) | {"init", "complete"}

        for from_phase, to_list in transitions.items():
            assert from_phase in all_phases, f"Unknown from_phase '{from_phase}'"
            for to_phase in to_list:
                assert to_phase in all_phases | {"complete"}, \
                    f"Unknown to_phase '{to_phase}' in transition"

    def test_transitions_cover_all_phases(self, state_mgr):
        state = state_mgr.load()
        transitions = state.get("valid_transitions", {})
        phases = set(state["phases"].keys())

        assert set(transitions.keys()) == phases


def _read_events(path: Path) -> list:
    if not path.exists():
        return []
    lines = path.read_text().strip().split("\n")
    return [json.loads(line) for line in lines if line]


def _read_last_event(path: Path) -> dict:
    return _read_events(path)[-1]


def _count_events(path: Path) -> int:
    return len(_read_events(path))

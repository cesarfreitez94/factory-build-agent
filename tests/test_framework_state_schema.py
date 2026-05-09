"""Tests for framework-state schema validation."""

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "framework-state.schema.json"


@pytest.fixture
def fw_state_schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid_state():
    return {
        "schema_version": "1.0",
        "last_updated": "2026-05-09T00:00:00Z",
        "last_session": {
            "date": "2026-05-09",
            "agent": "framework-builder",
            "action": "test session",
            "completed_feats": ["feat/10.1"],
            "pending_feats": ["feat/10.2"],
            "blockers": []
        },
        "active_milestone": {
            "id": "M10",
            "name": "Framework Meta-Development",
            "branch": "milestone/10.0-framework-meta-dev",
            "status": "in_progress",
            "feats_total": 5,
            "feats_done": 1,
            "feats_pending": ["feat/10.2", "feat/10.3", "feat/10.4", "feat/10.5"],
            "ready_for_user_review": False
        },
        "roadmap_status": {
            "M0": "completed",
            "M1": "completed",
            "M5": "completed",
            "M10": "in_progress",
            "M6": "planned"
        },
        "roadmap_summary": [
            {"milestone":"M0","name":"Fundacion","status":"completed","start_date":"2026-05-02","end_date":"2026-05-02"},
            {"milestone":"M1","name":"Elicitacion","status":"completed","start_date":"2026-05-03","end_date":"2026-05-03"},
            {"milestone":"M5","name":"Bug Fixes","status":"completed","start_date":"2026-05-06","end_date":"2026-05-08"},
            {"milestone":"M10","name":"Meta-Development","status":"in_progress","start_date":"2026-05-09"},
            {"milestone":"M6","name":"Optimizacion","status":"planned"}
        ],
        "pending_decisions": [],
        "open_briefs": [],
        "agents": {
            "framework-orchestrator": {"status": "active", "file": ".opencode/agents/framework-orchestrator.md"},
            "framework-planner":     {"status": "active", "file": ".opencode/agents/framework-planner.md"},
            "framework-builder":     {"status": "active", "file": ".opencode/agents/framework-builder.md"}
        }
    }


class TestFrameworkStateSchemaValid:
    """Valid states must pass validation."""

    def test_valid_state_passes(self, fw_state_schema):
        jsonschema.validate(_valid_state(), fw_state_schema)

    def test_with_pending_decisions_passes(self, fw_state_schema):
        state = _valid_state()
        state["pending_decisions"] = [
            {
                "id": "DEC-001",
                "description": "Should we add multi-model support?",
                "raised_by": "framework-planner",
                "raised_at": "2026-05-08",
                "status": "awaiting_user"
            }
        ]
        jsonschema.validate(state, fw_state_schema)

    def test_with_open_briefs_passes(self, fw_state_schema):
        state = _valid_state()
        state["open_briefs"] = [
            {
                "file": ".factory/fw-brief.md",
                "milestone": "M10",
                "feats_remaining": 4,
                "status": "active"
            }
        ]
        jsonschema.validate(state, fw_state_schema)

    def test_with_blockers_passes(self, fw_state_schema):
        state = _valid_state()
        state["last_session"]["blockers"] = ["Missing dependency X"]
        jsonschema.validate(state, fw_state_schema)


class TestFrameworkStateSchemaMissingFields:
    """Missing required fields must fail validation."""

    def test_missing_schema_version_fails(self, fw_state_schema):
        state = _valid_state()
        del state["schema_version"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(state, fw_state_schema)

    def test_missing_last_updated_fails(self, fw_state_schema):
        state = _valid_state()
        del state["last_updated"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(state, fw_state_schema)

    def test_missing_last_session_fails(self, fw_state_schema):
        state = _valid_state()
        del state["last_session"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(state, fw_state_schema)

    def test_missing_active_milestone_fails(self, fw_state_schema):
        state = _valid_state()
        del state["active_milestone"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(state, fw_state_schema)

    def test_missing_roadmap_status_fails(self, fw_state_schema):
        state = _valid_state()
        del state["roadmap_status"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(state, fw_state_schema)

    def test_missing_roadmap_summary_fails(self, fw_state_schema):
        state = _valid_state()
        del state["roadmap_summary"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(state, fw_state_schema)

    def test_missing_agents_fails(self, fw_state_schema):
        state = _valid_state()
        del state["agents"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(state, fw_state_schema)

    def test_missing_last_session_date_fails(self, fw_state_schema):
        state = _valid_state()
        del state["last_session"]["date"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(state, fw_state_schema)

    def test_missing_active_milestone_id_fails(self, fw_state_schema):
        state = _valid_state()
        del state["active_milestone"]["id"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(state, fw_state_schema)


class TestFrameworkStateSchemaInvalidValues:
    """Invalid enum values must fail validation."""

    def test_invalid_milestone_status_fails(self, fw_state_schema):
        state = _valid_state()
        state["active_milestone"]["status"] = "unknown"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(state, fw_state_schema)

    def test_invalid_roadmap_status_fails(self, fw_state_schema):
        state = _valid_state()
        state["roadmap_status"]["M6"] = "started"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(state, fw_state_schema)

    def test_invalid_decision_status_fails(self, fw_state_schema):
        state = _valid_state()
        state["pending_decisions"] = [
            {
                "id": "DEC-001",
                "description": "Test",
                "raised_by": "framework-planner",
                "raised_at": "2026-05-08",
                "status": "in_progress"
            }
        ]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(state, fw_state_schema)

    def test_invalid_brief_status_fails(self, fw_state_schema):
        state = _valid_state()
        state["open_briefs"] = [
            {
                "file": "brief.md",
                "milestone": "M10",
                "feats_remaining": 3,
                "status": "paused"
            }
        ]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(state, fw_state_schema)

    def test_decision_status_resolved_passes(self, fw_state_schema):
        state = _valid_state()
        state["pending_decisions"] = [
            {
                "id": "DEC-001",
                "description": "Test",
                "raised_by": "framework-planner",
                "raised_at": "2026-05-08",
                "status": "resolved"
            }
        ]
        jsonschema.validate(state, fw_state_schema)

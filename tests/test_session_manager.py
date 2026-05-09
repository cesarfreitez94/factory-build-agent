"""Tests for the SessionManager module."""

import json
from pathlib import Path

import pytest

from fba.session_manager import ActionType, SessionManager, SessionQuery


def _write_state(project_dir: Path, phases: dict, current_phase="init"):
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "project": project_dir.name,
        "framework_version": "0.5.0",
        "init_at": "2026-05-09T00:00:00+00:00",
        "current_phase": current_phase,
        "methodology": "BABOK",
        "phases": phases,
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
        "gates": {
            "documentation": {
                "description": "Validates PRD",
                "owner_agent": "documentador",
                "rules": [{"type": "artifact_exists", "rule_name": "prd_exists", "path": ".factory/prd.json"}],
            },
        },
        "artifacts": {},
        "context": {},
    }
    (factory_dir / "state.json").write_text(json.dumps(state, indent=2))
    return factory_dir


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


class TestInteractivePhase:
    def test_elicitation_pending_no_files(self, project_dir):
        """Interactive phase with no files yet → invoke_agent to generate questions."""
        _write_state(project_dir, {
            "init": {"status": "complete", "agent": "orchestrator"},
            "elicitation": {
                "status": "pending", "agent": "elicitador",
                "command": "/fba:elicit", "type": "interactive",
                "questions_file": "elicit_questions.json",
                "answers_file": "elicit_answers.json",
                "output_file": "context/elicitation.json",
            },
            "documentation": {"status": "pending", "agent": "documentador", "command": "/fba:specify", "type": "batch"},
        })

        mgr = SessionManager(project_dir)
        q = SessionQuery(query="next_action", current_phase="elicitation")
        resp = mgr.query(q)

        assert resp.action == ActionType.INVOKE_AGENT
        assert resp.agent == "elicitador"
        assert resp.command == "/fba:elicit"

    def test_elicit_questions_ready(self, project_dir):
        """Interactive phase with questions_file but no answers → elicit_round."""
        _write_state(project_dir, {
            "init": {"status": "complete", "agent": "orchestrator"},
            "elicitation": {
                "status": "pending", "agent": "elicitador",
                "command": "/fba:elicit", "type": "interactive",
                "questions_file": "elicit_questions.json",
                "answers_file": "elicit_answers.json",
                "output_file": "context/elicitation.json",
            },
            "documentation": {"status": "pending", "agent": "documentador", "command": "/fba:specify", "type": "batch"},
        })
        (project_dir / "elicit_questions.json").write_text("[]")

        mgr = SessionManager(project_dir)
        q = SessionQuery(query="next_action", current_phase="elicitation")
        resp = mgr.query(q)

        assert resp.action == ActionType.ELICIT_ROUND
        assert resp.questions_file == "elicit_questions.json"
        assert resp.answers_file == "elicit_answers.json"

    def test_elicit_answers_ready(self, project_dir):
        """Interactive phase with answers but no output → invoke_agent to process answers."""
        _write_state(project_dir, {
            "init": {"status": "complete", "agent": "orchestrator"},
            "elicitation": {
                "status": "pending", "agent": "elicitador",
                "command": "/fba:elicit", "type": "interactive",
                "questions_file": "elicit_questions.json",
                "answers_file": "elicit_answers.json",
                "output_file": "context/elicitation.json",
            },
            "documentation": {"status": "pending", "agent": "documentador", "command": "/fba:specify", "type": "batch"},
        })
        (project_dir / "elicit_questions.json").write_text("[]")
        (project_dir / "elicit_answers.json").write_text("{}")

        mgr = SessionManager(project_dir)
        q = SessionQuery(query="next_action", current_phase="elicitation")
        resp = mgr.query(q)

        assert resp.action == ActionType.INVOKE_AGENT
        assert resp.agent == "elicitador"
        assert resp.command == "/fba:elicit"
        assert resp.input_files == ["elicit_answers.json"]

    def test_elicit_output_done(self, project_dir):
        """Interactive phase with output_file → transition to next phase."""
        _write_state(project_dir, {
            "init": {"status": "complete", "agent": "orchestrator"},
            "elicitation": {
                "status": "complete", "agent": "elicitador",
                "command": "/fba:elicit", "type": "interactive",
                "questions_file": "elicit_questions.json",
                "answers_file": "elicit_answers.json",
                "output_file": "context/elicitation.json",
            },
            "documentation": {"status": "pending", "agent": "documentador", "command": "/fba:specify", "type": "batch"},
        })
        (project_dir / "context").mkdir(parents=True)
        (project_dir / "context" / "elicitation.json").write_text("{}")

        mgr = SessionManager(project_dir)
        q = SessionQuery(query="next_action", current_phase="elicitation")
        resp = mgr.query(q)

        assert resp.action == ActionType.TRANSITION
        assert resp.to_phase == "documentation"


class TestBatchPhase:
    def test_batch_phase_pending(self, project_dir):
        """Batch phase with status=pending → invoke_agent."""
        _write_state(project_dir, {
            "init": {"status": "complete", "agent": "orchestrator"},
            "elicitation": {"status": "complete", "agent": "elicitador", "command": "/fba:elicit", "type": "batch"},
            "documentation": {
                "status": "pending", "agent": "documentador",
                "command": "/fba:specify", "type": "batch",
            },
            "planning": {"status": "pending", "agent": "planificador", "command": "/fba:plan", "type": "batch"},
        })

        mgr = SessionManager(project_dir)
        q = SessionQuery(query="next_action", current_phase="documentation")
        resp = mgr.query(q)

        assert resp.action == ActionType.INVOKE_AGENT
        assert resp.agent == "documentador"
        assert resp.command == "/fba:specify"

    def test_batch_phase_completed(self, project_dir):
        """Batch phase with status=completed and no gate failure → transition."""
        _write_state(project_dir, {
            "init": {"status": "complete", "agent": "orchestrator"},
            "elicitation": {
                "status": "complete", "agent": "elicitador",
                "command": "/fba:elicit", "type": "batch",
            },
            "documentation": {
                "status": "completed", "agent": "documentador",
                "command": "/fba:specify", "type": "batch",
            },
            "planning": {"status": "pending", "agent": "planificador", "command": "/fba:plan", "type": "batch"},
        })

        mgr = SessionManager(project_dir)
        q = SessionQuery(query="next_action", current_phase="documentation")
        resp = mgr.query(q)

        assert resp.action == ActionType.TRANSITION
        assert resp.to_phase == "planning"


class TestGateFailure:
    def test_gate_failure(self, project_dir):
        """Batch phase completed with gate failure → ask_user."""
        _write_state(project_dir, {
            "init": {"status": "complete", "agent": "orchestrator"},
            "elicitation": {"status": "complete", "agent": "elicitador", "command": "/fba:elicit", "type": "batch"},
            "documentation": {
                "status": "completed", "agent": "documentador",
                "command": "/fba:specify", "type": "batch",
            },
            "planning": {"status": "pending", "agent": "planificador", "command": "/fba:plan", "type": "batch"},
        })

        mgr = SessionManager(project_dir)
        q = SessionQuery(
            query="gate_failure",
            current_phase="documentation",
            gate_result={"passed": False, "failed_rules": ["prd_exists"]},
        )
        resp = mgr.query(q)

        assert resp.action == ActionType.ASK_USER
        assert resp.user_question is not None
        assert resp.user_question["header"] is not None
        assert len(resp.user_question["options"]) == 3


class TestUserDecision:
    def test_user_choice_force(self, project_dir):
        """user_decision with choice=force → transition."""
        _write_state(project_dir, {
            "init": {"status": "complete", "agent": "orchestrator"},
            "elicitation": {"status": "complete", "agent": "elicitador", "command": "/fba:elicit", "type": "batch"},
            "documentation": {
                "status": "completed", "agent": "documentador",
                "command": "/fba:specify", "type": "batch",
            },
            "planning": {"status": "pending", "agent": "planificador", "command": "/fba:plan", "type": "batch"},
        })

        mgr = SessionManager(project_dir)
        q = SessionQuery(
            query="user_decision",
            current_phase="documentation",
            user_choice="force",
        )
        resp = mgr.query(q)

        assert resp.action == ActionType.TRANSITION
        assert resp.to_phase == "planning"

    def test_user_choice_retry(self, project_dir):
        """user_decision with choice=retry → invoke_agent."""
        _write_state(project_dir, {
            "init": {"status": "complete", "agent": "orchestrator"},
            "elicitation": {"status": "complete", "agent": "elicitador", "command": "/fba:elicit", "type": "batch"},
            "documentation": {
                "status": "completed", "agent": "documentador",
                "command": "/fba:specify", "type": "batch",
            },
            "planning": {"status": "pending", "agent": "planificador", "command": "/fba:plan", "type": "batch"},
        })

        mgr = SessionManager(project_dir)
        q = SessionQuery(
            query="user_decision",
            current_phase="documentation",
            user_choice="retry",
        )
        resp = mgr.query(q)

        assert resp.action == ActionType.INVOKE_AGENT
        assert resp.agent == "documentador"

    def test_user_choice_cancel(self, project_dir):
        """user_decision with choice=cancel → complete."""
        _write_state(project_dir, {
            "init": {"status": "complete", "agent": "orchestrator"},
            "elicitation": {"status": "complete", "agent": "elicitador", "command": "/fba:elicit", "type": "batch"},
            "documentation": {
                "status": "completed", "agent": "documentador",
                "command": "/fba:specify", "type": "batch",
            },
            "planning": {"status": "pending", "agent": "planificador", "command": "/fba:plan", "type": "batch"},
        })

        mgr = SessionManager(project_dir)
        q = SessionQuery(
            query="user_decision",
            current_phase="documentation",
            user_choice="cancel",
        )
        resp = mgr.query(q)

        assert resp.action == ActionType.COMPLETE


class TestComplete:
    def test_complete_phase(self, project_dir):
        """current_phase=complete → complete."""
        _write_state(project_dir, {
            "init": {"status": "complete", "agent": "orchestrator"},
            "elicitation": {"status": "complete", "agent": "elicitador", "command": "/fba:elicit", "type": "batch"},
            "documentation": {"status": "complete", "agent": "documentador", "command": "/fba:specify", "type": "batch"},
            "planning": {"status": "complete", "agent": "planificador", "command": "/fba:plan", "type": "batch"},
            "tasks": {"status": "complete", "agent": "planificador", "command": "/fba:tasks", "type": "batch"},
            "construction": {"status": "complete", "agent": "code-generator", "command": "/fba:construct", "type": "batch"},
            "testing": {"status": "complete", "agent": "tester_qa", "command": "/fba:test", "type": "batch"},
            "review": {"status": "complete", "agent": "revisor_codigo", "command": "/fba:review", "type": "batch"},
            "ci_cd": {"status": "complete", "agent": "cicd_manager", "command": "/fba:ship", "type": "batch"},
        }, current_phase="complete")

        mgr = SessionManager(project_dir)
        q = SessionQuery(query="next_action", current_phase="complete")
        resp = mgr.query(q)

        assert resp.action == ActionType.COMPLETE


class TestStateless:
    def test_session_manager_stateless(self, project_dir):
        """Same query twice produces the same result."""
        _write_state(project_dir, {
            "init": {"status": "complete", "agent": "orchestrator"},
            "elicitation": {"status": "complete", "agent": "elicitador", "command": "/fba:elicit", "type": "batch"},
            "documentation": {
                "status": "pending", "agent": "documentador",
                "command": "/fba:specify", "type": "batch",
            },
            "planning": {"status": "pending", "agent": "planificador", "command": "/fba:plan", "type": "batch"},
        })

        mgr = SessionManager(project_dir)
        q = SessionQuery(query="next_action", current_phase="documentation")

        resp1 = mgr.query(q)
        resp2 = mgr.query(q)

        assert resp1.action == resp2.action
        assert resp1.agent == resp2.agent
        assert resp1.command == resp2.command

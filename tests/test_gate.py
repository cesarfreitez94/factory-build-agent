"""Tests for the Gate system: GateRunner, GateResult, RuleResult, GateError."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from fba.cli import main
from fba.gate import GateError, GateResult, GateRunner, RuleResult
from fba.state import StateManager


@pytest.fixture
def state_without_gates(tmp_path):
    factory_dir = tmp_path / ".factory"
    factory_dir.mkdir()
    state = {
        "project": "test",
        "current_phase": "init",
        "methodology": "BABOK",
        "phases": {
            "init": {"status": "in_progress", "agent": "orchestrator"},
            "elicitation": {"status": "pending", "agent": "elicitador"},
        },
        "valid_transitions": {"init": ["elicitation"]},
        "artifacts": {},
        "context": {},
    }
    (factory_dir / "state.json").write_text(json.dumps(state, indent=2))
    return tmp_path


@pytest.fixture
def state_with_gates(tmp_path):
    factory_dir = tmp_path / ".factory"
    factory_dir.mkdir()
    state = {
        "project": "test",
        "current_phase": "documentation",
        "methodology": "BABOK",
        "phases": {
            "init": {"status": "complete", "agent": "orchestrator"},
            "elicitation": {"status": "complete", "agent": "elicitador"},
            "documentation": {"status": "in_progress", "agent": "documentador"},
            "planning": {"status": "pending", "agent": "planificador"},
        },
        "valid_transitions": {
            "init": ["elicitation"],
            "elicitation": ["documentation"],
            "documentation": ["planning"],
        },
        "gates": {
            "elicitation": {
                "description": "Validates elicitation output",
                "owner_agent": "elicitador",
                "rules": [
                    {"type": "artifact_exists", "rule_name": "ctx_exists", "path": ".factory/context/elicitation.json"},
                    {"type": "content_check", "rule_name": "ctx_content", "path": ".factory/context/elicitation.json", "checks": {"min_stakeholders": 1}},
                ],
            },
            "documentation": {
                "description": "Validates PRD",
                "owner_agent": "documentador",
                "rules": [
                    {"type": "artifact_exists", "rule_name": "prd_exists", "path": ".factory/prd.json"},
                ],
            },
        },
        "artifacts": {},
        "context": {},
    }
    (factory_dir / "state.json").write_text(json.dumps(state, indent=2))
    return tmp_path


class TestRuleResult:
    def test_dataclass_defaults(self):
        r = RuleResult(passed=True, rule="test_rule")
        assert r.passed is True
        assert r.rule == "test_rule"
        assert r.message == ""
        assert r.details == {}

    def test_dataclass_with_message(self):
        r = RuleResult(passed=False, rule="schema", message="missing field xyz")
        assert r.passed is False
        assert r.message == "missing field xyz"

    def test_to_dict(self):
        r = RuleResult(passed=True, rule="exists", message="ok", details={"path": "/tmp/x"})
        d = r.to_dict()
        assert d["passed"] is True
        assert d["rule"] == "exists"
        assert d["message"] == "ok"
        assert d["details"]["path"] == "/tmp/x"

    def test_to_dict_sets_required_fields(self):
        r = RuleResult(passed=False, rule="check")
        d = r.to_dict()
        for key in ["passed", "rule", "message", "details"]:
            assert key in d


class TestGateResult:
    def test_all_passed(self):
        results = [
            RuleResult(passed=True, rule="r1", message="ok"),
            RuleResult(passed=True, rule="r2", message="ok"),
        ]
        gr = GateResult(passed=True, phase="documentation", description="PRD check", results=results, owner_agent="doc")
        assert gr.passed is True
        assert gr.error_count == 0
        assert gr.failures == []

    def test_one_failed(self):
        results = [
            RuleResult(passed=True, rule="r1", message="ok"),
            RuleResult(passed=False, rule="r2", message="not found"),
        ]
        gr = GateResult(passed=False, phase="docs", description="x", results=results, owner_agent="doc")
        assert gr.passed is False
        assert gr.error_count == 1
        assert len(gr.failures) == 1
        assert gr.failures[0].rule == "r2"

    def test_to_dict_includes_error_count(self):
        results = [RuleResult(passed=False, rule="r1", message="fail")]
        gr = GateResult(passed=False, phase="x", description="d", results=results, owner_agent="a")
        d = gr.to_dict()
        assert d["error_count"] == 1
        assert len(d["results"]) == 1
        assert d["owner_agent"] == "a"

    def test_empty_results(self):
        gr = GateResult(passed=True, phase="init", description="no rules")
        assert gr.passed is True
        assert gr.error_count == 0
        assert gr.failures == []


class TestGateError:
    def test_exception_carries_gate_result(self):
        gr = GateResult(passed=False, phase="docs", owner_agent="doc", results=[
            RuleResult(passed=False, rule="r1", message="file missing"),
        ])
        err = GateError(gr)
        assert err.gate_result is gr
        assert err.gate_result.phase == "docs"

    def test_exception_message_single_failure(self):
        gr = GateResult(passed=False, phase="docs", owner_agent="doc", results=[
            RuleResult(passed=False, rule="r1", message="file missing"),
        ])
        err = GateError(gr)
        assert "Gate 'docs' failed" in str(err)
        assert "file missing" in str(err)

    def test_exception_message_multiple_failures(self):
        gr = GateResult(passed=False, phase="planning", owner_agent="plan", results=[
            RuleResult(passed=False, rule="r1", message="err1"),
            RuleResult(passed=False, rule="r2", message="err2"),
            RuleResult(passed=False, rule="r3", message="err3"),
            RuleResult(passed=False, rule="r4", message="err4"),
        ])
        err = GateError(gr)
        assert "err1" in str(err)
        assert "err2" in str(err)
        assert "err3" in str(err)
        assert "(+1 more)" in str(err)


class TestGateRunnerArtifactExists:
    def test_file_exists(self, state_with_gates):
        (state_with_gates / ".factory" / "prd.json").write_text('{"valid": true}')
        runner = GateRunner(state_with_gates)
        result = runner.check_phase("documentation")
        assert result.passed is True
        assert result.results[0].passed is True
        assert "Artifact exists" in result.results[0].message

    def test_file_not_found(self, state_with_gates):
        runner = GateRunner(state_with_gates)
        result = runner.check_phase("documentation")
        assert result.passed is False
        assert result.results[0].passed is False
        assert "not found" in result.results[0].message

    def test_file_empty(self, state_with_gates):
        (state_with_gates / ".factory" / "prd.json").write_text("   ")
        runner = GateRunner(state_with_gates)
        result = runner.check_phase("documentation")
        assert result.passed is False
        assert "empty" in result.results[0].message.lower()


class TestGateRunnerSchemaValidation:
    def setup_state_with_schema(self, tmp_path):
        factory = tmp_path / ".factory"
        factory.mkdir(parents=True, exist_ok=True)

        schemas_dir = factory / "schemas"
        schemas_dir.mkdir()

        (schemas_dir / "test.schema.json").write_text(json.dumps({
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        }))

        state = {
            "project": "test",
            "current_phase": "test_phase",
            "methodology": "BABOK",
            "phases": {},
            "valid_transitions": {},
            "gates": {
                "test_phase": {
                    "description": "Schema gate test",
                    "owner_agent": "doc",
                    "rules": [
                        {"type": "schema", "rule_name": "schema_test", "schema": "test.schema.json", "path": ".factory/artifact.json"},
                    ],
                },
            },
            "artifacts": {},
        }
        (factory / "state.json").write_text(json.dumps(state, indent=2))
        return tmp_path

    def test_schema_valid(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path as P
            d = self.setup_state_with_schema(P(tmp))
            (d / ".factory" / "artifact.json").write_text('{"name": "hello"}')
            runner = GateRunner(d)
            result = runner.check_phase("test_phase")
            assert result.passed is True
            assert "passed" in result.results[0].message.lower()

    def test_schema_invalid(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path as P
            d = self.setup_state_with_schema(P(tmp))
            (d / ".factory" / "artifact.json").write_text('{"name": 123}')
            runner = GateRunner(d)
            result = runner.check_phase("test_phase")
            assert result.passed is False
            assert "failed" in result.results[0].message.lower()

    def test_schema_artifact_not_found(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path as P
            d = self.setup_state_with_schema(P(tmp))
            runner = GateRunner(d)
            result = runner.check_phase("test_phase")
            assert result.passed is False
            assert "not found" in result.results[0].message

    def test_schema_invalid_json(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path as P
            d = self.setup_state_with_schema(P(tmp))
            (d / ".factory" / "artifact.json").write_text('not json')
            runner = GateRunner(d)
            result = runner.check_phase("test_phase")
            assert result.passed is False
            assert "invalid json" in result.results[0].message.lower()


class TestGateRunnerTraceability:
    def setup_traceability_state(self, tmp_path):
        factory = tmp_path / ".factory"
        factory.mkdir(parents=True)

        state = {
            "project": "test",
            "current_phase": "planning",
            "methodology": "BABOK",
            "phases": {},
            "valid_transitions": {},
            "gates": {
                "planning": {
                    "description": "Traceability test",
                    "owner_agent": "plan",
                    "rules": [
                        {
                            "type": "traceability",
                            "rule_name": "trace",
                            "prd_path": ".factory/prd.json",
                            "sdd_path": ".factory/sdd.json",
                        },
                    ],
                },
            },
            "artifacts": {},
        }
        (factory / "state.json").write_text(json.dumps(state, indent=2))
        return tmp_path

    def test_traceability_complete(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path as P
            d = self.setup_traceability_state(P(tmp))

            prd = {
                "functional_requirements": [
                    {"id": "RF-01", "description": "feature 1"},
                ],
                "non_functional_requirements": [
                    {"id": "RNF-01", "description": "nfr 1"},
                ],
            }
            (d / ".factory" / "prd.json").write_text(json.dumps(prd))

            sdd = {
                "traceability_matrix": {
                    "mappings": [
                        {"requirement": "RF-01", "sdD_components": ["model x"]},
                        {"requirement": "RNF-01", "sdD_components": ["security"]},
                    ],
                },
            }
            (d / ".factory" / "sdd.json").write_text(json.dumps(sdd))

            runner = GateRunner(d)
            result = runner.check_phase("planning")
            assert result.passed is True
            assert "complete" in result.results[0].message.lower()

    def test_traceability_incomplete(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path as P
            d = self.setup_traceability_state(P(tmp))

            prd = {
                "functional_requirements": [
                    {"id": "RF-01", "description": "f1"},
                    {"id": "RF-02", "description": "f2"},
                ],
            }
            (d / ".factory" / "prd.json").write_text(json.dumps(prd))

            sdd = {
                "traceability_matrix": {
                    "mappings": [
                        {"requirement": "RF-01", "sdD_components": ["x"]},
                    ],
                },
            }
            (d / ".factory" / "sdd.json").write_text(json.dumps(sdd))

            runner = GateRunner(d)
            result = runner.check_phase("planning")
            assert result.passed is False
            assert "incomplete" in result.results[0].message.lower()

    def test_traceability_prd_not_found(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path as P
            d = self.setup_traceability_state(P(tmp))

            sdd = {"traceability_matrix": {"mappings": []}}
            (d / ".factory" / "sdd.json").write_text(json.dumps(sdd))

            runner = GateRunner(d)
            result = runner.check_phase("planning")
            assert result.passed is False
            assert "PRD not found" in result.results[0].message


class TestGateRunnerContentCheck:
    def test_content_check_passes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path as P
            d = P(tmp)
            factory = d / ".factory"
            factory.mkdir()

            ctx_dir = factory / "context"
            ctx_dir.mkdir()
            ctx = {
                "stakeholders": [{"name": "test"}],
                "functional_requirements": [{"id": "RF-01"}],
            }
            (ctx_dir / "elicitation.json").write_text(json.dumps(ctx))

            state = {
                "project": "test",
                "current_phase": "elicitation",
                "methodology": "BABOK",
                "phases": {},
                "valid_transitions": {},
                "gates": {
                    "elicitation": {
                        "description": "t",
                        "owner_agent": "e",
                        "rules": [{
                            "type": "content_check",
                            "rule_name": "check",
                            "path": ".factory/context/elicitation.json",
                            "checks": {"min_stakeholders": 1, "min_functional_requirements": 1},
                        }],
                    },
                },
                "artifacts": {},
            }
            (factory / "state.json").write_text(json.dumps(state))

            runner = GateRunner(d)
            result = runner.check_phase("elicitation")
            assert result.passed is True
            assert "passed" in result.results[0].message.lower()

    def test_content_check_fails_insufficient(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path as P
            d = P(tmp)
            factory = d / ".factory"
            factory.mkdir()

            ctx_dir = factory / "context"
            ctx_dir.mkdir()
            ctx = {
                "stakeholders": [],
                "functional_requirements": [],
            }
            (ctx_dir / "elicitation.json").write_text(json.dumps(ctx))

            state = {
                "project": "test",
                "current_phase": "elicitation",
                "methodology": "BABOK",
                "phases": {},
                "valid_transitions": {},
                "gates": {
                    "elicitation": {
                        "description": "t",
                        "owner_agent": "e",
                        "rules": [{
                            "type": "content_check",
                            "rule_name": "check",
                            "path": ".factory/context/elicitation.json",
                            "checks": {"min_stakeholders": 1},
                        }],
                    },
                },
                "artifacts": {},
            }
            (factory / "state.json").write_text(json.dumps(state))

            runner = GateRunner(d)
            result = runner.check_phase("elicitation")
            assert result.passed is False
            assert "Expected at least" in result.results[0].message


class TestGateRunnerCheckPhase:
    def test_no_gates_defined(self, state_without_gates):
        runner = GateRunner(state_without_gates)
        result = runner.check_phase("init")
        assert result.passed is True
        assert "No gates defined" in result.description

    def test_unknown_rule_type(self, state_with_gates):
        state = json.loads((state_with_gates / ".factory" / "state.json").read_text())
        state["gates"]["documentation"]["rules"].append(
            {"type": "nonexistent_rule", "rule_name": "bad"}
        )
        (state_with_gates / ".factory" / "state.json").write_text(json.dumps(state, indent=2))
        (state_with_gates / ".factory" / "prd.json").write_text('{"x": 1}')

        runner = GateRunner(state_with_gates)
        result = runner.check_phase("documentation")
        assert result.passed is False
        assert any("Unknown rule type" in r.message for r in result.results)

    def test_check_current_phase(self, state_with_gates):
        runner = GateRunner(state_with_gates)
        result = runner.check_current_phase()
        assert result.phase == "documentation"
        assert result.owner_agent == "documentador"

    def test_check_all(self, state_with_gates):
        runner = GateRunner(state_with_gates)
        results = runner.check_all()
        assert set(results.keys()) == {"elicitation", "documentation"}

    def test_check_without_owner_agent(self, state_with_gates):
        state = json.loads((state_with_gates / ".factory" / "state.json").read_text())
        del state["gates"]["documentation"]["owner_agent"]
        (state_with_gates / ".factory" / "state.json").write_text(json.dumps(state, indent=2))
        (state_with_gates / ".factory" / "prd.json").write_text('{"x": 1}')

        runner = GateRunner(state_with_gates)
        result = runner.check_phase("documentation")
        assert result.owner_agent == ""


class TestGateBlockedTransition:
    def test_transition_blocked_by_gate(self, state_with_gates):
        sm = StateManager(state_with_gates)
        with pytest.raises(GateError) as exc_info:
            sm.transition_to("planning")
        assert exc_info.value.gate_result.phase == "documentation"
        assert exc_info.value.gate_result.error_count > 0

    def test_transition_with_skip_gates(self, state_with_gates):
        sm = StateManager(state_with_gates)
        state = sm.transition_to("planning", skip_gates=True)
        assert state["current_phase"] == "planning"
        assert state["phases"]["documentation"]["status"] == "complete"
        assert state["phases"]["planning"]["status"] == "in_progress"

    def test_transition_no_gates_defined(self, state_without_gates):
        sm = StateManager(state_without_gates)
        state = sm.transition_to("elicitation")
        assert state["current_phase"] == "elicitation"

    def test_has_gate_passed_false(self, state_with_gates):
        sm = StateManager(state_with_gates)
        assert sm.has_gate_passed("documentation") is False

    def test_has_gate_passed_true_when_none(self, state_without_gates):
        sm = StateManager(state_without_gates)
        assert sm.has_gate_passed("init") is True

    def test_has_gate_passed_defaults_to_current(self, state_with_gates):
        sm = StateManager(state_with_gates)
        assert sm.has_gate_passed() is False


class TestCLIGateCommand:
    def test_gate_current_phase(self, state_with_gates):
        runner = CliRunner()
        result = runner.invoke(main, ["gate", "-d", str(state_with_gates)])
        assert "Gate: documentation" in result.output
        assert result.exit_code == 1

    def test_gate_specific_phase(self, state_with_gates):
        runner = CliRunner()
        result = runner.invoke(main, ["gate", "elicitation", "-d", str(state_with_gates)])
        assert "Gate: elicitation" in result.output
        assert result.exit_code == 1

    def test_gate_all(self, state_with_gates):
        runner = CliRunner()
        result = runner.invoke(main, ["gate", "--all", "-d", str(state_with_gates)])
        assert "Gate: elicitation" in result.output
        assert "Gate: documentation" in result.output
        assert result.exit_code == 1

    def test_gate_passes_when_artifacts_exist(self, state_with_gates):
        (state_with_gates / ".factory" / "prd.json").write_text('{"valid": true}')
        runner = CliRunner()
        result = runner.invoke(main, ["gate", "documentation", "-d", str(state_with_gates)])
        assert result.exit_code == 0
        assert "✅ Gate:" in result.output

    def test_gate_shows_owner_agent(self, state_with_gates):
        runner = CliRunner()
        result = runner.invoke(main, ["gate", "documentation", "-d", str(state_with_gates)])
        assert "Owner agent:" in result.output
        assert "documentador" in result.output

    def test_gate_requires_factory(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["gate", "-d", str(tmp_path)])
        assert result.exit_code == 1
        assert "Error:" in result.output


class TestCLITransitionWithForce:
    def test_transition_force_bypasses_gate(self, state_with_gates):
        runner = CliRunner()
        result = runner.invoke(main, ["transition", "planning", "--force", "-d", str(state_with_gates)])
        assert result.exit_code == 0
        assert "Transitioned" in result.output
        assert "Gate validation was skipped" in result.output

    def test_transition_fails_without_force(self, state_with_gates):
        runner = CliRunner()
        result = runner.invoke(main, ["transition", "planning", "-d", str(state_with_gates)])
        assert result.exit_code == 1
        assert "Gate 'documentation' failed" in result.output
        assert "fba gate" in result.output


class TestGateRunnerMissingFactory:
    def test_no_state_json(self, tmp_path):
        runner = GateRunner(tmp_path)
        result = runner.check_current_phase()
        assert result.passed is True
        assert result.phase == "init"

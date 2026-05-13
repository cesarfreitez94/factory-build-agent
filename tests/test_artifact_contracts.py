"""Tests for artifact contract validation — invariants, ownership, and allowed mutations."""

import json
import uuid

import pytest

from fba.contract_engine import ContractEngine, ContractError


def _make_prd(requirements=None, stakeholders=None):
    """Create a minimal PRD artifact."""
    return {
        "vision": "A test product for validating contracts.",
        "stakeholders": stakeholders if stakeholders is not None else [
            {"name": "Alice", "role": "PM", "interest": "Success"},
        ],
        "objectives": ["Obj 1"],
        "functional_requirements": requirements if requirements is not None else [
            {"id": "RF-001", "description": "Login screen", "uuid": str(uuid.uuid4())},
        ],
        "non_functional_requirements": [],
        "acceptance_criteria": [],
        "glossary": [],
    }


def _make_sdd(models=None):
    """Create a minimal SDD artifact."""
    return {
        "module_name": "test_module",
        "module_display_name": "Test Module",
        "version": "18.0.1.0.0",
        "architecture": {"description": "A test architecture with enough detail."},
        "models": models if models is not None else [
            {"name": "test.model", "description": "A test model."},
        ],
        "views": [],
        "security": {},
        "dependencies": [],
        "file_structure": [],
        "traceability_matrix": {"mappings": []},
    }


def _make_schema_data(models=None):
    """Create a minimal schema.json artifact."""
    return {
        "manifest": {"name": "test_module", "version": "18.0.1.0.0", "depends": ["base"]},
        "models": models if models is not None else [
            {"name": "test.model", "fields": [{"name": "name", "type": "char"}]},
        ],
        "views": [],
        "security": {"groups": [], "access_rights": [], "record_rules": []},
        "data": [],
    }


# ---------------------------------------------------------------------------
# Invariant tests: PRD
# ---------------------------------------------------------------------------

class TestPrdInvariants:
    """Tests for PRD contract invariants."""

    def test_prd_with_stakeholders_passes(self):
        engine = ContractEngine()
        prd = _make_prd(stakeholders=[{"name": "A", "role": "PM", "interest": "X"}])
        violations = engine.validate_invariants("prd", prd)
        assert violations == []

    def test_prd_without_stakeholders_fails(self):
        engine = ContractEngine()
        prd = _make_prd(stakeholders=[])
        violations = engine.validate_invariants("prd", prd)
        assert len(violations) >= 1
        assert any("stakeholder" in v["id"].lower() for v in violations)

    def test_prd_without_functional_requirements_fails(self):
        engine = ContractEngine()
        prd = _make_prd(requirements=[])
        violations = engine.validate_invariants("prd", prd)
        assert len(violations) >= 1
        assert any("functional" in v["id"].lower() for v in violations)

    def test_prd_vision_too_short_fails(self):
        engine = ContractEngine()
        prd = _make_prd()
        prd["vision"] = "Short"
        violations = engine.validate_invariants("prd", prd)
        assert len(violations) >= 1
        assert any("vision" in v["id"].lower() for v in violations)

    def test_prd_requirement_missing_id_fails(self):
        engine = ContractEngine()
        prd = _make_prd(requirements=[{"description": "No ID here"}])
        violations = engine.validate_invariants("prd", prd)
        assert len(violations) >= 1
        assert any("id" in v["id"].lower() for v in violations)

    def test_prd_stakeholder_missing_required_field_fails(self):
        engine = ContractEngine()
        prd = _make_prd(stakeholders=[{"name": "Bob"}])
        violations = engine.validate_invariants("prd", prd)
        assert len(violations) >= 1
        assert any("stakeholder" in v["id"].lower() for v in violations)


# ---------------------------------------------------------------------------
# Invariant tests: SDD
# ---------------------------------------------------------------------------

class TestSddInvariants:
    """Tests for SDD contract invariants."""

    def test_sdd_with_models_passes(self):
        engine = ContractEngine()
        sdd = _make_sdd(models=[{"name": "m1", "description": "A model"}])
        violations = engine.validate_invariants("sdd", sdd)
        assert violations == []

    def test_sdd_without_models_fails(self):
        engine = ContractEngine()
        sdd = _make_sdd(models=[])
        violations = engine.validate_invariants("sdd", sdd)
        assert len(violations) >= 1
        assert any("model" in v["id"].lower() for v in violations)

    def test_sdd_model_missing_name_fails(self):
        engine = ContractEngine()
        sdd = _make_sdd(models=[{"description": "No name"}])
        violations = engine.validate_invariants("sdd", sdd)
        assert len(violations) >= 1

    def test_sdd_architecture_too_short_fails(self):
        engine = ContractEngine()
        sdd = _make_sdd()
        sdd["architecture"]["description"] = "Short"
        violations = engine.validate_invariants("sdd", sdd)
        assert len(violations) >= 1


# ---------------------------------------------------------------------------
# Invariant tests: schema
# ---------------------------------------------------------------------------

class TestSchemaInvariants:
    """Tests for schema.json contract invariants."""

    def test_schema_with_models_passes(self):
        engine = ContractEngine()
        schema_data = _make_schema_data(models=[
            {"name": "m1", "fields": [{"name": "f1", "type": "char"}]},
        ])
        violations = engine.validate_invariants("schema", schema_data)
        assert violations == []

    def test_schema_without_models_fails(self):
        engine = ContractEngine()
        schema_data = _make_schema_data(models=[])
        violations = engine.validate_invariants("schema", schema_data)
        assert len(violations) >= 1

    def test_schema_field_missing_type_fails(self):
        engine = ContractEngine()
        schema_data = _make_schema_data(models=[
            {"name": "m1", "fields": [{"name": "f1"}]},
        ])
        violations = engine.validate_invariants("schema", schema_data)
        assert len(violations) >= 1
        assert any("type" in v["id"].lower() for v in violations)

    def test_schema_model_without_fields_fails(self):
        engine = ContractEngine()
        schema_data = _make_schema_data(models=[
            {"name": "m1", "fields": []},
        ])
        violations = engine.validate_invariants("schema", schema_data)
        assert len(violations) >= 1


# ---------------------------------------------------------------------------
# Ownership tests
# ---------------------------------------------------------------------------

class TestOwnership:
    """Tests for ownership validation."""

    def test_owner_allowed(self):
        engine = ContractEngine()
        result = engine.validate_ownership("prd", "vision", "elicitador", "elicitation")
        assert result is None

    def test_owner_wrong_agent(self):
        engine = ContractEngine()
        result = engine.validate_ownership("prd", "vision", "code-generator", "elicitation")
        assert result is not None
        assert "elicitador" in result

    def test_owner_wrong_phase(self):
        engine = ContractEngine()
        result = engine.validate_ownership("prd", "vision", "elicitador", "construction")
        assert result is not None
        assert "elicitation" in result

    def test_owner_unowned_field(self):
        engine = ContractEngine()
        result = engine.validate_ownership("prd", "unknown_field", "elicitador", "elicitation")
        assert result is not None
        assert "ownership rule" in result


# ---------------------------------------------------------------------------
# Mutation tests
# ---------------------------------------------------------------------------

class TestMutations:
    """Tests for allowed mutation validation."""

    def test_mutation_no_changes_passes(self):
        engine = ContractEngine()
        prd = _make_prd()
        violations = engine.validate_mutations("prd", prd, prd)
        assert violations == []

    def test_mutation_remove_model_not_referenced_passes(self):
        engine = ContractEngine()
        old_sdd = _make_sdd(models=[
            {"name": "model.one", "description": "First"},
            {"name": "model.two", "description": "Second"},
        ])
        new_sdd = _make_sdd(models=[
            {"name": "model.one", "description": "First"},
        ])
        violations = engine.validate_mutations("sdd", old_sdd, new_sdd)
        assert violations == []

    def test_mutation_remove_model_with_view_fails(self):
        engine = ContractEngine()
        old_sdd = _make_sdd(models=[
            {"name": "model.one", "description": "First"},
        ])
        new_sdd = _make_sdd(models=[])
        new_sdd["views"] = [{"model": "model.one", "type": "tree"}]
        violations = engine.validate_mutations("sdd", old_sdd, new_sdd)
        assert len(violations) >= 1
        assert any("view" in v["id"].lower() or "delete" in v["id"].lower() for v in violations)

    def test_mutation_delete_req_with_context(self):
        engine = ContractEngine()
        old_prd = _make_prd(requirements=[
            {"id": "RF-001", "description": "Login"},
            {"id": "RF-002", "description": "Logout"},
        ])
        new_prd = _make_prd(requirements=[
            {"id": "RF-001", "description": "Login"},
        ])
        context = {
            "sdd": {
                "traceability_matrix": {
                    "mappings": [
                        {"requirement": "RF-002", "model": "some.model"},
                    ]
                }
            }
        }
        violations = engine.validate_mutations("prd", old_prd, new_prd, context=context)
        assert len(violations) >= 1
        assert any("RF-002" in str(v.get("deleted", "")) for v in violations)


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestContractErrors:
    """Tests for error handling in contract validation."""

    def test_unknown_artifact_type(self):
        engine = ContractEngine()
        with pytest.raises(ContractError, match="Unknown artifact type"):
            engine.validate_invariants("unknown_type", {})

    def test_unknown_artifact_type_ownership(self):
        engine = ContractEngine()
        with pytest.raises(ContractError, match="Unknown artifact type"):
            engine.validate_ownership("unknown_type", "field", "agent", "phase")


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestContractCli:
    """Tests for the fba validate --contract CLI command."""

    def test_validate_contract_prd_passes(self, tmp_path):
        from click.testing import CliRunner

        from fba.cli import main

        factory = tmp_path / ".factory"
        factory.mkdir()
        prd = _make_prd()
        (factory / "prd.json").write_text(json.dumps(prd))

        runner = CliRunner()
        result = runner.invoke(main, ["validate", "--contract", "prd", "--project-dir", str(tmp_path)])

        assert result.exit_code == 0
        assert "pass" in result.output.lower() or "✅" in result.output

    def test_validate_contract_prd_fails(self, tmp_path):
        from click.testing import CliRunner

        from fba.cli import main

        factory = tmp_path / ".factory"
        factory.mkdir()
        prd = _make_prd(stakeholders=[])
        (factory / "prd.json").write_text(json.dumps(prd))

        runner = CliRunner()
        result = runner.invoke(main, ["validate", "--contract", "prd", "--project-dir", str(tmp_path)])

        assert result.exit_code != 0
        assert "violation" in result.output.lower() or "❌" in result.output

    def test_validate_contract_sdd_passes(self, tmp_path):
        from click.testing import CliRunner

        from fba.cli import main

        factory = tmp_path / ".factory"
        factory.mkdir()
        sdd = _make_sdd()
        (factory / "sdd.json").write_text(json.dumps(sdd))

        runner = CliRunner()
        result = runner.invoke(main, ["validate", "--contract", "sdd", "--project-dir", str(tmp_path)])

        assert result.exit_code == 0
        assert "pass" in result.output.lower() or "✅" in result.output

    def test_validate_contract_schema_passes(self, tmp_path):
        from click.testing import CliRunner

        from fba.cli import main

        factory = tmp_path / ".factory"
        factory.mkdir()
        schema_data = _make_schema_data()
        (factory / "schema.json").write_text(json.dumps(schema_data))

        runner = CliRunner()
        result = runner.invoke(main, ["validate", "--contract", "schema", "--project-dir", str(tmp_path)])

        assert result.exit_code == 0
        assert "pass" in result.output.lower() or "✅" in result.output

    def test_validate_contract_missing_file(self, tmp_path):
        from click.testing import CliRunner

        from fba.cli import main

        factory = tmp_path / ".factory"
        factory.mkdir()

        runner = CliRunner()
        result = runner.invoke(main, ["validate", "--contract", "prd", "--project-dir", str(tmp_path)])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "Error" in result.output

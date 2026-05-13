"""Tests for stable IDs — UUID v4 generation, assignment, immutability, and tracing."""

import json
import re

import pytest

from fba.stable_ids import StableIdError, StableIdManager

UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class TestUuidGeneration:
    """Tests for UUID v4 generation."""

    def test_generate_uuid_is_valid_format(self):
        uid = StableIdManager.generate_id()
        assert UUID4_RE.match(uid), f"Not a valid UUID v4: {uid}"

    def test_generate_uuid_is_unique(self):
        ids = {StableIdManager.generate_id() for _ in range(100)}
        assert len(ids) == 100

    def test_assign_id_requirement(self):
        uid = StableIdManager.assign_id("RF-001", "requirement")
        assert UUID4_RE.match(uid)

    def test_assign_id_model(self):
        uid = StableIdManager.assign_id("res.partner", "model")
        assert UUID4_RE.match(uid)

    def test_assign_id_field(self):
        uid = StableIdManager.assign_id("name", "field")
        assert UUID4_RE.match(uid)

    def test_assign_id_invalid_type(self):
        with pytest.raises(StableIdError, match="Unknown entity type"):
            StableIdManager.assign_id("x", "invalid_type")


class TestEnsureIds:
    """Tests for ensuring UUIDs in entity arrays."""

    def test_ensure_ids_assigns_to_items_without_uuid(self):
        items = [
            {"id": "RF-001", "description": "Login"},
            {"id": "RF-002", "description": "Logout"},
        ]
        assigned = StableIdManager.ensure_ids_in_array(items, "requirement")

        assert assigned == 2
        assert UUID4_RE.match(items[0]["uuid"])
        assert UUID4_RE.match(items[1]["uuid"])

    def test_ensure_ids_preserves_existing_uuids(self):
        existing_uuid = StableIdManager.generate_id()
        items = [
            {"id": "RF-001", "description": "Login", "uuid": existing_uuid},
            {"id": "RF-002", "description": "Logout"},
        ]
        assigned = StableIdManager.ensure_ids_in_array(items, "requirement")

        assert assigned == 1
        assert items[0]["uuid"] == existing_uuid
        assert UUID4_RE.match(items[1]["uuid"])

    def test_ensure_ids_empty_list(self):
        assigned = StableIdManager.ensure_ids_in_array([], "requirement")
        assert assigned == 0

    def test_ensure_ids_skips_non_dict_items(self):
        items = [{"id": "RF-001"}, "not a dict", 42]
        assigned = StableIdManager.ensure_ids_in_array(items, "requirement")
        assert assigned == 1


class TestUuidImmutability:
    """Tests for UUID immutability validation."""

    def test_unchanged_uuid_passes(self):
        uid = StableIdManager.generate_id()
        old_items = [{"id": "RF-001", "uuid": uid, "description": "Old"}]
        new_items = [{"id": "RF-001", "uuid": uid, "description": "New"}]

        violations = StableIdManager.validate_immutability(old_items, new_items)
        assert violations == []

    def test_changed_uuid_fails(self):
        old_items = [{"id": "RF-001", "uuid": StableIdManager.generate_id()}]
        new_items = [{"id": "RF-001", "uuid": StableIdManager.generate_id()}]

        violations = StableIdManager.validate_immutability(old_items, new_items)
        assert len(violations) >= 1
        assert violations[0]["logical_id"] == "RF-001"

    def test_new_item_no_uuid_passes(self):
        old_items = [{"id": "RF-001", "uuid": StableIdManager.generate_id()}]
        new_items = [{"id": "RF-001", "uuid": StableIdManager.generate_id()}, {"id": "RF-002"}]

        violations = StableIdManager.validate_immutability(old_items, new_items)
        assert len(violations) >= 1

    def test_item_removed_no_violation(self):
        old_items = [{"id": "RF-001", "uuid": StableIdManager.generate_id()}]
        new_items = []

        violations = StableIdManager.validate_immutability(old_items, new_items)
        assert violations == []

    def test_no_uuids_no_violations(self):
        old_items = [{"id": "RF-001"}]
        new_items = [{"id": "RF-001", "description": "Changed"}]

        violations = StableIdManager.validate_immutability(old_items, new_items)
        assert violations == []


class TestTrace:
    """Tests for UUID tracing across artifacts."""

    def test_trace_finds_uuid_in_prd(self, tmp_path):
        factory = tmp_path / ".factory"
        factory.mkdir()
        uid = StableIdManager.generate_id()
        prd = {
            "functional_requirements": [
                {"id": "RF-001", "description": "Login", "uuid": uid},
            ],
        }
        (factory / "prd.json").write_text(json.dumps(prd))

        result = StableIdManager.trace(uid, factory)

        assert result is not None
        assert result["found_in"] >= 1
        locations = result["locations"]
        assert any("RF-001" in str(loc.get("entity_id", "")) for loc in locations)

    def test_trace_finds_uuid_in_sdd(self, tmp_path):
        factory = tmp_path / ".factory"
        factory.mkdir()
        uid = StableIdManager.generate_id()
        sdd = {
            "models": [
                {"name": "test.model", "uuid": uid},
            ],
        }
        (factory / "sdd.json").write_text(json.dumps(sdd))

        result = StableIdManager.trace(uid, factory)

        assert result is not None
        assert result["found_in"] >= 1

    def test_trace_finds_uuid_in_schema(self, tmp_path):
        factory = tmp_path / ".factory"
        factory.mkdir()
        uid = StableIdManager.generate_id()
        schema_data = {
            "models": [
                {"name": "test.model", "fields": [{"name": "field1", "type": "char", "uuid": uid}]},
            ],
        }
        (factory / "schema.json").write_text(json.dumps(schema_data))

        result = StableIdManager.trace(uid, factory)

        assert result is not None
        assert result["found_in"] >= 1

    def test_trace_not_found(self, tmp_path):
        factory = tmp_path / ".factory"
        factory.mkdir()
        (factory / "prd.json").write_text("{}")

        result = StableIdManager.trace("00000000-0000-0000-0000-000000000000", factory)
        assert result is None

    def test_trace_factory_not_found(self, tmp_path):
        with pytest.raises(StableIdError, match="not found"):
            StableIdManager.trace("any-uuid", tmp_path / "nonexistent")

    def test_trace_handles_malformed_json(self, tmp_path):
        factory = tmp_path / ".factory"
        factory.mkdir()
        (factory / "prd.json").write_text("not json {{")

        result = StableIdManager.trace("any-uuid", factory)
        assert result is None


class TestStableIdsCli:
    """Tests for the fba trace CLI command."""

    def test_trace_cli_found(self, tmp_path):
        from click.testing import CliRunner

        from fba.cli import main

        factory = tmp_path / ".factory"
        factory.mkdir()
        uid = StableIdManager.generate_id()
        prd = {
            "functional_requirements": [
                {"id": "RF-001", "description": "Login", "uuid": uid},
            ],
        }
        (factory / "prd.json").write_text(json.dumps(prd))

        runner = CliRunner()
        result = runner.invoke(main, ["trace", uid, "--project-dir", str(tmp_path)])

        assert result.exit_code == 0
        assert "RF-001" in result.output

    def test_trace_cli_not_found(self, tmp_path):
        from click.testing import CliRunner

        from fba.cli import main

        factory = tmp_path / ".factory"
        factory.mkdir()
        (factory / "prd.json").write_text("{}")

        runner = CliRunner()
        result = runner.invoke(main, ["trace", "00000000-0000-0000-0000-000000000000", "--project-dir", str(tmp_path)])

        assert result.exit_code != 0
        assert "not found" in result.output.lower()


class TestUuidInContracts:
    """Tests for UUID immutability via contract engine."""

    def test_uuid_immutability_via_contract(self):
        from fba.contract_engine import ContractEngine

        engine = ContractEngine()
        uid1 = StableIdManager.generate_id()
        uid2 = StableIdManager.generate_id()

        old_prd = {
            "vision": "Test vision long enough",
            "stakeholders": [{"name": "A", "role": "PM", "interest": "X"}],
            "objectives": ["Obj 1"],
            "functional_requirements": [
                {"id": "RF-001", "description": "Login", "uuid": uid1},
            ],
            "non_functional_requirements": [],
            "acceptance_criteria": [],
            "glossary": [],
        }
        new_prd = {
            "vision": "Test vision long enough",
            "stakeholders": [{"name": "A", "role": "PM", "interest": "X"}],
            "objectives": ["Obj 1"],
            "functional_requirements": [
                {"id": "RF-001", "description": "Login", "uuid": uid2},
            ],
            "non_functional_requirements": [],
            "acceptance_criteria": [],
            "glossary": [],
        }

        violations = engine.validate_mutations("prd", old_prd, new_prd)

        uuid_violations = [
            v for v in violations if v["id"] == "prd-uuids-are-immutable"
        ]
        assert len(uuid_violations) >= 1
        assert uuid_violations[0]["logical_id"] == "RF-001"

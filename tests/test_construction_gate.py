"""Tests for the construction gate (view_coverage, view_field_check, acl_coverage)."""

import json
from pathlib import Path

from fba.gate import GateRunner


def _make_project(tmp_path: Path, schema: dict, gates: dict) -> GateRunner:
    factory = tmp_path / ".factory"
    factory.mkdir(parents=True)

    state = {
        "project": "test",
        "current_phase": "construction",
        "methodology": "BABOK",
        "phases": {"construction": {"status": "in_progress", "agent": "code-generator"}},
        "valid_transitions": {"construction": ["testing"]},
        "gates": {"construction": gates},
        "artifacts": {},
        "context": {},
    }
    (factory / "state.json").write_text(json.dumps(state))
    (factory / "schema.json").write_text(json.dumps(schema))
    return GateRunner(str(tmp_path))


class TestViewCoverage:
    def test_passes_with_form_and_list(self, tmp_path):
        schema = {
            "manifest": {"name": "test", "version": "18.0.1.0.0", "summary": "test", "depends": ["base"], "license": "LGPL-3"},
            "models": [
                {"name": "test.model", "description": "Test model", "mode": "new", "fields": [
                    {"name": "name", "type": "Char", "label": "Name"},
                ]},
            ],
            "views": [
                {"name": "test.model.form", "type": "form", "model": "test.model", "fields": ["name"]},
                {"name": "test.model.list", "type": "list", "model": "test.model", "fields": ["name"]},
            ],
            "security": {"groups": [], "access_rights": []},
            "data": [],
        }
        gates = {
            "description": "test",
            "owner_agent": "code-generator",
            "rules": [
                {"type": "view_coverage", "rule_name": "vc", "path": ".factory/schema.json"},
            ],
        }
        runner = _make_project(tmp_path, schema, gates)
        result = runner.check_phase("construction")
        assert result.passed is True

    def test_fails_without_form(self, tmp_path):
        schema = {
            "manifest": {"name": "test", "version": "18.0.1.0.0", "summary": "test", "depends": ["base"], "license": "LGPL-3"},
            "models": [
                {"name": "test.model", "description": "Test model", "mode": "new", "fields": [
                    {"name": "name", "type": "Char", "label": "Name"},
                ]},
            ],
            "views": [
                {"name": "test.model.list", "type": "list", "model": "test.model", "fields": ["name"]},
            ],
            "security": {"groups": [], "access_rights": []},
            "data": [],
        }
        gates = {
            "description": "test",
            "owner_agent": "code-generator",
            "rules": [
                {"type": "view_coverage", "rule_name": "vc", "path": ".factory/schema.json"},
            ],
        }
        runner = _make_project(tmp_path, schema, gates)
        result = runner.check_phase("construction")
        assert result.passed is False
        assert "form" in result.results[0].message.lower()

    def test_fails_without_list(self, tmp_path):
        schema = {
            "manifest": {"name": "test", "version": "18.0.1.0.0", "summary": "test", "depends": ["base"], "license": "LGPL-3"},
            "models": [
                {"name": "test.model", "description": "Test model", "mode": "new", "fields": [
                    {"name": "name", "type": "Char", "label": "Name"},
                ]},
            ],
            "views": [
                {"name": "test.model.form", "type": "form", "model": "test.model", "fields": ["name"]},
            ],
            "security": {"groups": [], "access_rights": []},
            "data": [],
        }
        gates = {
            "description": "test",
            "owner_agent": "code-generator",
            "rules": [
                {"type": "view_coverage", "rule_name": "vc", "path": ".factory/schema.json"},
            ],
        }
        runner = _make_project(tmp_path, schema, gates)
        result = runner.check_phase("construction")
        assert result.passed is False
        assert "list" in result.results[0].message.lower()

    def test_fails_when_schema_missing(self, tmp_path):
        gates = {
            "description": "test",
            "owner_agent": "code-generator",
            "rules": [
                {"type": "view_coverage", "rule_name": "vc", "path": ".factory/schema.json"},
            ],
        }
        factory = tmp_path / ".factory"
        factory.mkdir(parents=True)
        state = {
            "project": "test", "current_phase": "construction", "methodology": "BABOK",
            "phases": {"construction": {"status": "in_progress", "agent": "code-generator"}},
            "valid_transitions": {"construction": ["testing"]},
            "gates": {"construction": gates},
            "artifacts": {}, "context": {},
        }
        (factory / "state.json").write_text(json.dumps(state))
        runner = GateRunner(str(tmp_path))
        result = runner.check_phase("construction")
        assert result.passed is False


class TestViewFieldCheck:
    def test_passes_when_fields_exist(self, tmp_path):
        schema = {
            "manifest": {"name": "test", "version": "18.0.1.0.0", "summary": "test", "depends": ["base"], "license": "LGPL-3"},
            "models": [
                {"name": "test.model", "description": "Test model", "mode": "new", "fields": [
                    {"name": "name", "type": "Char", "label": "Name"},
                    {"name": "partner_id", "type": "Many2one", "label": "Partner", "relation": "res.partner"},
                ]},
            ],
            "views": [
                {"name": "test.model.form", "type": "form", "model": "test.model", "fields": ["name", "partner_id"]},
            ],
            "security": {"groups": [], "access_rights": []},
            "data": [],
        }
        gates = {
            "description": "test",
            "owner_agent": "code-generator",
            "rules": [
                {"type": "view_field_check", "rule_name": "vfc", "path": ".factory/schema.json"},
            ],
        }
        runner = _make_project(tmp_path, schema, gates)
        result = runner.check_phase("construction")
        assert result.passed is True

    def test_fails_when_field_does_not_exist(self, tmp_path):
        schema = {
            "manifest": {"name": "test", "version": "18.0.1.0.0", "summary": "test", "depends": ["base"], "license": "LGPL-3"},
            "models": [
                {"name": "test.model", "description": "Test model", "mode": "new", "fields": [
                    {"name": "name", "type": "Char", "label": "Name"},
                ]},
            ],
            "views": [
                {"name": "test.model.form", "type": "form", "model": "test.model", "fields": ["name", "nonexistent_field"]},
            ],
            "security": {"groups": [], "access_rights": []},
            "data": [],
        }
        gates = {
            "description": "test",
            "owner_agent": "code-generator",
            "rules": [
                {"type": "view_field_check", "rule_name": "vfc", "path": ".factory/schema.json"},
            ],
        }
        runner = _make_project(tmp_path, schema, gates)
        result = runner.check_phase("construction")
        assert result.passed is False
        assert "nonexistent_field" in result.results[0].message


class TestAclCoverage:
    def test_passes_when_all_models_have_acl(self, tmp_path):
        schema = {
            "manifest": {"name": "test", "version": "18.0.1.0.0", "summary": "test", "depends": ["base"], "license": "LGPL-3"},
            "models": [
                {"name": "test.model", "description": "Test model", "mode": "new", "fields": [
                    {"name": "name", "type": "Char", "label": "Name"},
                ]},
            ],
            "views": [],
            "security": {
                "groups": [],
                "access_rights": [
                    {"model": "test.model", "group": "user", "perm_read": True, "perm_write": True, "perm_create": True, "perm_unlink": False},
                ],
            },
            "data": [],
        }
        gates = {
            "description": "test",
            "owner_agent": "code-generator",
            "rules": [
                {"type": "acl_coverage", "rule_name": "ac", "path": ".factory/schema.json"},
            ],
        }
        runner = _make_project(tmp_path, schema, gates)
        result = runner.check_phase("construction")
        assert result.passed is True

    def test_fails_when_model_missing_acl(self, tmp_path):
        schema = {
            "manifest": {"name": "test", "version": "18.0.1.0.0", "summary": "test", "depends": ["base"], "license": "LGPL-3"},
            "models": [
                {"name": "test.model", "description": "Test model", "mode": "new", "fields": [
                    {"name": "name", "type": "Char", "label": "Name"},
                ]},
                {"name": "test.other", "description": "Other model", "mode": "new", "fields": [
                    {"name": "name", "type": "Char", "label": "Name"},
                ]},
            ],
            "views": [],
            "security": {
                "groups": [],
                "access_rights": [
                    {"model": "test.model", "group": "user", "perm_read": True, "perm_write": True, "perm_create": True, "perm_unlink": False},
                ],
            },
            "data": [],
        }
        gates = {
            "description": "test",
            "owner_agent": "code-generator",
            "rules": [
                {"type": "acl_coverage", "rule_name": "ac", "path": ".factory/schema.json"},
            ],
        }
        runner = _make_project(tmp_path, schema, gates)
        result = runner.check_phase("construction")
        assert result.passed is False
        assert "test.other" in result.results[0].message


class TestConstructionGateIntegration:
    def test_all_rules_pass(self, tmp_path):
        schema = {
            "manifest": {"name": "test", "version": "18.0.1.0.0", "summary": "test", "depends": ["base"], "license": "LGPL-3"},
            "models": [
                {"name": "test.model", "description": "Test model", "mode": "new", "fields": [
                    {"name": "name", "type": "Char", "label": "Name"},
                    {"name": "state", "type": "Selection", "label": "Status", "selection": [["draft", "Draft"], ["done", "Done"]]},
                ]},
            ],
            "views": [
                {"name": "test.model.form", "type": "form", "model": "test.model", "fields": ["name", "state"]},
                {"name": "test.model.list", "type": "list", "model": "test.model", "fields": ["name", "state"]},
            ],
            "security": {
                "groups": [{"id": "user", "name": "User", "description": "Group"}],
                "access_rights": [
                    {"model": "test.model", "group": "user", "perm_read": True, "perm_write": True, "perm_create": True, "perm_unlink": False},
                ],
            },
            "data": [],
        }
        gates = {
            "description": "full",
            "owner_agent": "code-generator",
            "rules": [
                {"type": "artifact_exists", "rule_name": "schema_exists", "path": ".factory/schema.json"},
                {"type": "view_coverage", "rule_name": "vc", "path": ".factory/schema.json"},
                {"type": "view_field_check", "rule_name": "vfc", "path": ".factory/schema.json"},
                {"type": "acl_coverage", "rule_name": "ac", "path": ".factory/schema.json"},
            ],
        }
        runner = _make_project(tmp_path, schema, gates)
        result = runner.check_phase("construction")
        assert result.passed is True
        assert result.error_count == 0

    def test_multiple_failures_reported(self, tmp_path):
        schema = {
            "manifest": {"name": "test", "version": "18.0.1.0.0", "summary": "test", "depends": ["base"], "license": "LGPL-3"},
            "models": [
                {"name": "test.model", "description": "Test model", "mode": "new", "fields": [
                    {"name": "name", "type": "Char", "label": "Name"},
                ]},
            ],
            "views": [
                {"name": "test.model.form", "type": "form", "model": "test.model", "fields": ["name", "missing_field"]},
            ],
            "security": {"groups": [], "access_rights": []},
            "data": [],
        }
        gates = {
            "description": "full",
            "owner_agent": "code-generator",
            "rules": [
                {"type": "view_coverage", "rule_name": "vc", "path": ".factory/schema.json"},
                {"type": "view_field_check", "rule_name": "vfc", "path": ".factory/schema.json"},
                {"type": "acl_coverage", "rule_name": "ac", "path": ".factory/schema.json"},
            ],
        }
        runner = _make_project(tmp_path, schema, gates)
        result = runner.check_phase("construction")
        assert result.passed is False
        assert result.error_count == 3

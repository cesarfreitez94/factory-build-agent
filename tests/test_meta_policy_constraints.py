"""Tests for the V2 policy constraints utility."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from fba.meta_policy_constraints import build_policy_constraints, generate_policy_constraints


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "meta" / "policy_constraints.schema.json"


def _prepare_project(tmp_path: Path) -> Path:
    schema_dir = tmp_path / "schemas" / "meta"
    factory_dir = tmp_path / ".factory"
    plugin_dir = tmp_path / ".opencode" / "plugins"
    schema_dir.mkdir(parents=True)
    factory_dir.mkdir(parents=True)
    plugin_dir.mkdir(parents=True)

    (tmp_path / "CONTRIBUTING.md").write_text((REPO_ROOT / "CONTRIBUTING.md").read_text())
    (tmp_path / "CHANGELOG.md").write_text((REPO_ROOT / "CHANGELOG.md").read_text())
    (schema_dir / "policy_constraints.schema.json").write_text(SCHEMA_PATH.read_text())
    (factory_dir / "framework-state.json").write_text('{"schema_version": "1.0", "marker": "unchanged"}\n')
    (plugin_dir / "fba-agent-observer.ts").write_text("export const marker = 'unchanged'\n")
    return tmp_path


def _intent(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "intent_id": "INTENT-20260515-001",
        "objective": "Implement a pure meta-workflow utility",
        "scope": {"include": ["src/fba/meta_policy_constraints.py"], "exclude": []},
        "requested_outputs": ["implementation"],
    }
    value.update(overrides)
    return value


def test_generates_artifact_valid_against_policy_constraints_schema(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    result = generate_policy_constraints(
        project_dir,
        _intent(),
        created_at="2026-05-15T14:00:00Z",
    )

    schema = json.loads(SCHEMA_PATH.read_text())
    artifact = json.loads(result.artifact_path.read_text())

    jsonschema.Draft7Validator(schema).validate(artifact)
    assert result.schema_valid is True
    assert result.artifact_path == project_dir / ".factory/meta/artifacts/policy_constraints/POLICY-20260515-001.json"
    assert artifact["contract_name"] == "policy_constraints"
    assert artifact["contract_version"] == "2.0"
    assert artifact["constraints_id"] == "POLICY-20260515-001"
    assert artifact["intent_id"] == "INTENT-20260515-001"
    assert artifact["created_at"] == "2026-05-15T14:00:00Z"
    assert result.validation_path == project_dir / ".factory/meta/validation/last_policy_constraints.json"


def test_does_not_copy_long_policy_source_content() -> None:
    constraints = build_policy_constraints(
        _intent(),
        (REPO_ROOT / "CONTRIBUTING.md").read_text(),
        (REPO_ROOT / "CHANGELOG.md").read_text(),
        created_at="2026-05-15T14:00:00Z",
    )
    serialized = json.dumps(constraints, ensure_ascii=False)

    assert "CONTRIBUTING.md::branch_policy" in constraints["policy_refs"]
    assert "CHANGELOG.md::unreleased" in constraints["policy_refs"]
    assert "main es SOLO-LECTURA" not in serialized
    assert "Todas las cambios notables" not in serialized
    assert len(constraints["rationale"]) < 300
    assert len(constraints["human_summary"]) < 500


def test_includes_no_direct_commit_to_main() -> None:
    constraints = build_policy_constraints(
        _intent(),
        (REPO_ROOT / "CONTRIBUTING.md").read_text(),
        (REPO_ROOT / "CHANGELOG.md").read_text(),
        created_at="2026-05-15T14:00:00Z",
    )

    assert "no_direct_commit_to_main" in constraints["required_checks"]


def test_blocks_execute_git_operation_and_all_direct_git_actions() -> None:
    constraints = build_policy_constraints(
        _intent(),
        (REPO_ROOT / "CONTRIBUTING.md").read_text(),
        (REPO_ROOT / "CHANGELOG.md").read_text(),
        created_at="2026-05-15T14:00:00Z",
    )

    assert "execute_git_operation" in constraints["blocked_operations"]
    assert "commit" in constraints["blocked_operations"]
    assert "push" in constraints["blocked_operations"]
    assert "open_pr" in constraints["blocked_operations"]
    assert "merge_pr" in constraints["blocked_operations"]


def test_allows_request_git_operation() -> None:
    constraints = build_policy_constraints(
        _intent(),
        (REPO_ROOT / "CONTRIBUTING.md").read_text(),
        (REPO_ROOT / "CHANGELOG.md").read_text(),
        created_at="2026-05-15T14:00:00Z",
    )

    assert "request_git_operation" in constraints["allowed_operations"]


def test_requires_changelog_for_architecture_schema_and_workflow_changes() -> None:
    for objective in (
        "Design architecture changes for the meta workflow",
        "Implement schema updates for policy constraints",
        "Change workflow routing for V2 artifacts",
    ):
        constraints = build_policy_constraints(
            _intent(objective=objective),
            (REPO_ROOT / "CONTRIBUTING.md").read_text(),
            (REPO_ROOT / "CHANGELOG.md").read_text(),
            created_at="2026-05-15T14:00:00Z",
        )

        assert "changelog_required" in constraints["required_checks"]


def test_requires_manual_review_before_pr_or_merge_to_main() -> None:
    for objective in ("Open PR to main", "Merge to main after milestone approval"):
        constraints = build_policy_constraints(
            _intent(objective=objective),
            (REPO_ROOT / "CONTRIBUTING.md").read_text(),
            (REPO_ROOT / "CHANGELOG.md").read_text(),
            created_at="2026-05-15T14:00:00Z",
        )

        assert constraints["requires_user_confirmation"] is True
        assert "manual_review_before_main_pr" in constraints["required_checks"]


def test_blocks_modify_odoo_generator_when_intent_excludes_it() -> None:
    constraints = build_policy_constraints(
        _intent(scope={"include": ["meta workflow"], "exclude": ["odoo generator"]}),
        (REPO_ROOT / "CONTRIBUTING.md").read_text(),
        (REPO_ROOT / "CHANGELOG.md").read_text(),
        created_at="2026-05-15T14:00:00Z",
    )

    assert "modify_odoo_generator" in constraints["blocked_operations"]


def test_does_not_modify_framework_state_or_agent_observer_plugin(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    v1_path = project_dir / ".factory" / "framework-state.json"
    plugin_path = project_dir / ".opencode" / "plugins" / "fba-agent-observer.ts"
    v1_before = v1_path.read_text()
    plugin_before = plugin_path.read_text()

    generate_policy_constraints(
        project_dir,
        _intent(scope={"include": ["schemas"], "exclude": ["odoo generator"]}),
        created_at="2026-05-15T14:00:00Z",
    )

    assert v1_path.read_text() == v1_before
    assert plugin_path.read_text() == plugin_before

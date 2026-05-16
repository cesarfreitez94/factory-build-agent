"""Tests for the V2 context broker utility."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from fba.meta_context_broker import ContextBrokerError, build_context_bundle


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTEXT_SCHEMA_PATH = REPO_ROOT / "schemas" / "meta" / "context_bundle.schema.json"


def _prepare_project(tmp_path: Path) -> Path:
    schema_dir = tmp_path / "schemas" / "meta"
    factory_dir = tmp_path / ".factory"
    plugin_dir = tmp_path / ".opencode" / "plugins"
    generator_dir = tmp_path / "src" / "fba" / "generator"
    schema_dir.mkdir(parents=True)
    factory_dir.mkdir(parents=True)
    plugin_dir.mkdir(parents=True)
    generator_dir.mkdir(parents=True)

    for name in (
        "context_bundle.schema.json",
        "task_packet.schema.json",
        "policy_constraints.schema.json",
        "schema_catalog.schema.json",
    ):
        (schema_dir / name).write_text((REPO_ROOT / "schemas" / "meta" / name).read_text())

    (tmp_path / "CONTRIBUTING.md").write_text((REPO_ROOT / "CONTRIBUTING.md").read_text())
    (factory_dir / "framework-state.json").write_text('{"schema_version": "1.0", "marker": "unchanged"}\n')
    (plugin_dir / "fba-agent-observer.ts").write_text("export const marker = 'unchanged'\n")
    (generator_dir / "renderer.py").write_text("def marker():\n    return 'blocked'\n")
    return tmp_path


def _task_packet(**overrides: object) -> dict[str, object]:
    packet: dict[str, object] = {
        "contract_name": "task_packet",
        "contract_version": "2.0",
        "packet_id": "TPACKET-20260515-001",
        "plan_id": "PLAN-20260515-001",
        "task_id": "TASK-20260515-001",
        "created_at": "2026-05-15T14:04:00Z",
        "objective": "Build a context bundle for policy_constraints contracts",
        "allowed_files": ["schemas/meta/*.json"],
        "forbidden_files": [],
        "allowed_operations": ["read", "validate_schema"],
        "acceptance_criteria": ["context_bundle validates"],
        "inputs_required": ["policy_constraints"],
        "policy_refs": ["CONTRIBUTING"],
    }
    packet.update(overrides)
    return packet


def _policy_constraints(**overrides: object) -> dict[str, object]:
    constraints: dict[str, object] = {
        "contract_name": "policy_constraints",
        "contract_version": "2.0",
        "constraints_id": "POLICY-20260515-001",
        "intent_id": "INTENT-20260515-001",
        "created_at": "2026-05-15T14:00:00Z",
        "policy_refs": ["CONTRIBUTING.md::branch_policy", "CONTRIBUTING.md::tests_policy"],
        "allowed_operations": ["read_contract", "validate_schema", "build_context_bundle"],
        "blocked_operations": ["execute_git_operation", "commit", "push", "open_pr", "merge_pr"],
        "required_checks": ["no_direct_commit_to_main"],
        "requires_user_confirmation": False,
    }
    constraints.update(overrides)
    return constraints


def _schema_catalog() -> dict[str, object]:
    return {
        "contract_name": "schema_catalog",
        "contract_version": "2.0",
        "catalog_id": "SCAT-20260515-001",
        "updated_at": "2026-05-15T14:00:00Z",
        "contracts": [
            {
                "contract_name": "context_bundle",
                "contract_version": "2.0",
                "path": "schemas/meta/context_bundle.schema.json",
                "status": "active",
            },
            {
                "contract_name": "task_packet",
                "contract_version": "2.0",
                "path": "schemas/meta/task_packet.schema.json",
                "status": "active",
            },
            {
                "contract_name": "policy_constraints",
                "contract_version": "2.0",
                "path": "schemas/meta/policy_constraints.schema.json",
                "status": "active",
            },
            {
                "contract_name": "odoo_generator",
                "contract_version": "2.0",
                "path": "src/fba/generator/renderer.py",
                "status": "active",
            },
        ],
        "global_policies": [
            {"policy_id": "CONTRIBUTING", "path": "CONTRIBUTING.md", "mode": "reference"},
        ],
        "compatibility_matrix": [
            {"from": "task_packet@2.0", "to": "context_bundle@2.0", "status": "compatible"},
        ],
    }


def test_generates_context_bundle_valid_against_schema(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    result = build_context_bundle(
        project_dir,
        _task_packet(),
        _policy_constraints(),
        _schema_catalog(),
        now="2026-05-15T14:05:00Z",
    )

    artifact = json.loads(result.artifact_path.read_text())
    schema = json.loads(CONTEXT_SCHEMA_PATH.read_text())
    jsonschema.Draft7Validator(schema).validate(artifact)

    assert result.schema_valid is True
    assert result.artifact_path == project_dir / ".factory/meta/artifacts/context_bundles/CTX-20260515-001.json"
    assert result.validation_path == project_dir / ".factory/meta/validation/last_context_bundle.json"
    assert artifact["contract_name"] == "context_bundle"
    assert artifact["contract_version"] == "2.0"
    assert artifact["packet_id"] == "TPACKET-20260515-001"
    assert artifact["context_items"]


def test_forbidden_files_win_over_allowed_files(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    result = build_context_bundle(
        project_dir,
        _task_packet(forbidden_files=["schemas/meta/task_packet.schema.json"], inputs_required=["task_packet"]),
        _policy_constraints(),
        _schema_catalog(),
        now="2026-05-15T14:05:00Z",
    )

    paths = {item["path"] for item in result.bundle["context_items"]}
    excluded = {item["path"]: item["reason"] for item in result.bundle["excluded_context"]}

    assert "schemas/meta/task_packet.schema.json" not in paths
    assert excluded["schemas/meta/task_packet.schema.json"] == "forbidden_by_task_packet"


def test_fails_when_build_context_bundle_is_not_allowed(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    with pytest.raises(ContextBrokerError, match="build_context_bundle"):
        build_context_bundle(
            project_dir,
            _task_packet(),
            _policy_constraints(allowed_operations=["read_contract", "validate_schema"]),
            _schema_catalog(),
            now="2026-05-15T14:05:00Z",
        )


def test_fails_when_build_context_bundle_is_blocked(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    with pytest.raises(ContextBrokerError, match="blocked"):
        build_context_bundle(
            project_dir,
            _task_packet(),
            _policy_constraints(blocked_operations=["build_context_bundle"]),
            _schema_catalog(),
            now="2026-05-15T14:05:00Z",
        )


def test_fails_when_read_is_not_allowed_by_task_packet(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    with pytest.raises(ContextBrokerError, match="read"):
        build_context_bundle(
            project_dir,
            _task_packet(allowed_operations=["validate_schema"]),
            _policy_constraints(),
            _schema_catalog(),
            now="2026-05-15T14:05:00Z",
        )


def test_blocks_absolute_paths(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    with pytest.raises(ContextBrokerError, match="absolute"):
        build_context_bundle(
            project_dir,
            _task_packet(allowed_files=["/tmp/secret.json"]),
            _policy_constraints(),
            _schema_catalog(),
            now="2026-05-15T14:05:00Z",
        )


def test_blocks_parent_traversal_paths(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    with pytest.raises(ContextBrokerError, match="parent traversal"):
        build_context_bundle(
            project_dir,
            _task_packet(allowed_files=["../secret.json"]),
            _policy_constraints(),
            _schema_catalog(),
            now="2026-05-15T14:05:00Z",
        )


def test_blocks_odoo_generator_when_modify_operation_is_blocked(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    result = build_context_bundle(
        project_dir,
        _task_packet(
            objective="Build context and inspect odoo_generator references",
            allowed_files=["schemas/meta/*.json", "src/fba/generator/*"],
            inputs_required=["odoo_generator"],
        ),
        _policy_constraints(blocked_operations=["modify_odoo_generator"]),
        _schema_catalog(),
        now="2026-05-15T14:05:00Z",
    )

    paths = {item["path"] for item in result.bundle["context_items"]}
    excluded = {item["path"]: item["reason"] for item in result.bundle["excluded_context"]}

    assert "src/fba/generator/renderer.py" not in paths
    assert excluded["src/fba/generator/renderer.py"] == "odoo_generator_blocked"


def test_uses_line_ranges_for_every_context_item(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    result = build_context_bundle(
        project_dir,
        _task_packet(),
        _policy_constraints(),
        _schema_catalog(),
        now="2026-05-15T14:05:00Z",
    )

    for item in result.bundle["context_items"]:
        assert item["line_ranges"]
        assert all(range_item["start"] >= 1 for range_item in item["line_ranges"])
        assert all(range_item["end"] >= range_item["start"] for range_item in item["line_ranges"])


def test_source_count_matches_context_items(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    result = build_context_bundle(
        project_dir,
        _task_packet(),
        _policy_constraints(),
        _schema_catalog(),
        now="2026-05-15T14:05:00Z",
    )

    assert result.bundle["integrity"]["source_count"] == len(result.bundle["context_items"])


def test_truncated_is_true_when_candidates_are_reduced(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    result = build_context_bundle(
        project_dir,
        _task_packet(),
        _policy_constraints(),
        _schema_catalog(),
        now="2026-05-15T14:05:00Z",
    )

    assert result.bundle["integrity"]["truncated"] is True


def test_does_not_modify_framework_state_or_agent_observer_plugin(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    v1_path = project_dir / ".factory" / "framework-state.json"
    plugin_path = project_dir / ".opencode" / "plugins" / "fba-agent-observer.ts"
    v1_before = v1_path.read_text()
    plugin_before = plugin_path.read_text()

    build_context_bundle(
        project_dir,
        _task_packet(),
        _policy_constraints(),
        _schema_catalog(),
        now="2026-05-15T14:05:00Z",
    )

    assert v1_path.read_text() == v1_before
    assert plugin_path.read_text() == plugin_before

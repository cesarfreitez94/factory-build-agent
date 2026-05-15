"""Tests for the V2 task packet builder utility."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from fba.meta_task_packet_builder import (
    TaskPacketBuilderError,
    build_task_packet,
    generate_task_packet,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "meta" / "task_packet.schema.json"


def _prepare_project(tmp_path: Path) -> Path:
    schema_dir = tmp_path / "schemas" / "meta"
    factory_dir = tmp_path / ".factory"
    plugin_dir = tmp_path / ".opencode" / "plugins"
    source_dir = tmp_path / "src" / "fba"
    test_dir = tmp_path / "tests"
    schema_dir.mkdir(parents=True)
    factory_dir.mkdir(parents=True)
    plugin_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)
    test_dir.mkdir(parents=True)

    for name in (
        "plan.schema.json",
        "policy_constraints.schema.json",
        "schema_catalog.schema.json",
        "task_packet.schema.json",
    ):
        (schema_dir / name).write_text((REPO_ROOT / "schemas" / "meta" / name).read_text())

    (factory_dir / "framework-state.json").write_text('{"schema_version": "1.0", "marker": "unchanged"}\n')
    (plugin_dir / "fba-agent-observer.ts").write_text("export const marker = 'unchanged'\n")
    (source_dir / "meta_task_packet_builder.py").write_text("def marker():\n    return 'unchanged'\n")
    (source_dir / "cli.py").write_text("def marker():\n    return 'unchanged'\n")
    (source_dir / "generator").mkdir(parents=True, exist_ok=True)
    (source_dir / "generator" / "renderer.py").write_text("def marker():\n    return 'blocked'\n")
    (test_dir / "test_meta_task_packet_builder.py").write_text("def marker():\n    return 'unchanged'\n")
    return tmp_path


def _plan(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "contract_name": "plan",
        "contract_version": "2.0",
        "plan_id": "PLAN-20260515-001",
        "intent_id": "INTENT-20260515-001",
        "roadmap_slice_id": "RSLICE-20260515-001",
        "created_at": "2026-05-15T14:03:00Z",
        "goal": "Build a deterministic task packet builder",
        "tasks": [
            {
                "task_id": "TASK-20260515-001",
                "title": "Implement task packet builder utility",
                "type": "implementation",
                "depends_on": [],
                "inputs": ["plan", "policy_constraints", "schema_catalog", "task_packet"],
                "outputs": [
                    "src/fba/meta_task_packet_builder.py",
                    "tests/test_meta_task_packet_builder.py",
                ],
                "owner_hint": "framework-builder",
            }
        ],
        "acceptance_criteria": ["The packet is schema-valid."],
        "constraints": ["contracts_only"],
        "requires_user_confirmation": False,
    }
    value.update(overrides)
    return value


def _policy_constraints(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "contract_name": "policy_constraints",
        "contract_version": "2.0",
        "constraints_id": "POLICY-20260515-001",
        "intent_id": "INTENT-20260515-001",
        "created_at": "2026-05-15T14:01:00Z",
        "policy_refs": ["CONTRIBUTING.md::branch_policy", "CONTRIBUTING.md::tests_policy"],
        "allowed_operations": ["read_contract", "validate_schema", "run_tests", "request_git_operation"],
        "blocked_operations": ["execute_git_operation", "commit", "push", "open_pr", "merge_pr"],
        "required_checks": ["no_direct_commit_to_main"],
        "requires_user_confirmation": False,
    }
    value.update(overrides)
    return value


def _schema_catalog(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "contract_name": "schema_catalog",
        "contract_version": "2.0",
        "catalog_id": "SCAT-20260515-001",
        "updated_at": "2026-05-15T14:00:00Z",
        "contracts": [
            {
                "contract_name": "plan",
                "contract_version": "2.0",
                "path": "schemas/meta/plan.schema.json",
                "status": "active",
            },
            {
                "contract_name": "policy_constraints",
                "contract_version": "2.0",
                "path": "schemas/meta/policy_constraints.schema.json",
                "status": "active",
            },
            {
                "contract_name": "schema_catalog",
                "contract_version": "2.0",
                "path": "schemas/meta/schema_catalog.schema.json",
                "status": "active",
            },
            {
                "contract_name": "task_packet",
                "contract_version": "2.0",
                "path": "schemas/meta/task_packet.schema.json",
                "status": "active",
            },
        ],
        "global_policies": [
            {"policy_id": "CONTRIBUTING", "path": "CONTRIBUTING.md", "mode": "reference"},
            {"policy_id": "CHANGELOG", "path": "CHANGELOG.md", "mode": "reference"},
        ],
        "compatibility_matrix": [
            {"from": "plan@2.0", "to": "task_packet@2.0", "status": "compatible"},
        ],
    }
    value.update(overrides)
    return value


def test_generates_task_packet_valid_against_schema(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    result = generate_task_packet(
        project_dir,
        _plan(),
        _policy_constraints(),
        _schema_catalog(),
        "TASK-20260515-001",
        now="2026-05-15T14:05:00Z",
    )

    schema = json.loads(SCHEMA_PATH.read_text())
    artifact = json.loads(result.artifact_path.read_text())

    jsonschema.Draft7Validator(schema).validate(artifact)
    assert result.schema_valid is True
    assert result.artifact_path == project_dir / ".factory/meta/artifacts/task_packets/TPACKET-20260515-001.json"
    assert result.validation_path == project_dir / ".factory/meta/validation/last_task_packet.json"
    assert artifact["contract_name"] == "task_packet"
    assert artifact["contract_version"] == "2.0"
    assert artifact["task_id"] == "TASK-20260515-001"
    assert artifact["plan_id"] == "PLAN-20260515-001"


def test_fails_when_task_id_is_missing(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    with pytest.raises(TaskPacketBuilderError, match="not found"):
        build_task_packet(
            project_dir,
            _plan(),
            _policy_constraints(),
            _schema_catalog(),
            "TASK-20260515-999",
            now="2026-05-15T14:05:00Z",
        )


def test_fails_when_task_id_is_duplicated(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    plan = _plan(
        tasks=[
            {
                "task_id": "TASK-20260515-001",
                "title": "First task",
                "type": "implementation",
                "depends_on": [],
                "inputs": ["plan"],
                "outputs": ["src/fba/meta_task_packet_builder.py"],
            },
            {
                "task_id": "TASK-20260515-001",
                "title": "Duplicate task",
                "type": "implementation",
                "depends_on": [],
                "inputs": ["plan"],
                "outputs": ["tests/test_meta_task_packet_builder.py"],
            },
        ]
    )

    with pytest.raises(TaskPacketBuilderError, match="duplicate"):
        build_task_packet(
            project_dir,
            plan,
            _policy_constraints(),
            _schema_catalog(),
            "TASK-20260515-001",
            now="2026-05-15T14:05:00Z",
        )


def test_forbidden_files_win_over_allowed_files(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    result = build_task_packet(
        project_dir,
        _plan(
            tasks=[
                {
                    "task_id": "TASK-20260515-001",
                    "title": "Implement task packet builder utility",
                    "type": "implementation",
                    "depends_on": [],
                    "inputs": ["plan", "policy_constraints", "schema_catalog", "task_packet"],
                    "outputs": [
                        "src/fba/meta_task_packet_builder.py",
                        "src/fba/generator/renderer.py",
                    ],
                }
            ]
        ),
        _policy_constraints(blocked_operations=["modify_odoo_generator"]),
        _schema_catalog(),
        "TASK-20260515-001",
        now="2026-05-15T14:05:00Z",
    )

    assert "src/fba/generator/renderer.py" not in result["allowed_files"]
    assert "src/fba/generator/**" in result["forbidden_files"]


def test_rejects_broad_globs_in_allowed_files(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    with pytest.raises(TaskPacketBuilderError, match="glob"):
        build_task_packet(
            project_dir,
            _plan(
                tasks=[
                    {
                        "task_id": "TASK-20260515-001",
                        "title": "Implement task packet builder utility",
                        "type": "implementation",
                        "depends_on": [],
                        "inputs": ["plan", "policy_constraints", "schema_catalog", "task_packet"],
                        "outputs": ["src/**"],
                    }
                ]
            ),
            _policy_constraints(),
            _schema_catalog(),
            "TASK-20260515-001",
            now="2026-05-15T14:05:00Z",
        )


def test_applies_hard_deny_permanent(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    result = build_task_packet(
        project_dir,
        _plan(
            tasks=[
                {
                    "task_id": "TASK-20260515-001",
                    "title": "Implement task packet builder utility",
                    "type": "implementation",
                    "depends_on": [],
                    "inputs": ["plan", "policy_constraints", "schema_catalog", "task_packet"],
                    "outputs": [
                        "src/fba/meta_task_packet_builder.py",
                        ".factory/framework-state.json",
                        "src/fba/cli.py",
                    ],
                }
            ]
        ),
        _policy_constraints(),
        _schema_catalog(),
        "TASK-20260515-001",
        now="2026-05-15T14:05:00Z",
    )

    assert ".factory/framework-state.json" not in result["allowed_files"]
    assert ".factory/framework-state.json" in result["forbidden_files"]
    assert "src/fba/cli.py" not in result["allowed_files"]
    assert "src/fba/cli.py" in result["forbidden_files"]


def test_blocks_generator_when_modify_odoo_generator_is_blocked(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    result = build_task_packet(
        project_dir,
        _plan(
            tasks=[
                {
                    "task_id": "TASK-20260515-001",
                    "title": "Implement task packet builder utility",
                    "type": "implementation",
                    "depends_on": [],
                    "inputs": ["plan", "policy_constraints", "schema_catalog", "task_packet"],
                    "outputs": ["src/fba/meta_task_packet_builder.py", "src/fba/generator/renderer.py"],
                }
            ]
        ),
        _policy_constraints(blocked_operations=["modify_odoo_generator"]),
        _schema_catalog(),
        "TASK-20260515-001",
        now="2026-05-15T14:05:00Z",
    )

    assert "src/fba/generator/renderer.py" not in result["allowed_files"]
    assert "src/fba/generator/**" in result["forbidden_files"]


def test_does_not_add_create_or_modify_schema_unless_explicit(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    packet = build_task_packet(
        project_dir,
        _plan(),
        _policy_constraints(),
        _schema_catalog(),
        "TASK-20260515-001",
        now="2026-05-15T14:05:00Z",
    )

    assert "create_schema" not in packet["allowed_operations"]
    assert "modify_schema" not in packet["allowed_operations"]


def test_adds_changelog_criterion_when_policy_requires_it(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    packet = build_task_packet(
        project_dir,
        _plan(),
        _policy_constraints(required_checks=["no_direct_commit_to_main", "changelog_required"]),
        _schema_catalog(),
        "TASK-20260515-001",
        now="2026-05-15T14:05:00Z",
    )

    assert any("CHANGELOG.md" in criterion for criterion in packet["acceptance_criteria"])


def test_adds_test_requirements_when_policy_requires_it(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    packet = build_task_packet(
        project_dir,
        _plan(),
        _policy_constraints(required_checks=["no_direct_commit_to_main", "tests_required_before_pr"]),
        _schema_catalog(),
        "TASK-20260515-001",
        now="2026-05-15T14:05:00Z",
    )

    assert packet["test_requirements"]
    assert any("pytest" in requirement.lower() for requirement in packet["test_requirements"])


def test_does_not_add_direct_git_operations(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)

    packet = build_task_packet(
        project_dir,
        _plan(),
        _policy_constraints(),
        _schema_catalog(),
        "TASK-20260515-001",
        now="2026-05-15T14:05:00Z",
    )

    assert "commit" not in packet["allowed_operations"]
    assert "push" not in packet["allowed_operations"]
    assert "open_pr" not in packet["allowed_operations"]
    assert "merge_pr" not in packet["allowed_operations"]
    assert "execute_git_operation" not in packet["allowed_operations"]


def test_does_not_modify_framework_state_or_agent_observer_plugin(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    v1_path = project_dir / ".factory" / "framework-state.json"
    plugin_path = project_dir / ".opencode" / "plugins" / "fba-agent-observer.ts"
    v1_before = v1_path.read_text()
    plugin_before = plugin_path.read_text()

    generate_task_packet(
        project_dir,
        _plan(),
        _policy_constraints(),
        _schema_catalog(),
        "TASK-20260515-001",
        now="2026-05-15T14:05:00Z",
    )

    assert v1_path.read_text() == v1_before
    assert plugin_path.read_text() == plugin_before

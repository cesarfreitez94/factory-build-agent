"""Tests for the V2 plan builder utility."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from fba.meta_plan_builder import PlanBuilderError, build_plan, generate_plan
from fba.meta_task_packet_builder import generate_task_packet


REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_SCHEMA_PATH = REPO_ROOT / "schemas" / "meta" / "plan.schema.json"


def _prepare_project(tmp_path: Path) -> Path:
    schema_dir = tmp_path / "schemas" / "meta"
    factory_dir = tmp_path / ".factory"
    plugin_dir = tmp_path / ".opencode" / "plugins"
    schema_dir.mkdir(parents=True, exist_ok=True)
    factory_dir.mkdir(parents=True, exist_ok=True)
    plugin_dir.mkdir(parents=True, exist_ok=True)

    for name in (
        "plan.schema.json",
        "intent.schema.json",
        "roadmap_slice.schema.json",
        "policy_constraints.schema.json",
        "task_packet.schema.json",
        "schema_catalog.schema.json",
    ):
        (schema_dir / name).write_text((REPO_ROOT / "schemas" / "meta" / name).read_text())

    (factory_dir / "framework-state.json").write_text('{"schema_version": "1.0", "marker": "unchanged"}\n')
    (plugin_dir / "fba-agent-observer.ts").write_text("export const marker = 'unchanged'\n")
    return tmp_path


def _intent(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "contract_name": "intent",
        "contract_version": "2.0",
        "intent_id": "INTENT-20260515-001",
        "created_at": "2026-05-15T14:00:00Z",
        "source": "user",
        "objective": "Implement the Plan Builder V2 utility",
        "scope": {
            "include": ["src/fba/meta_plan_builder.py", "tests/test_meta_plan_builder.py"],
            "exclude": [".factory/framework-state.json", ".opencode/plugins/fba-agent-observer.ts"],
        },
        "constraints": ["no_v1_runtime_changes"],
        "requested_outputs": ["src/fba/meta_plan_builder.py", "tests/test_meta_plan_builder.py"],
        "non_goals": ["modify_odoo_generator"],
        "urgency": "high",
        "requires_user_confirmation": False,
        "related_milestone": {"id": "M18", "status": "in_progress", "branch": "milestone/18.0-input-extension-layer"},
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
        "blocked_operations": ["execute_git_operation", "commit", "push", "open_pr", "merge_pr", "modify_odoo_generator"],
        "required_checks": ["no_direct_commit_to_main", "tests_required_before_pr"],
        "requires_user_confirmation": False,
    }
    value.update(overrides)
    return value


def _roadmap_slice(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "contract_name": "roadmap_slice",
        "contract_version": "2.0",
        "slice_id": "RSLICE-20260515-001",
        "intent_id": "INTENT-20260515-001",
        "created_at": "2026-05-15T14:02:00Z",
        "active_milestone": {"id": "M18", "status": "in_progress", "branch": "milestone/18.0-input-extension-layer"},
        "relevant_milestones": [{"id": "M18", "status": "in_progress"}],
        "policy_refs": ["CONTRIBUTING.md::branch_policy", "CONTRIBUTING.md::tests_policy"],
        "allowed_operations": ["read_contract", "validate_schema", "create_task_packet", "build_context_bundle", "run_tests", "request_git_operation"],
        "blocked_operations": ["execute_git_operation", "commit", "push", "open_pr", "merge_pr", "modify_odoo_generator"],
        "source_refs": [{"path": "ROADMAP.md", "section": "M18", "line_ranges": [{"start": 1, "end": 10}]}],
    }
    value.update(overrides)
    return value


def _schema_catalog() -> dict[str, object]:
    return {
        "contract_name": "schema_catalog",
        "contract_version": "2.0",
        "catalog_id": "SCAT-20260515-001",
        "updated_at": "2026-05-15T14:00:00Z",
        "contracts": [
            {"contract_name": "plan", "contract_version": "2.0", "path": "schemas/meta/plan.schema.json", "status": "active"},
            {"contract_name": "policy_constraints", "contract_version": "2.0", "path": "schemas/meta/policy_constraints.schema.json", "status": "active"},
            {"contract_name": "schema_catalog", "contract_version": "2.0", "path": "schemas/meta/schema_catalog.schema.json", "status": "active"},
            {"contract_name": "task_packet", "contract_version": "2.0", "path": "schemas/meta/task_packet.schema.json", "status": "active"},
        ],
        "global_policies": [
            {"policy_id": "CONTRIBUTING", "path": "CONTRIBUTING.md", "mode": "reference"},
            {"policy_id": "CHANGELOG", "path": "CHANGELOG.md", "mode": "reference"},
        ],
        "compatibility_matrix": [{"from": "plan@2.0", "to": "task_packet@2.0", "status": "compatible"}],
    }


def test_builds_valid_plan_against_schema() -> None:
    plan = build_plan(_intent(), _policy_constraints(), _roadmap_slice(), now="2026-05-15T14:03:00Z")

    schema = json.loads(PLAN_SCHEMA_PATH.read_text())
    jsonschema.Draft7Validator(schema).validate(plan)

    assert plan["contract_name"] == "plan"
    assert plan["contract_version"] == "2.0"
    assert plan["intent_id"] == "INTENT-20260515-001"
    assert plan["roadmap_slice_id"] == "RSLICE-20260515-001"
    assert plan["tasks"]
    assert all("task_id" in task and "inputs" in task and "outputs" in task and "depends_on" in task for task in plan["tasks"])


def test_fails_when_intent_id_is_inconsistent() -> None:
    with pytest.raises(PlanBuilderError, match="intent_id"):
        build_plan(_intent(), _policy_constraints(intent_id="INTENT-20260515-999"), _roadmap_slice(), now="2026-05-15T14:03:00Z")


def test_blocked_operations_win_and_are_excluded() -> None:
    plan = build_plan(
        _intent(
            scope={
                "include": ["src/fba/meta_plan_builder.py", "src/fba/generator/renderer.py"],
                "exclude": [],
            },
            requested_outputs=["src/fba/meta_plan_builder.py", "src/fba/generator/renderer.py"],
        ),
        _policy_constraints(),
        _roadmap_slice(),
        now="2026-05-15T14:03:00Z",
    )

    assert all("src/fba/generator/" not in output for task in plan["tasks"] for output in task["outputs"])
    assert any("src/fba/generator/renderer.py" in item for item in plan.get("out_of_scope", []))
    assert any(constraint == "blocked_operation:modify_odoo_generator" for constraint in plan["constraints"])


def test_warns_when_plan_exceeds_five_tasks() -> None:
    include = [f"src/fba/meta_feature_{index}.py" for index in range(1, 7)]
    outputs = list(include)
    plan = build_plan(
        _intent(scope={"include": include, "exclude": []}, requested_outputs=outputs),
        _policy_constraints(),
        _roadmap_slice(),
        now="2026-05-15T14:03:00Z",
    )

    assert len(plan["tasks"]) == 6
    assert "Warning" in plan["human_summary"]


def test_requires_user_confirmation_when_plan_exceeds_eight_tasks() -> None:
    include = [f"src/fba/meta_feature_{index}.py" for index in range(1, 10)]
    plan = build_plan(
        _intent(scope={"include": include, "exclude": []}, requested_outputs=list(include)),
        _policy_constraints(),
        _roadmap_slice(),
        now="2026-05-15T14:03:00Z",
    )

    assert len(plan["tasks"]) == 9
    assert plan["requires_user_confirmation"] is True


def test_does_not_emit_broad_outputs() -> None:
    plan = build_plan(
        _intent(
            scope={"include": ["src/**", "src/fba/meta_plan_builder.py"], "exclude": []},
            requested_outputs=["src/**", "src/fba/meta_plan_builder.py"],
        ),
        _policy_constraints(),
        _roadmap_slice(),
        now="2026-05-15T14:03:00Z",
    )

    outputs = [output for task in plan["tasks"] for output in task["outputs"]]
    assert all("*" not in output and "?" not in output and "[" not in output and "]" not in output for output in outputs)
    assert all(output != "src/**" for output in outputs)


def test_does_not_generate_direct_git_operations() -> None:
    plan = build_plan(_intent(), _policy_constraints(), _roadmap_slice(), now="2026-05-15T14:03:00Z")

    assert all(task["type"] != "git_operation" for task in plan["tasks"])
    assert all("commit" not in task["type"] for task in plan["tasks"])
    assert all("push" not in task["type"] for task in plan["tasks"])
    assert all("merge" not in task["type"] for task in plan["tasks"])


def test_generated_tasks_are_consumable_by_task_packet_builder(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    plan = build_plan(_intent(), _policy_constraints(), _roadmap_slice(), now="2026-05-15T14:03:00Z")

    for task in plan["tasks"]:
        result = generate_task_packet(
            project_dir,
            plan,
            _policy_constraints(),
            _schema_catalog(),
            task["task_id"],
            now="2026-05-15T14:05:00Z",
            write_validation_report=False,
        )
        assert result.schema_valid is True
        assert result.packet["task_id"] == task["task_id"]


def test_generate_plan_writes_only_v2_artifacts(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    v1_path = project_dir / ".factory" / "framework-state.json"
    plugin_path = project_dir / ".opencode" / "plugins" / "fba-agent-observer.ts"
    v1_before = v1_path.read_text()
    plugin_before = plugin_path.read_text()

    result = generate_plan(
        project_dir,
        _intent(),
        _policy_constraints(),
        _roadmap_slice(),
        now="2026-05-15T14:03:00Z",
    )

    assert result.artifact_path.exists()
    assert result.validation_path is not None and result.validation_path.exists()
    assert v1_path.read_text() == v1_before
    assert plugin_path.read_text() == plugin_before

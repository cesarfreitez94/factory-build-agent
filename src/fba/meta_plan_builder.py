"""Pure utility for V2 plan generation.

The V1 framework state remains authoritative. This module only reads explicit
V2 inputs, validates them against the meta schemas, and can write a shadow
plan artifact under .factory/meta/artifacts.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, cast

import jsonschema


MAX_NORMAL_TASKS = 5
MAX_CONFIRMATION_TASKS = 8
BASE_CONTRACT_INPUTS = ["intent", "policy_constraints", "roadmap_slice"]
HARD_DENY_PATTERNS = [
    ".factory/framework-state.json",
    ".factory/state.json",
    ".factory/events.jsonl",
    ".opencode/agents/**",
    ".opencode/commands/**",
    "templates/.opencode/agents/**",
    "templates/.opencode/commands/**",
    ".opencode/plugins/fba-agent-observer.ts",
    "src/fba/generator/**",
    "src/fba/cli.py",
]
TASK_PRIORITY = {
    "schema_design": 0,
    "implementation": 1,
    "test": 2,
    "review": 3,
}


@dataclass(frozen=True)
class PlanBuilderResult:
    artifact_path: Path
    validation_path: Path | None
    plan: dict[str, Any]
    schema_valid: bool


class PlanBuilderError(Exception):
    """Raised when a plan cannot be built safely."""


def build_plan(
    intent: Mapping[str, Any],
    policy_constraints: Mapping[str, Any],
    roadmap_slice: Mapping[str, Any],
    *,
    now: datetime | str | None = None,
    sequence: int = 1,
) -> dict[str, Any]:
    """Build a V2 plan instance without writing files."""

    root = _repo_root()
    timestamp = _normalize_timestamp(now)
    stamp = timestamp[:10].replace("-", "")

    _validate_instance(root, "intent.schema.json", intent, "intent")
    _validate_instance(root, "policy_constraints.schema.json", policy_constraints, "policy_constraints")
    _validate_instance(root, "roadmap_slice.schema.json", roadmap_slice, "roadmap_slice")

    intent_id = _required_string(intent, "intent_id")
    if intent_id != _required_string(policy_constraints, "intent_id"):
        raise PlanBuilderError("intent_id mismatch between intent and policy_constraints")
    if intent_id != _required_string(roadmap_slice, "intent_id"):
        raise PlanBuilderError("intent_id mismatch between intent and roadmap_slice")

    plan_id = f"PLAN-{stamp}-{sequence:03d}"
    effective_allowed_operations, effective_blocked_operations = _effective_operations(policy_constraints, roadmap_slice)
    constraints = _build_constraints(intent, policy_constraints, roadmap_slice, effective_blocked_operations)
    out_of_scope: list[str] = []
    for value in _excluded_items(intent):
        out_of_scope.append(f"scope exclusion: {value}")
    work_items = _work_items(intent)
    executable_items, filtered_out_of_scope = _filter_work_items(work_items, effective_allowed_operations, effective_blocked_operations)
    out_of_scope.extend(filtered_out_of_scope)
    task_specs = _build_task_specs(
        executable_items,
        plan_id,
        effective_allowed_operations,
    )

    if not task_specs:
        task_specs = [_fallback_task_spec(intent, plan_id)]
        out_of_scope.append("requested scope could not be translated into executable work items")

    tasks = _materialize_tasks(task_specs, stamp, sequence)
    acceptance_criteria = _build_acceptance_criteria(intent, policy_constraints, roadmap_slice, tasks)
    requires_user_confirmation = bool(
        intent.get("requires_user_confirmation", False)
        or policy_constraints.get("requires_user_confirmation", False)
        or len(tasks) > MAX_CONFIRMATION_TASKS
        or roadmap_slice.get("active_milestone", {}).get("status") == "paused"
    )

    plan: dict[str, Any] = {
        "contract_name": "plan",
        "contract_version": "2.0",
        "plan_id": plan_id,
        "intent_id": intent_id,
        "roadmap_slice_id": _required_string(roadmap_slice, "slice_id"),
        "created_at": timestamp,
        "goal": _required_string(intent, "objective"),
        "tasks": tasks,
        "acceptance_criteria": acceptance_criteria,
        "constraints": constraints,
        "requires_user_confirmation": requires_user_confirmation,
        "estimated_order": [task["task_id"] for task in tasks],
        "assumptions": _build_assumptions(intent, roadmap_slice, effective_allowed_operations),
        "out_of_scope": _ordered_unique(out_of_scope),
        "risk_register": _build_risk_register(tasks, out_of_scope, requires_user_confirmation),
        "human_summary": _human_summary(tasks, out_of_scope, requires_user_confirmation),
    }

    _validate_plan(root, plan)
    return plan


def generate_plan(
    project_dir: Path,
    intent: Mapping[str, Any],
    policy_constraints: Mapping[str, Any],
    roadmap_slice: Mapping[str, Any],
    *,
    now: datetime | str | None = None,
    sequence: int = 1,
    write_validation_report: bool = True,
) -> PlanBuilderResult:
    """Generate, validate, and write a V2 plan artifact."""

    root = Path(project_dir).resolve()
    timestamp = _normalize_timestamp(now)
    plan = build_plan(intent, policy_constraints, roadmap_slice, now=timestamp, sequence=sequence)

    artifact_dir = root / ".factory" / "meta" / "artifacts" / "plans"
    artifact_path = artifact_dir / f"{plan['plan_id']}.json"
    _write_json(artifact_path, plan)

    validation_report_path: Path | None = None
    if write_validation_report:
        validation_path = root / ".factory" / "meta" / "validation" / "last_plan.json"
        validation_report = {
            "contract_name": "plan_validation",
            "contract_version": "2.0",
            "validated_at": timestamp,
            "artifact_path": str(artifact_path.relative_to(root)),
            "schema_path": "schemas/meta/plan.schema.json",
            "schema_valid": True,
        }
        _write_json(validation_path, validation_report)
        validation_report_path = validation_path

    return PlanBuilderResult(
        artifact_path=artifact_path,
        validation_path=validation_report_path,
        plan=plan,
        schema_valid=True,
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _validate_instance(root: Path, schema_name: str, instance: Mapping[str, Any], contract_name: str) -> None:
    schema_path = root / "schemas" / "meta" / schema_name
    schema = cast(dict[str, Any], json.loads(_read_text(schema_path)))
    try:
        jsonschema.Draft7Validator(schema).validate(instance)
    except jsonschema.ValidationError as exc:
        raise PlanBuilderError(f"Invalid {contract_name} input: {exc.message}") from exc


def _validate_plan(root: Path, plan: Mapping[str, Any]) -> None:
    schema_path = root / "schemas" / "meta" / "plan.schema.json"
    schema = cast(dict[str, Any], json.loads(_read_text(schema_path)))
    try:
        jsonschema.Draft7Validator(schema).validate(plan)
    except jsonschema.ValidationError as exc:
        raise PlanBuilderError(f"Invalid plan output: {exc.message}") from exc


def _build_constraints(
    intent: Mapping[str, Any],
    policy_constraints: Mapping[str, Any],
    roadmap_slice: Mapping[str, Any],
    effective_blocked_operations: list[str],
) -> list[str]:
    values: list[str] = []

    for value in _string_list(intent.get("constraints", [])):
        values.append(f"intent_constraint:{value}")

    scope = intent.get("scope")
    if isinstance(scope, Mapping):
        for value in _string_list(scope.get("include", [])):
            values.append(f"scope_include:{value}")
        for value in _string_list(scope.get("exclude", [])):
            values.append(f"scope_exclude:{value}")

    for value in _string_list(intent.get("non_goals", [])):
        values.append(f"non_goal:{value}")

    for value in _string_list(policy_constraints.get("policy_refs", [])):
        values.append(f"policy_ref:{value}")

    for value in _string_list(policy_constraints.get("required_checks", [])):
        values.append(f"required_check:{value}")

    for value in effective_blocked_operations:
        values.append(f"blocked_operation:{value}")

    active_milestone = roadmap_slice.get("active_milestone")
    if isinstance(active_milestone, Mapping):
        milestone_id = active_milestone.get("id")
        if isinstance(milestone_id, str) and milestone_id:
            values.append(f"active_milestone:{milestone_id}")

    for value in _string_list(roadmap_slice.get("policy_refs", [])):
        values.append(f"roadmap_policy_ref:{value}")

    return _ordered_unique(values)


def _work_items(intent: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    scope = intent.get("scope")
    if isinstance(scope, Mapping):
        values.extend(_string_list(scope.get("include", [])))

    values.extend(_string_list(intent.get("requested_outputs", [])))

    ordered = _ordered_unique([value for value in values if value])
    return ordered or [_required_string(intent, "objective")]


def _excluded_items(intent: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    scope = intent.get("scope")
    if isinstance(scope, Mapping):
        values.extend(_string_list(scope.get("exclude", [])))
    values.extend(_string_list(intent.get("non_goals", [])))
    return _ordered_unique(values)


def _filter_work_items(
    work_items: list[str],
    effective_allowed_operations: list[str],
    effective_blocked_operations: list[str],
) -> tuple[list[str], list[str]]:
    executable: list[str] = []
    out_of_scope: list[str] = []

    for item in work_items:
        if _looks_like_glob(item):
            out_of_scope.append(f"excluded glob reference: {item}")
            continue
        if _is_hard_denied(item, effective_blocked_operations):
            out_of_scope.append(f"blocked by policy/roadmap: {item}")
            continue

        task_type = _classify_item(item)
        if task_type == "schema_design" and "design_schema" not in effective_allowed_operations:
            out_of_scope.append(f"schema design not allowed: {item}")
            continue
        if task_type == "test" and "run_tests" not in effective_allowed_operations:
            out_of_scope.append(f"tests not allowed: {item}")
            continue

        executable.append(item)

    return _ordered_unique(executable), _ordered_unique(out_of_scope)


def _build_task_specs(
    items: list[str],
    plan_id: str,
    effective_allowed_operations: list[str],
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for index, item in enumerate(_sort_items(items), start=1):
        task_type = _classify_item(item)
        if task_type == "schema_design" and "design_schema" not in effective_allowed_operations:
            continue
        if task_type == "test" and "run_tests" not in effective_allowed_operations:
            continue

        outputs = [_normalize_output(item, task_type, plan_id, index)]
        title = _title_from_item(item, task_type)
        specs.append(
            {
                "task_id": f"TASK-{plan_id.split('-')[1]}-{index:03d}",
                "title": title,
                "type": task_type,
                "inputs": BASE_CONTRACT_INPUTS,
                "outputs": outputs,
                "depends_on": [f"TASK-{plan_id.split('-')[1]}-{index - 1:03d}"] if index > 1 else [],
            }
        )

    return specs


def _fallback_task_spec(intent: Mapping[str, Any], plan_id: str) -> dict[str, Any]:
    stamp = plan_id.split("-")[1]
    return {
        "task_id": f"TASK-{stamp}-001",
        "title": f"Review blocked scope for {_slug_from_text(_required_string(intent, 'objective'))}",
        "type": "review",
        "inputs": BASE_CONTRACT_INPUTS,
        "outputs": [f".factory/meta/validation/{plan_id}.json"],
        "depends_on": [],
    }


def _materialize_tasks(task_specs: list[dict[str, Any]], stamp: str, sequence: int) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for index, spec in enumerate(task_specs, start=1):
        task = dict(spec)
        task["task_id"] = f"TASK-{stamp}-{index:03d}"
        if index > 1:
            task["depends_on"] = [f"TASK-{stamp}-{index - 1:03d}"]
        tasks.append(task)
    return tasks


def _build_acceptance_criteria(
    intent: Mapping[str, Any],
    policy_constraints: Mapping[str, Any],
    roadmap_slice: Mapping[str, Any],
    tasks: list[dict[str, Any]],
) -> list[str]:
    values = [
        "The plan validates against schemas/meta/plan.schema.json.",
        "Every task has concrete outputs and explicit dependencies.",
        "Blocked operations inherited from policy and roadmap are excluded from the executable scope.",
        "The resulting tasks can be turned into task_packet artifacts without broad file globs.",
    ]

    if "tests_required_before_pr" in _string_list(policy_constraints.get("required_checks", [])):
        values.append("Relevant tests are planned before any release or PR step.")
    if _string_list(intent.get("non_goals", [])):
        values.append("Declared non-goals remain out of scope.")
    if len(tasks) > MAX_NORMAL_TASKS:
        values.append("The plan is split into a bounded set of execution tasks.")

    active_milestone = roadmap_slice.get("active_milestone")
    if isinstance(active_milestone, Mapping) and isinstance(active_milestone.get("id"), str):
        values.append(f"The plan stays aligned with milestone {active_milestone['id']}.")

    return _ordered_unique(values)


def _build_assumptions(
    intent: Mapping[str, Any],
    roadmap_slice: Mapping[str, Any],
    effective_allowed_operations: list[str],
) -> list[str]:
    values = [
        "Requested outputs are treated as deterministic work-item hints.",
        "Only explicitly allowed operations are planned.",
    ]
    if "design_schema" not in effective_allowed_operations:
        values.append("Schema design work is assumed to be out of scope unless explicitly allowed.")
    if _string_list(intent.get("requested_outputs", [])):
        values.append("Requested outputs are mapped to concrete deliverables when possible.")
    active_milestone = roadmap_slice.get("active_milestone")
    if isinstance(active_milestone, Mapping) and active_milestone.get("status") == "paused":
        values.append("Paused milestones require human confirmation before execution.")
    return _ordered_unique(values)


def _build_risk_register(
    tasks: list[dict[str, Any]],
    out_of_scope: list[str],
    requires_user_confirmation: bool,
) -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    if out_of_scope:
        values.append(
            {
                "risk": "Some requested items were excluded from the executable scope.",
                "impact": "The plan may need follow-up confirmation or a narrower scope.",
                "mitigation": "Review out_of_scope items before generating task packets.",
            }
        )
    if len(tasks) > MAX_NORMAL_TASKS:
        values.append(
            {
                "risk": "The plan spans more than the normal task budget.",
                "impact": "Execution will need stricter sequencing and review.",
                "mitigation": "Split the plan or confirm the expanded scope.",
            }
        )
    if requires_user_confirmation:
        values.append(
            {
                "risk": "User confirmation is required before execution.",
                "impact": "Downstream generation must wait for approval.",
                "mitigation": "Pause after plan generation and request confirmation.",
            }
        )
    return values


def _human_summary(tasks: list[dict[str, Any]], out_of_scope: list[str], requires_user_confirmation: bool) -> str:
    parts = [f"Plan with {len(tasks)} task(s)."]
    if len(tasks) > MAX_NORMAL_TASKS:
        parts.append(f"Warning: {len(tasks)} tasks exceed the normal budget.")
    if out_of_scope:
        parts.append(f"{len(out_of_scope)} item(s) were excluded from scope.")
    if requires_user_confirmation:
        parts.append("User confirmation required.")
    return " ".join(parts)


def _effective_operations(
    policy_constraints: Mapping[str, Any],
    roadmap_slice: Mapping[str, Any],
) -> tuple[list[str], list[str]]:
    policy_allowed = _string_list(policy_constraints.get("allowed_operations", []))
    roadmap_allowed = _string_list(roadmap_slice.get("allowed_operations", []))
    blocked = _ordered_unique(_string_list(policy_constraints.get("blocked_operations", [])) + _string_list(roadmap_slice.get("blocked_operations", [])))
    allowed = [operation for operation in policy_allowed if operation in roadmap_allowed and operation not in blocked]
    return _ordered_unique(allowed), blocked


def _sort_items(items: list[str]) -> list[str]:
    indexed = list(enumerate(items))
    indexed.sort(key=lambda pair: (_task_priority(_classify_item(pair[1])), pair[0]))
    return [item for _, item in indexed]


def _task_priority(task_type: str) -> int:
    return TASK_PRIORITY.get(task_type, 9)


def _classify_item(item: str) -> str:
    lower = item.lower()
    if ".schema.json" in lower or lower.endswith("schema.json") or "/schemas/" in lower:
        return "schema_design"
    if lower.startswith("tests/") or "/tests/" in lower or "test" in Path(lower).name:
        return "test"
    if "review" in lower or "revis" in lower:
        return "review"
    return "implementation"


def _normalize_output(reference: str, task_type: str, plan_id: str, index: int) -> str:
    if _is_safe_relative_path(reference) and not _looks_like_glob(reference):
        return PurePosixPath(reference).as_posix()

    slug = _slug_from_text(reference)
    if task_type == "test":
        return f"tests/test_meta_{slug}.py"
    if task_type == "schema_design":
        return f"schemas/meta/{slug}.schema.json"
    if task_type == "review":
        return f".factory/meta/validation/{plan_id}-{index:03d}.json"
    return f"src/fba/meta_{slug}.py"


def _title_from_item(reference: str, task_type: str) -> str:
    slug = _friendly_label(reference)
    if task_type == "test":
        return f"Add tests for {slug}"
    if task_type == "schema_design":
        return f"Define schema for {slug}"
    if task_type == "review":
        return f"Review {slug}"
    return f"Implement {slug}"


def _friendly_label(reference: str) -> str:
    if _is_safe_relative_path(reference):
        name = Path(reference).name
        name = re.sub(r"^test_", "", name)
        name = re.sub(r"^meta_", "", name)
        name = re.sub(r"\.schema\.json$", "", name)
        name = re.sub(r"\.[^.]+$", "", name)
        name = name.replace("_", " ")
        return name.strip() or "work item"

    text = _slug_from_text(reference).replace("_", " ")
    return text.strip() or "work item"


def _slug_from_text(value: str) -> str:
    slug = value.lower()
    slug = re.sub(r"\.schema\.json$", "", slug)
    slug = re.sub(r"\.[^.]+$", "", slug)
    slug = re.sub(r"^test_", "", slug)
    slug = re.sub(r"^meta_", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug or "work_item"


def _is_hard_denied(reference: str, effective_blocked_operations: list[str]) -> bool:
    if reference in {".factory/framework-state.json", ".factory/state.json", ".factory/events.jsonl", ".opencode/plugins/fba-agent-observer.ts", "src/fba/cli.py"}:
        return True
    if _matches_any(reference, HARD_DENY_PATTERNS):
        return True
    if reference.startswith("src/fba/generator/") and "modify_odoo_generator" in effective_blocked_operations:
        return True
    if reference.startswith(".opencode/agents/") and "create_agent" in effective_blocked_operations:
        return True
    if reference.startswith(".opencode/commands/") and "create_prompt" in effective_blocked_operations:
        return True
    return False


def _looks_like_glob(value: str) -> bool:
    return any(char in value for char in "*?[]")


def _is_safe_relative_path(value: str) -> bool:
    if Path(value).is_absolute():
        return False
    return ".." not in PurePosixPath(value).parts


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(Path(path).match(pattern) for pattern in patterns)


def _ordered_unique(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def _required_string(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise PlanBuilderError(f"{key} is required")
    return item


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _normalize_timestamp(value: datetime | str | None) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, str) and value:
        return value
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_text(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError as exc:
        raise PlanBuilderError(f"Required schema not found: {path}") from exc


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

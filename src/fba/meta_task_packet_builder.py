"""Pure utility for V2 task packet generation.

The V1 framework state remains authoritative. This module only reads explicit
V2 inputs, validates them against the meta schemas, and can write a shadow
task_packet artifact under .factory/meta/artifacts.
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


BASE_CONTRACTS = ["plan", "policy_constraints", "schema_catalog", "task_packet"]
BASE_ALLOWED_OPERATION_ORDER = [
    "read",
    "create_schema",
    "modify_schema",
    "validate_schema",
    "run_tests",
    "request_git_operation",
]
HARD_DENY_PATTERNS = [
    ".factory/framework-state.json",
    ".factory/state.json",
    ".factory/events.jsonl",
    "src/fba/generator/**",
    "templates/**",
    ".opencode/agents/**",
    ".opencode/commands/**",
    "templates/.opencode/agents/**",
    "templates/.opencode/commands/**",
    "src/fba/cli.py",
]
BROAD_ALLOWED_FILE_PATTERNS = {
    "**/*",
    "src/**",
    "schemas/**",
    ".factory/**",
    "templates/**",
}
SCHEMA_OPERATION_MAP = {
    "create_schema": "design_schema",
    "modify_schema": "design_schema",
    "validate_schema": "validate_schema",
    "run_tests": "run_tests",
    "request_git_operation": "request_git_operation",
    "read": "read_contract",
}
SCHEMA_CONTRACT_PATHS = {
    "plan": "schemas/meta/plan.schema.json",
    "policy_constraints": "schemas/meta/policy_constraints.schema.json",
    "schema_catalog": "schemas/meta/schema_catalog.schema.json",
    "task_packet": "schemas/meta/task_packet.schema.json",
}


@dataclass(frozen=True)
class TaskPacketBuilderResult:
    artifact_path: Path
    validation_path: Path | None
    packet: dict[str, Any]
    schema_valid: bool


class TaskPacketBuilderError(Exception):
    """Raised when a task packet cannot be built safely."""


def build_task_packet(
    project_dir: Path,
    plan: Mapping[str, Any],
    policy_constraints: Mapping[str, Any],
    schema_catalog: Mapping[str, Any],
    task_id: str,
    *,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    """Build a V2 task_packet instance without writing files."""

    root = Path(project_dir).resolve()
    timestamp = _normalize_timestamp(now)
    stamp = timestamp[:10].replace("-", "")

    _validate_instance(root, "plan.schema.json", plan, "plan")
    _validate_instance(root, "policy_constraints.schema.json", policy_constraints, "policy_constraints")
    _validate_instance(root, "schema_catalog.schema.json", schema_catalog, "schema_catalog")

    task = _resolve_task(plan, task_id)
    contract_paths = _contract_paths(schema_catalog)
    base_allowed_files = [_contract_path(contract_paths, contract) for contract in BASE_CONTRACTS]
    task_specific_files = _task_specific_allowed_files(task, plan, contract_paths)
    allowed_files = _ordered_unique(base_allowed_files + task_specific_files)
    forbidden_files = _forbidden_files(policy_constraints)

    if _contains_broad_allowed_glob(task_specific_files):
        raise TaskPacketBuilderError("allowed_files cannot include broad glob patterns")

    allowed_files = [path for path in allowed_files if not _matches_any(path, forbidden_files)]
    if not allowed_files:
        raise TaskPacketBuilderError("task_packet.allowed_files cannot be empty after forbidden filtering")

    task_specific_effective = [path for path in allowed_files if path not in base_allowed_files]
    if task["type"] in {"implementation", "schema_design"} and not task_specific_effective:
        raise TaskPacketBuilderError("task requires at least one task-specific allowed file")

    if len(allowed_files) > 8:
        raise TaskPacketBuilderError("task_packet.allowed_files exceeds the maximum scope limit")

    allowed_operations = _allowed_operations(task, policy_constraints)
    acceptance_criteria = _acceptance_criteria(plan, task, policy_constraints, allowed_files, allowed_operations)
    inputs_required = _inputs_required(task, contract_paths)
    dependencies = _dependencies(task)
    test_requirements = _test_requirements(task, policy_constraints, allowed_operations)
    policy_refs = _policy_refs(policy_constraints)
    risk_notes = _risk_notes(task, allowed_files, forbidden_files, allowed_operations, test_requirements)

    packet: dict[str, Any] = {
        "contract_name": "task_packet",
        "contract_version": "2.0",
        "packet_id": f"TPACKET-{stamp}-{_next_sequence(root, stamp):03d}",
        "plan_id": _required_string(plan, "plan_id"),
        "task_id": task_id,
        "created_at": timestamp,
        "objective": _objective(task, plan),
        "allowed_files": allowed_files,
        "forbidden_files": _ordered_unique(forbidden_files),
        "allowed_operations": allowed_operations,
        "acceptance_criteria": acceptance_criteria,
        "inputs_required": inputs_required,
        "dependencies": dependencies,
        "test_requirements": test_requirements,
        "policy_refs": policy_refs,
        "risk_notes": risk_notes,
        "human_summary": _human_summary(task_id, task, allowed_files, allowed_operations),
    }

    schema = cast(dict[str, Any], json.loads(_read_text(root / "schemas" / "meta" / "task_packet.schema.json")))
    jsonschema.Draft7Validator(schema).validate(packet)
    return packet


def generate_task_packet(
    project_dir: Path,
    plan: Mapping[str, Any],
    policy_constraints: Mapping[str, Any],
    schema_catalog: Mapping[str, Any],
    task_id: str,
    *,
    now: datetime | str | None = None,
    write_validation_report: bool = True,
) -> TaskPacketBuilderResult:
    """Generate, validate, and write a V2 task_packet artifact."""

    root = Path(project_dir).resolve()
    timestamp = _normalize_timestamp(now)
    stamp = timestamp[:10].replace("-", "")
    packet = build_task_packet(root, plan, policy_constraints, schema_catalog, task_id, now=timestamp)

    artifact_dir = root / ".factory" / "meta" / "artifacts" / "task_packets"
    artifact_path = artifact_dir / f"{packet['packet_id']}.json"
    _write_json(artifact_path, packet)

    validation_report_path: Path | None = None
    if write_validation_report:
        validation_path = root / ".factory" / "meta" / "validation" / "last_task_packet.json"
        validation_report = {
            "contract_name": "task_packet_validation",
            "contract_version": "2.0",
            "validated_at": timestamp,
            "artifact_path": str(artifact_path.relative_to(root)),
            "schema_path": "schemas/meta/task_packet.schema.json",
            "schema_valid": True,
        }
        _write_json(validation_path, validation_report)
        validation_report_path = validation_path

    return TaskPacketBuilderResult(
        artifact_path=artifact_path,
        validation_path=validation_report_path,
        packet=packet,
        schema_valid=True,
    )


def _validate_instance(root: Path, schema_name: str, instance: Mapping[str, Any], contract_name: str) -> None:
    schema_path = root / "schemas" / "meta" / schema_name
    schema = cast(dict[str, Any], json.loads(_read_text(schema_path)))
    try:
        jsonschema.Draft7Validator(schema).validate(instance)
    except jsonschema.ValidationError as exc:
        raise TaskPacketBuilderError(f"Invalid {contract_name} input: {exc.message}") from exc


def _resolve_task(plan: Mapping[str, Any], task_id: str) -> dict[str, Any]:
    matches = [task for task in _string_tasks(plan.get("tasks", [])) if task.get("task_id") == task_id]
    if not matches:
        raise TaskPacketBuilderError(f"task_id not found in plan: {task_id}")
    if len(matches) > 1:
        raise TaskPacketBuilderError(f"duplicate task_id in plan: {task_id}")
    return matches[0]


def _string_tasks(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _contract_paths(schema_catalog: Mapping[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for contract in schema_catalog.get("contracts", []):
        if not isinstance(contract, Mapping):
            continue
        name = contract.get("contract_name")
        path = contract.get("path")
        status = contract.get("status")
        if not isinstance(name, str) or not isinstance(path, str):
            continue
        if status not in {None, "active", "experimental"}:
            continue
        _validate_relative_value(path, "schema_catalog.contracts.path")
        values[name] = path
    return values


def _contract_path(contract_paths: Mapping[str, str], contract_name: str) -> str:
    if contract_name in contract_paths:
        return contract_paths[contract_name]
    if contract_name in SCHEMA_CONTRACT_PATHS:
        return SCHEMA_CONTRACT_PATHS[contract_name]
    raise TaskPacketBuilderError(f"Missing contract path for: {contract_name}")


def _task_specific_allowed_files(
    task: Mapping[str, Any],
    plan: Mapping[str, Any],
    contract_paths: Mapping[str, str],
) -> list[str]:
    values: list[str] = []
    texts = [
        _required_string(task, "title"),
        _required_string(plan, "goal"),
        _optional_string(task.get("owner_hint")),
        _optional_string(task.get("type")),
    ]
    texts.extend(_string_list(task.get("inputs", [])))
    texts.extend(_string_list(task.get("outputs", [])))

    for value in _string_list(task.get("inputs", [])) + _string_list(task.get("outputs", [])):
        values.extend(_candidate_allowed_file(value, contract_paths))

    text_blob = " ".join(text for text in texts if text)
    for contract_name, path in contract_paths.items():
        if contract_name in BASE_CONTRACTS:
            continue
        if re.search(rf"\b{re.escape(contract_name)}\b", text_blob, flags=re.IGNORECASE):
            values.append(path)

    if _task_requires_schema_creation(task, text_blob):
        values.extend(_schema_targets_from_task(task, contract_paths))
    if _task_requires_schema_modification(task, text_blob):
        values.extend(_schema_targets_from_task(task, contract_paths))

    return _ordered_unique(values)


def _candidate_allowed_file(value: str, contract_paths: Mapping[str, str]) -> list[str]:
    if _looks_like_glob(value):
        if value in BROAD_ALLOWED_FILE_PATTERNS:
            raise TaskPacketBuilderError(f"broad glob patterns are not allowed: {value}")
        raise TaskPacketBuilderError(f"glob patterns are not allowed in allowed_files: {value}")
    if value in contract_paths:
        return [contract_paths[value]]
    if _is_safe_relative_path(value):
        return [_normalize_path(value)]
    return []


def _schema_targets_from_task(task: Mapping[str, Any], contract_paths: Mapping[str, str]) -> list[str]:
    values: list[str] = []
    for value in _string_list(task.get("inputs", [])) + _string_list(task.get("outputs", [])):
        if value in contract_paths:
            values.append(contract_paths[value])
    return values


def _task_requires_schema_creation(task: Mapping[str, Any], text_blob: str) -> bool:
    if task.get("type") == "schema_design":
        return True
    return bool(re.search(r"\b(create|design|define|draft)\s+(the\s+)?schema\b", text_blob, flags=re.IGNORECASE))


def _task_requires_schema_modification(task: Mapping[str, Any], text_blob: str) -> bool:
    if task.get("type") == "schema_design" and re.search(r"\b(modify|update|extend|change|refactor)\b", text_blob, flags=re.IGNORECASE):
        return True
    return bool(re.search(r"\b(modify|update|extend|change|refactor)\s+(the\s+)?schema\b", text_blob, flags=re.IGNORECASE))


def _allowed_operations(task: Mapping[str, Any], policy_constraints: Mapping[str, Any]) -> list[str]:
    values = ["read", "validate_schema"]
    text_blob = f"{_optional_string(task.get('title'))} {_optional_string(task.get('type'))}"
    text_blob = text_blob.lower()

    if _task_requires_schema_creation(task, text_blob):
        values.append("create_schema")
    if _task_requires_schema_modification(task, text_blob):
        values.append("modify_schema")
    if _task_requires_tests(task, policy_constraints):
        values.append("run_tests")
    if _task_requires_git_request(task, text_blob):
        values.append("request_git_operation")

    values = _ordered_unique(values)
    _validate_policy_compatibility(values, policy_constraints)
    return values


def _validate_policy_compatibility(allowed_operations: list[str], policy_constraints: Mapping[str, Any]) -> None:
    policy_allowed = set(_string_list(policy_constraints.get("allowed_operations", [])))
    policy_blocked = set(_string_list(policy_constraints.get("blocked_operations", [])))

    for op in allowed_operations:
        required_policy_op = SCHEMA_OPERATION_MAP.get(op)
        if required_policy_op is None:
            raise TaskPacketBuilderError(f"unsupported task_packet operation: {op}")
        if required_policy_op not in policy_allowed:
            raise TaskPacketBuilderError(f"policy_constraints.allowed_operations missing required operation: {required_policy_op}")
        if required_policy_op in policy_blocked:
            raise TaskPacketBuilderError(f"policy_constraints blocks required operation: {required_policy_op}")


def _task_requires_tests(task: Mapping[str, Any], policy_constraints: Mapping[str, Any]) -> bool:
    required_checks = set(_string_list(policy_constraints.get("required_checks", [])))
    if "tests_required_before_pr" in required_checks:
        return True
    return task.get("type") in {"implementation", "test", "review", "git_operation"}


def _task_requires_git_request(task: Mapping[str, Any], text_blob: str) -> bool:
    if task.get("type") == "git_operation":
        return True
    return bool(re.search(r"\b(release|git operation|git request|request git)\b", text_blob, flags=re.IGNORECASE))


def _objective(task: Mapping[str, Any], plan: Mapping[str, Any]) -> str:
    title = _required_string(task, "title")
    goal = _required_string(plan, "goal")
    return f"{title} for {goal}"


def _acceptance_criteria(
    plan: Mapping[str, Any],
    task: Mapping[str, Any],
    policy_constraints: Mapping[str, Any],
    allowed_files: list[str],
    allowed_operations: list[str],
) -> list[str]:
    values: list[str] = []
    for criterion in _string_list(plan.get("acceptance_criteria", [])):
        values.append(f"[plan] {criterion}")

    values.append(f"[task] Complete {task.get('title', task.get('task_id', 'the task'))}.")
    values.append(f"[task] Respect the effective scope for {len(allowed_files)} allowed files.")
    values.append(f"[task] Validate the packet against schemas/meta/task_packet.schema.json.")

    required_checks = set(_string_list(policy_constraints.get("required_checks", [])))
    if "changelog_required" in required_checks:
        values.append("[policy] Update CHANGELOG.md when the change reaches a releasable state.")
    if "issue_required_before_code" in required_checks:
        values.append("[policy] Ensure the work is linked to an issue before code changes.")
    if "tests_required_before_pr" in required_checks and "run_tests" in allowed_operations:
        values.append("[policy] Run the relevant tests before any PR request.")

    return _ordered_unique(values)


def _inputs_required(task: Mapping[str, Any], contract_paths: Mapping[str, str]) -> list[str]:
    values = ["plan", "policy_constraints", "schema_catalog", "task_packet"]
    for value in _string_list(task.get("inputs", [])) + _string_list(task.get("outputs", [])):
        if value in contract_paths and value not in values:
            values.append(value)
    return values


def _dependencies(task: Mapping[str, Any]) -> list[str]:
    values = [value for value in _string_list(task.get("depends_on", [])) if value.startswith("TASK-")]
    return _ordered_unique(values)


def _test_requirements(task: Mapping[str, Any], policy_constraints: Mapping[str, Any], allowed_operations: list[str]) -> list[str]:
    values: list[str] = []
    required_checks = set(_string_list(policy_constraints.get("required_checks", [])))

    if "tests_required_before_pr" in required_checks or "run_tests" in allowed_operations:
        values.append("Execute the focused pytest suite for the affected task scope.")
    if task.get("type") in {"implementation", "schema_design"}:
        values.append("Validate the generated packet against schemas/meta/task_packet.schema.json.")

    return _ordered_unique(values)


def _policy_refs(policy_constraints: Mapping[str, Any]) -> list[str]:
    return _ordered_unique(_string_list(policy_constraints.get("policy_refs", [])))


def _forbidden_files(policy_constraints: Mapping[str, Any]) -> list[str]:
    values = list(HARD_DENY_PATTERNS)
    if "modify_odoo_generator" in _string_list(policy_constraints.get("blocked_operations", [])):
        values.append("src/fba/generator/**")
    return _ordered_unique(values)


def _risk_notes(
    task: Mapping[str, Any],
    allowed_files: list[str],
    forbidden_files: list[str],
    allowed_operations: list[str],
    test_requirements: list[str],
) -> list[str]:
    notes: list[str] = []
    if len(allowed_files) >= 6:
        notes.append("Allowed scope is close to the packet limit.")
    if any(path.startswith("src/fba/generator/") for path in forbidden_files):
        notes.append("Generator paths are hard-denied to protect the Odoo runtime boundary.")
    if "request_git_operation" in allowed_operations:
        notes.append("Git actions remain request-only; direct execution is blocked.")
    if not test_requirements and task.get("type") in {"implementation", "schema_design"}:
        notes.append("Task has no explicit test requirement and should be reviewed carefully.")
    return _ordered_unique(notes)


def _human_summary(task_id: str, task: Mapping[str, Any], allowed_files: list[str], allowed_operations: list[str]) -> str:
    title = _optional_string(task.get("title")) or task_id
    return (
        f"Task packet for {task_id}: {title}. "
        f"Allows {len(allowed_files)} files and {len(allowed_operations)} operations."
    )


def _looks_like_glob(value: str) -> bool:
    return any(char in value for char in "*?[]")


def _is_safe_relative_path(value: str) -> bool:
    if Path(value).is_absolute():
        return False
    return ".." not in PurePosixPath(value).parts


def _normalize_path(value: str) -> str:
    _validate_relative_value(value, "allowed_files")
    return PurePosixPath(value).as_posix()


def _validate_relative_value(value: str, field_name: str) -> None:
    if Path(value).is_absolute():
        raise TaskPacketBuilderError(f"{field_name} cannot contain absolute paths: {value}")
    if ".." in PurePosixPath(value).parts:
        raise TaskPacketBuilderError(f"{field_name} cannot contain parent traversal: {value}")


def _contains_broad_allowed_glob(values: list[str]) -> bool:
    return any(value in BROAD_ALLOWED_FILE_PATTERNS for value in values)


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
        raise TaskPacketBuilderError(f"{key} is required")
    return item


def _optional_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""


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


def _next_sequence(project_dir: Path, stamp: str) -> int:
    artifact_dir = project_dir / ".factory" / "meta" / "artifacts" / "task_packets"
    if not artifact_dir.exists():
        return 1
    prefix = f"TPACKET-{stamp}-"
    values: list[int] = []
    for path in artifact_dir.glob(f"{prefix}*.json"):
        suffix = path.stem.removeprefix(prefix)
        if suffix.isdigit():
            values.append(int(suffix))
    return max(values, default=0) + 1


def _read_text(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError as exc:
        raise TaskPacketBuilderError(f"Required schema source not found: {path}") from exc


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

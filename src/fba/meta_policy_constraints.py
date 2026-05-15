"""Pure utility for V2 meta-workflow policy constraints.

The V1 framework state remains authoritative. This module only reads repository
policy sources and writes a V2 shadow artifact under .factory/meta/artifacts.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, cast

import jsonschema

POLICY_REFS = [
    "CONTRIBUTING.md::branch_policy",
    "CONTRIBUTING.md::commit_policy",
    "CONTRIBUTING.md::tests_policy",
    "CONTRIBUTING.md::pr_policy",
    "CHANGELOG.md::unreleased",
]

BASE_ALLOWED_OPERATIONS = [
    "read_contract",
    "validate_schema",
    "create_task_packet",
    "build_context_bundle",
    "run_tests",
    "create_review_report",
    "request_git_operation",
]

BASE_BLOCKED_OPERATIONS = [
    "execute_git_operation",
    "commit",
    "push",
    "open_pr",
    "merge_pr",
]

BASE_REQUIRED_CHECKS = ["no_direct_commit_to_main"]

ARCHITECTURE_KEYWORDS = {
    "architecture",
    "arquitectura",
    "schema",
    "schemas",
    "agent",
    "agents",
    "agente",
    "agentes",
    "command",
    "commands",
    "comando",
    "comandos",
    "workflow",
    "meta-workflow",
    "pipeline",
}

CODE_KEYWORDS = {
    "code",
    "codigo",
    "implementar",
    "implementa",
    "implementation",
    "crear utilidad",
    "create utility",
    "modificar",
    "modify",
    "write file",
}

MAIN_PR_KEYWORDS = {
    "pr to main",
    "pr a main",
    "pull request to main",
    "pull request a main",
    "merge to main",
    "merge a main",
    "merge into main",
}

ODOO_GENERATOR_KEYWORDS = {
    "odoo generator",
    "generador odoo",
    "modify_odoo_generator",
    "src/fba/generator",
}


@dataclass(frozen=True)
class PolicyConstraintsResult:
    artifact_path: Path
    validation_path: Path | None
    constraints: dict[str, Any]
    schema_valid: bool


class PolicyConstraintsError(Exception):
    """Raised when policy constraints cannot be generated or validated."""


def build_policy_constraints(
    intent: Mapping[str, Any],
    contributing_text: str,
    changelog_text: str,
    *,
    created_at: datetime | str | None = None,
    sequence: int = 1,
) -> dict[str, Any]:
    """Build a policy_constraints V2 instance without writing files."""

    timestamp = _normalize_timestamp(created_at)
    stamp = timestamp[:10].replace("-", "")
    intent_id = _intent_id(intent, stamp)
    text = _flatten_intent(intent)

    _validate_policy_sources(contributing_text, changelog_text)

    allowed_operations = list(BASE_ALLOWED_OPERATIONS)
    blocked_operations = list(BASE_BLOCKED_OPERATIONS)
    required_checks = list(BASE_REQUIRED_CHECKS)

    if _intent_implies_architecture_change(intent, text):
        _append_unique(required_checks, "changelog_required")
        _append_unique(allowed_operations, "design_schema")

    if _intent_implies_main_pr(intent, text):
        _append_unique(required_checks, "manual_review_before_main_pr")
        requires_user_confirmation = True
    else:
        requires_user_confirmation = bool(intent.get("requires_user_confirmation", False))

    if _intent_implies_code(intent, text):
        _append_unique(required_checks, "issue_required_before_code")
        _append_unique(required_checks, "tests_required_before_pr")

    if _intent_excludes_odoo_generator(intent, text):
        _append_unique(blocked_operations, "modify_odoo_generator")

    if _intent_excludes_agents(intent, text):
        _append_unique(blocked_operations, "create_agent")
        _append_unique(blocked_operations, "create_prompt")

    allowed_operations = [op for op in allowed_operations if op not in set(blocked_operations)]

    return {
        "contract_name": "policy_constraints",
        "contract_version": "2.0",
        "constraints_id": f"POLICY-{stamp}-{sequence:03d}",
        "intent_id": intent_id,
        "created_at": timestamp,
        "policy_refs": POLICY_REFS,
        "allowed_operations": allowed_operations,
        "blocked_operations": blocked_operations,
        "required_checks": required_checks,
        "requires_user_confirmation": requires_user_confirmation,
        "rationale": _build_rationale(required_checks, blocked_operations),
        "human_summary": _build_human_summary(required_checks, blocked_operations, requires_user_confirmation),
    }


def generate_policy_constraints(
    project_dir: Path,
    intent: Mapping[str, Any],
    *,
    created_at: datetime | str | None = None,
    sequence: int | None = None,
    write_validation_report: bool = True,
) -> PolicyConstraintsResult:
    """Generate, validate, and write a policy_constraints V2 artifact."""

    root = Path(project_dir).resolve()
    contributing_path = root / "CONTRIBUTING.md"
    changelog_path = root / "CHANGELOG.md"
    schema_path = root / "schemas" / "meta" / "policy_constraints.schema.json"
    artifact_dir = root / ".factory" / "meta" / "artifacts" / "policy_constraints"
    validation_path = root / ".factory" / "meta" / "validation" / "last_policy_constraints.json"

    contributing_text = _read_text(contributing_path)
    changelog_text = _read_text(changelog_path)
    timestamp = _normalize_timestamp(created_at)
    stamp = timestamp[:10].replace("-", "")
    resolved_sequence = sequence if sequence is not None else _next_sequence(artifact_dir, stamp)

    constraints = build_policy_constraints(
        intent,
        contributing_text,
        changelog_text,
        created_at=timestamp,
        sequence=resolved_sequence,
    )
    schema = cast(dict[str, Any], json.loads(_read_text(schema_path)))
    jsonschema.Draft7Validator(schema).validate(constraints)

    artifact_path = artifact_dir / f"{constraints['constraints_id']}.json"
    _write_json(artifact_path, constraints)

    validation_report_path: Path | None = None
    if write_validation_report:
        validation_report = {
            "contract_name": "policy_constraints_validation",
            "contract_version": "2.0",
            "validated_at": timestamp,
            "artifact_path": str(artifact_path.relative_to(root)),
            "schema_path": str(schema_path.relative_to(root)),
            "schema_valid": True,
        }
        _write_json(validation_path, validation_report)
        validation_report_path = validation_path

    return PolicyConstraintsResult(
        artifact_path=artifact_path,
        validation_path=validation_report_path,
        constraints=constraints,
        schema_valid=True,
    )


def _normalize_timestamp(value: datetime | str | None) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, str) and value:
        return value
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _intent_id(intent: Mapping[str, Any], stamp: str) -> str:
    value = intent.get("intent_id")
    if isinstance(value, str) and value:
        return value
    return f"INTENT-{stamp}-001"


def _read_text(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError as exc:
        raise PolicyConstraintsError(f"Required policy source not found: {path}") from exc


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


def _next_sequence(artifact_dir: Path, stamp: str) -> int:
    if not artifact_dir.exists():
        return 1
    prefix = f"POLICY-{stamp}-"
    values: list[int] = []
    for path in artifact_dir.glob(f"{prefix}*.json"):
        suffix = path.stem.removeprefix(prefix)
        if suffix.isdigit():
            values.append(int(suffix))
    return max(values, default=0) + 1


def _validate_policy_sources(contributing_text: str, changelog_text: str) -> None:
    if "CONTRIBUTING" not in contributing_text and "Contributing" not in contributing_text:
        raise PolicyConstraintsError("CONTRIBUTING.md does not look like a contributing policy source")
    if "Changelog" not in changelog_text and "CHANGELOG" not in changelog_text:
        raise PolicyConstraintsError("CHANGELOG.md does not look like a changelog policy source")


def _flatten_intent(value: Any) -> str:
    parts: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                parts.append(str(key))
                visit(child)
        elif isinstance(item, list | tuple | set):
            for child in item:
                visit(child)
        elif item is not None:
            parts.append(str(item))

    visit(value)
    return " ".join(parts).lower()


def _scope_values(intent: Mapping[str, Any], key: str) -> str:
    scope = intent.get("scope")
    if not isinstance(scope, Mapping):
        return ""
    return _flatten_intent(scope.get(key, ""))


def _intent_implies_architecture_change(intent: Mapping[str, Any], text: str) -> bool:
    explicit = intent.get("changes_architecture") or intent.get("architecture_change")
    if explicit is not None:
        return bool(explicit)
    return any(keyword in text for keyword in ARCHITECTURE_KEYWORDS)


def _intent_implies_code(intent: Mapping[str, Any], text: str) -> bool:
    explicit = intent.get("implies_code") or intent.get("code_changes")
    if explicit is not None:
        return bool(explicit)
    requested_outputs = _flatten_intent(intent.get("requested_outputs", ""))
    if "code" in requested_outputs or "implementation" in requested_outputs:
        return True
    return any(keyword in text for keyword in CODE_KEYWORDS)


def _intent_implies_main_pr(intent: Mapping[str, Any], text: str) -> bool:
    explicit = intent.get("pr_to_main") or intent.get("merge_to_main")
    if explicit is not None:
        return bool(explicit)
    target_branch = intent.get("target_branch") or intent.get("base_branch")
    operation = _flatten_intent(intent.get("operation", ""))
    if target_branch == "main" and any(word in operation for word in ("pr", "merge", "open_pr", "merge_pr")):
        return True
    return any(keyword in text for keyword in MAIN_PR_KEYWORDS)


def _intent_excludes_odoo_generator(intent: Mapping[str, Any], text: str) -> bool:
    excludes = _scope_values(intent, "exclude")
    constraints = _flatten_intent(intent.get("constraints", ""))
    combined = f"{excludes} {constraints} {text}"
    return any(keyword in combined for keyword in ODOO_GENERATOR_KEYWORDS)


def _intent_excludes_agents(intent: Mapping[str, Any], text: str) -> bool:
    excludes = _scope_values(intent, "exclude")
    constraints = _flatten_intent(intent.get("constraints", ""))
    combined = f"{excludes} {constraints} {text}"
    return "no modificar agentes" in combined or "agents" in excludes or "agentes" in excludes


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _build_rationale(required_checks: list[str], blocked_operations: list[str]) -> str:
    reasons = ["Normalized from repository policies and the current intent."]
    if "changelog_required" in required_checks:
        reasons.append("Architecture, schema, agent, command, or workflow changes require changelog tracking.")
    if "execute_git_operation" in blocked_operations:
        reasons.append("Git execution is deferred to a future authorized git_operation.")
    return " ".join(reasons)


def _build_human_summary(
    required_checks: list[str],
    blocked_operations: list[str],
    requires_user_confirmation: bool,
) -> str:
    summary = "Issue-backed work must avoid direct commits to main and route git execution through git_operation."
    if "tests_required_before_pr" in required_checks:
        summary += " Tests are required before PR."
    if "changelog_required" in required_checks:
        summary += " Changelog updates are required for architecture or workflow-impacting changes."
    if requires_user_confirmation:
        summary += " Explicit user confirmation is required before PR or merge to main."
    if "modify_odoo_generator" in blocked_operations:
        summary += " Odoo generator changes are blocked by intent scope."
    return summary

"""Pure utility for V2 meta-workflow context bundles.

The V1 framework state remains authoritative. This module only reads explicitly
allowed repository files and writes a V2 shadow artifact under .factory/meta.
"""

from __future__ import annotations

import fnmatch
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, cast

import jsonschema

SMALL_COMPLETE_FILE_LINES = 80
MAX_RANGE_LINES = 120
MAX_RANGES_PER_ITEM = 4
MAX_EXCLUDED_CONTEXT = 25

CONTRACT_CONTEXT_KEYS = {
    "context_bundle": ["context_items", "excluded_context", "integrity", "policy_refs"],
    "task_packet": ["allowed_files", "forbidden_files", "allowed_operations", "inputs_required"],
    "policy_constraints": ["allowed_operations", "blocked_operations", "policy_refs"],
    "schema_catalog": ["contracts", "global_policies", "compatibility_matrix"],
}


@dataclass(frozen=True)
class ContextBundleResult:
    artifact_path: Path
    validation_path: Path | None
    bundle: dict[str, Any]
    schema_valid: bool


class ContextBrokerError(Exception):
    """Raised when a context bundle cannot be generated safely."""


def build_context_bundle(
    project_dir: Path,
    task_packet: Mapping[str, Any],
    policy_constraints: Mapping[str, Any],
    schema_catalog: Mapping[str, Any],
    *,
    now: datetime | str | None = None,
    write_validation_report: bool = True,
) -> ContextBundleResult:
    """Generate, validate, and write a V2 context_bundle artifact."""

    root = Path(project_dir).resolve()
    timestamp = _normalize_timestamp(now)
    stamp = timestamp[:10].replace("-", "")
    artifact_dir = root / ".factory" / "meta" / "artifacts" / "context_bundles"
    validation_path = root / ".factory" / "meta" / "validation" / "last_context_bundle.json"
    schema_path = root / "schemas" / "meta" / "context_bundle.schema.json"

    _validate_operations(task_packet, policy_constraints)

    allowed_patterns = _validated_patterns(task_packet.get("allowed_files", []), "allowed_files")
    forbidden_patterns = _validated_patterns(task_packet.get("forbidden_files", []), "forbidden_files")
    effective_forbidden = list(forbidden_patterns)
    blocked_operations = _string_list(policy_constraints.get("blocked_operations", []))
    if "modify_odoo_generator" in blocked_operations:
        effective_forbidden.append("src/fba/generator/*")

    expanded_allowed = _expand_allowed_files(root, allowed_patterns)
    broad_glob = len(expanded_allowed) > 8
    relevant_candidates = _relevant_candidates(task_packet, schema_catalog)
    context_items: list[dict[str, Any]] = []
    excluded_context: list[dict[str, Any]] = []
    selected_paths: set[str] = set()
    truncated = False

    for candidate in relevant_candidates:
        path = candidate["path"]
        reason = _candidate_exclusion_reason(path, allowed_patterns, effective_forbidden, blocked_operations)
        if reason is not None:
            _append_excluded(excluded_context, path, reason)
            if reason in {"glob_too_broad", "operation_blocked"}:
                truncated = True
            continue

        relative_path = _safe_relative_path(root, path)
        absolute_path = root / relative_path
        if not absolute_path.is_file():
            _append_excluded(excluded_context, relative_path, "outside_allowed_files: candidate file does not exist")
            continue

        line_ranges, item_truncated = _select_line_ranges(
            absolute_path,
            candidate["contract_name"],
            _selection_keywords(task_packet, candidate["contract_name"]),
        )
        truncated = truncated or item_truncated
        selected_paths.add(relative_path)
        context_items.append(
            {
                "type": _context_type(relative_path),
                "path": relative_path,
                "section": candidate["section"],
                "line_ranges": line_ranges,
                "reason": candidate["reason"],
            }
        )

    for relative_path in expanded_allowed:
        if relative_path in selected_paths:
            continue
        if _matches_any(relative_path, effective_forbidden):
            reason = "odoo_generator_blocked" if relative_path.startswith("src/fba/generator/") else "forbidden_by_task_packet"
            _append_excluded(excluded_context, relative_path, reason)
            truncated = True
        elif broad_glob:
            _append_excluded(excluded_context, relative_path, "glob_too_broad")
            truncated = True

    if not context_items:
        raise ContextBrokerError("No allowed context items could be selected for the task packet")

    _validate_context_paths(context_items, allowed_patterns, effective_forbidden)

    bundle_id = f"CTX-{stamp}-{_next_sequence(artifact_dir, stamp):03d}"
    bundle = {
        "contract_name": "context_bundle",
        "contract_version": "2.0",
        "bundle_id": bundle_id,
        "packet_id": _required_string(task_packet, "packet_id"),
        "created_at": timestamp,
        "context_items": context_items,
        "excluded_context": excluded_context,
        "policy_refs": _policy_refs(task_packet, policy_constraints),
        "integrity": {"source_count": len(context_items), "truncated": truncated},
        "human_summary": _human_summary(context_items, excluded_context, truncated),
    }

    schema = cast(dict[str, Any], json.loads(_read_text(schema_path)))
    jsonschema.Draft7Validator(schema).validate(bundle)

    artifact_path = artifact_dir / f"{bundle_id}.json"
    _write_json(artifact_path, bundle)

    validation_report_path: Path | None = None
    if write_validation_report:
        validation_report = {
            "contract_name": "context_bundle_validation",
            "contract_version": "2.0",
            "validated_at": timestamp,
            "artifact_path": str(artifact_path.relative_to(root)),
            "schema_path": str(schema_path.relative_to(root)),
            "schema_valid": True,
        }
        _write_json(validation_path, validation_report)
        validation_report_path = validation_path

    return ContextBundleResult(
        artifact_path=artifact_path,
        validation_path=validation_report_path,
        bundle=bundle,
        schema_valid=True,
    )


def _validate_operations(task_packet: Mapping[str, Any], policy_constraints: Mapping[str, Any]) -> None:
    task_allowed = set(_string_list(task_packet.get("allowed_operations", [])))
    policy_allowed = set(_string_list(policy_constraints.get("allowed_operations", [])))
    policy_blocked = set(_string_list(policy_constraints.get("blocked_operations", [])))

    if "read" not in task_allowed:
        raise ContextBrokerError("task_packet.allowed_operations must include read")
    if "build_context_bundle" not in policy_allowed:
        raise ContextBrokerError("policy_constraints.allowed_operations must include build_context_bundle")
    if "build_context_bundle" in policy_blocked:
        raise ContextBrokerError("build_context_bundle is blocked by policy_constraints")
    if "read_contract" in policy_blocked:
        raise ContextBrokerError("read_contract is blocked by policy_constraints")


def _validated_patterns(value: Any, field_name: str) -> list[str]:
    patterns = _string_list(value)
    if field_name == "allowed_files" and not patterns:
        raise ContextBrokerError("task_packet.allowed_files must include at least one path pattern")
    for pattern in patterns:
        _validate_relative_value(pattern, field_name)
    return patterns


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _validate_relative_value(value: str, field_name: str) -> None:
    if Path(value).is_absolute():
        raise ContextBrokerError(f"{field_name} cannot contain absolute paths: {value}")
    if ".." in PurePosixPath(value).parts:
        raise ContextBrokerError(f"{field_name} cannot contain parent traversal: {value}")


def _expand_allowed_files(root: Path, allowed_patterns: list[str]) -> list[str]:
    values: set[str] = set()
    for pattern in allowed_patterns:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            values.add(_relative_to_root(root, path))
    return sorted(values)


def _relevant_candidates(task_packet: Mapping[str, Any], schema_catalog: Mapping[str, Any]) -> list[dict[str, str]]:
    inputs_required = set(_string_list(task_packet.get("inputs_required", [])))
    preferred_contracts = inputs_required | {"context_bundle", "task_packet"}
    objective = str(task_packet.get("objective", "")).lower()
    candidates: list[dict[str, str]] = []

    for contract in schema_catalog.get("contracts", []):
        if not isinstance(contract, Mapping):
            continue
        name = contract.get("contract_name")
        path = contract.get("path")
        if not isinstance(name, str) or not isinstance(path, str):
            continue
        _validate_relative_value(path, "schema_catalog.contracts.path")
        if name not in preferred_contracts and name not in objective:
            continue
        candidates.append(
            {
                "contract_name": name,
                "path": path,
                "section": _section_for_contract(name),
                "reason": f"Reference contract required for {name} context.",
            }
        )

    for policy in schema_catalog.get("global_policies", []):
        if not isinstance(policy, Mapping):
            continue
        path = policy.get("path")
        policy_id = policy.get("policy_id")
        if not isinstance(path, str) or not isinstance(policy_id, str):
            continue
        _validate_relative_value(path, "schema_catalog.global_policies.path")
        if policy_id.lower() not in objective and policy_id not in _string_list(task_packet.get("policy_refs", [])):
            continue
        candidates.append(
            {
                "contract_name": policy_id.lower(),
                "path": path,
                "section": "policy reference",
                "reason": f"Policy reference required by task packet: {policy_id}.",
            }
        )

    return _dedupe_candidates(candidates)


def _dedupe_candidates(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    values: list[dict[str, str]] = []
    for candidate in candidates:
        if candidate["path"] in seen:
            continue
        seen.add(candidate["path"])
        values.append(candidate)
    return values


def _candidate_exclusion_reason(
    path: str,
    allowed_patterns: list[str],
    forbidden_patterns: list[str],
    blocked_operations: list[str],
) -> str | None:
    _validate_relative_value(path, "candidate.path")
    if _matches_any(path, forbidden_patterns):
        if path.startswith("src/fba/generator/") and "modify_odoo_generator" in blocked_operations:
            return "odoo_generator_blocked"
        return "forbidden_by_task_packet"
    if not _matches_any(path, allowed_patterns):
        return "outside_allowed_files"
    if path.startswith("src/fba/generator/") and "modify_odoo_generator" in blocked_operations:
        return "odoo_generator_blocked"
    if path.startswith(".opencode/agents/") and "create_agent" in blocked_operations:
        return "operation_blocked"
    if path.startswith(".opencode/commands/") and "create_prompt" in blocked_operations:
        return "operation_blocked"
    return None


def _safe_relative_path(root: Path, value: str) -> str:
    _validate_relative_value(value, "path")
    path = root / value
    return _relative_to_root(root, path)


def _relative_to_root(root: Path, path: Path) -> str:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(resolved_root).as_posix()
    except ValueError as exc:
        raise ContextBrokerError(f"Path escapes project directory: {path}") from exc


def _select_line_ranges(path: Path, contract_name: str, keywords: list[str]) -> tuple[list[dict[str, int]], bool]:
    lines = _read_text(path).splitlines()
    total_lines = len(lines) or 1
    if total_lines <= SMALL_COMPLETE_FILE_LINES:
        return ([{"start": 1, "end": total_lines}], False)

    lower_keywords = [keyword.lower() for keyword in keywords if keyword]
    matched_lines: list[int] = []
    for index, line in enumerate(lines, start=1):
        lower_line = line.lower()
        if any(keyword in lower_line for keyword in lower_keywords):
            matched_lines.append(index)

    if not matched_lines:
        matched_lines = [1]

    ranges = _ranges_from_matches(matched_lines, total_lines)
    selected_lines = sum(item["end"] - item["start"] + 1 for item in ranges)
    truncated = selected_lines < total_lines
    return ranges, truncated


def _ranges_from_matches(matches: list[int], total_lines: int) -> list[dict[str, int]]:
    ranges: list[dict[str, int]] = []
    for line in matches:
        start = max(1, line - 4)
        end = min(total_lines, line + 8)
        if ranges and start <= ranges[-1]["end"] + 5:
            ranges[-1]["end"] = min(total_lines, max(ranges[-1]["end"], end))
        else:
            ranges.append({"start": start, "end": end})
        ranges = ranges[:MAX_RANGES_PER_ITEM]

    trimmed: list[dict[str, int]] = []
    used_lines = 0
    for item in ranges:
        available = MAX_RANGE_LINES - used_lines
        if available <= 0:
            break
        item_length = item["end"] - item["start"] + 1
        if item_length > available:
            item = {"start": item["start"], "end": item["start"] + available - 1}
        trimmed.append(item)
        used_lines += item["end"] - item["start"] + 1
    return trimmed or [{"start": 1, "end": min(total_lines, MAX_RANGE_LINES)}]


def _selection_keywords(task_packet: Mapping[str, Any], contract_name: str) -> list[str]:
    keywords = [contract_name, "required", "properties"]
    keywords.extend(CONTRACT_CONTEXT_KEYS.get(contract_name, []))
    keywords.extend(_string_list(task_packet.get("inputs_required", [])))
    keywords.extend(str(item) for item in task_packet.get("acceptance_criteria", []) if isinstance(item, str))
    return keywords


def _section_for_contract(contract_name: str) -> str:
    if contract_name == "context_bundle":
        return "artifact shape and integrity"
    if contract_name == "task_packet":
        return "scope and operations"
    if contract_name == "policy_constraints":
        return "policy operations"
    return "contract reference"


def _context_type(path: str) -> str:
    if path.startswith("schemas/meta/"):
        return "schema"
    if path in {"CONTRIBUTING.md", "CHANGELOG.md"}:
        return "policy"
    if path == "ROADMAP.md":
        return "roadmap"
    if path.startswith(".factory/"):
        return "state"
    if path.startswith("tests/"):
        return "test_file"
    return "source_file"


def _validate_context_paths(
    context_items: list[dict[str, Any]],
    allowed_patterns: list[str],
    forbidden_patterns: list[str],
) -> None:
    for item in context_items:
        path = cast(str, item["path"])
        _validate_relative_value(path, "context_items.path")
        if not _matches_any(path, allowed_patterns):
            raise ContextBrokerError(f"context item is outside allowed_files: {path}")
        if _matches_any(path, forbidden_patterns):
            raise ContextBrokerError(f"context item violates forbidden_files: {path}")


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _append_excluded(excluded_context: list[dict[str, Any]], path: str, reason: str) -> None:
    if len(excluded_context) >= MAX_EXCLUDED_CONTEXT:
        return
    _validate_relative_value(path, "excluded_context.path")
    if any(item["path"] == path and item["reason"] == reason for item in excluded_context):
        return
    excluded_context.append({"path": path, "reason": reason})


def _policy_refs(task_packet: Mapping[str, Any], policy_constraints: Mapping[str, Any]) -> list[str]:
    values = _string_list(task_packet.get("policy_refs", [])) + _string_list(policy_constraints.get("policy_refs", []))
    unique: list[str] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    if not unique:
        raise ContextBrokerError("policy refs are required to build a context bundle")
    return unique


def _human_summary(
    context_items: list[dict[str, Any]],
    excluded_context: list[dict[str, Any]],
    truncated: bool,
) -> str:
    summary = f"Context bundle references {len(context_items)} source(s) using line ranges."
    if truncated:
        summary += " Context was truncated to reduce token usage."
    if excluded_context:
        reasons = sorted({str(item["reason"]).split(":", 1)[0] for item in excluded_context})
        summary += " Excluded context reasons: " + ", ".join(reasons) + "."
    return summary


def _required_string(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ContextBrokerError(f"{key} is required")
    return item


def _normalize_timestamp(value: datetime | str | None) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, str) and value:
        return value
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _next_sequence(artifact_dir: Path, stamp: str) -> int:
    if not artifact_dir.exists():
        return 1
    prefix = f"CTX-{stamp}-"
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
        raise ContextBrokerError(f"Required context source not found: {path}") from exc


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

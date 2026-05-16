"""Pure utility for V2 roadmap slice generation.

The V1 framework state remains authoritative. This module only reads explicit
V2 inputs, validates them against the meta schemas, and can write a shadow
roadmap_slice artifact under .factory/meta/artifacts.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, cast

import jsonschema

ALLOWED_OPERATIONS = [
    "read_contract",
    "validate_schema",
    "design_schema",
    "create_task_packet",
    "build_context_bundle",
    "run_tests",
    "create_review_report",
    "request_git_operation",
]
BLOCKED_OPERATIONS = [
    "execute_git_operation",
    "commit",
    "push",
    "open_pr",
    "merge_pr",
]
MAX_RELEVANT_MILESTONES_WARNING = 3
MAX_RELEVANT_MILESTONES_CONFIRMATION = 5

ROADMAP_HEADING_RE = re.compile(r"^###\s+(M\d+):\s*(.+)$")
ROADMAP_BRANCH_RE = re.compile(r"^\*\*Branch sugerido\*\*:\s*`([^`]+)`")
ROADMAP_TABLE_HEADER_RE = re.compile(r"^\|\s*Milestone\s*\|\s*Estado\s*\|\s*Inicio\s*\|")
ROADMAP_TABLE_ROW_RE = re.compile(r"^\|\s*(M\d+)\s*:\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")


@dataclass(frozen=True)
class RoadmapSliceBuilderResult:
    artifact_path: Path
    validation_path: Path | None
    slice: dict[str, Any]
    schema_valid: bool


class RoadmapSliceBuilderError(Exception):
    """Raised when a roadmap slice cannot be built safely."""


def build_roadmap_slice(
    intent: Mapping[str, Any],
    framework_state_v2: Mapping[str, Any],
    roadmap_text: str,
    *,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    """Build a V2 roadmap_slice instance without writing files."""

    root = _repo_root()
    timestamp = _normalize_timestamp(now)
    stamp = timestamp[:10].replace("-", "")

    if not isinstance(roadmap_text, str) or not roadmap_text.strip():
        raise RoadmapSliceBuilderError("roadmap_text is required")

    _validate_instance(root, "intent.schema.json", intent, "intent")
    _validate_instance(root, "framework_state.v2.schema.json", framework_state_v2, "framework_state_v2")

    lines = roadmap_text.splitlines()
    table_rows = _parse_status_table(lines)
    section_map = _parse_sections(lines)

    active_milestone = _resolve_active_milestone(intent, framework_state_v2, table_rows, section_map)
    relevant_milestones = _select_relevant_milestones(active_milestone, table_rows, section_map)
    source_refs = _build_source_refs(active_milestone, relevant_milestones, table_rows, section_map)
    policy_refs = _build_policy_refs(active_milestone, relevant_milestones)
    blocked_operations = list(BLOCKED_OPERATIONS)
    allowed_operations = _build_allowed_operations(intent, roadmap_text)
    branch_context = _build_branch_context(active_milestone)
    requires_user_confirmation = bool(
        intent.get("requires_user_confirmation", False)
        or active_milestone["status"] == "paused"
        or len(relevant_milestones) > MAX_RELEVANT_MILESTONES_CONFIRMATION
    )
    open_issues = _build_open_issues(active_milestone, relevant_milestones, requires_user_confirmation, stamp)
    risk_notes = _build_risk_notes(active_milestone, relevant_milestones, requires_user_confirmation)
    recent_changes = _build_recent_changes(relevant_milestones)

    roadmap_slice: dict[str, Any] = {
        "contract_name": "roadmap_slice",
        "contract_version": "2.0",
        "slice_id": f"RSLICE-{stamp}-001",
        "intent_id": _required_string(intent, "intent_id"),
        "created_at": timestamp,
        "active_milestone": active_milestone,
        "relevant_milestones": relevant_milestones,
        "policy_refs": policy_refs,
        "allowed_operations": allowed_operations,
        "blocked_operations": blocked_operations,
        "source_refs": source_refs,
        "open_issues": open_issues,
        "branch_context": branch_context,
        "recent_changes": recent_changes,
        "risk_notes": risk_notes,
        "human_summary": _build_human_summary(active_milestone, relevant_milestones, requires_user_confirmation),
    }

    _validate_output(root, roadmap_slice)
    return roadmap_slice


def generate_roadmap_slice(
    project_dir: Path,
    intent: Mapping[str, Any],
    framework_state_v2: Mapping[str, Any],
    roadmap_text: str,
    *,
    now: datetime | str | None = None,
    write_validation_report: bool = True,
) -> RoadmapSliceBuilderResult:
    """Generate, validate, and write a V2 roadmap_slice artifact."""

    root = Path(project_dir).resolve()
    timestamp = _normalize_timestamp(now)
    roadmap_slice = build_roadmap_slice(intent, framework_state_v2, roadmap_text, now=timestamp)

    artifact_dir = root / ".factory" / "meta" / "artifacts" / "roadmap_slices"
    artifact_path = artifact_dir / f"{roadmap_slice['slice_id']}.json"
    _write_json(artifact_path, roadmap_slice)

    validation_report_path: Path | None = None
    if write_validation_report:
        validation_path = root / ".factory" / "meta" / "validation" / "last_roadmap_slice.json"
        validation_report = {
            "contract_name": "roadmap_slice_validation",
            "contract_version": "2.0",
            "validated_at": timestamp,
            "artifact_path": str(artifact_path.relative_to(root)),
            "schema_path": "schemas/meta/roadmap_slice.schema.json",
            "schema_valid": True,
        }
        _write_json(validation_path, validation_report)
        validation_report_path = validation_path

    return RoadmapSliceBuilderResult(
        artifact_path=artifact_path,
        validation_path=validation_report_path,
        slice=roadmap_slice,
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
        raise RoadmapSliceBuilderError(f"Invalid {contract_name} input: {exc.message}") from exc


def _validate_output(root: Path, roadmap_slice: Mapping[str, Any]) -> None:
    schema_path = root / "schemas" / "meta" / "roadmap_slice.schema.json"
    schema = cast(dict[str, Any], json.loads(_read_text(schema_path)))
    try:
        jsonschema.Draft7Validator(schema).validate(roadmap_slice)
    except jsonschema.ValidationError as exc:
        raise RoadmapSliceBuilderError(f"Invalid roadmap_slice output: {exc.message}") from exc


def _resolve_active_milestone(
    intent: Mapping[str, Any],
    framework_state_v2: Mapping[str, Any],
    table_rows: list[dict[str, Any]],
    section_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    active = framework_state_v2.get("active_milestone")
    if isinstance(active, Mapping):
        milestone_id = _required_string(active, "id")
        status = _normalize_status(_required_string(active, "status"))
        name = _optional_string(active.get("name")) or _section_name(section_map.get(milestone_id)) or _table_name(table_rows, milestone_id)
        branch = _optional_string(active.get("branch")) or _section_branch(section_map.get(milestone_id)) or "main"
        return _milestone_object(milestone_id, status, branch, name)

    related = intent.get("related_milestone")
    if isinstance(related, Mapping):
        milestone_id = _required_string(related, "id")
        table_row = _table_row(table_rows, milestone_id)
        section = section_map.get(milestone_id)
        status = _normalize_status(_optional_string(related.get("status")) or (table_row["status"] if table_row else "planned"))
        name = _optional_string(related.get("name")) or _section_name(section) or _table_name(table_rows, milestone_id)
        branch = _optional_string(related.get("branch")) or _section_branch(section) or "main"
        return _milestone_object(milestone_id, status, branch, name)

    for row in table_rows:
        if row["status"] != "completed":
            section = section_map.get(row["id"])
            branch = _section_branch(section) or "main"
            return _milestone_object(row["id"], row["status"], branch, row["name"])

    if table_rows:
        row = table_rows[0]
        section = section_map.get(row["id"])
        branch = _section_branch(section) or "main"
        return _milestone_object(row["id"], row["status"], branch, row["name"])

    raise RoadmapSliceBuilderError("roadmap_text does not contain a milestone table")


def _select_relevant_milestones(
    active_milestone: dict[str, Any],
    table_rows: list[dict[str, Any]],
    section_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not table_rows:
        return [active_milestone]

    index_by_id = {row["id"]: index for index, row in enumerate(table_rows)}
    active_id = active_milestone["id"]
    active_index = index_by_id.get(active_id)
    if active_index is None:
        active_index = next((index for index, row in enumerate(table_rows) if row["status"] != "completed"), 0)

    start = active_index
    while start > 0 and table_rows[start - 1]["status"] != "completed":
        start -= 1

    end = active_index
    while end + 1 < len(table_rows) and table_rows[end + 1]["status"] != "completed":
        end += 1

    relevant: list[dict[str, Any]] = []
    for row in table_rows[start : end + 1]:
        section = section_map.get(row["id"])
        branch = _section_branch(section)
        item = _milestone_object(row["id"], row["status"], branch or active_milestone["branch"], row["name"])
        relevant.append(item)

    if active_id not in {item["id"] for item in relevant}:
        relevant.insert(0, active_milestone)

    return _ordered_unique_milestones(relevant)


def _build_allowed_operations(intent: Mapping[str, Any], roadmap_text: str) -> list[str]:
    values = ["read_contract", "validate_schema", "create_task_packet", "build_context_bundle", "run_tests", "create_review_report", "request_git_operation"]
    text = _flatten_text(intent) + " " + roadmap_text.lower()
    if any(keyword in text for keyword in ("schema", "schemas", ".schema.json", "architecture", "arquitectura")):
        values.insert(2, "design_schema")
    return _ordered_unique(values)


def _build_policy_refs(active_milestone: dict[str, Any], relevant_milestones: list[dict[str, Any]]) -> list[str]:
    values = ["ROADMAP.md::Estado General"]
    values.append(f"ROADMAP.md::{active_milestone['id']}")
    if active_milestone.get("name"):
        values.append(f"ROADMAP.md::{active_milestone['name']}")
    for milestone in relevant_milestones:
        if milestone["id"] == active_milestone["id"]:
            continue
        if milestone.get("name"):
            values.append(f"ROADMAP.md::{milestone['id']}")
    return _ordered_unique(values)


def _build_branch_context(active_milestone: dict[str, Any]) -> dict[str, str]:
    return {
        "current": _required_string(active_milestone, "branch"),
        "base": "main",
    }


def _build_open_issues(
    active_milestone: dict[str, Any],
    relevant_milestones: list[dict[str, Any]],
    requires_user_confirmation: bool,
    stamp: str,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if requires_user_confirmation:
        issues.append(
            {
                "issue_id": f"RSLICE-{stamp}-CONFIRM",
                "title": f"Confirm roadmap slice for {active_milestone['id']}",
                "status": "needs_user_confirmation",
            }
        )
    if active_milestone["status"] == "paused":
        issues.append(
            {
                "issue_id": f"RSLICE-{stamp}-PAUSED",
                "title": f"Resolve paused milestone {active_milestone['id']}",
                "status": "blocked",
            }
        )
    if len(relevant_milestones) > MAX_RELEVANT_MILESTONES_CONFIRMATION and not requires_user_confirmation:
        issues.append(
            {
                "issue_id": f"RSLICE-{stamp}-SCOPE",
                "title": "Narrow the roadmap slice scope",
                "status": "open",
            }
        )
    return issues


def _build_risk_notes(
    active_milestone: dict[str, Any],
    relevant_milestones: list[dict[str, Any]],
    requires_user_confirmation: bool,
) -> list[str]:
    notes: list[str] = []
    if len(relevant_milestones) > MAX_RELEVANT_MILESTONES_WARNING:
        notes.append("relevant_milestones_warning")
    if len(relevant_milestones) > MAX_RELEVANT_MILESTONES_CONFIRMATION:
        notes.append("relevant_milestones_requires_user_confirmation")
    if active_milestone["status"] == "paused":
        notes.append("milestone_paused")
    if requires_user_confirmation and "requires_user_confirmation" not in notes:
        notes.append("requires_user_confirmation")
    return _ordered_unique(notes)


def _build_recent_changes(relevant_milestones: list[dict[str, Any]]) -> list[str]:
    values = [f"{milestone['id']}: {milestone['status']}" for milestone in relevant_milestones]
    return _ordered_unique(values)


def _build_source_refs(
    active_milestone: dict[str, Any],
    relevant_milestones: list[dict[str, Any]],
    table_rows: list[dict[str, Any]],
    section_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []

    row_numbers = [row["line"] for row in table_rows if row["id"] in {milestone["id"] for milestone in relevant_milestones}]
    if row_numbers:
        refs.append(
            {
                "path": "ROADMAP.md",
                "section": "Estado General",
                "line_ranges": [{"start": min(row_numbers), "end": max(row_numbers)}],
            }
        )

    active_section = section_map.get(active_milestone["id"])
    if active_section:
        refs.append(
            {
                "path": "ROADMAP.md",
                "section": f"{active_milestone['id']}: {active_section['name']}",
                "line_ranges": _compact_line_ranges(active_section["start_line"], active_section["end_line"]),
            }
        )

    return refs or [
        {
            "path": "ROADMAP.md",
            "section": "Estado General",
            "line_ranges": [{"start": 1, "end": min(10, len(table_rows) or 10)}],
        }
    ]


def _compact_line_ranges(start_line: int, end_line: int) -> list[dict[str, int]]:
    if start_line > end_line:
        return [{"start": end_line, "end": start_line}]

    ranges: list[dict[str, int]] = []
    cursor = start_line
    while cursor <= end_line and len(ranges) < 3:
        range_end = min(end_line, cursor + 7)
        ranges.append({"start": cursor, "end": range_end})
        cursor = range_end + 1
    return ranges


def _parse_status_table(lines: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    in_table = False
    for line_number, line in enumerate(lines, start=1):
        if ROADMAP_TABLE_HEADER_RE.match(line):
            in_table = True
            continue
        if in_table and not line.strip().startswith("|"):
            if rows:
                break
            continue
        if not in_table:
            continue
        if set(line.strip()) <= {"|", "-", ":", " "}:
            continue
        match = ROADMAP_TABLE_ROW_RE.match(line)
        if not match:
            continue
        rows.append(
            {
                "id": match.group(1),
                "name": match.group(2).strip(),
                "status": _normalize_roadmap_status(match.group(3)),
                "start": match.group(4).strip(),
                "line": line_number,
            }
        )
    return rows


def _parse_sections(lines: list[str]) -> dict[str, dict[str, Any]]:
    sections: dict[str, dict[str, Any]] = {}
    current_id: str | None = None
    for line_number, line in enumerate(lines, start=1):
        heading_match = ROADMAP_HEADING_RE.match(line)
        if heading_match:
            if current_id is not None:
                sections[current_id]["end_line"] = line_number - 1
            current_id = heading_match.group(1)
            sections[current_id] = {
                "name": heading_match.group(2).strip(),
                "start_line": line_number,
                "end_line": len(lines),
                "branch": None,
            }
            continue
        if current_id is None:
            continue
        branch_match = ROADMAP_BRANCH_RE.match(line)
        if branch_match:
            sections[current_id]["branch"] = branch_match.group(1)
    return sections


def _normalize_roadmap_status(value: str) -> str:
    normalized = " ".join(value.lower().split())
    if "paused" in normalized or "pausado" in normalized:
        return "paused"
    if "completed" in normalized or "completado" in normalized or "✅" in value:
        return "completed"
    if "in progress" in normalized or "en progreso" in normalized or "🔄" in value:
        return "in_progress"
    return "planned"


def _normalize_status(value: str) -> str:
    normalized = value.lower().strip()
    if normalized in {"planned", "in_progress", "completed", "paused"}:
        return normalized
    return _normalize_roadmap_status(value)


def _milestone_object(milestone_id: str, status: str, branch: str, name: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "id": milestone_id,
        "status": status,
        "branch": branch,
    }
    if name:
        value["name"] = name
    return value


def _ordered_unique(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def _ordered_unique_milestones(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        milestone_id = str(value.get("id", ""))
        if not milestone_id or milestone_id in seen:
            continue
        seen.add(milestone_id)
        unique.append(value)
    return unique


def _table_row(table_rows: list[dict[str, Any]], milestone_id: str) -> dict[str, Any] | None:
    for row in table_rows:
        if row["id"] == milestone_id:
            return row
    return None


def _table_name(table_rows: list[dict[str, Any]], milestone_id: str) -> str | None:
    row = _table_row(table_rows, milestone_id)
    return row["name"] if row else None


def _section_name(section: dict[str, Any] | None) -> str | None:
    if not section:
        return None
    return _optional_string(section.get("name"))


def _section_branch(section: dict[str, Any] | None) -> str | None:
    if not section:
        return None
    return _optional_string(section.get("branch"))


def _build_human_summary(active_milestone: dict[str, Any], relevant_milestones: list[dict[str, Any]], requires_user_confirmation: bool) -> str:
    parts = [
        f"Roadmap slice for {active_milestone['id']} on {active_milestone['branch']} with {len(relevant_milestones)} relevant milestone(s).",
    ]
    if len(relevant_milestones) > MAX_RELEVANT_MILESTONES_WARNING:
        parts.append("Warning: slice spans more than three milestones.")
    if requires_user_confirmation:
        parts.append("User confirmation required.")
    return " ".join(parts)


def _flatten_text(value: Any) -> str:
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


def _required_string(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise RoadmapSliceBuilderError(f"{key} is required")
    return item


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


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
        raise RoadmapSliceBuilderError(f"Required schema not found: {path}") from exc


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

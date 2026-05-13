"""Diff engine for comparing JSON artifacts from the FBA pipeline.

Compares two versions of an artifact (PRD, SDD, schema.json, tasks/index.json,
T*.json) and produces a structured changelog listing additions, deletions, and
modifications with field/section granularity.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DiffError(Exception):
    """Raised when diff comparison fails."""


class DiffEngine:
    """Compares two JSON artifacts and produces deterministic changelogs.

    Supports PRD, SDD, schema.json, tasks/index.json, and T*.json artifacts.
    Output formats: text (human-readable) and json (machine-readable).

    Usage:
        engine = DiffEngine()
        changelog = engine.diff(Path("v1/prd.json"), Path("v2/prd.json"))
        print(changelog)
    """

    ARTIFACT_SIGNATURES = {
        "prd": ["vision", "stakeholders", "functional_requirements"],
        "sdd": ["module_name", "models", "traceability_matrix"],
        "schema": ["manifest", "models", "views"],
        "tasks_index": ["tasks", "generated_at"],
    }

    @staticmethod
    def detect_artifact_type(data: dict[str, Any]) -> str:
        """Detect the artifact type from its top-level keys.

        Returns one of: prd, sdd, schema, tasks_index, task_item, unknown.
        """
        if not isinstance(data, dict):
            return "unknown"
        keys = set(data.keys())

        if keys >= {"vision", "stakeholders", "functional_requirements"}:
            return "prd"
        if keys >= {"module_name", "architecture", "models"}:
            return "sdd"
        if keys >= {"manifest", "models"} and ("views" in keys or "security" in keys):
            return "schema"
        if keys >= {"tasks", "generated_at"}:
            return "tasks_index"
        if "component" in keys and "task_id" in keys:
            return "task_item"

        return "unknown"

    @staticmethod
    def diff(
        file_v1: Path,
        file_v2: Path,
        output_format: str = "text",
    ) -> str:
        """Compare two artifact files and return a structured changelog.

        Args:
            file_v1: Path to the older version of the artifact (JSON).
            file_v2: Path to the newer version of the artifact (JSON).
            output_format: 'text' for human-readable or 'json' for machine-readable.

        Returns:
            Formatted changelog string.

        Raises:
            DiffError: If a file does not exist or contains invalid JSON.
        """
        if not file_v1.exists():
            raise DiffError(f"File not found: {file_v1}")
        if not file_v2.exists():
            raise DiffError(f"File not found: {file_v2}")

        try:
            data_v1 = json.loads(file_v1.read_text())
        except json.JSONDecodeError as e:
            raise DiffError(f"Invalid JSON in {file_v1}: {e}")

        try:
            data_v2 = json.loads(file_v2.read_text())
        except json.JSONDecodeError as e:
            raise DiffError(f"Invalid JSON in {file_v2}: {e}")

        artifact_type = DiffEngine.detect_artifact_type(data_v2) or DiffEngine.detect_artifact_type(data_v1)

        changes = DiffEngine._deep_diff(data_v1, data_v2)

        added = changes["added"]
        removed = changes["removed"]
        modified = changes["modified"]

        changelog = {
            "artifact_type": artifact_type,
            "version_old": str(file_v1),
            "version_new": str(file_v2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "changes": {
                "added": added,
                "removed": removed,
                "modified": modified,
            },
            "summary": {
                "total_changes": len(added) + len(removed) + len(modified),
                "added_count": len(added),
                "removed_count": len(removed),
                "modified_count": len(modified),
            },
        }

        if output_format == "json":
            return DiffEngine._format_json(changelog)
        return DiffEngine._format_text(changelog)

    @staticmethod
    def _deep_diff(
        old: Any,
        new: Any,
        path: str = "$",
    ) -> dict[str, list[dict[str, Any]]]:
        """Recursively compare two JSON values.

        Returns a dict with 'added', 'removed', and 'modified' lists.
        Each change entry has a 'path' (JSONPath-like) and relevant values.

        For arrays of objects, matches elements by 'id' field when available,
        otherwise compares by index.
        """
        result: dict[str, list[dict[str, Any]]] = {"added": [], "removed": [], "modified": []}

        if type(old) is not type(new):
            result["modified"].append({
                "path": path,
                "old_value": old,
                "new_value": new,
            })
            return result

        if isinstance(old, dict):
            old_keys = set(old.keys())
            new_keys = set(new.keys())

            for key in old_keys - new_keys:
                result["removed"].append({
                    "path": f"{path}.{key}" if path != "$" else f"$.{key}",
                    "value": old[key],
                })

            for key in new_keys - old_keys:
                result["added"].append({
                    "path": f"{path}.{key}" if path != "$" else f"$.{key}",
                    "value": new[key],
                })

            for key in old_keys & new_keys:
                child_path = f"{path}.{key}" if path != "$" else f"$.{key}"
                child_changes = DiffEngine._deep_diff(old[key], new[key], child_path)
                result["added"].extend(child_changes["added"])
                result["removed"].extend(child_changes["removed"])
                result["modified"].extend(child_changes["modified"])

        elif isinstance(old, list):
            old_indexed = DiffEngine._index_array(old)
            new_indexed = DiffEngine._index_array(new)

            old_ids = set(old_indexed.keys())
            new_ids = set(new_indexed.keys())

            for idx in old_ids - new_ids:
                result["removed"].append({
                    "path": f"{path}[{idx}]",
                    "value": old_indexed[idx]["value"],
                })

            for idx in new_ids - old_ids:
                result["added"].append({
                    "path": f"{path}[{idx}]",
                    "value": new_indexed[idx]["value"],
                })

            for idx in old_ids & new_ids:
                old_idx = old_indexed[idx]["index"]
                new_idx = new_indexed[idx]["index"]
                child_path = f"{path}[{old_idx}]"
                child_changes = DiffEngine._deep_diff(
                    old[old_idx], new[new_idx], child_path
                )
                result["added"].extend(child_changes["added"])
                result["removed"].extend(child_changes["removed"])
                result["modified"].extend(child_changes["modified"])

        else:
            if old != new:
                result["modified"].append({
                    "path": path,
                    "old_value": old,
                    "new_value": new,
                })

        return result

    @staticmethod
    def _index_array(arr: list[Any]) -> dict[str, dict[str, Any]]:
        """Index an array for comparison.

        Arrays of dicts with an 'id' field are indexed by id.
        Other arrays are indexed by position (0, 1, 2, ...).
        """
        indexed = {}
        for i, item in enumerate(arr):
            if isinstance(item, dict) and "id" in item:
                key = str(item["id"])
            else:
                key = str(i)
            indexed[key] = {"index": i, "value": item}
        return indexed

    @staticmethod
    def _format_text(changelog: dict[str, Any]) -> str:
        """Format changelog as human-readable text."""
        lines = []
        lines.append(f"=== Diff: {changelog['artifact_type']} ===")
        lines.append(f"Old: {changelog['version_old']}")
        lines.append(f"New: {changelog['version_new']}")
        lines.append(f"Time: {changelog['timestamp']}")
        lines.append("")

        changes = changelog["changes"]
        if changes["added"]:
            lines.append("Added:")
            for entry in changes["added"]:
                value_str = DiffEngine._truncate_value(entry["value"])
                lines.append(f"  + {entry['path']}: {value_str}")
            lines.append("")

        if changes["removed"]:
            lines.append("Removed:")
            for entry in changes["removed"]:
                value_str = DiffEngine._truncate_value(entry["value"])
                lines.append(f"  - {entry['path']}: {value_str}")
            lines.append("")

        if changes["modified"]:
            lines.append("Modified:")
            for entry in changes["modified"]:
                old_str = DiffEngine._truncate_value(entry["old_value"])
                new_str = DiffEngine._truncate_value(entry["new_value"])
                lines.append(f"  ~ {entry['path']}: {old_str} → {new_str}")
            lines.append("")

        summary = changelog["summary"]
        total = summary["total_changes"]
        if total == 0:
            lines.append("No changes detected.")
        else:
            parts = []
            if summary["added_count"]:
                parts.append(f"{summary['added_count']} added")
            if summary["removed_count"]:
                parts.append(f"{summary['removed_count']} removed")
            if summary["modified_count"]:
                parts.append(f"{summary['modified_count']} modified")
            lines.append(f"Summary: {total} changes ({', '.join(parts)})")

        return "\n".join(lines)

    @staticmethod
    def _format_json(changelog: dict[str, Any]) -> str:
        """Format changelog as a deterministic JSON string."""
        return json.dumps(changelog, indent=2, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _truncate_value(value: Any, max_len: int = 60) -> str:
        """Truncate a value for display in text output."""
        if isinstance(value, (dict, list)):
            s = json.dumps(value, ensure_ascii=False)
        else:
            s = str(value)
        if len(s) > max_len:
            return s[: max_len - 3] + "..."
        return s

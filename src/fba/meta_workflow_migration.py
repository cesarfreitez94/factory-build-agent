"""Infrastructure for the V1 -> V2 meta-workflow projection.

The V1 framework state remains authoritative. This module only projects the
current V1 state into a validated V2 shadow state and writes migration metadata
without altering the V1 runtime files.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import jsonschema


def _atomic_write(path: Path, content: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _date_stamp(timestamp: str | None) -> str:
    if timestamp:
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return parsed.strftime("%Y%m%d")
        except ValueError:
            pass
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _safe_json_loads(path: Path) -> dict[str, Any]:
    try:
        return cast(dict[str, Any], json.loads(path.read_text()))
    except json.JSONDecodeError as exc:
        raise MetaWorkflowMigrationError(f"Invalid JSON in {path}: {exc}") from exc


@dataclass(frozen=True)
class MigrationProjection:
    v1_state: dict[str, Any]
    v2_state: dict[str, Any]
    decision_records: list[dict[str, Any]]
    decision_mappings: list[dict[str, str]]
    migration_notes: list[str]


@dataclass(frozen=True)
class BootstrapResult:
    v1_state_path: Path
    v2_state_path: Path
    config_path: Path
    schema_catalog_path: Path
    migration_path: Path
    decisions_path: Path
    last_validation_path: Path
    drift_report_path: Path
    schema_valid: bool
    active_milestone_match: bool
    pending_decisions_projected: bool


class MetaWorkflowMigrationError(Exception):
    """Raised when the V1 -> V2 projection cannot be completed."""


class MetaWorkflowMigrator:
    """Creates a validated V2 shadow state from the authoritative V1 state."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.factory_dir = self.project_dir / ".factory"
        self.meta_dir = self.factory_dir / "meta"
        self.artifacts_dir = self.meta_dir / "artifacts"
        self.snapshots_dir = self.meta_dir / "snapshots"
        self.validation_dir = self.meta_dir / "validation"
        self.v1_state_path = self.factory_dir / "framework-state.json"
        self.v2_state_path = self.meta_dir / "framework_state.v2.json"
        self.config_path = self.meta_dir / "meta_workflow_config.json"
        self.schema_catalog_path = self.meta_dir / "schema_catalog.json"
        self.migration_path = self.meta_dir / "migration.json"
        self.decisions_path = self.meta_dir / "decisions.jsonl"
        self.last_validation_path = self.validation_dir / "last_validation.json"
        self.drift_report_path = self.validation_dir / "drift_report.json"
        self.v2_schema_path = self.project_dir / "schemas" / "meta" / "framework_state.v2.schema.json"
        self.catalog_schema_path = self.project_dir / "schemas" / "meta" / "schema_catalog.schema.json"

    def bootstrap(self) -> BootstrapResult:
        self._ensure_structure()

        v1_state = self.load_v1_state()
        projection = self.project_v1_to_v2(v1_state)

        self._write_json(self.v2_state_path, projection.v2_state)
        self._validate_instance(self.v2_state_path, self.v2_schema_path)

        config = self._build_config()
        schema_catalog = self._build_schema_catalog()
        migration = self._build_migration_record(projection)
        drift_report = self._build_drift_report(projection.v1_state, projection.v2_state, projection)
        validation_report = self._build_validation_report(projection, drift_report)

        self._write_json(self.config_path, config)
        self._write_json(self.schema_catalog_path, schema_catalog)
        self._validate_instance(self.schema_catalog_path, self.catalog_schema_path)
        self._write_json(self.migration_path, migration)
        self._write_json(self.last_validation_path, validation_report)
        self._write_json(self.drift_report_path, drift_report)
        self._append_decision_records(projection.decision_records)

        return BootstrapResult(
            v1_state_path=self.v1_state_path,
            v2_state_path=self.v2_state_path,
            config_path=self.config_path,
            schema_catalog_path=self.schema_catalog_path,
            migration_path=self.migration_path,
            decisions_path=self.decisions_path,
            last_validation_path=self.last_validation_path,
            drift_report_path=self.drift_report_path,
            schema_valid=True,
            active_milestone_match=bool(drift_report["active_milestone_match"]),
            pending_decisions_projected=bool(drift_report["pending_decisions_projected"]),
        )

    def load_v1_state(self) -> dict[str, Any]:
        if not self.v1_state_path.exists():
            raise MetaWorkflowMigrationError(f"V1 state not found: {self.v1_state_path}")
        return _safe_json_loads(self.v1_state_path)

    def project_v1_to_v2(self, v1_state: dict[str, Any]) -> MigrationProjection:
        updated_at = cast(str | None, v1_state.get("last_updated"))
        stamp = _date_stamp(updated_at)
        state_id = f"FWSTATE-{stamp}-001"

        active_milestone = self._project_active_milestone(v1_state.get("active_milestone"))
        pending_decisions, decision_records, decision_mappings, migration_notes = self._project_pending_decisions(
            cast(list[dict[str, Any]], v1_state.get("pending_decisions", [])),
            stamp,
        )

        v2_state = {
            "contract_name": "framework_state_v2",
            "contract_version": "2.0",
            "state_id": state_id,
            "updated_at": updated_at or _now_iso(),
            "workflow_version": "meta_v2",
            "current_phase": self._derive_current_phase(v1_state),
            "active_intent_id": None,
            "active_plan_id": None,
            "active_task_id": None,
            "active_milestone": active_milestone,
            "last_completed_step": None,
            "artifacts": [
                {
                    "contract_name": "framework_state_v2",
                    "contract_version": "2.0",
                    "artifact_id": state_id,
                    "path": ".factory/meta/framework_state.v2.json",
                    "status": "valid",
                    "version": 1,
                }
            ],
            "pending_decisions": pending_decisions,
            "human_summary": "V2 shadow projection generated from the authoritative V1 framework state.",
        }

        return MigrationProjection(
            v1_state=v1_state,
            v2_state=v2_state,
            decision_records=decision_records,
            decision_mappings=decision_mappings,
            migration_notes=migration_notes,
        )

    def _ensure_structure(self) -> None:
        for path in (self.meta_dir, self.artifacts_dir, self.snapshots_dir, self.validation_dir):
            path.mkdir(parents=True, exist_ok=True)

    def _project_active_milestone(self, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            return None

        projected = {
            "id": str(value.get("id", "")),
            "status": self._normalize_milestone_status(str(value.get("status", "planned"))),
            "branch": str(value.get("branch", "")),
        }
        name = value.get("name")
        if name is not None:
            projected["name"] = str(name)
        return projected

    def _project_pending_decisions(
        self,
        values: list[dict[str, Any]],
        stamp: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]], list[str]]:
        projected: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        mappings: list[dict[str, str]] = []
        notes: list[str] = []

        pending_values = [value for value in values if self._is_pending_decision(value)]

        for index, value in enumerate(pending_values, start=1):
            source_id = str(value.get("id") or value.get("decision_id") or f"legacy-{index:03d}")
            decision_id = f"DEC-{stamp}-{index:03d}"
            status = self._normalize_decision_status(str(value.get("status", "awaiting_user")))
            question = str(value.get("description") or value.get("question") or source_id)
            projected_item: dict[str, Any] = {
                "decision_id": decision_id,
                "status": status,
                "question": question,
            }

            projected.append(projected_item)
            records.append(
                {
                    "contract_name": "decisions",
                    "contract_version": "2.0",
                    "decision_id": decision_id,
                    "created_at": self._decision_created_at(value),
                    "decision_type": "user_confirmation",
                    "status": status,
                    "question": question,
                    "options": ["approve", "reject"],
                    "selected_option": None,
                    "required_by": ["meta-migration"],
                }
            )
            mappings.append(
                {
                    "source_id": source_id,
                    "decision_id": decision_id,
                    "status": status,
                }
            )

            if source_id != decision_id:
                notes.append(f"Projected pending decision {source_id} -> {decision_id}")

        return projected, records, mappings, notes

    def _is_pending_decision(self, value: dict[str, Any]) -> bool:
        return str(value.get("status", "")).lower() in {"pending", "awaiting_user"}

    def _decision_created_at(self, value: dict[str, Any]) -> str:
        raw_value = value.get("created_at") or value.get("raised_at") or value.get("created")
        if isinstance(raw_value, str) and raw_value:
            if "T" in raw_value:
                return raw_value
            return f"{raw_value}T00:00:00Z"
        return _now_iso()

    def _derive_current_phase(self, v1_state: dict[str, Any]) -> str:
        last_session = v1_state.get("last_session")
        if isinstance(last_session, dict) and last_session.get("blockers"):
            return "blocked"

        active_milestone = v1_state.get("active_milestone")
        if isinstance(active_milestone, dict):
            status = str(active_milestone.get("status", "planned"))
            if status == "completed":
                return "completed"
            if status == "paused":
                return "blocked"
            if status == "in_progress":
                return "implementation"

        return "idle"

    def _normalize_milestone_status(self, status: str) -> str:
        if status in {"planned", "in_progress", "completed", "paused"}:
            return status
        return "planned"

    def _normalize_decision_status(self, status: str) -> str:
        if status == "awaiting_user":
            return "pending"
        if status in {"pending", "resolved", "cancelled"}:
            return status
        return "pending"

    def _build_config(self) -> dict[str, Any]:
        return {
            "meta_workflow_version": "v1",
            "authoritative_state": ".factory/framework-state.json",
            "projected_state": ".factory/meta/framework_state.v2.json",
            "fallback_enabled": True,
            "rollback_enabled": True,
            "projection_mode": "shadow",
            "schema_catalog_path": ".factory/meta/schema_catalog.json",
            "migration_path": ".factory/meta/migration.json",
            "validation_path": ".factory/meta/validation",
        }

    def _build_schema_catalog(self) -> dict[str, Any]:
        contracts = [
            {
                "contract_name": "schema_catalog",
                "contract_version": "2.0",
                "path": "schemas/meta/schema_catalog.schema.json",
                "status": "active",
                "owner": "framework-registry",
                "consumers": ["meta-migration"],
            },
            {
                "contract_name": "decisions",
                "contract_version": "2.0",
                "path": "schemas/meta/decisions.schema.json",
                "status": "active",
                "owner": "framework-registry",
                "consumers": ["meta-migration"],
            },
            {
                "contract_name": "framework_state_v2",
                "contract_version": "2.0",
                "path": "schemas/meta/framework_state.v2.schema.json",
                "status": "experimental",
                "owner": "framework-registry",
                "consumers": ["meta-migration"],
                "depends_on": ["schema_catalog@2.0"],
            },
            {
                "contract_name": "intent",
                "contract_version": "2.0",
                "path": "schemas/meta/intent.schema.json",
                "status": "active",
                "owner": "framework-planner",
            },
            {
                "contract_name": "policy_constraints",
                "contract_version": "2.0",
                "path": "schemas/meta/policy_constraints.schema.json",
                "status": "active",
                "owner": "framework-planner",
            },
            {
                "contract_name": "roadmap_slice",
                "contract_version": "2.0",
                "path": "schemas/meta/roadmap_slice.schema.json",
                "status": "active",
                "owner": "framework-planner",
            },
            {
                "contract_name": "plan",
                "contract_version": "2.0",
                "path": "schemas/meta/plan.schema.json",
                "status": "active",
                "owner": "framework-planner",
            },
            {
                "contract_name": "task_packet",
                "contract_version": "2.0",
                "path": "schemas/meta/task_packet.schema.json",
                "status": "active",
                "owner": "framework-builder",
            },
            {
                "contract_name": "context_bundle",
                "contract_version": "2.0",
                "path": "schemas/meta/context_bundle.schema.json",
                "status": "active",
                "owner": "framework-builder",
            },
            {
                "contract_name": "implementation_report",
                "contract_version": "2.0",
                "path": "schemas/meta/implementation_report.schema.json",
                "status": "active",
                "owner": "framework-builder",
            },
            {
                "contract_name": "test_report",
                "contract_version": "2.0",
                "path": "schemas/meta/test_report.schema.json",
                "status": "active",
                "owner": "framework-builder",
            },
            {
                "contract_name": "review_report",
                "contract_version": "2.0",
                "path": "schemas/meta/review_report.schema.json",
                "status": "active",
                "owner": "framework-builder",
            },
            {
                "contract_name": "git_operation",
                "contract_version": "2.0",
                "path": "schemas/meta/git_operation.schema.json",
                "status": "active",
                "owner": "framework-git",
            },
        ]

        return {
            "contract_name": "schema_catalog",
            "contract_version": "2.0",
            "catalog_id": f"SCAT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-001",
            "updated_at": _now_iso(),
            "contracts": contracts,
            "global_policies": [
                {"policy_id": "CONTRIBUTING", "path": "CONTRIBUTING.md", "mode": "reference"},
                {"policy_id": "ROADMAP", "path": "ROADMAP.md", "mode": "reference"},
            ],
            "compatibility_matrix": [
                {
                    "from": "framework_state@1.0",
                    "to": "framework_state_v2@2.0",
                    "status": "requires_migration",
                    "notes": "V1 remains authoritative during the hybrid migration window.",
                },
                {
                    "from": "intent@2.0",
                    "to": "plan@2.0",
                    "status": "compatible",
                    "notes": "Planning contracts remain stable.",
                },
            ],
            "human_summary": "Initial schema catalog for the schema-driven meta-workflow migration.",
        }

    def _build_migration_record(self, projection: MigrationProjection) -> dict[str, Any]:
        state_id = cast(str, projection.v2_state["state_id"])
        updated_at = cast(str, projection.v2_state["updated_at"])
        return {
            "migration_id": f"MIG-{_date_stamp(updated_at)}-001",
            "created_at": _now_iso(),
            "meta_workflow_version": "v1",
            "mode": "shadow_projection",
            "status": "projected",
            "source_state_path": ".factory/framework-state.json",
            "target_state_path": ".factory/meta/framework_state.v2.json",
            "source_schema_version": cast(str, projection.v1_state.get("schema_version", "1.0")),
            "target_contract_version": "2.0",
            "projected_state_id": state_id,
            "decision_mappings": projection.decision_mappings,
            "migration_notes": projection.migration_notes,
        }

    def _build_drift_report(
        self,
        v1_state: dict[str, Any],
        v2_state: dict[str, Any],
        projection: MigrationProjection,
    ) -> dict[str, Any]:
        v1_active = v1_state.get("active_milestone")
        v2_active = v2_state.get("active_milestone")

        active_match = self._compare_active_milestones(v1_active, v2_active)

        source_decisions = [
            item
            for item in cast(list[dict[str, Any]], v1_state.get("pending_decisions", []))
            if self._is_pending_decision(item)
        ]
        projected_decisions = cast(list[dict[str, Any]], v2_state.get("pending_decisions", []))
        projected_ids = {str(item.get("decision_id")) for item in projected_decisions}

        mapped_source_ids = {entry["source_id"] for entry in projection.decision_mappings}
        source_ids = [str(item.get("id") or item.get("decision_id") or "") for item in source_decisions]
        missing_ids = [source_id for source_id in source_ids if source_id and source_id not in mapped_source_ids]

        pending_decisions_projected = len(source_decisions) == len(projected_decisions) and not missing_ids

        return {
            "checked_at": _now_iso(),
            "status": "clean" if active_match and pending_decisions_projected else "drift_detected",
            "active_milestone_match": active_match,
            "pending_decisions_projected": pending_decisions_projected,
            "source_pending_decision_ids": source_ids,
            "projected_pending_decision_ids": sorted(projected_ids),
            "decision_mappings": projection.decision_mappings,
            "unmapped_pending_decisions": missing_ids,
            "notes": projection.migration_notes,
        }

    def _build_validation_report(
        self,
        projection: MigrationProjection,
        drift_report: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "checked_at": _now_iso(),
            "schema_path": str(self.v2_schema_path),
            "state_path": str(self.v2_state_path),
            "schema_valid": True,
            "active_milestone_match": bool(drift_report["active_milestone_match"]),
            "pending_decisions_projected": bool(drift_report["pending_decisions_projected"]),
            "status": "passed" if drift_report["status"] == "clean" else "warning",
            "state_id": cast(str, projection.v2_state["state_id"]),
            "notes": projection.migration_notes,
        }

    def _compare_active_milestones(self, v1_active: Any, v2_active: Any) -> bool:
        if v1_active is None and v2_active is None:
            return True
        if not isinstance(v1_active, dict) or not isinstance(v2_active, dict):
            return False

        keys = ("id", "name", "status", "branch")
        for key in keys:
            v1_value = v1_active.get(key)
            v2_value = v2_active.get(key)
            if key == "name" and v2_value is None:
                continue
            if v1_value is None or v2_value is None:
                return False
            if str(v1_value) != str(v2_value):
                return False
        return True

    def _validate_instance(self, instance_path: Path, schema_path: Path) -> None:
        if not schema_path.exists():
            raise MetaWorkflowMigrationError(f"Schema not found: {schema_path}")
        schema = _safe_json_loads(schema_path)
        instance = _safe_json_loads(instance_path)
        try:
            jsonschema.Draft7Validator(schema).validate(instance)
        except jsonschema.ValidationError as exc:
            raise MetaWorkflowMigrationError(f"Validation failed for {instance_path}: {exc}") from exc

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        _atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    def _append_decision_records(self, rows: list[dict[str, Any]]) -> None:
        self.decisions_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.decisions_path.exists():
            self.decisions_path.touch()

        existing_ids: set[str] = set()
        for line in self.decisions_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and isinstance(value.get("decision_id"), str):
                existing_ids.add(value["decision_id"])

        missing_rows = [row for row in rows if row["decision_id"] not in existing_ids]
        if not missing_rows:
            return

        with self.decisions_path.open("a", encoding="utf8") as handle:
            for row in missing_rows:
                handle.write(f"{json.dumps(row, ensure_ascii=False)}\n")
            handle.flush()
            os.fsync(handle.fileno())


def bootstrap_meta_workflow(project_dir: Path) -> BootstrapResult:
    """Convenience wrapper used by tests and local bootstrap commands."""

    return MetaWorkflowMigrator(project_dir).bootstrap()

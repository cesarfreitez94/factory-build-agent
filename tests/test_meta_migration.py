"""Tests for the V1 -> V2 meta-workflow migration projection."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from fba.meta_workflow_migration import MetaWorkflowMigrator, bootstrap_meta_workflow


REPO_ROOT = Path(__file__).resolve().parent.parent
V2_SCHEMA_PATH = REPO_ROOT / "schemas" / "meta" / "framework_state.v2.schema.json"
DECISIONS_SCHEMA_PATH = REPO_ROOT / "schemas" / "meta" / "decisions.schema.json"


def _sample_v1_state(*, include_pending_decision: bool = True) -> dict[str, object]:
    pending_decisions: list[dict[str, object]] = [
        {
            "id": "D2026-05-15-002",
            "description": "Approve schema catalog bootstrap",
            "raised_by": "framework-registry",
            "raised_at": "2026-05-15",
            "status": "resolved",
        }
    ]
    if include_pending_decision:
        pending_decisions.insert(
            0,
            {
                "id": "D2026-05-15-001",
                "description": "Authorize V1 -> V2 projection",
                "raised_by": "framework-orchestrator",
                "raised_at": "2026-05-15",
                "status": "awaiting_user",
            },
        )

    return {
        "schema_version": "1.0",
        "last_updated": "2026-05-15T13:00:00Z",
        "last_session": {
            "date": "2026-05-15",
            "agent": "framework-registry",
            "action": "Bootstrap migration projection",
            "completed_feats": ["feat/18.1"],
            "pending_feats": ["feat/18.2"],
            "blockers": [],
        },
        "active_milestone": {
            "id": "M18",
            "name": "Input & Extension Layer",
            "branch": "milestone/18.0-input-extension-layer",
            "status": "in_progress",
            "feats_total": 3,
            "feats_done": 1,
            "feats_pending": ["feat/18.2", "feat/18.3"],
            "ready_for_user_review": False,
        },
        "roadmap_status": {"M18": "in_progress"},
        "roadmap_summary": [
            {
                "milestone": "M18",
                "name": "Input & Extension Layer",
                "status": "in_progress",
                "start_date": "2026-05-15",
            }
        ],
        "pending_decisions": pending_decisions,
        "open_briefs": [],
        "agents": {
            "framework-orchestrator": {"status": "active", "file": ".opencode/agents/framework-orchestrator.md"},
            "framework-registry": {"status": "active", "file": ".opencode/agents/framework-registry.md"},
        },
    }


def _prepare_project(tmp_path: Path, *, include_pending_decision: bool = True) -> Path:
    factory_dir = tmp_path / ".factory"
    plugin_dir = tmp_path / ".opencode" / "plugins"
    schema_dir = tmp_path / "schemas" / "meta"
    factory_dir.mkdir(parents=True, exist_ok=True)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    schema_dir.mkdir(parents=True, exist_ok=True)
    (factory_dir / "framework-state.json").write_text(
        json.dumps(_sample_v1_state(include_pending_decision=include_pending_decision), indent=2) + "\n"
    )
    (plugin_dir / "fba-agent-observer.ts").write_text("export const marker = 'unchanged'\n")
    (schema_dir / "framework_state.v2.schema.json").write_text(V2_SCHEMA_PATH.read_text())
    (schema_dir / "decisions.schema.json").write_text(DECISIONS_SCHEMA_PATH.read_text())
    (schema_dir / "schema_catalog.schema.json").write_text(
        (REPO_ROOT / "schemas" / "meta" / "schema_catalog.schema.json").read_text()
    )
    return tmp_path


def _jsonl_rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_projection_v1_to_v2_is_valid(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    migrator = MetaWorkflowMigrator(project_dir)

    projection = migrator.project_v1_to_v2(migrator.load_v1_state())

    schema = json.loads(V2_SCHEMA_PATH.read_text())
    jsonschema.Draft7Validator(schema).validate(projection.v2_state)

    assert projection.v2_state["workflow_version"] == "meta_v2"
    assert projection.v2_state["active_milestone"]["id"] == "M18"
    assert projection.v2_state["active_milestone"]["status"] == "in_progress"
    assert projection.v2_state["pending_decisions"][0]["decision_id"].startswith("DEC-20260515-")
    assert projection.v2_state["pending_decisions"][0]["status"] == "pending"


def test_bootstrap_writes_v2_state_and_metadata(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    result = bootstrap_meta_workflow(project_dir)

    assert result.v2_state_path.exists()
    assert result.config_path.exists()
    assert result.schema_catalog_path.exists()
    assert result.migration_path.exists()
    assert result.decisions_path.exists()
    assert result.last_validation_path.exists()
    assert result.drift_report_path.exists()

    config = json.loads(result.config_path.read_text())
    v2_state = json.loads(result.v2_state_path.read_text())
    validation = json.loads(result.last_validation_path.read_text())
    schema = json.loads(V2_SCHEMA_PATH.read_text())

    jsonschema.Draft7Validator(schema).validate(v2_state)

    assert config["meta_workflow_version"] == "v1"
    assert v2_state["contract_name"] == "framework_state_v2"
    assert validation["schema_valid"] is True


def test_decisions_jsonl_lines_validate_against_schema(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    result = bootstrap_meta_workflow(project_dir)

    schema = json.loads(DECISIONS_SCHEMA_PATH.read_text())
    rows = _jsonl_rows(result.decisions_path)

    assert rows
    for row in rows:
        jsonschema.Draft7Validator(schema).validate(row)


def test_decisions_jsonl_is_not_json_array(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    result = bootstrap_meta_workflow(project_dir)

    content = result.decisions_path.read_text().strip()

    assert not content.startswith("[")
    assert all(isinstance(row, dict) for row in _jsonl_rows(result.decisions_path))


def test_no_pending_decisions_writes_empty_decisions_jsonl_and_empty_v2_refs(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path, include_pending_decision=False)
    result = bootstrap_meta_workflow(project_dir)

    v2_state = json.loads(result.v2_state_path.read_text())

    assert result.decisions_path.read_text() == ""
    assert v2_state["pending_decisions"] == []


def test_bootstrap_does_not_modify_v1_state_or_agent_observer_plugin(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    v1_path = project_dir / ".factory" / "framework-state.json"
    plugin_path = project_dir / ".opencode" / "plugins" / "fba-agent-observer.ts"
    v1_before = v1_path.read_text()
    plugin_before = plugin_path.read_text()

    bootstrap_meta_workflow(project_dir)

    assert v1_path.read_text() == v1_before
    assert plugin_path.read_text() == plugin_before


def test_drift_check_matches_active_milestone_and_decisions(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    result = bootstrap_meta_workflow(project_dir)

    drift_report = json.loads(result.drift_report_path.read_text())

    assert drift_report["status"] == "clean"
    assert drift_report["active_milestone_match"] is True
    assert drift_report["pending_decisions_projected"] is True
    assert drift_report["unmapped_pending_decisions"] == []


def test_bootstrap_result_reports_v1_authority(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    result = bootstrap_meta_workflow(project_dir)

    migration = json.loads(result.migration_path.read_text())

    assert migration["meta_workflow_version"] == "v1"
    assert migration["mode"] == "shadow_projection"
    assert migration["status"] == "projected"

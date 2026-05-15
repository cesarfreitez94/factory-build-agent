"""Tests for the V2 roadmap slice builder utility."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from fba.meta_roadmap_slice_builder import build_roadmap_slice, generate_roadmap_slice


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "meta" / "roadmap_slice.schema.json"
ROADMAP_TEXT = (REPO_ROOT / "ROADMAP.md").read_text()


def _prepare_project(tmp_path: Path) -> Path:
    factory_dir = tmp_path / ".factory"
    plugin_dir = tmp_path / ".opencode" / "plugins"
    factory_dir.mkdir(parents=True, exist_ok=True)
    plugin_dir.mkdir(parents=True, exist_ok=True)

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
        "objective": "Implement the Roadmap Slice Builder V2 utility",
        "scope": {
            "include": ["src/fba/meta_roadmap_slice_builder.py", "tests/test_meta_roadmap_slice_builder.py"],
            "exclude": [".factory/framework-state.json", ".opencode/plugins/fba-agent-observer.ts"],
        },
        "constraints": ["no_v1_runtime_changes"],
        "requested_outputs": ["src/fba/meta_roadmap_slice_builder.py", "tests/test_meta_roadmap_slice_builder.py"],
        "non_goals": ["modify_odoo_generator"],
        "urgency": "high",
        "requires_user_confirmation": False,
        "related_milestone": {"id": "M18", "status": "in_progress", "branch": "milestone/18.0-input-extension-layer"},
    }
    value.update(overrides)
    return value


def _framework_state_v2(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "contract_name": "framework_state_v2",
        "contract_version": "2.0",
        "state_id": "FWSTATE-20260515-001",
        "updated_at": "2026-05-15T13:00:00Z",
        "workflow_version": "meta_v2",
        "current_phase": "implementation",
        "active_intent_id": None,
        "active_plan_id": None,
        "active_task_id": None,
        "active_milestone": {
            "id": "M18",
            "status": "in_progress",
            "branch": "milestone/18.0-input-extension-layer",
            "name": "Input & Extension Layer",
        },
        "last_completed_step": None,
        "artifacts": [
            {
                "contract_name": "framework_state_v2",
                "contract_version": "2.0",
                "artifact_id": "FWSTATE-20260515-001",
                "path": ".factory/meta/framework_state.v2.json",
                "status": "valid",
                "version": 1,
            }
        ],
        "pending_decisions": [],
        "human_summary": "V2 shadow projection generated from the authoritative V1 framework state.",
    }
    value.update(overrides)
    return value


def _small_roadmap_text() -> str:
    return "\n".join(
        [
            "# Roadmap - Mini",
            "",
            "## Estado General",
            "",
            "| Milestone | Estado | Inicio |",
            "|-----------|--------|--------|",
            "| M1: Base | ✅ Completado | 2026-05-01 / 2026-05-01 |",
            "| M2: Alpha | ⏳ Planificado | Pendiente |",
            "| M3: Beta | 🔄 En progreso | Pendiente |",
            "| M4: Gamma | ⏳ Planificado | Pendiente |",
            "| M5: Delta | ⏳ Planificado | Pendiente |",
            "",
            "---",
            "",
            "### M3: Beta",
            "",
            "**Estado**: En progreso.",
            "",
            "**Branch sugerido**: `milestone/3.0-beta`",
            "",
            "**Alcance**: Example milestone for warning coverage.",
        ]
    )


def test_builds_valid_roadmap_slice_against_schema() -> None:
    roadmap_slice = build_roadmap_slice(_intent(), _framework_state_v2(), ROADMAP_TEXT, now="2026-05-15T14:02:00Z")

    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.Draft7Validator(schema).validate(roadmap_slice)

    assert roadmap_slice["contract_name"] == "roadmap_slice"
    assert roadmap_slice["contract_version"] == "2.0"
    assert roadmap_slice["slice_id"] == "RSLICE-20260515-001"
    assert roadmap_slice["intent_id"] == "INTENT-20260515-001"
    assert roadmap_slice["active_milestone"]["id"] == "M18"
    assert roadmap_slice["blocked_operations"] == ["execute_git_operation", "commit", "push", "open_pr", "merge_pr"]
    assert "request_git_operation" in roadmap_slice["allowed_operations"]


def test_emits_source_refs_with_line_ranges() -> None:
    roadmap_slice = build_roadmap_slice(_intent(), _framework_state_v2(), ROADMAP_TEXT, now="2026-05-15T14:02:00Z")

    assert roadmap_slice["source_refs"]
    assert all(ref["line_ranges"] for ref in roadmap_slice["source_refs"])
    assert all(range_item["end"] >= range_item["start"] for ref in roadmap_slice["source_refs"] for range_item in ref["line_ranges"])
    assert all((range_item["end"] - range_item["start"] + 1) <= 8 for ref in roadmap_slice["source_refs"] for range_item in ref["line_ranges"])


def test_does_not_pass_full_roadmap_downstream() -> None:
    roadmap_slice = build_roadmap_slice(_intent(), _framework_state_v2(), ROADMAP_TEXT, now="2026-05-15T14:02:00Z")
    total_lines = len(ROADMAP_TEXT.splitlines())
    selected_lines = sum(
        range_item["end"] - range_item["start"] + 1
        for ref in roadmap_slice["source_refs"]
        for range_item in ref["line_ranges"]
    )

    assert selected_lines < total_lines
    assert not any(range_item["start"] == 1 and range_item["end"] == total_lines for ref in roadmap_slice["source_refs"] for range_item in ref["line_ranges"])


def test_paused_milestone_requires_user_confirmation() -> None:
    roadmap_slice = build_roadmap_slice(
        _intent(),
        _framework_state_v2(active_milestone={"id": "M18", "status": "paused", "branch": "milestone/18.0-input-extension-layer", "name": "Input & Extension Layer"}),
        ROADMAP_TEXT,
        now="2026-05-15T14:02:00Z",
    )

    assert "milestone_paused" in roadmap_slice["risk_notes"]
    assert any(issue["status"] == "needs_user_confirmation" for issue in roadmap_slice["open_issues"])
    assert "requires_user_confirmation" in roadmap_slice["risk_notes"]


def test_never_emits_direct_git_operations() -> None:
    roadmap_slice = build_roadmap_slice(_intent(), _framework_state_v2(), ROADMAP_TEXT, now="2026-05-15T14:02:00Z")

    assert "commit" not in roadmap_slice["allowed_operations"]
    assert "push" not in roadmap_slice["allowed_operations"]
    assert "open_pr" not in roadmap_slice["allowed_operations"]
    assert "merge_pr" not in roadmap_slice["allowed_operations"]
    assert "execute_git_operation" not in roadmap_slice["allowed_operations"]
    assert "request_git_operation" in roadmap_slice["allowed_operations"]


def test_warns_when_more_than_three_milestones_are_relevant() -> None:
    roadmap_slice = build_roadmap_slice(_intent(), _framework_state_v2(active_milestone={"id": "M3", "status": "in_progress", "branch": "milestone/3.0-beta", "name": "Beta"}), _small_roadmap_text(), now="2026-05-15T14:02:00Z")

    assert len(roadmap_slice["relevant_milestones"]) == 4
    assert not any(issue["status"] == "needs_user_confirmation" for issue in roadmap_slice["open_issues"])
    assert "relevant_milestones_warning" in roadmap_slice["risk_notes"]


def test_generate_writes_only_v2_artifacts(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    v1_path = project_dir / ".factory" / "framework-state.json"
    plugin_path = project_dir / ".opencode" / "plugins" / "fba-agent-observer.ts"
    v1_before = v1_path.read_text()
    plugin_before = plugin_path.read_text()

    result = generate_roadmap_slice(project_dir, _intent(), _framework_state_v2(), ROADMAP_TEXT, now="2026-05-15T14:02:00Z")

    assert result.artifact_path.exists()
    assert result.validation_path is not None and result.validation_path.exists()
    assert v1_path.read_text() == v1_before
    assert plugin_path.read_text() == plugin_before

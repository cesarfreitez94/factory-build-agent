"""Tests for the V2 intent builder utility."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from fba.meta_intent_builder import build_intent, generate_intent


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "meta" / "intent.schema.json"


def _prepare_project(tmp_path: Path) -> Path:
    factory_dir = tmp_path / ".factory"
    plugin_dir = tmp_path / ".opencode" / "plugins"
    factory_dir.mkdir(parents=True, exist_ok=True)
    plugin_dir.mkdir(parents=True, exist_ok=True)

    (factory_dir / "framework-state.json").write_text('{"schema_version": "1.0", "marker": "unchanged"}\n')
    (plugin_dir / "fba-agent-observer.ts").write_text("export const marker = 'unchanged'\n")
    return tmp_path


def _framework_state(**overrides: object) -> dict[str, object]:
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
        "artifacts": [],
        "pending_decisions": [],
        "human_summary": "V2 shadow projection generated from the authoritative V1 framework state.",
    }
    value.update(overrides)
    return value


def test_builds_valid_intent_against_schema() -> None:
    intent = build_intent(
        "Implementa la utility pura Intent Builder V2.\n\nNo modificar agentes, comandos, generador Odoo, schemas, runtime V1 ni fba-agent-observer.",
        _framework_state(),
        now="2026-05-15T14:00:00Z",
    )

    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.Draft7Validator(schema).validate(intent)

    assert intent["contract_name"] == "intent"
    assert intent["contract_version"] == "2.0"
    assert intent["intent_id"] == "INTENT-20260515-001"
    assert intent["source"] == "user"
    assert intent["requires_user_confirmation"] is False
    assert intent["related_milestone"]["id"] == "M18"


def test_design_only_does_not_require_confirmation() -> None:
    intent = build_intent(
        "Diseña la utility de intents para el meta-workflow.",
        _framework_state(current_phase="design"),
        now="2026-05-15T14:00:00Z",
    )

    assert intent["requires_user_confirmation"] is False
    assert intent["constraints"][0] == "dominant_phase:design"


def test_design_and_implementation_requires_confirmation() -> None:
    intent = build_intent(
        "Diseña e implementa la utility de intents para el meta-workflow.",
        _framework_state(current_phase="implementation"),
        now="2026-05-15T14:00:00Z",
    )

    assert intent["requires_user_confirmation"] is True
    assert "requires_user_confirmation" in intent["constraints"]


def test_implementation_and_git_requires_confirmation() -> None:
    intent = build_intent(
        "Implementa la utility y prepara commit y pull request.",
        _framework_state(current_phase="implementation"),
        now="2026-05-15T14:00:00Z",
    )

    assert intent["requires_user_confirmation"] is True
    assert intent["constraints"][0] == "dominant_phase:implementation"


def test_multiple_milestones_require_confirmation() -> None:
    intent = build_intent(
        "Trabaja sobre M18 y M19 para el builder de intents.",
        _framework_state(),
        [
            {"related_milestone": {"id": "M19", "status": "planned"}},
        ],
        now="2026-05-15T14:00:00Z",
    )

    assert intent["requires_user_confirmation"] is True
    assert intent["related_milestone"]["id"] == "M18"


def test_detects_exclusion_of_agents_commands_and_generator() -> None:
    intent = build_intent(
        "Implementa la utility sin modificar agentes, comandos ni el generador Odoo.",
        _framework_state(),
        now="2026-05-15T14:00:00Z",
    )

    assert ".opencode/agents/**" in intent["scope"]["exclude"]
    assert ".opencode/commands/**" in intent["scope"]["exclude"]
    assert "src/fba/generator/**" in intent["scope"]["exclude"]
    assert all("agents" not in item for item in intent["requested_outputs"])
    assert all("commands" not in item for item in intent["requested_outputs"])
    assert all("generator" not in item for item in intent["requested_outputs"])


def test_generate_writes_only_v2_artifacts(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    v1_path = project_dir / ".factory" / "framework-state.json"
    plugin_path = project_dir / ".opencode" / "plugins" / "fba-agent-observer.ts"
    v1_before = v1_path.read_text()
    plugin_before = plugin_path.read_text()

    result = generate_intent(
        project_dir,
        "Implementa la utility pura Intent Builder V2.",
        _framework_state(),
        now="2026-05-15T14:00:00Z",
    )

    assert result.artifact_path.exists()
    assert result.validation_path is not None and result.validation_path.exists()
    assert result.artifact_path == project_dir / ".factory/meta/artifacts/intents/INTENT-20260515-001.json"
    assert v1_path.read_text() == v1_before
    assert plugin_path.read_text() == plugin_before

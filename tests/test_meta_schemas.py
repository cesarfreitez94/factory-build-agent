"""Validation tests for the meta-workflow V2 schemas."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator, ValidationError


SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas" / "meta"


def _load_schema(name: str):
    return json.loads((SCHEMAS_DIR / name).read_text())


@pytest.mark.parametrize(
    "schema_name",
    [
        "schema_catalog.schema.json",
        "decisions.schema.json",
        "framework_state.v2.schema.json",
        "intent.schema.json",
        "policy_constraints.schema.json",
        "roadmap_slice.schema.json",
        "plan.schema.json",
        "task_packet.schema.json",
        "context_bundle.schema.json",
        "implementation_report.schema.json",
        "test_report.schema.json",
        "review_report.schema.json",
        "git_operation.schema.json",
    ],
)
def test_schema_is_valid_json_schema(schema_name):
    schema = _load_schema(schema_name)
    Draft7Validator.check_schema(schema)


def test_schema_catalog_valid():
    schema = _load_schema("schema_catalog.schema.json")
    instance = {
        "contract_name": "schema_catalog",
        "contract_version": "2.0",
        "catalog_id": "SCAT-20260515-001",
        "updated_at": "2026-05-15T14:00:00Z",
        "contracts": [
            {
                "contract_name": "intent",
                "contract_version": "2.0",
                "path": "schemas/meta/intent.schema.json",
                "status": "active"
            }
        ],
        "global_policies": [
            {"policy_id": "CONTRIBUTING", "path": "CONTRIBUTING.md", "mode": "reference"},
            {"policy_id": "CHANGELOG", "path": "CHANGELOG.md", "mode": "reference"}
        ],
        "compatibility_matrix": [
            {"from": "intent@2.0", "to": "policy_constraints@2.0", "status": "compatible"}
        ]
    }
    Draft7Validator(schema).validate(instance)


def test_decision_pending_and_resolved_valid():
    schema = _load_schema("decisions.schema.json")
    pending = {
        "contract_name": "decisions",
        "contract_version": "2.0",
        "decision_id": "DEC-20260515-001",
        "created_at": "2026-05-15T14:10:00Z",
        "decision_type": "user_confirmation",
        "status": "pending",
        "question": "Authorize PR to main?",
        "options": ["approve", "reject"],
        "selected_option": None,
        "required_by": ["git_operation"]
    }
    resolved = json.loads(json.dumps(pending))
    resolved["status"] = "resolved"
    resolved["selected_option"] = "approve"
    resolved["resolved_at"] = "2026-05-15T14:11:00Z"
    Draft7Validator(schema).validate(pending)
    Draft7Validator(schema).validate(resolved)


def test_framework_state_idle_valid():
    schema = _load_schema("framework_state.v2.schema.json")
    instance = {
        "contract_name": "framework_state_v2",
        "contract_version": "2.0",
        "state_id": "FWSTATE-20260515-001",
        "updated_at": "2026-05-15T14:00:00Z",
        "workflow_version": "meta_v2",
        "current_phase": "idle",
        "active_intent_id": None,
        "active_plan_id": None,
        "active_task_id": None,
        "active_milestone": None,
        "last_completed_step": None,
        "artifacts": [],
        "pending_decisions": []
    }
    Draft7Validator(schema).validate(instance)


def test_intent_valid():
    schema = _load_schema("intent.schema.json")
    instance = {
        "contract_name": "intent",
        "contract_version": "2.0",
        "intent_id": "INTENT-20260515-001",
        "created_at": "2026-05-15T14:00:00Z",
        "source": "user",
        "objective": "Design the V2 meta-workflow schemas",
        "scope": {"include": ["schemas"], "exclude": ["agents", "prompts"]},
        "constraints": ["contracts_only"],
        "requested_outputs": ["schema_map", "dependencies"],
        "human_summary": "Design only"
    }
    Draft7Validator(schema).validate(instance)


def test_policy_constraints_valid():
    schema = _load_schema("policy_constraints.schema.json")
    instance = {
        "contract_name": "policy_constraints",
        "contract_version": "2.0",
        "constraints_id": "POLICY-20260515-001",
        "intent_id": "INTENT-20260515-001",
        "created_at": "2026-05-15T14:01:00Z",
        "policy_refs": ["CONTRIBUTING", "CHANGELOG"],
        "allowed_operations": ["design_schema"],
        "blocked_operations": ["create_agent", "create_prompt"],
        "required_checks": ["issue_required_before_code", "no_direct_commit_to_main"],
        "requires_user_confirmation": False
    }
    Draft7Validator(schema).validate(instance)


def test_roadmap_slice_valid():
    schema = _load_schema("roadmap_slice.schema.json")
    instance = {
        "contract_name": "roadmap_slice",
        "contract_version": "2.0",
        "slice_id": "RSLICE-20260515-001",
        "intent_id": "INTENT-20260515-001",
        "created_at": "2026-05-15T14:02:00Z",
        "active_milestone": {"id": "M18", "status": "in_progress", "branch": "milestone/18.0-input-extension-layer"},
        "relevant_milestones": [{"id": "M18", "status": "in_progress"}],
        "policy_refs": ["CONTRIBUTING", "CHANGELOG"],
        "allowed_operations": ["design_schema"],
        "blocked_operations": ["create_agent", "modify_odoo_generator"],
        "source_refs": [
            {
                "path": "ROADMAP.md",
                "section": "M18",
                "line_ranges": [{"start": 1, "end": 10}]
            }
        ]
    }
    Draft7Validator(schema).validate(instance)


def test_plan_valid():
    schema = _load_schema("plan.schema.json")
    instance = {
        "contract_name": "plan",
        "contract_version": "2.0",
        "plan_id": "PLAN-20260515-001",
        "intent_id": "INTENT-20260515-001",
        "roadmap_slice_id": "RSLICE-20260515-001",
        "created_at": "2026-05-15T14:03:00Z",
        "goal": "Design contracts",
        "tasks": [
            {"task_id": "TASK-20260515-001", "title": "Define schemas", "type": "schema_design", "depends_on": []}
        ],
        "acceptance_criteria": ["All requested contracts exist"],
        "constraints": ["contracts_only"],
        "requires_user_confirmation": False
    }
    Draft7Validator(schema).validate(instance)


def test_task_packet_valid():
    schema = _load_schema("task_packet.schema.json")
    instance = {
        "contract_name": "task_packet",
        "contract_version": "2.0",
        "packet_id": "TPACKET-20260515-001",
        "plan_id": "PLAN-20260515-001",
        "task_id": "TASK-20260515-001",
        "created_at": "2026-05-15T14:04:00Z",
        "objective": "Create the schema contracts",
        "allowed_files": ["schemas/meta/*.json"],
        "forbidden_files": [".opencode/agents/*", "src/fba/generator/*"],
        "allowed_operations": ["read", "create_schema", "validate_schema"],
        "acceptance_criteria": ["JSON Schema validates"],
        "inputs_required": ["intent", "policy_constraints", "roadmap_slice"],
        "policy_refs": ["CONTRIBUTING"]
    }
    Draft7Validator(schema).validate(instance)


def test_context_bundle_valid():
    schema = _load_schema("context_bundle.schema.json")
    instance = {
        "contract_name": "context_bundle",
        "contract_version": "2.0",
        "bundle_id": "CTX-20260515-001",
        "packet_id": "TPACKET-20260515-001",
        "created_at": "2026-05-15T14:05:00Z",
        "context_items": [
            {
                "type": "schema",
                "path": "schemas/meta/intent.schema.json",
                "line_ranges": [{"start": 1, "end": 20}],
                "reason": "Reference contract"
            }
        ],
        "excluded_context": [
            {"path": "src/fba/generator", "reason": "Out of scope"}
        ],
        "policy_refs": ["CONTRIBUTING"],
        "integrity": {"source_count": 1, "truncated": False}
    }
    Draft7Validator(schema).validate(instance)


def test_implementation_report_valid():
    schema = _load_schema("implementation_report.schema.json")
    instance = {
        "contract_name": "implementation_report",
        "contract_version": "2.0",
        "report_id": "IMPL-20260515-001",
        "packet_id": "TPACKET-20260515-001",
        "created_at": "2026-05-15T14:06:00Z",
        "status": "completed",
        "changed_files": [{"path": "schemas/meta/intent.schema.json", "change_type": "created"}],
        "created_artifacts": [{"contract_name": "intent", "contract_version": "2.0", "artifact_id": "INTENT-20260515-001", "path": "schemas/meta/intent.schema.json"}],
        "acceptance_status": "passed",
        "blockers": [],
        "commands_run": [{"command": "python -m json.tool", "exit_code": 0}]
    }
    Draft7Validator(schema).validate(instance)


def test_test_report_valid():
    schema = _load_schema("test_report.schema.json")
    instance = {
        "contract_name": "test_report",
        "contract_version": "2.0",
        "report_id": "TEST-20260515-001",
        "implementation_report_id": "IMPL-20260515-001",
        "created_at": "2026-05-15T14:07:00Z",
        "status": "passed",
        "test_runs": [{"command": "pytest", "status": "passed", "exit_code": 0, "kind": "pytest"}],
        "failures": [],
        "coverage": {"required": True, "satisfied": True}
    }
    Draft7Validator(schema).validate(instance)


def test_review_report_valid():
    schema = _load_schema("review_report.schema.json")
    instance = {
        "contract_name": "review_report",
        "contract_version": "2.0",
        "report_id": "REV-20260515-001",
        "implementation_report_id": "IMPL-20260515-001",
        "test_report_id": "TEST-20260515-001",
        "created_at": "2026-05-15T14:08:00Z",
        "status": "approved",
        "findings": [],
        "policy_compliance": [{"policy_ref": "CONTRIBUTING", "status": "passed"}],
        "recommendation": "proceed_to_git"
    }
    Draft7Validator(schema).validate(instance)


def test_git_operation_requested_valid():
    schema = _load_schema("git_operation.schema.json")
    instance = {
        "contract_name": "git_operation",
        "contract_version": "2.0",
        "operation_id": "GIT-20260515-001",
        "created_at": "2026-05-15T14:09:00Z",
        "produced_by": "review_gate",
        "executed_by": "git_operator",
        "operation_type": "open_pr",
        "status": "requested",
        "source_refs": {"review_report_id": "REV-20260515-001"},
        "branch": {"current": "feat/18.1-contracts", "base": "milestone/18.0-input-extension-layer"},
        "policy_checks": [{"policy_ref": "CONTRIBUTING", "status": "passed"}]
    }
    Draft7Validator(schema).validate(instance)


def test_git_operation_merge_pr_requires_confirmation():
    schema = _load_schema("git_operation.schema.json")
    instance = {
        "contract_name": "git_operation",
        "contract_version": "2.0",
        "operation_id": "GIT-20260515-002",
        "created_at": "2026-05-15T14:10:00Z",
        "produced_by": "orchestrator",
        "executed_by": "git_operator",
        "operation_type": "merge_pr",
        "status": "requested",
        "source_refs": {"review_report_id": "REV-20260515-001"},
        "branch": {"current": "milestone/18.0-input-extension-layer", "base": "main", "target": "main"},
        "policy_checks": [{"policy_ref": "CONTRIBUTING", "status": "passed"}],
        "requires_user_confirmation": True
    }
    Draft7Validator(schema).validate(instance)


def test_context_bundle_requires_line_ranges():
    schema = _load_schema("context_bundle.schema.json")
    instance = {
        "contract_name": "context_bundle",
        "contract_version": "2.0",
        "bundle_id": "CTX-20260515-002",
        "packet_id": "TPACKET-20260515-001",
        "created_at": "2026-05-15T14:05:00Z",
        "context_items": [
            {
                "type": "schema",
                "path": "schemas/meta/intent.schema.json",
                "reason": "Reference contract"
            }
        ],
        "excluded_context": [],
        "policy_refs": ["CONTRIBUTING"],
        "integrity": {"source_count": 1, "truncated": False}
    }
    with pytest.raises(ValidationError):
        Draft7Validator(schema).validate(instance)


def test_decision_resolved_requires_resolution_timestamp():
    schema = _load_schema("decisions.schema.json")
    instance = {
        "contract_name": "decisions",
        "contract_version": "2.0",
        "decision_id": "DEC-20260515-002",
        "created_at": "2026-05-15T14:10:00Z",
        "decision_type": "user_confirmation",
        "status": "resolved",
        "question": "Authorize PR?",
        "options": ["approve", "reject"],
        "selected_option": "approve",
        "required_by": ["git_operation"]
    }
    with pytest.raises(ValidationError):
        Draft7Validator(schema).validate(instance)

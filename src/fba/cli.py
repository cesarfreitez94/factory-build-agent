import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from fba import __version__
from fba.contract_engine import ContractEngine, ContractError
from fba.dependency_analyzer import DependencyAnalyzer, DependencyError
from fba.diff_engine import DiffEngine, DiffError
from fba.gate import GateError
from fba.stable_ids import StableIdManager, StableIdError
from fba.schema_manager import SchemaManager
from fba.state import StateManager, _atomic_write

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
SCHEMAS_DIR = Path(__file__).resolve().parent.parent.parent / "schemas"

PROJECT_DIR_OPTION = click.option(
    "--project-dir", "-d", default=None,
    help="Target project directory (default: current directory)"
)


def _resolve_project_dir(project_dir: str | None) -> Path:
    target = Path(project_dir).resolve() if project_dir else Path.cwd()
    if not (target / ".factory").exists():
        click.echo(f"Error: No .factory/ found in {target}. Run 'fba init' first.")
        raise SystemExit(1)
    return target


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Factory Build Agent - Multi-agent framework for Odoo v18 module development."""


@main.command()
@click.option("--project-dir", "-d", default=None, help="Target project directory (default: current directory)")
def init(project_dir: str | None) -> None:
    """Initialize a project with Factory Build Agent structure.

    Creates .factory/, .opencode/, and .github/ directories with
    all necessary templates, schemas, and agent configurations.
    """
    target = Path(project_dir).resolve() if project_dir else Path.cwd()

    click.echo(f"Initializing Factory Build Agent in {target}...")

    if (target / ".factory").exists():
        click.echo("⚠  .factory/ already exists. Run fba init in a project without it.")
        raise SystemExit(1)

    _copy_templates(target)
    _copy_schemas(target)
    _copy_registry(target)
    _init_factory_state(target)
    _init_events_log(target)

    click.echo(f"✅ Factory Build Agent initialized in {target}")
    click.echo("")
    click.echo("Next steps:")
    click.echo("  1. Open the project with OpenCode: opencode .")
    click.echo("  2. Start eliciting requirements: /fba:elicit \"your idea\"")


@main.command()
@click.option("--project-dir", "-d", default=None, help="Target project directory (default: current directory)")
def update(project_dir: str | None) -> None:
    """Update project templates without touching state or artifacts.

    Overwrites .opencode/, .github/workflows/, and AGENTS.md with
    the latest templates. Removes known obsolete files.
    Does NOT modify .factory/state.json, .factory/events.jsonl,
    or any generated artifacts.
    """
    target = _resolve_project_dir(project_dir)

    click.echo(f"Updating Factory Build Agent templates in {target}...")

    _copy_templates(target)
    _copy_registry(target)
    _cleanup_obsolete(target)

    click.echo(f"✅ Factory Build Agent templates updated in {target}")


def _copy_templates(target: Path) -> None:
    templates_src = TEMPLATES_DIR
    if not templates_src.exists():
        click.echo(f"⚠  Templates directory not found: {templates_src}")
        return

    shutil.copytree(
        templates_src, target,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(".factory", ".factory/*"),
    )


def _cleanup_obsolete(target: Path) -> None:
    """Remove known obsolete files from project after template update."""
    agents_dir = target / ".opencode" / "agents"
    if agents_dir.is_dir():
        for yaml_file in agents_dir.glob("*.yaml"):
            yaml_file.unlink()
            click.echo(f"  🗑  Removed obsolete: agents/{yaml_file.name}")


def _copy_schemas(target: Path) -> None:
    schemas_src = SCHEMAS_DIR
    if not schemas_src.exists():
        return

    factory_schemas = target / ".factory" / "schemas"
    factory_schemas.mkdir(parents=True, exist_ok=True)

    for schema_file in schemas_src.glob("*.schema.json"):
        dest = factory_schemas / schema_file.name
        if not dest.exists():
            shutil.copy2(schema_file, dest)


def _copy_registry(target: Path) -> None:
    registry_src = TEMPLATES_DIR / ".factory" / "module_registry.json"
    if not registry_src.exists():
        click.echo("Warning: Module registry not found in templates. All models will be treated as new.")
        return
    factory_dir = target / ".factory"
    factory_dir.mkdir(parents=True, exist_ok=True)
    dest = factory_dir / "module_registry.json"
    _atomic_write(dest, registry_src.read_text())


def _init_factory_state(target: Path) -> None:
    factory_dir = target / ".factory"
    factory_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "project": target.name,
        "framework_version": __version__,
        "init_at": datetime.now(timezone.utc).isoformat(),
        "current_phase": "init",
        "methodology": "BABOK",
        "phases": {
            "init": {"status": "in_progress", "agent": "orchestrator"},
            "elicitation": {"status": "pending", "agent": "elicitador"},
            "documentation": {"status": "pending", "agent": "documentador"},
            "planning": {"status": "pending", "agent": "planificador"},
            "tasks": {"status": "pending", "agent": "planificador"},
            "construction": {"status": "pending", "agent": "code-generator"},
            "testing": {"status": "pending", "agent": "tester_qa"},
            "review": {"status": "pending", "agent": "revisor_codigo"},
            "ci_cd": {"status": "pending", "agent": "cicd_manager"},
        },
        "valid_transitions": {
            "init": ["elicitation"],
            "elicitation": ["documentation"],
            "documentation": ["planning"],
            "planning": ["tasks"],
            "tasks": ["construction"],
            "construction": ["testing"],
            "testing": ["review"],
            "review": ["ci_cd"],
            "ci_cd": ["complete"],
        },
        "gates": {
            "elicitation": {
                "description": "Validates that BABOK elicitation produced complete requirements",
                "owner_agent": "elicitador",
                "rules": [
                    {
                        "type": "artifact_exists",
                        "rule_name": "elicitation_context_exists",
                        "path": ".factory/context/elicitation.json",
                    },
                    {
                        "type": "content_check",
                        "rule_name": "elicitation_content_minimum",
                        "path": ".factory/context/elicitation.json",
                        "checks": {
                            "min_stakeholders": 1,
                            "min_functional_requirements": 1,
                            "min_non_functional_requirements": 1,
                            "min_acceptance_criteria": 1,
                        },
                    },
                ],
            },
            "documentation": {
                "description": "Validates that PRD is complete and schema-valid",
                "owner_agent": "documentador",
                "rules": [
                    {
                        "type": "artifact_exists",
                        "rule_name": "prd_json_exists",
                        "path": ".factory/prd.json",
                    },
                    {
                        "type": "artifact_exists",
                        "rule_name": "prd_md_exists",
                        "path": ".factory/prd.md",
                    },
                    {
                        "type": "schema",
                        "rule_name": "prd_schema_valid",
                        "schema": "prd.schema.json",
                        "path": ".factory/prd.json",
                    },
                    {
                        "type": "semantic_check",
                        "rule_name": "prd_semantic_relevance",
                        "source_path": ".factory/context/elicitation.json",
                        "target_path": ".factory/prd.json",
                        "dimensions": [
                            "domain_consistency",
                            "objective_alignment",
                            "terminology_match",
                            "stakeholder_relevance",
                            "requirement_relevance",
                        ],
                    },
                ],
            },
            "planning": {
                "description": "Validates SDD, traceability, and technical plan",
                "owner_agent": "planificador",
                "rules": [
                    {
                        "type": "artifact_exists",
                        "rule_name": "sdd_json_exists",
                        "path": ".factory/sdd.json",
                    },
                    {
                        "type": "artifact_exists",
                        "rule_name": "plan_md_exists",
                        "path": ".factory/plan.md",
                    },
                    {
                        "type": "schema",
                        "rule_name": "sdd_schema_valid",
                        "schema": "sdd.schema.json",
                        "path": ".factory/sdd.json",
                    },
                    {
                        "type": "traceability",
                        "rule_name": "prd_sdd_traceability",
                        "prd_path": ".factory/prd.json",
                        "sdd_path": ".factory/sdd.json",
                    },
                    {
                        "type": "semantic_check",
                        "rule_name": "sdd_semantic_relevance",
                        "source_path": ".factory/context/elicitation.json",
                        "target_path": ".factory/sdd.json",
                        "dimensions": [
                            "domain_consistency",
                            "objective_alignment",
                            "terminology_match",
                            "stakeholder_relevance",
                            "requirement_relevance",
                        ],
                    },
                ],
            },
            "tasks": {
                "description": "Validates task index and individual task files",
                "owner_agent": "planificador",
                "rules": [
                    {
                        "type": "artifact_exists",
                        "rule_name": "task_index_exists",
                        "path": ".factory/tasks/index.json",
                    },
                    {
                        "type": "schema",
                        "rule_name": "task_index_schema_valid",
                        "schema": "task_index.schema.json",
                        "path": ".factory/tasks/index.json",
                    },
                    {
                        "type": "content_check",
                        "rule_name": "task_index_content_minimum",
                        "path": ".factory/tasks/index.json",
                        "checks": {"min_tasks": 1},
                    },
                    {
                        "type": "task_files_exist",
                        "rule_name": "all_task_files_exist",
                        "index_path": ".factory/tasks/index.json",
                    },
                ],
            },
            "schema": {
                "description": "Validates schema.json SSOT before code generation",
                "owner_agent": "code-generator",
                "rules": [
                    {
                        "type": "artifact_exists",
                        "rule_name": "schema_json_exists",
                        "path": ".factory/schema.json",
                    },
                    {
                        "type": "schema",
                        "rule_name": "schema_json_valid",
                        "schema": "schema.schema.json",
                        "path": ".factory/schema.json",
                    },
                    {
                        "type": "content_check",
                        "rule_name": "schema_has_models",
                        "path": ".factory/schema.json",
                        "checks": {"min_models": 1},
                    },
                ],
            },
            "construction": {
                "description": "Validates generated Odoo module structure matches schema.json",
                "owner_agent": "code-generator",
                "rules": [
                    {
                        "type": "artifact_exists",
                        "rule_name": "schema_json_exists_for_construction",
                        "path": ".factory/schema.json",
                    },
                    {
                        "type": "content_check",
                        "rule_name": "construction_min_tasks_built",
                        "path": ".factory/state.json",
                        "checks": {},
                    },
                    {
                        "type": "view_coverage",
                        "rule_name": "construction_view_coverage",
                        "path": ".factory/schema.json",
                        "require_form": True,
                        "require_list": True,
                    },
                    {
                        "type": "view_field_check",
                        "rule_name": "construction_view_fields",
                        "path": ".factory/schema.json",
                    },
                    {
                        "type": "acl_coverage",
                        "rule_name": "construction_acl_coverage",
                        "path": ".factory/schema.json",
                    },
                ],
            },
            "testing": {
                "description": "Validates that Odoo tests were generated and a test report exists",
                "owner_agent": "tester_qa",
                "rules": [
                    {
                        "type": "artifact_exists",
                        "rule_name": "test_report_json_exists",
                        "path": ".factory/test_report.json",
                    },
                    {
                        "type": "artifact_exists",
                        "rule_name": "test_report_md_exists",
                        "path": ".factory/test_report.md",
                    },
                ],
            },
            "review": {
                "description": "Validates that code review completed with no critical issues",
                "owner_agent": "revisor_codigo",
                "rules": [
                    {
                        "type": "artifact_exists",
                        "rule_name": "review_report_json_exists",
                        "path": ".factory/review_report.json",
                    },
                    {
                        "type": "artifact_exists",
                        "rule_name": "review_report_md_exists",
                        "path": ".factory/review_report.md",
                    },
                ],
            },
            "ci_cd": {
                "description": "Validates CI/CD workflow exists and project is ready for release",
                "owner_agent": "cicd_manager",
                "rules": [
                    {
                        "type": "artifact_exists",
                        "rule_name": "ci_workflow_exists",
                        "path": ".github/workflows/factory-ci.yml",
                    },
                    {
                        "type": "artifact_exists",
                        "rule_name": "ship_report_json_exists",
                        "path": ".factory/ship_report.json",
                    },
                    {
                        "type": "artifact_exists",
                        "rule_name": "ship_report_md_exists",
                        "path": ".factory/ship_report.md",
                    },
                ],
            },
        },
        "artifacts": {},
        "context": {},
    }

    state_path = factory_dir / "state.json"
    _atomic_write(state_path, json.dumps(state, indent=2, ensure_ascii=False))


def _init_events_log(target: Path) -> None:
    factory_dir = target / ".factory"
    events_path = factory_dir / "events.jsonl"

    init_event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": "init",
        "agent": "fba_cli",
        "framework_version": __version__,
        "project": target.name,
    }

    events_path.write_text(json.dumps(init_event, ensure_ascii=False) + "\n")


@main.command()
@PROJECT_DIR_OPTION
def status(project_dir: str | None) -> None:
    """Show the current state of the Factory Build Agent project."""
    target = _resolve_project_dir(project_dir)
    state_mgr = StateManager(target)
    state = state_mgr.load()

    click.echo(f"Project: {state['project']}")
    click.echo(f"Version: {state.get('framework_version', 'unknown')}")
    click.echo(f"Methodology: {state['methodology']}")
    click.echo(f"Current phase: {state['current_phase']}")
    click.echo("")

    click.echo("Phases:")
    for phase_name, phase_info in state.get("phases", {}).items():
        symbol = {
            "pending": "⬜",
            "in_progress": "🔄",
            "complete": "✅",
            "failed": "❌",
        }.get(phase_info.get("status", "pending"), "⬜")
        click.echo(f"  {symbol} {phase_name}: {phase_info['status']}")

    click.echo("")
    click.echo("Artifacts:")
    artifacts = state.get("artifacts", {})
    if artifacts:
        for name, info in artifacts.items():
            click.echo(f"  📄 {name}: {info['status']} (v{info.get('version', 1)})")
    else:
        click.echo("  (none)")


@main.command()
@click.argument("phase")
@click.option("--force", is_flag=True, help="Skip gate validation (force transition)")
@PROJECT_DIR_OPTION
def transition(phase: str, force: bool, project_dir: str | None) -> None:
    """Transition the project to a new development phase.

    By default, validates gates for the current phase before allowing
    the transition. Use --force to bypass gate validation.
    """
    target = _resolve_project_dir(project_dir)
    state_mgr = StateManager(target)

    try:
        state = state_mgr.transition_to(phase, skip_gates=force)
        click.echo(f"Transitioned to '{phase}'")
        if force:
            click.echo("⚠️  Gate validation was skipped (--force)")
    except GateError as e:
        click.echo(f"❌ Gate '{e.gate_result.phase}' failed:")
        for r in e.gate_result.failures:
            click.echo(f"   - {r.message}")
        click.echo("")
        click.echo("Use 'fba gate' to diagnose or '--force' to skip validation.")
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}")
        raise SystemExit(1)


@main.command()
@click.argument("event_type")
@click.option("--data", default=None, help="JSON string with event data")
@PROJECT_DIR_OPTION
def record(event_type: str, data: str | None, project_dir: str | None) -> None:
    """Record an event in the append-only event log."""
    target = _resolve_project_dir(project_dir)
    state_mgr = StateManager(target)

    parsed_data = None
    if data:
        parsed_data = json.loads(data)

    state_mgr.record_event(event_type, parsed_data)
    click.echo(f"Event '{event_type}' recorded.")


@main.command()
@click.argument("phase", required=False)
@click.option("--all", "all_gates", is_flag=True, help="Check all defined gates")
@PROJECT_DIR_OPTION
def gate(phase: str | None, all_gates: bool, project_dir: str | None) -> None:
    """Check validation gates for the current or a specific phase.

    Runs gate validation rules and reports pass/fail for each rule.
    Exit code is non-zero if any gate fails.
    """
    target = _resolve_project_dir(project_dir)
    from fba.gate import GateRunner

    runner = GateRunner(target)

    if all_gates:
        results = runner.check_all()
    elif phase:
        results = {phase: runner.check_phase(phase)}
    else:
        current = runner._state.get("current_phase", "init")
        results = {current: runner.check_current_phase()}

    all_passed = True
    for phase_name, result in results.items():
        symbol = "✅" if result.passed else "❌"
        click.echo(f"{symbol} Gate: {phase_name}")
        click.echo(f"   {result.description}")

        if not result.results:
            click.echo("   (no rules defined)")

        for r in result.results:
            if r.requires_agent:
                rs = "⏳"
            else:
                rs = "✅" if r.passed else "❌"
            click.echo(f"   {rs} {r.rule}: {r.message}")

        if result.failures:
            click.echo(f"   Owner agent: {result.owner_agent}")
            click.echo(f"   {result.error_count} failure(s)")
            all_passed = False

        if result.pending_agent_checks:
            click.echo(f"   ⏳ {len(result.pending_agent_checks)} pending agent evaluation(s)")
        click.echo("")

    if not all_passed:
        raise SystemExit(1)


@main.command()
@click.argument("artifact", required=False)
@PROJECT_DIR_OPTION
@click.option("--contract", "contract_type", default=None, help="Validate against artifact contract (prd, sdd, schema) instead of JSON schema")
def validate(artifact: str | None, project_dir: str | None, contract_type: str | None) -> None:
    """Validate project artifacts against their JSON schemas or contracts.

    If no artifact is specified, validates all artifacts found in state.json.
    Use --contract to validate business rules (invariants, ownership, mutations)
    instead of structural JSON schema validation.
    """
    if contract_type:
        _validate_contract(contract_type, project_dir)
        return

    target = _resolve_project_dir(project_dir)

    schemas_available = _list_schemas(target)
    if not schemas_available:
        click.echo("No schemas found for validation.")
        return

    artifacts_to_validate = []
    if artifact:
        schema_name = f"{artifact}.schema.json"
        if schema_name not in schemas_available:
            click.echo(f"No schema found for artifact '{artifact}'.")
            click.echo("Available schemas: " + ", ".join(
                s.replace(".schema.json", "") for s in schemas_available
            ))
            raise SystemExit(1)
        artifacts_to_validate = [artifact]
    else:
        artifacts_to_validate = [
            s.replace(".schema.json", "") for s in schemas_available
        ]

    import jsonschema

    all_valid = True
    for art_name in artifacts_to_validate:
        art_path = target / ".factory" / f"{art_name}.json"
        if not art_path.exists():
            click.echo(f"Skipping '{art_name}': artifact file not found ({art_path})")
            continue

        schema_path = _find_schema(target, f"{art_name}.schema.json")
        if not schema_path:
            click.echo(f"Skipping '{art_name}': schema not found")
            continue

        try:
            artifact_data = json.loads(art_path.read_text())
            schema = json.loads(schema_path.read_text())
            jsonschema.validate(artifact_data, schema)
            click.echo(f"✅ {art_name}: valid")

            if art_name == "sdd":
                if not _check_traceability(target, artifact_data):
                    all_valid = False

        except jsonschema.ValidationError as e:
            click.echo(f"❌ {art_name}: validation failed - {e.message}")
            all_valid = False
        except json.JSONDecodeError as e:
            click.echo(f"❌ {art_name}: invalid JSON - {e}")
            all_valid = False

    if not all_valid:
        raise SystemExit(1)


def _validate_contract(contract_type: str, project_dir: str | None) -> None:
    """Validate an artifact against its business contract."""
    target = _resolve_project_dir(project_dir)

    art_path = target / ".factory" / f"{contract_type}.json"
    if not art_path.exists():
        click.echo(f"Error: Artifact file not found: {art_path}")
        raise SystemExit(1)

    try:
        artifact_data = json.loads(art_path.read_text())
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON in {art_path}: {e}")
        raise SystemExit(1)

    engine = ContractEngine()

    try:
        violations = engine.validate_invariants(contract_type, artifact_data)
    except ContractError as e:
        click.echo(f"Error: {e}")
        raise SystemExit(1)

    if not violations:
        click.echo(f"✅ Contract '{contract_type}': all invariants pass")
        return

    click.echo(f"❌ Contract '{contract_type}': {len(violations)} violation(s) found")
    for v in violations:
        click.echo(f"  - [{v['id']}] {v['description']}")
        click.echo(f"    Field: {v['field']} — {v['detail']}")
    raise SystemExit(1)


_schema_group = click.group("schema")(lambda: None)
_schema_group.help = "Schema assembly and validation commands (SSOT)."


@_schema_group.command("assemble")
@PROJECT_DIR_OPTION
@click.option("--output", "-o", default=None, help="Output path for schema.json (default: .factory/schema.json)")
def schema_assemble(project_dir: str | None, output: str | None) -> None:
    """Assemble schema.json (SSOT) from task files, SDD, and module registry.

    Runs the deterministic Schema Manager: loads task index + individual task
    files, extracts components, merges models, normalizes field names, resolves
    relations, and produces a single schema.json that serves as the single
    source of truth for downstream code rendering.
    """
    target = _resolve_project_dir(project_dir)
    output_path = Path(output) if output else (target / ".factory" / "schema.json")

    click.echo("Assembling schema.json (SSOT)...")

    manager = SchemaManager(target)
    result = manager.assemble(output_path=output_path)

    if result.warnings:
        click.echo("")
        click.echo(f"Warnings ({len(result.warnings)}):")
        for w in result.warnings:
            click.echo(f"  ⚠  {w.message}")
            if w.detail:
                click.echo(f"      {w.detail}")

    if result.errors:
        click.echo("")
        click.echo(f"Errors ({len(result.errors)}):")
        for e in result.errors:
            click.echo(f"  ❌ {e.message}")
            if e.detail:
                click.echo(f"      {e.detail}")
        raise SystemExit(1)

    click.echo("")
    click.echo(f"✅ schema.json assembled at {output_path}")
    click.echo(f"   Models: {len(result.schema.get('models', []))}")
    click.echo(f"   Views:  {len(result.schema.get('views', []))}")
    click.echo(f"   Groups: {len(result.schema.get('security', {}).get('groups', []))}")
    click.echo(f"   ACLs:   {len(result.schema.get('security', {}).get('access_rights', []))}")


def _check_traceability(target: Path, sdd: dict[str, Any]) -> bool:
    """Verify PRD→SDD traceability completeness.

    Returns True if all PRD requirements are mapped in the SDD.
    """
    prd_path = target / ".factory" / "prd.json"
    if not prd_path.exists():
        click.echo("ℹ️  prd.json not found, skipping traceability check")
        return True

    try:
        prd = json.loads(prd_path.read_text())
    except json.JSONDecodeError:
        click.echo("⚠️  prd.json is invalid JSON, skipping traceability check")
        return True

    prd_rfs = {rf["id"] for rf in prd.get("functional_requirements", [])}
    prd_rnfs = {rnf["id"] for rnf in prd.get("non_functional_requirements", [])}
    all_requirements = prd_rfs | prd_rnfs

    if not all_requirements:
        click.echo("ℹ️  No requirements found in PRD, skipping traceability check")
        return True

    mappings = sdd.get("traceability_matrix", {}).get("mappings", [])
    mapped_requirements = set()
    for mapping in mappings:
        req = mapping.get("requirement", "")
        if req:
            mapped_requirements.add(req)

    unmapped = all_requirements - mapped_requirements
    if unmapped:
        for req in sorted(unmapped):
            click.echo(f"❌ traceability: PRD requirement '{req}' not mapped to any SDD component")
        click.echo(f"   {len(unmapped)} unmapped requirement(s)")
        return False

    click.echo(f"✅ traceability: {len(all_requirements)} requirements mapped to SDD components")
    return True


def _list_schemas(target: Path) -> list[str]:
    schemas: list[str] = []
    project_schemas = target / ".factory" / "schemas"
    if project_schemas.is_dir():
        schemas.extend(
            f.name for f in project_schemas.glob("*.schema.json")
        )
    if SCHEMAS_DIR.is_dir():
        for f in SCHEMAS_DIR.glob("*.schema.json"):
            if f.name not in schemas:
                schemas.append(f.name)
    return sorted(schemas)


def _find_schema(target: Path, schema_name: str) -> Path | None:
    project_schema = target / ".factory" / "schemas" / schema_name
    if project_schema.exists():
        return project_schema
    framework_schema = SCHEMAS_DIR / schema_name
    if framework_schema.exists():
        return framework_schema
    return None


@main.command()
@PROJECT_DIR_OPTION
@click.option("--verbose", "-v", is_flag=True, help="Detailed diagnostic output")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format (for CI)")
def doctor(project_dir: str | None, verbose: bool, json_output: bool) -> None:
    """Diagnose the health of a Factory Build Agent project.

    Checks: registry health, state file integrity, writability, and schema alignment.
    Exit codes: 0=OK (no errors or warnings), 1=warnings present, 2=errors present.
    """
    target = Path(project_dir).resolve() if project_dir else Path.cwd()
    factory_dir = target / ".factory"

    checks = []
    errors = []
    results = []

    if not factory_dir.exists():
        msg = "No .factory/ directory found. Run 'fba init' first."
        if json_output:
            click.echo(json.dumps({"status": "ERROR", "checks": [], "exit_code": 2, "error": msg}))
        else:
            click.echo(f"❌ {msg}")
        raise SystemExit(2)

    def _check(label: str, fn: Any) -> None:
        try:
            ok, detail, severity = fn()
            results.append({"label": label, "ok": ok, "detail": detail, "severity": severity or ("error" if not ok else "ok")})
            if not ok:
                if severity == "warning":
                    checks.append(("⚠", label, detail))
                else:
                    errors.append(("❌", label, detail))
        except Exception as e:
            results.append({"label": label, "ok": False, "detail": str(e), "severity": "error"})
            errors.append(("❌", label, str(e)))

    def _d1_check() -> tuple[bool, str, str | None]:
        try:
            import warnings as _w
            with _w.catch_warnings(record=True) as caught:
                _w.simplefilter("always")
                from fba.module_registry import ModuleRegistry
                registry = ModuleRegistry(target)
            reg_warnings = [str(w.message) for w in caught]
            modules = registry.modules
            model_count = sum(len(info.get("models", [])) for info in modules.values())
            detail = f"{len(modules)} modules, {model_count} models"
            if reg_warnings:
                detail += f", warnings: {'; '.join(reg_warnings)}"
                return False, detail, "error" if len(modules) == 0 else "warning"
            if len(modules) == 0:
                return False, detail + " (registry empty)", "warning"
            return True, detail, None
        except Exception as e:
            return False, f"Registry error: {e}", "error"

    def _d2_check() -> tuple[bool, str, str | None]:
        state_path = factory_dir / "state.json"
        if state_path.exists():
            return True, f"Found at {state_path}", None
        return False, "state.json not found", "error"

    def _d3_check() -> tuple[bool, str, str | None]:
        state_path = factory_dir / "state.json"
        if not state_path.exists():
            return False, "state.json does not exist", "error"
        try:
            data = json.loads(state_path.read_text())
            phase = data.get("current_phase", "unknown")
            return True, f"Valid JSON, current phase: {phase}", None
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}", "error"

    def _d4_check() -> tuple[bool, str, str | None]:
        test_file = factory_dir / ".doctor_write_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
            return True, "Writable", None
        except Exception as e:
            return False, f"Not writable: {e}", "error"

    def _d5_check() -> tuple[bool, str, str | None]:
        implemented_types = set(SchemaManager.IMPLEMENTED_TYPES)
        schema_path = factory_dir / "schemas" / "task_item.schema.json"
        if not schema_path.exists():
            schema_path = SCHEMAS_DIR / "task_item.schema.json"
        if not schema_path.exists():
            return True, "task_item.schema.json not found, skipping alignment check", None
        try:
            schema = json.loads(schema_path.read_text())
            enum = schema.get("properties", {}).get("components", {}).get("items", {}).get("properties", {}).get("type", {}).get("enum", [])
        except Exception:
            return True, "Could not parse schema, skipping alignment check", None
        unimplemented = [t for t in enum if t not in implemented_types]
        if unimplemented:
            return False, f"Unimplemented types: {', '.join(unimplemented)}", "warning"
        return True, "All schema types have implementations", None

    _check("registry", _d1_check)
    _check("state_exists", _d2_check)
    _check("state_json", _d3_check)
    _check("writable", _d4_check)
    _check("schema_alignment", _d5_check)

    if json_output:
        output = {
            "status": "ERROR" if errors else ("WARNING" if checks else "OK"),
            "checks": results,
            "exit_code": 2 if errors else (1 if checks else 0),
            "warnings": len(checks),
            "errors": len(errors),
        }
        click.echo(json.dumps(output, indent=2, ensure_ascii=False))
        raise SystemExit(output["exit_code"])

    for symbol, label, detail in errors:
        click.echo(f"{symbol} {label}: {detail}")
    for symbol, label, detail in checks:
        click.echo(f"{symbol} {label}: {detail}")

    ok_count = len(results) - len(errors) - len(checks)
    if not errors and not checks:
        for r in results:
            click.echo(f"✅ {r['label']}: {r['detail']}")
    else:
        for r in results:
            if r["severity"] == "ok":
                click.echo(f"✅ {r['label']}: {r['detail']}")

    if verbose:
        click.echo("")
        click.echo("─" * 40)
        click.echo("Verbose details:")
        click.echo(f"  Project: {target}")
        click.echo(f"  Factory dir: {factory_dir}")
        for r in results:
            click.echo(f"  [{r['severity'].upper()}] {r['label']}: {r['detail']}")

    if errors:
        raise SystemExit(2)
    if checks:
        raise SystemExit(1)
    raise SystemExit(0)


@main.command()
@click.argument("file_v1", type=click.Path(exists=True, path_type=Path))
@click.argument("file_v2", type=click.Path(exists=True, path_type=Path))
@click.option("--format", "-f", "output_format", type=click.Choice(["text", "json"]), default="text", help="Output format (text or json)")
def diff(file_v1: Path, file_v2: Path, output_format: str) -> None:
    """Compare two JSON artifact versions and produce a structured changelog.

    FILE_V1 is the older version, FILE_V2 is the newer version.
    Supports PRD, SDD, schema.json, tasks/index.json, and T*.json artifacts.

    \b
    Examples:
      fba diff v1/prd.json v2/prd.json
      fba diff old/sdd.json new/sdd.json --format json
    """
    try:
        result = DiffEngine.diff(file_v1, file_v2, output_format=output_format)
        click.echo(result)
    except DiffError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


_deps_group = click.group("deps")(lambda: None)
_deps_group.help = "Odoo dependency integrity analysis."


@_deps_group.command("check")
@PROJECT_DIR_OPTION
def deps_check(project_dir: str | None) -> None:
    """Analyze Odoo module dependencies for integrity issues.

    Checks:
      - Unused dependencies: modules in 'depends' not referenced in code
      - Missing dependencies: modules used in code but missing from 'depends'
      - Circular dependencies: cycles in the module dependency graph
    """
    target = _resolve_project_dir(project_dir)

    analyzer = DependencyAnalyzer()

    try:
        results = analyzer.analyze_project(target)
    except DependencyError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    total_issues = 0
    for mod_name, result in sorted(results.items()):
        summary = result.summary
        if not result.has_issues:
            click.echo(f"✅ {mod_name}: clean")
            continue

        click.echo(f"❌ {mod_name}: {summary['total_issues']} issue(s)")
        for issue in result.issues:
            icon = {"unused_dependency": "⚠", "missing_dependency": "❌", "circular_dependency": "🔄"}.get(issue["type"], "?")
            click.echo(f"   {icon} [{issue['type']}] {issue['message']}")
        total_issues += summary["total_issues"]

    if total_issues > 0:
        click.echo(f"\n{total_issues} total dependency issue(s) found across {len(results)} module(s)")
        raise SystemExit(1)

    click.echo(f"\nAll {len(results)} module(s) have clean dependencies.")


@main.command()
@click.argument("entity_id")
@PROJECT_DIR_OPTION
def trace(entity_id: str, project_dir: str | None) -> None:
    """Trace a stable UUID across all project artifacts.

    Searches PRD, SDD, and schema.json for the given UUID and reports
    where the entity is referenced.
    """
    target = _resolve_project_dir(project_dir)
    factory_dir = target / ".factory"

    try:
        result = StableIdManager.trace(entity_id, factory_dir)
    except StableIdError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if result is None:
        click.echo(f"UUID '{entity_id[:16]}...' not found in any artifact.")
        raise SystemExit(1)

    click.echo(f"🔍 Tracing UUID: {entity_id}")
    click.echo(f"   Found in {result['found_in']} location(s):")
    for loc in result["locations"]:
        click.echo(f"   - [{loc['entity_type']}] {loc['entity_id']}")
        click.echo(f"     Artifact: {loc['artifact']}")
        click.echo(f"     Path: {loc['path']}")


main.add_command(_deps_group)
main.add_command(_schema_group)

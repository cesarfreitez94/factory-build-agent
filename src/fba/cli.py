import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import click

from fba import __version__
from fba.state import StateManager

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
SCHEMAS_DIR = Path(__file__).resolve().parent.parent.parent / "schemas"

PROJECT_DIR_OPTION = click.option(
    "--project-dir", "-d", default=None,
    help="Target project directory (default: current directory)"
)


def _resolve_project_dir(project_dir):
    target = Path(project_dir).resolve() if project_dir else Path.cwd()
    if not (target / ".factory").exists():
        click.echo(f"Error: No .factory/ found in {target}. Run 'fba init' first.")
        raise SystemExit(1)
    return target


@click.group()
@click.version_option(version=__version__)
def main():
    """Factory Build Agent - Multi-agent framework for Odoo v18 module development."""


@main.command()
@click.option("--project-dir", "-d", default=None, help="Target project directory (default: current directory)")
def init(project_dir):
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
    _init_factory_state(target)
    _init_events_log(target)

    click.echo(f"✅ Factory Build Agent initialized in {target}")
    click.echo("")
    click.echo("Next steps:")
    click.echo("  1. Open the project with OpenCode: opencode .")
    click.echo("  2. Start eliciting requirements: /fba:elicit \"your idea\"")


def _copy_templates(target: Path):
    templates_src = TEMPLATES_DIR
    if not templates_src.exists():
        click.echo(f"⚠  Templates directory not found: {templates_src}")
        return

    shutil.copytree(templates_src, target, dirs_exist_ok=True)


def _copy_schemas(target: Path):
    schemas_src = SCHEMAS_DIR
    if not schemas_src.exists():
        return

    factory_schemas = target / ".factory" / "schemas"
    factory_schemas.mkdir(parents=True, exist_ok=True)

    for schema_file in schemas_src.glob("*.schema.json"):
        dest = factory_schemas / schema_file.name
        if not dest.exists():
            shutil.copy2(schema_file, dest)


def _init_factory_state(target: Path):
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
            "construction": {"status": "pending", "agent": "constructor"},
            "testing": {"status": "pending", "agent": "tester"},
            "review": {"status": "pending", "agent": "revisor"},
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
        "artifacts": {},
        "context": {},
    }

    state_path = factory_dir / "state.json"
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def _init_events_log(target: Path):
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
def status(project_dir):
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
@PROJECT_DIR_OPTION
def transition(phase, project_dir):
    """Transition the project to a new development phase."""
    target = _resolve_project_dir(project_dir)
    state_mgr = StateManager(target)

    try:
        state = state_mgr.transition_to(phase)
        click.echo(f"Transitioned from '{state['current_phase']}' to '{phase}'")
    except ValueError as e:
        click.echo(f"Error: {e}")
        raise SystemExit(1)


@main.command()
@click.argument("event_type")
@click.option("--data", default=None, help="JSON string with event data")
@PROJECT_DIR_OPTION
def record(event_type, data, project_dir):
    """Record an event in the append-only event log."""
    target = _resolve_project_dir(project_dir)
    state_mgr = StateManager(target)

    parsed_data = None
    if data:
        parsed_data = json.loads(data)

    state_mgr.record_event(event_type, parsed_data)
    click.echo(f"Event '{event_type}' recorded.")


@main.command()
@click.argument("artifact", required=False)
@PROJECT_DIR_OPTION
def validate(artifact, project_dir):
    """Validate project artifacts against their JSON schemas.

    If no artifact is specified, validates all artifacts found in state.json.
    """
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
        except jsonschema.ValidationError as e:
            click.echo(f"❌ {art_name}: validation failed - {e.message}")
            all_valid = False
        except json.JSONDecodeError as e:
            click.echo(f"❌ {art_name}: invalid JSON - {e}")
            all_valid = False

    if not all_valid:
        raise SystemExit(1)


def _list_schemas(target: Path) -> list:
    schemas = []
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

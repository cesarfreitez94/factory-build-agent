import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import click

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


@click.group()
@click.version_option(version="0.1.0")
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


def _init_factory_state(target: Path):
    factory_dir = target / ".factory"
    factory_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "project": target.name,
        "framework_version": "0.1.0",
        "init_at": datetime.now(timezone.utc).isoformat(),
        "current_phase": "init",
        "methodology": "BABOK",
        "phases": {
            "elicitation": {"status": "pending", "agent": "elicitador"},
            "documentation": {"status": "pending", "agent": "documentador"},
            "planning": {"status": "pending", "agent": "planificador"},
            "construction": {"status": "pending", "agent": "constructor"},
            "testing": {"status": "pending", "agent": "tester"},
            "review": {"status": "pending", "agent": "revisor"},
            "ci_cd": {"status": "pending", "agent": "cicd_manager"},
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
        "framework_version": "0.1.0",
        "project": target.name,
    }

    events_path.write_text(json.dumps(init_event, ensure_ascii=False) + "\n")

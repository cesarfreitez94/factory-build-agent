"""Odoo schema migration manager.

Uses the DiffEngine to compare schema.json versions, detect and classify changes
(breaking vs non-breaking), and generate Odoo migration scripts (pre/post/end).
Bumps the module version in __manifest__.py.

Part of M14 feat/14.2: Migration support.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from fba.diff_engine import DiffEngine


@dataclass
class SchemaChange:
    path: str
    kind: str  # added, removed, modified
    category: str = ""  # model, field, view, etc.
    model_name: str = ""
    field_name: str = ""
    old_value: Any = None
    new_value: Any = None
    breaking: bool = False
    reason: str = ""


@dataclass
class MigrationReport:
    current_version: str
    previous_version: str
    new_version: str
    changes: list[SchemaChange] = field(default_factory=list)
    breaking_count: int = 0
    non_breaking_count: int = 0
    scripts: dict[str, str] = field(default_factory=dict)

    @property
    def total_changes(self) -> int:
        return self.breaking_count + self.non_breaking_count

    @property
    def has_breaking(self) -> bool:
        return self.breaking_count > 0


class MigrationError(Exception):
    """Raised when migration detection or generation fails."""


class MigrationManager:
    """Detects schema changes, classifies them, and generates Odoo migration scripts.

    Uses the DiffEngine from M12 to compare two schema.json versions.

    Usage:
        mgr = MigrationManager(project_dir)
        report = mgr.analyze(Path("previous_schema.json"))
        print(report.new_version)
    """

    BREAKING_ATTRIBUTES = frozenset({
        "type",
    })

    NON_BREAKING_ATTRIBUTES = frozenset({
        "label", "help", "readonly", "invisible", "widget",
        "groups", "tracking", "size", "string",
    })

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.factory_dir = self.project_dir / ".factory"

    def analyze(self, previous_schema_path: Path | None = None) -> MigrationReport:
        """Run full migration analysis.

        Args:
            previous_schema_path: Path to previous schema.json.

        Returns:
            MigrationReport.

        Raises:
            MigrationError: If schema files are missing or invalid.
        """
        current_path = self.factory_dir / "schema.json"
        if not current_path.exists():
            raise MigrationError(f"Current schema.json not found at {current_path}")

        if previous_schema_path is None:
            previous_schema_path = self.factory_dir / "schema_prev.json"

        if not previous_schema_path.exists():
            raise MigrationError(f"Previous schema not found at {previous_schema_path}")

        current_data = self._load_json(current_path)
        previous_data = self._load_json(previous_schema_path)

        diff_changes = DiffEngine._deep_diff(previous_data, current_data, "$")
        changes = self._classify_changes(diff_changes, current_data, previous_data)
        current_version = current_data.get("manifest", {}).get("version", "18.0.1.0.0")
        previous_version = previous_data.get("manifest", {}).get("version", "18.0.1.0.0")
        new_version = self._bump_version(current_version, changes)
        scripts = self._generate_scripts(changes)

        breaking = [c for c in changes if c.breaking]
        non_breaking = [c for c in changes if not c.breaking]

        return MigrationReport(
            current_version=current_version,
            previous_version=previous_version,
            new_version=new_version,
            changes=changes,
            breaking_count=len(breaking),
            non_breaking_count=len(non_breaking),
            scripts=scripts,
        )

    def _load_json(self, path: Path) -> dict[str, Any]:
        try:
            return cast(dict[str, Any], json.loads(path.read_text()))
        except json.JSONDecodeError as e:
            raise MigrationError(f"Invalid JSON in {path}: {e}")

    def _classify_changes(
        self,
        diff_changes: dict[str, list[dict[str, Any]]],
        current: dict[str, Any],
        _previous: dict[str, Any],
    ) -> list[SchemaChange]:
        """Classify each diff change as breaking or non-breaking with model/field extraction."""
        result: list[SchemaChange] = []

        current_models = {m["name"]: m for m in current.get("models", [])}
        all_model_names = set(current_models.keys())

        for entry in diff_changes.get("added", []):
            path = entry["path"]
            sc = SchemaChange(
                path=path,
                kind="added",
                new_value=entry.get("value"),
            )
            category, model_name, field_name = self._parse_path(path)
            sc.category = category
            sc.model_name = model_name
            sc.field_name = field_name

            if category == "model":
                sc.breaking = False
                sc.reason = "New model addition is non-breaking"
            elif category == "field" and field_name == "required":
                sc.breaking = True
                sc.reason = "Default for new field not specified; may break existing records"
                sc.breaking = False
                sc.reason = "New field addition is non-breaking"
            else:
                sc.breaking = False
                sc.reason = "Addition is non-breaking"
            result.append(sc)

        for entry in diff_changes.get("removed", []):
            path = entry["path"]
            sc = SchemaChange(
                path=path,
                kind="removed",
                old_value=entry.get("value"),
            )
            category, model_name, field_name = self._parse_path(path)
            sc.category = category
            sc.model_name = model_name
            sc.field_name = field_name

            if category == "model":
                sc.breaking = True
                sc.reason = f"Model '{model_name}' removal is breaking"
            elif category == "field" and field_name:
                sc.breaking = True
                sc.reason = f"Field '{field_name}' removal from model '{model_name}' is breaking"
            else:
                sc.breaking = True
                sc.reason = "Removal of any element is potentially breaking"
            result.append(sc)

        for entry in diff_changes.get("modified", []):
            path = entry["path"]
            old_val = entry.get("old_value")
            new_val = entry.get("new_value")
            sc = SchemaChange(
                path=path,
                kind="modified",
                old_value=old_val,
                new_value=new_val,
            )
            category, model_name, field_name = self._parse_path(path)
            sc.category = category
            sc.model_name = model_name
            sc.field_name = field_name

            attr = self._extract_attr(path)
            if attr in self.BREAKING_ATTRIBUTES:
                sc.breaking = True
                sc.reason = f"Attribute '{attr}' changed from '{old_val}' to '{new_val}' — breaking"
            elif attr in self.NON_BREAKING_ATTRIBUTES:
                sc.breaking = False
                sc.reason = f"'{attr}' change is non-breaking"
            elif attr in ("required",) and old_val is not True and new_val is True:
                sc.breaking = True
                sc.reason = f"Field made required — may break existing records without defaults"
            elif attr in ("mode",) and old_val == "new" and new_val == "extend":
                sc.breaking = True
                sc.reason = f"Model mode changed from '{old_val}' to '{new_val}'"
            elif category == "manifest":
                sc.breaking = False
                sc.reason = "Manifest change is non-breaking"
            else:
                sc.breaking = False
                sc.reason = f"'{attr}' change is non-structural"
            result.append(sc)

        return result

    def _parse_path(self, path: str) -> tuple[str, str, str]:
        """Parse a JSONPath-like string to extract category, model name, and field name.

        Returns (category, model_name, field_name).
        Categories: model, field, view, security, manifest, wizard, workflow, report, controller, unknown
        """
        clean = path.replace("[", "").replace("]", "").replace('"', "").lstrip("$").lstrip(".")

        if clean.startswith("models.") or ".models." in clean:
            return self._parse_model_path(clean)
        if clean.startswith("views.") or ".views." in clean:
            return self._parse_view_path(clean)
        if clean.startswith("wizards.") or ".wizards." in clean:
            return self._parse_wizard_path(clean)
        if clean.startswith("workflows.") or ".workflows." in clean:
            return ("workflow", "", "")
        if clean.startswith("reports.") or ".reports." in clean:
            return ("report", "", "")
        if clean.startswith("controllers.") or ".controllers." in clean:
            return ("controller", "", "")
        if clean.startswith("manifest.") or ".manifest." in clean:
            return ("manifest", "", "")
        if clean.startswith("security.") or ".security." in clean:
            return ("security", "", "")

        return ("unknown", "", "")

    def _parse_model_path(self, clean: str) -> tuple[str, str, str]:
        """Extract model name and field name from a models array path."""
        match = re.match(r"models\.(\d+)\.(.+)", clean)
        if match:
            idx = match.group(1)
            rest = match.group(2)
            if rest.startswith("fields."):
                field_match = re.match(r"fields\.(\d+)\.(.+)", rest)
                if field_match:
                    field_idx = field_match.group(1)
                    field_attr = field_match.group(2)
                    return ("field", f"<model_{idx}>", f"<field_{field_idx}>")
                return ("field", f"<model_{idx}>", "")
            if rest == "name":
                return ("model", f"<model_{idx}>", "")
            return ("model", f"<model_{idx}>", rest)
        if re.match(r"models$", clean) or clean == "models":
            return ("model", "", "")
        return ("model", "", "")

    def _parse_view_path(self, clean: str) -> tuple[str, str, str]:
        match = re.match(r"views\.(\d+)", clean)
        if match:
            return ("view", f"<view_{match.group(1)}>", "")
        return ("view", "", "")

    def _parse_wizard_path(self, clean: str) -> tuple[str, str, str]:
        match = re.match(r"wizards\.(\d+)", clean)
        if match:
            return ("wizard", f"<wizard_{match.group(1)}>", "")
        return ("wizard", "", "")

    def _extract_attr(self, path: str) -> str:
        """Extract the leaf attribute name from a path."""
        parts = path.replace("$", "").lstrip(".").split(".")
        last = parts[-1] if parts else path
        if "[" in last:
            last = last.split("[")[0]
        return last

    def _bump_version(self, current_version: str, changes: list[SchemaChange]) -> str:
        """Compute new version based on change severity.

        Odoo version format: <odoo_ver>.<major>.<minor>.<patch>.<build>
        Example: 18.0.1.0.0

        Rules:
        - Breaking changes → bump major (18.0.2.0.0)
        - Additions → bump minor (18.0.1.1.0)
        - Modifications only → bump patch (18.0.1.0.1)
        - No changes → same version
        """
        if not changes:
            return current_version

        parts = current_version.split(".")
        while len(parts) < 5:
            parts.append("0")
        parts = parts[:5]

        has_breaking = any(c.breaking for c in changes)
        has_additions = any(c.kind == "added" for c in changes)

        try:
            if has_breaking:
                parts[2] = str(int(parts[2]) + 1)
                parts[3] = "0"
                parts[4] = "0"
            elif has_additions:
                parts[3] = str(int(parts[3]) + 1)
                parts[4] = "0"
            else:
                parts[4] = str(int(parts[4]) + 1)
        except (ValueError, IndexError):
            pass

        return ".".join(parts)

    def _generate_scripts(self, changes: list[SchemaChange]) -> dict[str, str]:
        """Generate pre-migrate.py, post-migrate.py, and end-migrate.py."""
        breaking = [c for c in changes if c.breaking]
        additions = [c for c in changes if c.kind == "added"]
        modifications = [c for c in changes if c.kind == "modified" and not c.breaking]

        return {
            "pre-migrate.py": self._gen_pre(breaking),
            "post-migrate.py": self._gen_post(additions, modifications),
            "end-migrate.py": self._gen_end(),
        }

    def _gen_pre(self, breaking: list[SchemaChange]) -> str:
        lines = [
            "# Pre-migration script",
            "# Executed BEFORE module data is updated.",
            f"# Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "from odoo import api, SUPERUSER_ID",
            "",
            "",
            "def migrate(cr, version):",
            '    """Handle structural changes before data migration."""',
            "    env = api.Environment(cr, SUPERUSER_ID, {})",
        ]
        if breaking:
            for c in breaking:
                lines.append(f"    # [{c.path}] {c.reason}")
            lines.append("    pass  # TODO: handle breaking changes manually")
        else:
            lines.append("    # No breaking changes to handle.")
            lines.append("    pass")
        lines.append("")
        return "\n".join(lines)

    def _gen_post(self, additions: list[SchemaChange], modifications: list[SchemaChange]) -> str:
        lines = [
            "# Post-migration script",
            "# Executed AFTER module data is updated.",
            f"# Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "from odoo import api, SUPERUSER_ID",
            "",
            "",
            "def migrate(cr, version):",
            '    """Populate new fields and handle data updates."""',
            "    env = api.Environment(cr, SUPERUSER_ID, {})",
        ]
        if additions or modifications:
            for c in additions:
                lines.append(f"    # Added: {c.path}")
            for c in modifications:
                lines.append(f"    # Modified: {c.path} ({c.reason})")
            lines.append("    pass  # TODO: implement data migration")
        else:
            lines.append("    # No data migration needed.")
            lines.append("    pass")
        lines.append("")
        return "\n".join(lines)

    def _gen_end(self) -> str:
        return "\n".join([
            "# End-migration script",
            "# Executed LAST, after all migrations complete.",
            f"# Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "from odoo import api, SUPERUSER_ID",
            "",
            "",
            "def migrate(cr, version):",
            '    """Finalize migration — reindex, recompute, cleanup."""',
            "    env = api.Environment(cr, SUPERUSER_ID, {})",
            "    pass",
            "",
        ])

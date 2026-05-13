"""Migration engine for Odoo schema change detection and migration script generation.

Detects field-level changes between schema versions (old vs new), generates Odoo
pre-migration.py and post-migration.xml scripts, and validates backward compatibility.

Usage:
    diff = SchemaDiff.detect(Path("schema_v1.json"), Path("schema_v2.json"))
    engine = MigrationEngine()
    scripts = engine.generate_migration_scripts(diff, "module_name")
    issues = engine.validate_backward_compatibility(diff)
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


def _empty_dict() -> dict[str, Any]:
    return {}


class MigrationError(Exception):
    """Raised when migration detection or generation fails."""


@dataclass
class FieldChange:
    action: str
    model: str
    field: str
    field_type: str = ""
    old_type: str = ""
    new_type: str = ""
    old_required: bool = False
    new_required: bool = False
    old_default: Any = None
    new_default: Any = None
    extra: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "action": self.action,
            "model": self.model,
            "field": self.field,
            "type": self.field_type or "field",
        }
        if self.action == "modify":
            d["old_type"] = self.old_type
            d["new_type"] = self.new_type
            d["old_required"] = self.old_required
            d["new_required"] = self.new_required
            d["old_default"] = self.old_default
            d["new_default"] = self.new_default
        if self.extra:
            d.update(self.extra)
        return d


@dataclass
class SchemaDiffResult:
    has_changes: bool = False
    field_changes: list[FieldChange] = field(default_factory=list)
    model_changes: list[dict[str, Any]] = field(default_factory=list)
    version_old: str = ""
    version_new: str = ""


class SchemaDiff:
    """Detects field-level changes between two schema.json versions."""

    @staticmethod
    def detect(file_v1: Path, file_v2: Path) -> SchemaDiffResult:
        """Compare two schema.json files and return detected changes.

        Args:
            file_v1: Path to the older schema version.
            file_v2: Path to the newer schema version.

        Returns:
            SchemaDiffResult with field_changes and model_changes lists.

        Raises:
            MigrationError: If files don't exist or contain invalid JSON.
        """
        if not file_v1.exists():
            raise MigrationError(f"File not found: {file_v1}")
        if not file_v2.exists():
            raise MigrationError(f"File not found: {file_v2}")

        try:
            data_v1 = json.loads(file_v1.read_text())
        except json.JSONDecodeError as e:
            raise MigrationError(f"Invalid JSON in {file_v1}: {e}")

        try:
            data_v2 = json.loads(file_v2.read_text())
        except json.JSONDecodeError as e:
            raise MigrationError(f"Invalid JSON in {file_v2}: {e}")

        models_v1 = {m["name"]: m for m in data_v1.get("models", [])}
        models_v2 = {m["name"]: m for m in data_v2.get("models", [])}

        version_old = data_v1.get("manifest", {}).get("version", "")
        version_new = data_v2.get("manifest", {}).get("version", "")

        field_changes: list[FieldChange] = []
        model_changes: list[dict[str, Any]] = []

        for model_name, model_v2 in models_v2.items():
            if model_name not in models_v1:
                model_changes.append({
                    "action": "add",
                    "model": model_name,
                })
                continue

            model_v1 = models_v1[model_name]
            fields_v1 = {f["name"]: f for f in model_v1.get("fields", [])}
            fields_v2 = {f["name"]: f for f in model_v2.get("fields", [])}

            for fname, fv2 in fields_v2.items():
                if fname not in fields_v1:
                    fc = FieldChange(
                        action="add",
                        model=model_name,
                        field=fname,
                        field_type=fv2.get("type", ""),
                    )
                    fc.extra = {k: v for k, v in fv2.items() if k not in ("name", "type")}
                    field_changes.append(fc)
                else:
                    fv1 = fields_v1[fname]
                    changes = _detect_field_modifications(model_name, fname, fv1, fv2)
                    field_changes.extend(changes)

            for fname in fields_v1:
                if fname not in fields_v2:
                    fc = FieldChange(
                        action="remove",
                        model=model_name,
                        field=fname,
                        field_type=fields_v1[fname].get("type", ""),
                    )
                    field_changes.append(fc)

        for model_name in models_v1:
            if model_name not in models_v2:
                model_changes.append({
                    "action": "remove",
                    "model": model_name,
                })

        result = SchemaDiffResult(
            has_changes=len(field_changes) > 0 or len(model_changes) > 0,
            field_changes=field_changes,
            model_changes=model_changes,
            version_old=version_old,
            version_new=version_new,
        )
        return result


def _detect_field_modifications(model: str, fname: str, fv1: dict[str, Any], fv2: dict[str, Any]) -> list[FieldChange]:
    """Detect modifications between two field versions."""
    changes = []

    t1 = fv1.get("type", "")
    t2 = fv2.get("type", "")
    if t1 != t2:
        changes.append(FieldChange(
            action="modify",
            model=model,
            field=fname,
            field_type="type_change",
            old_type=t1,
            new_type=t2,
            old_required=fv1.get("required", False),
            new_required=fv2.get("required", False),
        ))

    r1 = fv1.get("required", False)
    r2 = fv2.get("required", False)
    if r1 != r2:
        changes.append(FieldChange(
            action="modify",
            model=model,
            field=fname,
            field_type="required_change",
            old_type=t2,
            new_type=t2,
            old_required=r1,
            new_required=r2,
        ))

    d1 = fv1.get("default")
    d2 = fv2.get("default")
    if d1 != d2:
        changes.append(FieldChange(
            action="modify",
            model=model,
            field=fname,
            field_type="default_change",
            old_type=t2,
            new_type=t2,
            old_required=r2,
            new_required=r2,
            old_default=d1,
            new_default=d2,
        ))

    ondelete1 = fv1.get("ondelete")
    ondelete2 = fv2.get("ondelete")
    if ondelete1 != ondelete2:
        changes.append(FieldChange(
            action="modify",
            model=model,
            field=fname,
            field_type="ondelete_change",
            old_type=t2,
            new_type=t2,
            old_required=r2,
            new_required=r2,
            old_default=ondelete1,
            new_default=ondelete2,
        ))

    return changes


ODOO_TYPE_TO_SQL = {
    "Char": "VARCHAR",
    "Text": "TEXT",
    "Integer": "INTEGER",
    "Float": "FLOAT",
    "Boolean": "BOOLEAN",
    "Date": "DATE",
    "Datetime": "TIMESTAMP",
    "Binary": "BYTEA",
    "Html": "TEXT",
    "Selection": "VARCHAR",
    "Monetary": "DECIMAL",
}


class MigrationEngine:
    """Generates Odoo migration scripts and validates backward compatibility."""

    def generate_migration_scripts(self, diff: SchemaDiffResult, module_name: str) -> dict[str, str]:
        """Generate pre-migration.py and post-migration.xml content.

        Args:
            diff: Result from SchemaDiff.detect().
            module_name: Name of the Odoo module.

        Returns:
            Dict with keys 'pre_migration.py' and/or 'post_migration.xml' and their content.
            Empty dict if no changes detected.
        """
        if not diff.has_changes:
            return {}

        scripts: dict[str, str] = {}

        pre_lines = _generate_pre_migration(diff, module_name)
        if pre_lines:
            scripts["pre_migration.py"] = pre_lines

        post_lines = _generate_post_migration(diff, module_name)
        if post_lines:
            scripts["post_migration.xml"] = post_lines

        return scripts

    def validate_backward_compatibility(self, diff: SchemaDiffResult) -> list[dict[str, Any]]:
        """Validate backward compatibility and return list of issues.

        Args:
            diff: Result from SchemaDiff.detect().

        Returns:
            List of issue dicts with 'severity' (error/warning), 'type', 'message'.
        """
        issues: list[dict[str, Any]] = []

        for fc in diff.field_changes:
            if fc.action == "remove":
                issues.append({
                    "severity": "error",
                    "type": "field_removed",
                    "model": fc.model,
                    "field": fc.field,
                    "message": f"Field '{fc.field}' on model '{fc.model}' is being removed — data loss risk",
                })

            elif fc.action == "modify":
                if fc.field_type == "type_change":
                    issues.append({
                        "severity": "error",
                        "type": "field_type_changed",
                        "model": fc.model,
                        "field": fc.field,
                        "old_type": fc.old_type,
                        "new_type": fc.new_type,
                        "message": f"Field '{fc.field}' type changed from '{fc.old_type}' to '{fc.new_type}' — may break existing data",
                    })

                elif fc.field_type == "required_change" and fc.new_required and not fc.old_required:
                    issues.append({
                        "severity": "warning",
                        "type": "required_field_added",
                        "model": fc.model,
                        "field": fc.field,
                        "message": f"Required field '{fc.field}' added to model '{fc.model}' — existing records will fail validation",
                    })

        return issues


def _generate_pre_migration(diff: SchemaDiffResult, module_name: str) -> str:
    """Generate pre-migration.py content."""
    lines = [
        "# -*- coding: utf-8 -*-",
        f'"""{module_name} pre-migration script."""',
        "",
        "from odoo import SUPERUSER_ID",
        "from odoo.api import Environment",
        "",
        "",
        "def migrate(cr, version):",
        "    if not version:",
        "        return",
        "    env = Environment(cr, SUPERUSER_ID, {})",
        "",
    ]

    field_ops = [fc for fc in diff.field_changes if fc.action in ("add", "remove", "modify")]

    if not field_ops:
        lines.append("    pass")
    else:
        for fc in field_ops:
            if fc.action == "add":
                sql_type = ODOO_TYPE_TO_SQL.get(fc.field_type, "VARCHAR")
                lines.append(f"    _add_column(cr, '{module_name}', '{fc.field}', '{sql_type}')")
            elif fc.action == "remove":
                lines.append(f"    _drop_column(cr, '{module_name}', '{fc.field}')")
            elif fc.action == "modify" and fc.field_type == "type_change":
                sql_type = ODOO_TYPE_TO_SQL.get(fc.new_type, "VARCHAR")
                lines.append(f"    _alter_column_type(cr, '{module_name}', '{fc.field}', '{sql_type}')")

        lines.extend([
            "",
            "",
            "def _add_column(cr, module, column, col_type):",
            "    cr.execute(\"\"\"",
            "        SELECT column_name FROM information_schema.columns",
            "        WHERE table_name = %s AND column_name = %s",
            "    \"\"\", (module + '_' + module, column))",
            "    if not cr.fetchone():",
            "        cr.execute(",
            "            f'ALTER TABLE ' + module + '_' + module + ' ADD COLUMN ' + column + ' ' + col_type",
            "        )",
            "",
            "",
            "def _drop_column(cr, module, column):",
            "    cr.execute(\"\"\"",
            "        SELECT column_name FROM information_schema.columns",
            "        WHERE table_name = %s AND column_name = %s",
            "    \"\"\", (module + '_' + module, column))",
            "    if cr.fetchone():",
            "        cr.execute(",
            "            f'ALTER TABLE ' + module + '_' + module + ' DROP COLUMN ' + column",
            "        )",
            "",
            "",
            "def _alter_column_type(cr, module, column, new_type):",
            "    cr.execute(\"\"\"",
            "        SELECT column_name FROM information_schema.columns",
            "        WHERE table_name = %s AND column_name = %s",
            "    \"\"\", (module + '_' + module, column))",
            "    if cr.fetchone():",
            "        cr.execute(",
            "            f'ALTER TABLE ' + module + '_' + module + ' ALTER COLUMN ' + column + ' TYPE ' + new_type",
            "        )",
        ])

    return "\n".join(lines)


def _generate_post_migration(diff: SchemaDiffResult, module_name: str) -> str:
    """Generate post-migration.xml content."""
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<odoo>",
        "  <data noupdate=\"1\">",
        "    <record id=\"module_complete_notification\" model=\"mail.message\">",
        "      <field name=\"model\">ir.model</field>",
        "      <field name=\"res_id\">0</field>",
        "      <field name=\"body\">Migration completed successfully.</field>",
        "    </record>",
        "  </data>",
        "</odoo>",
    ]
    return "\n".join(lines)

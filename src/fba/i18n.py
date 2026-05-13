"""Internationalization (i18n) engine for Odoo module translation files.

Generates .pot (gettext template) and .po (locale-specific translation) files
in OCA-ready structure for Odoo v18 modules.

Usage:
    from fba.i18n import I18nExtractor, PoFileGenerator

    # Extract translatable strings from schema.json
    extractor = I18nExtractor()
    pot_content = extractor.extract_from_schema(schema_path)

    # Generate .po file for a locale
    generator = PoFileGenerator()
    po_content = generator.generate_po(pot_content, "es_ES", {"Hello": "Hola"})
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class I18nError(Exception):
    """Raised when i18n extraction or generation fails."""


@dataclass
class TranslatableString:
    """A translatable string with its context and location."""
    msgid: str
    msgctxt: str = ""
    source_module: str = ""
    source_type: str = ""
    source_id: str = ""
    field_name: str = ""

    def to_pot_entry(self) -> str:
        """Format as a gettext .pot entry."""
        lines = []
        if self.msgctxt:
            lines.append(f"#: {self.source_type}:{self.source_module}.{self.source_id}:{self.field_name}")
            lines.append(f"msgctxt \"{self._escape(self.msgctxt)}\"")
        else:
            lines.append(f"#: {self.source_type}:{self.source_module}.{self.source_id}:{self.field_name}")
        lines.append(f"msgid \"{self._escape(self.msgid)}\"")
        lines.append("msgid_plural \"\"")
        lines.append("msgstr[0] \"\"")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _escape(s: str) -> str:
        """Escape special characters for gettext format."""
        if not s:
            return ""
        s = s.replace("\\", "\\\\")
        s = s.replace('"', '\\"')
        s = s.replace("\n", "\\n")
        s = s.replace("\t", "\\t")
        return s


class I18nExtractor:
    """Extracts translatable strings from Odoo module schema.json."""

    def __init__(self, module_name: str = ""):
        self.module_name = module_name
        self.strings: list[TranslatableString] = []

    def extract_from_schema(self, schema_path: Path) -> str:
        """Extract all translatable strings from a schema.json file.

        Args:
            schema_path: Path to schema.json

        Returns:
            Formatted .pot file content
        """
        import json

        if not schema_path.exists():
            raise I18nError(f"Schema not found: {schema_path}")

        try:
            schema = json.loads(schema_path.read_text())
        except json.JSONDecodeError as e:
            raise I18nError(f"Invalid JSON in schema: {e}")

        self.strings = []
        self.module_name = schema.get("manifest", {}).get("name", self.module_name)

        self._extract_from_manifest(schema.get("manifest", {}))
        self._extract_from_models(schema.get("models", []))
        self._extract_from_views(schema.get("views", []))
        self._extract_from_wizards(schema.get("wizards", []))
        self._extract_from_workflows(schema.get("workflows", []))
        self._extract_from_reports(schema.get("reports", []))
        self._extract_from_controllers(schema.get("controllers", []))
        self._extract_from_security(schema.get("security", {}))

        return self._render_pot()

    def _extract_from_manifest(self, manifest: dict[str, Any]) -> None:
        """Extract strings from module manifest."""
        for field_name in ["summary", "description", "name"]:
            if field_name in manifest and manifest[field_name]:
                self._add_string(
                    manifest[field_name],
                    "manifest",
                    manifest.get("name", self.module_name),
                    field_name,
                    "module"
                )

    def _extract_from_models(self, models: list[dict[str, Any]]) -> None:
        """Extract strings from Odoo models."""
        for model in models:
            model_name = model.get("name", "unknown")
            self._add_string(
                model.get("description", ""),
                "model",
                model_name,
                "description",
                context=f"model:{model_name}"
            )
            if model.get("display_name"):
                self._add_string(
                    model.get("display_name"),
                    "model",
                    model_name,
                    "display_name",
                    context=f"model:{model_name}"
                )
            for field in model.get("fields", []):
                self._extract_from_field(field, model_name, "field")

    def _extract_from_field(
        self, field: dict[str, Any], model_name: str, source_type: str
    ) -> None:
        """Extract translatable strings from a model field."""
        field_name = field.get("name", "")
        self._add_string(
            field.get("label", ""),
            source_type,
            model_name,
            field_name,
            context=f"field:{model_name}.{field_name}"
        )
        if field.get("help"):
            self._add_string(
                field.get("help"),
                source_type,
                model_name,
                field_name,
                context=f"help:{model_name}.{field_name}"
            )
        if field.get("selection"):
            for selection in field.get("selection", []):
                if len(selection) >= 2:
                    self._add_string(
                        selection[1],
                        source_type,
                        model_name,
                        field_name,
                        context=f"selection:{model_name}.{field_name}"
                    )

    def _extract_from_views(self, views: list[dict[str, Any]]) -> None:
        """Extract strings from Odoo views."""
        for view in views:
            view_name = view.get("name", "unknown")
            self._add_string(
                view.get("display_name", ""),
                "view",
                view_name,
                "display_name",
                context=f"view:{view_name}"
            )

    def _extract_from_wizards(self, wizards: list[dict[str, Any]]) -> None:
        """Extract strings from Odoo wizard models."""
        for wizard in wizards:
            wizard_name = wizard.get("name", wizard.get("model", "unknown"))
            self._add_string(
                wizard.get("description", ""),
                "wizard",
                wizard_name,
                "description",
                context=f"wizard:{wizard_name}"
            )
            for field in wizard.get("fields", []):
                self._extract_from_field(field, wizard_name, "wizard_field")

    def _extract_from_workflows(self, workflows: list[dict[str, Any]]) -> None:
        """Extract strings from Odoo workflow definitions."""
        for workflow in workflows:
            workflow_name = workflow.get("name", "unknown")
            for state in workflow.get("states", []):
                self._add_string(
                    state.get("description", ""),
                    "workflow",
                    workflow_name,
                    f"state:{state.get('name', '')}",
                    context=f"workflow:{workflow_name}"
                )
            for signal in workflow.get("signals", []):
                self._add_string(
                    signal.get("description", ""),
                    "workflow",
                    workflow_name,
                    f"signal:{signal.get('name', '')}",
                    context=f"workflow:{workflow_name}"
                )

    def _extract_from_reports(self, reports: list[dict[str, Any]]) -> None:
        """Extract strings from Odoo report definitions."""
        for report in reports:
            report_name = report.get("name", "unknown")
            self._add_string(
                report.get("report_name", ""),
                "report",
                report_name,
                "report_name",
                context=f"report:{report_name}"
            )

    def _extract_from_controllers(self, controllers: list[dict[str, Any]]) -> None:
        """Extract strings from Odoo HTTP controllers."""
        for controller in controllers:
            controller_name = controller.get("name", "unknown")
            self._add_string(
                controller.get("route", ""),
                "controller",
                controller_name,
                "route",
                context=f"controller:{controller_name}"
            )

    def _extract_from_security(self, security: dict[str, Any]) -> None:
        """Extract strings from security definitions."""
        for group in security.get("groups", []):
            group_name = group.get("id", "unknown")
            self._add_string(
                group.get("name", ""),
                "security_group",
                group_name,
                "name",
                context=f"group:{group_name}"
            )
            self._add_string(
                group.get("description", ""),
                "security_group",
                group_name,
                "description",
                context=f"group:{group_name}"
            )

    def _add_string(
        self,
        value: str | None,
        source_type: str,
        source_id: str,
        field_name: str,
        context: str = ""
    ) -> None:
        """Add a translatable string if it's non-empty and valid."""
        if not value or not isinstance(value, str):
            return
        value = value.strip()
        if not value or len(value) < 1:
            return
        if self._is_code_identifier(value):
            return
        self.strings.append(TranslatableString(
            msgid=value,
            msgctxt=context,
            source_module=self.module_name,
            source_type=source_type,
            source_id=source_id,
            field_name=field_name
        ))

    @staticmethod
    def _is_code_identifier(value: str) -> bool:
        """Check if value looks like a code identifier rather than translatable text."""
        if not value:
            return False
        if re.match(r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$', value):
            return True
        if re.match(r'^[A-Z_]+$', value):
            return True
        if re.match(r'^[\d.]+$', value):
            return True
        return False

    def _render_pot(self) -> str:
        """Render collected strings as a .pot file."""
        lines = [
            "# Translation template for Odoo module",
            f"# Module: {self.module_name}",
            "# Generator: Factory Build Agent",
            "#",
            "",
            'msgid ""',
            'msgstr ""',
            f'"Content-Type: text/plain; charset=UTF-8\\n"',
            f'"Language: \\n"',
            "",
            "",
        ]

        seen: set[tuple[str, str]] = set()
        for s in self.strings:
            key = (s.msgid, s.msgctxt)
            if key in seen:
                continue
            seen.add(key)
            lines.append(s.to_pot_entry())

        return "\n".join(lines)


class PoFileGenerator:
    """Generates .po (locale-specific) translation files from .pot template."""

    HEADER_TEMPLATE = """\
# Translation for {locale} - {module_name}
# Generated by Factory Build Agent
#
msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"
"Language: {locale}\\n"
"MIME-Version: 1.0\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"
"""

    def generate_po(
        self,
        pot_content: str,
        locale: str,
        translations: dict[str, str] | None = None,
        module_name: str = "",
        charset: str = "UTF-8"
    ) -> str:
        """Generate a .po file from a .pot template.

        Args:
            pot_content: The .pot file content
            locale: Locale code (e.g., 'es_ES', 'en_US')
            translations: Optional dict of {msgid: translation} to pre-fill
            module_name: Module name for header
            charset: Character encoding (default UTF-8)

        Returns:
            Formatted .po file content
        """
        translations = translations or {}

        lines = self.HEADER_TEMPLATE.format(
            locale=locale,
            module_name=module_name or "module"
        ).split("\n")

        lines.append("")
        lines.append("msgid \"\"")
        lines.append("msgstr \"\"")
        lines.append(f"\"Content-Type: text/plain; charset={charset}\\n\"")
        lines.append("")
        lines.append("")

        in_entry = False
        current_entry: dict[str, str] = {}

        for raw_line in pot_content.split("\n"):
            stripped = raw_line.strip()

            if stripped.startswith("#:"):
                if in_entry and current_entry.get("msgid"):
                    self._write_po_entry(lines, current_entry, translations)
                current_entry = {}
                in_entry = True
                current_entry["_comment"] = stripped
            elif stripped.startswith("msgctxt "):
                current_entry["msgctxt"] = stripped[8:].strip('"')
            elif stripped.startswith("msgid "):
                current_entry["msgid"] = stripped[6:].strip('"')
            elif stripped.startswith("msgid_plural"):
                current_entry["msgid_plural"] = stripped
            elif stripped.startswith("msgstr[0] "):
                current_entry["msgstr_0"] = stripped[9:].strip('"')
            elif stripped == 'msgstr ""' and in_entry:
                pass
            elif stripped == "" and in_entry:
                if current_entry.get("msgid"):
                    self._write_po_entry(lines, current_entry, translations)
                current_entry = {}
                in_entry = False

        if current_entry.get("msgid"):
            self._write_po_entry(lines, current_entry, translations)

        return "\n".join(lines)

    def _write_po_entry(
        self,
        lines: list[str],
        entry: dict[str, str],
        translations: dict[str, str]
    ) -> None:
        """Write a single translation entry to .po file."""
        msgid = entry.get("msgid", "")
        if not msgid:
            return

        if entry.get("msgctxt"):
            lines.append(f"msgctxt \"{entry['msgctxt']}\"")

        lines.append(f"msgid \"{msgid}\"")

        translation = translations.get(msgid, "")
        if translation:
            lines.append(f"msgstr \"{translation}\"")
        else:
            lines.append("msgstr \"\"")

        lines.append("")


class OCAi18nStructure:
    """Manages OCA-standard i18n directory structure for Odoo modules."""

    def __init__(self, module_path: Path, module_name: str = ""):
        self.module_path = Path(module_path)
        self.module_name = module_name or self.module_path.name
        self.i18n_dir = self.module_path / "i18n"
        self.pot_file = self.i18n_dir / f"{self.module_name}.pot"

    def ensure_i18n_dir(self) -> None:
        """Create i18n directory if it doesn't exist."""
        self.i18n_dir.mkdir(parents=True, exist_ok=True)

    def write_pot(self, content: str) -> Path:
        """Write the .pot template file.

        Returns:
            Path to the written .pot file
        """
        self.ensure_i18n_dir()
        self.pot_file.write_text(content, encoding="utf-8")
        return self.pot_file

    def write_po(self, locale: str, content: str) -> Path:
        """Write a .po translation file for a locale.

        Args:
            locale: Locale code (e.g., 'es_ES')
            content: The .po file content

        Returns:
            Path to the written .po file
        """
        self.ensure_i18n_dir()
        po_path = self.i18n_dir / f"{locale}.po"
        po_path.write_text(content, encoding="utf-8")
        return po_path

    def list_locales(self) -> list[str]:
        """List available translation locales in the module."""
        if not self.i18n_dir.exists():
            return []
        return [p.stem for p in self.i18n_dir.glob("*.po")]

    def generate_default_es_es(self, pot_content: str, translations: dict[str, str]) -> Path:
        """Generate es_ES.po with default translations.

        Args:
            pot_content: The .pot file content
            translations: Dict of {msgid: msgstr} translations

        Returns:
            Path to the written es_ES.po file
        """
        generator = PoFileGenerator()
        po_content = generator.generate_po(
            pot_content,
            "es_ES",
            translations,
            self.module_name
        )
        return self.write_po("es_ES", po_content)

"""i18n Manager for Odoo modules.

Extracts translatable strings from Python and XML files, generates GNU gettext
.pot template files, and OCA-compliant .po files for Spanish variants (es_ES, es_CL).

Part of M14 feat/14.3: i18n internationalization support.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class I18nReport:
    module_name: str
    language: str = ""
    file_count: int = 0
    strings_found: int = 0
    pot_path: str = ""
    po_paths: list[str] = field(default_factory=list)


class I18nManager:
    """Extracts translatable strings and generates .pot/.po files.

    Usage:
        mgr = I18nManager()
        report = mgr.generate_all(Path("my_module"), "my_module")
        print(report.pot_path)
    """

    PYTHON_TRANSLATABLE = [
        re.compile(r'string\s*=\s*["\']([^"\']+)["\']'),
        re.compile(r'_description\s*=\s*["\']([^"\']+)["\']'),
        re.compile(r'_\(\s*["\']([^"\']+)["\']\s*\)'),
        re.compile(r'label\s*=\s*["\']([^"\']+)["\']'),
        re.compile(r'help\s*=\s*["\']([^"\']+)["\']'),
        re.compile(r'placeholder\s*=\s*["\']([^"\']+)["\']'),
    ]

    XML_TRANSLATABLE = [
        re.compile(r'string\s*=\s*"([^"]+)"'),
    ]

    PO_HEADER = """# Translation of {module} for Odoo.
# Copyright (C) {year} Odoo S.A.
# This file is distributed under the same license as the {module} module.
#
msgid ""
msgstr ""
"Project-Id-Version: {module} {version}\\n"
"Report-Msgid-Bugs-To: \\n"
"POT-Creation-Date: {date}\\n"
"PO-Revision-Date: {date}\\n"
"Last-Translator: Factory Build Agent <fba@autogen>\\n"
"Language-Team: {language_team}\\n"
"Language: {lang_code}\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"
"""

    CHILEAN_ES_VARIANTS: dict[str, str] = {
        "Guardar": "Grabar",
        "guardar": "grabar",
        "Buscar": "Filtrar",
        "buscar": "filtrar",
        "Lista": "Listado",
        "lista": "listado",
        "Listado de": "Listado de",
        "Archivo": "Archivo",
        "archivo": "archivo",
        "Fichero": "Archivo",
        "fichero": "archivo",
        "Imprimir": "Imprimir",
        "imprimir": "imprimir",
        "Exportar": "Exportar",
        "exportar": "exportar",
        "Importar": "Importar",
        "importar": "importar",
        "Cancelar": "Cancelar",
        "cancelar": "cancelar",
        "Confirmar": "Confirmar",
        "confirmar": "confirmar",
        "Eliminar": "Eliminar",
        "eliminar": "eliminar",
        "Editar": "Modificar",
        "editar": "modificar",
        "Crear": "Crear",
        "crear": "crear",
        "Cerrar": "Cerrar",
        "cerrar": "cerrar",
        "Aceptar": "Aceptar",
        "aceptar": "aceptar",
        "Rechazar": "Rechazar",
        "rechazar": "rechazar",
        "Activo": "Activo",
        "activo": "activo",
        "Inactivo": "Inactivo",
        "inactivo": "inactivo",
        "Borrador": "Borrador",
        "borrador": "borrador",
        "Hecho": "Listo",
        "hecho": "listo",
    }

    def extract_strings(self, module_path: Path) -> dict[str, list[str]]:
        """Extract all translatable strings from a module directory.

        Returns a dict with keys 'python' and 'xml', each a list of extracted strings.
        """
        result: dict[str, list[str]] = {"python": [], "xml": []}

        if not module_path.exists():
            return result

        for py_file in module_path.rglob("*.py"):
            if "/tests/" in str(py_file) or "__pycache__" in str(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                for pattern in self.PYTHON_TRANSLATABLE:
                    for match in pattern.finditer(content):
                        s = match.group(1)
                        if s and s not in result["python"]:
                            result["python"].append(s)
            except (OSError, UnicodeDecodeError):
                continue

        for xml_file in module_path.rglob("*.xml"):
            try:
                content = xml_file.read_text(encoding="utf-8")
                for pattern in self.XML_TRANSLATABLE:
                    for match in pattern.finditer(content):
                        s = match.group(1)
                        if s and s not in result["xml"]:
                            result["xml"].append(s)
            except (OSError, UnicodeDecodeError):
                continue

        return result

    def generate_pot(self, strings: dict[str, list[str]], module_name: str, version: str = "18.0") -> str:
        """Generate a .pot template file content."""
        all_strings: list[str] = []
        for category in ("python", "xml"):
            for s in strings.get(category, []):
                if s and s not in all_strings:
                    all_strings.append(s)

        all_strings.sort()

        header = self.PO_HEADER.format(
            module=module_name,
            year=datetime.now(timezone.utc).year,
            version=version,
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M%z"),
            language_team="",
            lang_code="",
        )

        entries = []
        for s in all_strings:
            escaped = self._escape_po_string(s)
            entries.append(f'msgid "{escaped}"\nmsgstr ""\n')

        return header + "\n" + "\n".join(entries)

    def generate_po(
        self,
        strings: dict[str, list[str]],
        module_name: str,
        language: str,
        version: str = "18.0",
        translations: dict[str, str] | None = None,
    ) -> str:
        """Generate a .po file for a specific language.

        Args:
            strings: Extracted strings by category.
            module_name: Module technical name.
            language: Language code (e.g., 'es_ES', 'es_CL').
            version: Odoo version.
            translations: Dict mapping msgid to msgstr. If None, uses identity.
        """
        all_strings: list[str] = []
        for category in ("python", "xml"):
            for s in strings.get(category, []):
                if s and s not in all_strings:
                    all_strings.append(s)

        all_strings.sort()

        lang_map = {
            "es_ES": "Spanish (Spain)",
            "es_CL": "Spanish (Chile)",
        }
        lang_team = lang_map.get(language, f"Language Team for {language}")

        header = self.PO_HEADER.format(
            module=module_name,
            year=datetime.now(timezone.utc).year,
            version=version,
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M%z"),
            language_team=lang_team,
            lang_code=language,
        )

        entries = []
        for s in all_strings:
            escaped_id = self._escape_po_string(s)
            if translations and s in translations:
                msgstr = self._escape_po_string(translations[s])
            else:
                msgstr = escaped_id
            entries.append(f'msgid "{escaped_id}"\nmsgstr "{msgstr}"\n')

        return header + "\n" + "\n".join(entries)

    def generate_all(
        self,
        module_path: Path,
        module_name: str,
        output_dir: Path | None = None,
    ) -> I18nReport:
        """Extract strings and generate all i18n files (.pot, es_ES.po, es_CL.po).

        Args:
            module_path: Path to the Odoo module directory.
            module_name: Technical module name.
            output_dir: Where to write i18n files (default: module_path/i18n).

        Returns:
            I18nReport with paths and stats.
        """
        if output_dir is None:
            output_dir = module_path / "i18n"
        output_dir.mkdir(parents=True, exist_ok=True)

        strings = self.extract_strings(module_path)
        all_count = len(strings.get("python", [])) + len(strings.get("xml", []))

        pot_content = self.generate_pot(strings, module_name)
        pot_path = output_dir / f"{module_name}.pot"
        pot_path.write_text(pot_content, encoding="utf-8")

        es_es_content = self.generate_po(strings, module_name, "es_ES")
        es_es_path = output_dir / "es_ES.po"
        es_es_path.write_text(es_es_content, encoding="utf-8")

        es_cl_content = self.generate_po(
            strings, module_name, "es_CL",
            translations=self.CHILEAN_ES_VARIANTS,
        )
        es_cl_path = output_dir / "es_CL.po"
        es_cl_path.write_text(es_cl_content, encoding="utf-8")

        return I18nReport(
            module_name=module_name,
            language="es",
            file_count=3,
            strings_found=all_count,
            pot_path=str(pot_path),
            po_paths=[str(es_es_path), str(es_cl_path)],
        )

    def _escape_po_string(self, s: str) -> str:
        """Escape a string for PO file format."""
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

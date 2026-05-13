"""Tests for i18n — internationalization (extract .pot, compile .po, OCA structure)."""

import json
from pathlib import Path

import pytest

from fba.i18n import (
    I18nError,
    I18nExtractor,
    OCAi18nStructure,
    PoFileGenerator,
    TranslatableString,
)


def _make_minimal_schema(module_name: str = "test_module", version: str = "18.0.1.0.0") -> dict:
    """Minimal schema.json for testing i18n extraction."""
    return {
        "manifest": {
            "name": module_name,
            "version": version,
            "depends": ["base"],
            "summary": "Test module for i18n",
            "description": "A module that tests i18n extraction",
        },
        "models": [
            {
                "name": "test.model",
                "description": "Test model description",
                "display_name": "Test Model Display",
                "mode": "new",
                "fields": [
                    {"name": "name", "type": "Char", "label": "Name Field", "required": True},
                    {"name": "state", "type": "Selection", "label": "Status", "selection": [
                        ["draft", "Draft State"],
                        ["done", "Done State"],
                    ]},
                ],
            },
        ],
        "views": [
            {"name": "test.model.form", "type": "form", "model": "test.model", "display_name": "Test Form View", "fields": ["name", "state"]},
        ],
        "wizards": [
            {
                "name": "test.wizard",
                "model": "test.wizard",
                "description": "A test wizard",
                "fields": [
                    {"name": "note", "type": "Text", "label": "Wizard Note"},
                ],
            },
        ],
        "workflows": [
            {
                "name": "test.workflow",
                "model": "test.model",
                "states": [
                    {"name": "draft", "description": "Draft state of workflow"},
                    {"name": "done", "description": "Done state of workflow"},
                ],
                "signals": [
                    {"name": "submit", "description": "Submit for approval"},
                ],
                "transitions": [
                    {"from_state": "draft", "to_state": "done", "signal": "submit"},
                ],
            },
        ],
        "reports": [
            {
                "name": "test.report",
                "model": "test.model",
                "report_type": "qweb",
                "report_name": "Test Report",
            },
        ],
        "controllers": [
            {
                "name": "test.controller",
                "route": "/test/controller",
                "model": "test.model",
                "methods": ["GET"],
                "auth": "public",
            },
        ],
        "security": {
            "groups": [
                {"id": "group_user", "name": "User Group", "description": "Standard user group"},
            ],
            "access_rights": [],
            "record_rules": [],
        },
        "data": [],
    }


class TestTranslatableString:
    """Tests for TranslatableString dataclass."""

    def test_to_pot_entry_basic(self):
        s = TranslatableString(msgid="Hello World", source_module="test", source_type="model", source_id="test.model", field_name="name")
        entry = s.to_pot_entry()
        assert 'msgid "Hello World"' in entry
        assert "#: model:test.test.model:name" in entry

    def test_to_pot_entry_with_context(self):
        s = TranslatableString(msgid="Status", msgctxt="field:test.model.state", source_module="test", source_type="field", source_id="test.model", field_name="state")
        entry = s.to_pot_entry()
        assert 'msgctxt "field:test.model.state"' in entry
        assert 'msgid "Status"' in entry

    def test_escape_newlines(self):
        s = TranslatableString(msgid="Line1\nLine2", source_module="test", source_type="model", source_id="test.model", field_name="name")
        entry = s.to_pot_entry()
        assert r"\n" in entry


class TestI18nExtractor:
    """Tests for I18nExtractor — extraction from schema.json."""

    def test_extract_from_manifest(self, tmp_path):
        schema = _make_minimal_schema()
        schema_path = tmp_path / "schema.json"
        schema_path.write_text(json.dumps(schema))

        extractor = I18nExtractor()
        pot = extractor.extract_from_schema(schema_path)

        assert "Test module for i18n" in pot
        assert "A module that tests i18n extraction" in pot
        assert "test_module" in pot

    def test_extract_from_models(self, tmp_path):
        schema = _make_minimal_schema()
        schema_path = tmp_path / "schema.json"
        schema_path.write_text(json.dumps(schema))

        extractor = I18nExtractor()
        pot = extractor.extract_from_schema(schema_path)

        assert "Test model description" in pot
        assert "Test Model Display" in pot
        assert "Name Field" in pot

    def test_extract_selection_field(self, tmp_path):
        schema = _make_minimal_schema()
        schema_path = tmp_path / "schema.json"
        schema_path.write_text(json.dumps(schema))

        extractor = I18nExtractor()
        pot = extractor.extract_from_schema(schema_path)

        assert "Draft State" in pot
        assert "Done State" in pot

    def test_extract_from_wizards(self, tmp_path):
        schema = _make_minimal_schema()
        schema_path = tmp_path / "schema.json"
        schema_path.write_text(json.dumps(schema))

        extractor = I18nExtractor()
        pot = extractor.extract_from_schema(schema_path)

        assert "A test wizard" in pot
        assert "Wizard Note" in pot

    def test_extract_from_workflow_states(self, tmp_path):
        schema = _make_minimal_schema()
        schema_path = tmp_path / "schema.json"
        schema_path.write_text(json.dumps(schema))

        extractor = I18nExtractor()
        pot = extractor.extract_from_schema(schema_path)

        assert "Draft state of workflow" in pot
        assert "Done state of workflow" in pot
        assert "Submit for approval" in pot

    def test_extract_ignores_code_identifiers(self, tmp_path):
        schema = _make_minimal_schema()
        schema_path = tmp_path / "schema.json"
        schema_path.write_text(json.dumps(schema))

        extractor = I18nExtractor()
        pot = extractor.extract_from_schema(schema_path)

        assert "test.model" not in pot.split("#:")[0]
        assert "vehicle.vehicle" not in pot

    def test_extract_nonexistent_schema_raises(self, tmp_path):
        extractor = I18nExtractor()
        with pytest.raises(I18nError, match="Schema not found"):
            extractor.extract_from_schema(tmp_path / "nonexistent.json")

    def test_extract_invalid_json_raises(self, tmp_path):
        bad_schema = tmp_path / "bad.json"
        bad_schema.write_text("{invalid json")
        extractor = I18nExtractor()
        with pytest.raises(I18nError, match="Invalid JSON"):
            extractor.extract_from_schema(bad_schema)


class TestPoFileGenerator:
    """Tests for PoFileGenerator — .po file generation."""

    def test_generate_po_basic(self):
        pot = '''msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"

msgid "Hello"
msgstr ""
'''
        generator = PoFileGenerator()
        po = generator.generate_po(pot, "es_ES", {"Hello": "Hola"}, "test_module")

        assert "es_ES" in po
        assert "test_module" in po
        assert '"Hola"' in po or 'Hola' in po

    def test_generate_po_header(self):
        pot = 'msgid ""\nmsgstr ""\n\nmsgid "Test"\nmsgstr ""\n'
        generator = PoFileGenerator()
        po = generator.generate_po(pot, "es_ES", {}, "my_module")

        assert "es_ES" in po
        assert "my_module" in po
        assert "Content-Type" in po
        assert "charset=UTF-8" in po

    def test_generate_po_with_translations(self):
        pot = '''#: model:test.model:name
msgid "Hello"
msgstr ""

#: model:test.model:desc
msgid "World"
msgstr ""
'''
        generator = PoFileGenerator()
        translations = {"Hello": "Hola", "World": "Mundo"}
        po = generator.generate_po(pot, "es_ES", translations, "test_module")

        assert "Hola" in po
        assert "Mundo" in po


class TestOCAi18nStructure:
    """Tests for OCAi18nStructure — OCA-ready directory structure."""

    def test_ensure_i18n_dir_creates_directory(self, tmp_path):
        module_path = tmp_path / "test_module"
        module_path.mkdir()
        struct = OCAi18nStructure(module_path, "test_module")

        struct.ensure_i18n_dir()

        assert (module_path / "i18n").is_dir()

    def test_write_pot(self, tmp_path):
        module_path = tmp_path / "test_module"
        module_path.mkdir()
        struct = OCAi18nStructure(module_path, "test_module")

        pot_content = 'msgid ""\nmsgstr ""\n\nmsgid "Test"\nmsgstr ""\n'
        pot_path = struct.write_pot(pot_content)

        assert pot_path.exists()
        assert pot_path.name == "test_module.pot"
        assert pot_path.read_text() == pot_content

    def test_write_po(self, tmp_path):
        module_path = tmp_path / "test_module"
        module_path.mkdir()
        struct = OCAi18nStructure(module_path, "test_module")

        po_content = 'msgid ""\nmsgstr ""\n\nmsgid "Test"\nmsgstr "Prueba"\n'
        po_path = struct.write_po("es_ES", po_content)

        assert po_path.exists()
        assert po_path.name == "es_ES.po"
        assert po_path.read_text() == po_content

    def test_list_locales_empty(self, tmp_path):
        module_path = tmp_path / "test_module"
        module_path.mkdir()
        struct = OCAi18nStructure(module_path, "test_module")

        assert struct.list_locales() == []

    def test_list_locales(self, tmp_path):
        module_path = tmp_path / "test_module"
        module_path.mkdir()
        i18n_dir = module_path / "i18n"
        i18n_dir.mkdir()
        (i18n_dir / "es_ES.po").write_text("content")
        (i18n_dir / "en_US.po").write_text("content")

        struct = OCAi18nStructure(module_path, "test_module")
        locales = struct.list_locales()

        assert set(locales) == {"es_ES", "en_US"}

    def test_generate_default_es_es(self, tmp_path):
        module_path = tmp_path / "test_module"
        module_path.mkdir()
        struct = OCAi18nStructure(module_path, "test_module")

        pot_content = 'msgid ""\nmsgstr ""\n\nmsgid "Hello"\nmsgstr ""\n'
        translations = {"Hello": "Hola"}
        po_path = struct.generate_default_es_es(pot_content, translations)

        assert po_path.exists()
        assert po_path.name == "es_ES.po"
        content = po_path.read_text()
        assert "Hola" in content


class TestI18nE2E:
    """End-to-end tests for i18n extraction and compilation."""

    def test_extract_and_compile_es_es(self, tmp_path):
        module_path = tmp_path / "test_module"
        module_path.mkdir()
        i18n_dir = module_path / "i18n"
        i18n_dir.mkdir()

        schema = _make_minimal_schema("test_module")
        schema_path = tmp_path / "schema.json"
        schema_path.write_text(json.dumps(schema))

        extractor = I18nExtractor()
        pot = extractor.extract_from_schema(schema_path)

        translations = {
            "Test module for i18n": "Modulo de prueba para i18n",
            "A module that tests i18n extraction": "Un modulo que prueba la extraccion de i18n",
            "Test model description": "Descripcion del modelo de prueba",
            "Name Field": "Campo de nombre",
            "Draft State": "Estado borrador",
            "Done State": "Estado hecho",
        }

        generator = PoFileGenerator()
        po = generator.generate_po(pot, "es_ES", translations, "test_module")

        po_path = i18n_dir / "es_ES.po"
        po_path.write_text(po, encoding="utf-8")

        assert po_path.exists()
        assert "es_ES" in po
        assert "Modulo de prueba" in po

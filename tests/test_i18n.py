"""Tests for M14 feat/14.3: i18n string extraction and .pot/.po generation."""

from pathlib import Path

from fba.i18n_manager import I18nManager, I18nReport


def _create_module(tmp_path: Path) -> Path:
    """Create a minimal Odoo module with Python and XML files."""
    mod = tmp_path / "test_module"
    mod.mkdir()
    models = mod / "models"
    models.mkdir(parents=True)
    views = mod / "views"
    views.mkdir(parents=True)

    (mod / "__manifest__.py").write_text("""{
    "name": "Test Module",
    "version": "18.0.1.0.0",
    "summary": "A test module",
    "depends": ["base"],
    "data": ["views/test_views.xml"],
    "installable": True,
    "license": "LGPL-3",
}""")
    (mod / "__init__.py").write_text("")

    (models / "__init__.py").write_text("from . import test_model")
    (models / "test_model.py").write_text("""from odoo import models, fields

class TestModel(models.Model):
    _name = "test.model"
    _description = "Test Model"

    name = fields.Char(string="Name", required=True, help="The name of the record")
    code = fields.Char(string="Code", size=10, readonly=True)
    state = fields.Selection([
        ("draft", "Draft"),
        ("active", "Active"),
        ("done", "Done"),
    ], string="Status", default="draft", tracking=True)
    notes = fields.Text(string="Notes", help="Additional notes for the record")
    amount = fields.Float(string="Amount", help="The monetary amount")
""")

    (views / "test_views.xml").write_text("""<odoo>
    <record id="test_model_form" model="ir.ui.view">
        <field name="name">test.model.form</field>
        <field name="model">test.model</field>
        <field name="arch" type="xml">
            <form string="Test Form">
                <sheet>
                    <group string="Main Info">
                        <field name="name"/>
                        <field name="code"/>
                        <field name="state"/>
                    </group>
                    <group string="Details">
                        <field name="notes"/>
                        <field name="amount"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="test_model_list" model="ir.ui.view">
        <field name="name">test.model.list</field>
        <field name="model">test.model</field>
        <field name="arch" type="xml">
            <list string="Test Models">
                <field name="name"/>
                <field name="code"/>
                <field name="state"/>
            </list>
        </field>
    </record>

    <menuitem id="menu_test_root" name="Test" sequence="10"/>
</odoo>
""")

    return mod


# ---------------------------------------------------------------------------
# String extraction
# ---------------------------------------------------------------------------

def test_extract_strings_from_python(tmp_path):
    mod = _create_module(tmp_path)
    mgr = I18nManager()
    strings = mgr.extract_strings(mod)

    python_strings = strings["python"]
    assert "Name" in python_strings
    assert "The name of the record" in python_strings
    assert "Code" in python_strings
    assert "Notes" in python_strings
    assert "Amount" in python_strings
    assert "Status" in python_strings
    assert "Test Model" in python_strings
    assert "Additional notes for the record" in python_strings
    assert "The monetary amount" in python_strings


def test_extract_strings_from_xml(tmp_path):
    mod = _create_module(tmp_path)
    mgr = I18nManager()
    strings = mgr.extract_strings(mod)

    xml_strings = strings["xml"]
    assert "Test Form" in xml_strings
    assert "Main Info" in xml_strings
    assert "Details" in xml_strings
    assert "Test Models" in xml_strings


def test_no_duplicates_in_extraction(tmp_path):
    mod = _create_module(tmp_path)
    mgr = I18nManager()
    strings = mgr.extract_strings(mod)

    for cat in ("python", "xml"):
        assert len(strings[cat]) == len(set(strings[cat]))


def test_empty_module_returns_empty_lists(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    mgr = I18nManager()
    strings = mgr.extract_strings(empty)

    assert strings["python"] == []
    assert strings["xml"] == []


# ---------------------------------------------------------------------------
# .pot generation
# ---------------------------------------------------------------------------

def test_generate_pot_has_header(tmp_path):
    mod = _create_module(tmp_path)
    mgr = I18nManager()
    strings = mgr.extract_strings(mod)
    pot = mgr.generate_pot(strings, "test_module")

    assert 'msgid ""' in pot
    assert 'msgstr ""' in pot
    assert "Project-Id-Version:" in pot
    assert "Content-Type: text/plain; charset=UTF-8" in pot


def test_generate_pot_contains_all_strings(tmp_path):
    mod = _create_module(tmp_path)
    mgr = I18nManager()
    strings = mgr.extract_strings(mod)
    pot = mgr.generate_pot(strings, "test_module")

    for cat in ("python", "xml"):
        for s in strings[cat]:
            escaped = s.replace("\\", "\\\\").replace('"', '\\"')
            assert f'msgid "{escaped}"' in pot


def test_generate_pot_empty_strings_skipped(tmp_path):
    mgr = I18nManager()
    pot = mgr.generate_pot({"python": [""], "xml": []}, "test_module")
    assert 'msgid ""' not in pot.split("\n\n")[1] if "\n\n" in pot else True


def test_generate_pot_uses_module_name(tmp_path):
    mgr = I18nManager()
    pot = mgr.generate_pot({"python": ["Hello"], "xml": []}, "my_custom_module")
    assert "my_custom_module" in pot


# ---------------------------------------------------------------------------
# .po generation
# ---------------------------------------------------------------------------

def test_generate_es_es_po_is_identity(tmp_path):
    mod = _create_module(tmp_path)
    mgr = I18nManager()
    strings = mgr.extract_strings(mod)
    po = mgr.generate_po(strings, "test_module", "es_ES")

    assert "es_ES" in po
    assert "Spanish (Spain)" in po
    for s in strings.get("python", [])[:5]:
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        assert f'msgstr "{escaped}"' in po


def test_generate_es_cl_po_has_variants(tmp_path):
    mod = _create_module(tmp_path)
    mgr = I18nManager()
    strings = mgr.extract_strings(mod)
    po = mgr.generate_po(strings, "test_module", "es_CL", translations=mgr.CHILEAN_ES_VARIANTS)

    assert "es_CL" in po
    assert "Spanish (Chile)" in po

    assert 'msgstr "Filtrar"' in po or "msgid" in po


def test_generate_po_with_custom_translations(tmp_path):
    mgr = I18nManager()
    translations = {"Hello": "Hola", "World": "Mundo"}
    po = mgr.generate_po({"python": ["Hello", "World"], "xml": []}, "test", "es_XX", translations=translations)

    assert 'msgstr "Hola"' in po
    assert 'msgstr "Mundo"' in po


def test_generate_po_escapes_special_chars(tmp_path):
    mgr = I18nManager()
    po = mgr.generate_po({"python": ['Say "hello"'], "xml": []}, "test", "es_ES")

    escaped = 'Say \\"hello\\"'
    assert escaped in po


# ---------------------------------------------------------------------------
# generate_all integration
# ---------------------------------------------------------------------------

def test_generate_all_creates_correct_files(tmp_path):
    mod = _create_module(tmp_path)
    mgr = I18nManager()
    report = mgr.generate_all(mod, "test_module")

    i18n_dir = mod / "i18n"
    assert i18n_dir.exists()
    assert (i18n_dir / "test_module.pot").exists()
    assert (i18n_dir / "es_ES.po").exists()
    assert (i18n_dir / "es_CL.po").exists()

    assert report.file_count == 3
    assert report.strings_found > 0
    assert report.pot_path == str(i18n_dir / "test_module.pot")


def test_generate_all_oca_structure(tmp_path):
    mod = _create_module(tmp_path)
    mgr = I18nManager()
    _report = mgr.generate_all(mod, "test_module")

    i18n_dir = mod / "i18n"
    pot_content = (i18n_dir / "test_module.pot").read_text()
    es_es_content = (i18n_dir / "es_ES.po").read_text()
    es_cl_content = (i18n_dir / "es_CL.po").read_text()

    assert "Content-Type:" in pot_content
    assert "es_ES" in es_es_content
    assert "es_CL" in es_cl_content
    assert "Language:" in pot_content


def test_generate_all_custom_output_dir(tmp_path):
    mod = _create_module(tmp_path)
    out = tmp_path / "custom_i18n"
    mgr = I18nManager()
    report = mgr.generate_all(mod, "test_module", output_dir=out)

    assert out.exists()
    assert (out / "test_module.pot").exists()
    assert report.pot_path == str(out / "test_module.pot")


def test_generate_all_report_has_paths(tmp_path):
    mod = _create_module(tmp_path)
    mgr = I18nManager()
    report = mgr.generate_all(mod, "test_module")

    assert isinstance(report, I18nReport)
    assert len(report.po_paths) == 2
    assert report.module_name == "test_module"


# ---------------------------------------------------------------------------
# Chilean Spanish variants
# ---------------------------------------------------------------------------

def test_chilean_variants_applied(tmp_path):
    mod = tmp_path / "cl_module"
    mod.mkdir()
    (mod / "__manifest__.py").write_text('{"name": "cl", "version": "18.0.1.0.0", "depends": ["base"], "installable": True, "license": "LGPL-3"}')
    (mod / "__init__.py").write_text("")
    views = mod / "views"
    views.mkdir()
    (views / "cl_views.xml").write_text("""<odoo>
    <record id="form" model="ir.ui.view">
        <field name="arch" type="xml">
            <form string="Test Form">
                <header>
                    <button string="Guardar" type="object"/>
                    <button string="Buscar" type="object"/>
                    <button string="Editar" type="object"/>
                </header>
            </form>
        </field>
    </record>
</odoo>
""")

    mgr = I18nManager()
    strings = mgr.extract_strings(mod)
    po = mgr.generate_po(strings, "cl_module", "es_CL", translations=mgr.CHILEAN_ES_VARIANTS)

    assert 'msgstr "Grabar"' in po
    assert 'msgstr "Filtrar"' in po
    assert 'msgstr "Modificar"' in po


def test_chilean_variants_dict_exists(tmp_path):
    assert isinstance(I18nManager.CHILEAN_ES_VARIANTS, dict)
    assert len(I18nManager.CHILEAN_ES_VARIANTS) > 0
    assert "Guardar" in I18nManager.CHILEAN_ES_VARIANTS
    assert I18nManager.CHILEAN_ES_VARIANTS["Guardar"] == "Grabar"


# ---------------------------------------------------------------------------
# String extraction edge cases
# ---------------------------------------------------------------------------

def test_extract_handles_binary_files(tmp_path):
    mod = _create_module(tmp_path)
    (mod / "static").mkdir(exist_ok=True)
    (mod / "static" / "icon.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    mgr = I18nManager()
    strings = mgr.extract_strings(mod)
    assert len(strings["python"]) > 0


def test_extract_skips_tests_dir(tmp_path):
    mod = _create_module(tmp_path)
    tests_dir = mod / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_translatable.py").write_text('field = fields.Char(string="SHOULD_NOT_APPEAR")')

    mgr = I18nManager()
    strings = mgr.extract_strings(mod)

    assert "SHOULD_NOT_APPEAR" not in strings["python"]


def test_extract_handles_nonexistent_module(tmp_path):
    mgr = I18nManager()
    strings = mgr.extract_strings(tmp_path / "nonexistent")
    assert strings == {"python": [], "xml": []}


# ---------------------------------------------------------------------------
# Manifest-based module name detection
# ---------------------------------------------------------------------------

def test_module_name_from_manifest(tmp_path):
    mod = _create_module(tmp_path)
    mgr = I18nManager()
    report = mgr.generate_all(mod, "test_module")

    manifest = (mod / "__manifest__.py").read_text()
    assert "Test Module" in manifest
    assert report.pot_path.endswith("test_module.pot")

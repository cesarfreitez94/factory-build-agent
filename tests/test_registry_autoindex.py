import json
from pathlib import Path

from click.testing import CliRunner

from fba.cli import main
from fba.module_registry import ModuleRegistry
from fba.registry_indexer import RegistryIndexer, normalize_odoo_version


def _write_demo_addon(addons_dir: Path, module_name: str = "demo_helpdesk") -> Path:
    addon = addons_dir / module_name
    (addon / "models").mkdir(parents=True)
    (addon / "wizards").mkdir()
    (addon / "controllers").mkdir()
    (addon / "views").mkdir()
    (addon / "security").mkdir()
    (addon / "data").mkdir()
    (addon / "demo").mkdir()
    (addon / "static" / "src" / "js").mkdir(parents=True)
    (addon / "static" / "src" / "xml").mkdir(parents=True)

    (addon / "__manifest__.py").write_text(
        """
{
    "name": "Demo Helpdesk",
    "summary": "Indexed demo addon",
    "version": "18.0.1.0.0",
    "depends": ["base", "mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/demo_ticket_views.xml",
        "data/cron.xml"
    ],
    "demo": ["demo/demo_ticket.xml"],
}
""".strip()
    )
    (addon / "models" / "demo_ticket.py").write_text(
        """
from odoo import fields, models


class DemoTicket(models.Model):
    _name = "demo.ticket"
    _description = "Demo Ticket"
    _inherit = ["mail.thread"]

    name = fields.Char(string="Name", required=True)
    partner_id = fields.Many2one("res.partner", string="Partner")
    amount = fields.Float(string="Amount")
""".strip()
    )
    (addon / "wizards" / "demo_ticket_wizard.py").write_text(
        """
from odoo import fields, models


class DemoTicketWizard(models.TransientModel):
    _name = "demo.ticket.wizard"
    _description = "Demo Ticket Wizard"

    ticket_id = fields.Many2one("demo.ticket", string="Ticket")
""".strip()
    )
    (addon / "controllers" / "main.py").write_text(
        """
from odoo import http


class DemoController(http.Controller):
    @http.route("/demo/ticket", type="json", auth="user", methods=["POST"])
    def create_ticket(self):
        return {}
""".strip()
    )
    (addon / "views" / "demo_ticket_views.xml").write_text(
        """
<odoo>
  <record id="view_demo_ticket_form" model="ir.ui.view">
    <field name="name">demo.ticket.form</field>
    <field name="model">demo.ticket</field>
    <field name="arch" type="xml">
      <form>
        <field name="name"/>
      </form>
    </field>
  </record>
  <record id="view_demo_ticket_list" model="ir.ui.view">
    <field name="name">demo.ticket.list</field>
    <field name="model">demo.ticket</field>
    <field name="arch" type="xml">
      <tree>
        <field name="name"/>
      </tree>
    </field>
  </record>
  <record id="action_report_demo_ticket" model="ir.actions.report">
    <field name="name">Demo Ticket</field>
    <field name="model">demo.ticket</field>
    <field name="report_name">demo_helpdesk.report_demo_ticket</field>
  </record>
  <template id="report_demo_ticket">
    <t t-call="web.html_container"/>
  </template>
</odoo>
""".strip()
    )
    (addon / "security" / "security.xml").write_text(
        """
<odoo>
  <record id="group_demo_user" model="res.groups">
    <field name="name">Demo User</field>
  </record>
  <record id="rule_demo_ticket_user" model="ir.rule">
    <field name="name">Demo ticket users</field>
    <field name="model_id" ref="model_demo_ticket"/>
  </record>
</odoo>
""".strip()
    )
    (addon / "security" / "ir.model.access.csv").write_text(
        "\n".join([
            "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink",
            "access_demo_ticket_user,demo.ticket user,model_demo_ticket,group_demo_user,1,1,1,0",
        ])
    )
    (addon / "data" / "cron.xml").write_text(
        """
<odoo>
  <record id="ir_cron_demo_ticket" model="ir.cron">
    <field name="name">Demo Ticket Cron</field>
    <field name="model_id" ref="model_demo_ticket"/>
  </record>
</odoo>
""".strip()
    )
    (addon / "demo" / "demo_ticket.xml").write_text("<odoo/>")
    (addon / "static" / "src" / "js" / "demo_widget.js").write_text(
        """
/** @odoo-module **/
import { Component } from "@odoo/owl";

export class DemoWidget extends Component {}
""".strip()
    )
    (addon / "static" / "src" / "xml" / "demo_widget.xml").write_text(
        """
<templates>
  <t t-name="demo_helpdesk.DemoWidget"/>
</templates>
""".strip()
    )
    return addon


def _project_with_registry(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    factory = project / ".factory"
    factory.mkdir(parents=True)
    (factory / "module_registry.json").write_text(json.dumps({
        "odoo_version": "18.0",
        "modules": {
            "base": {"description": "Base", "models": ["res.partner"]},
            "demo_helpdesk": {"description": "Old", "models": ["old.model"]},
        },
    }))
    return project


def test_normalize_odoo_version_accepts_common_forms():
    assert normalize_odoo_version("18") == "18.0"
    assert normalize_odoo_version("v18") == "18.0"
    assert normalize_odoo_version("odoo-18.0") == "18.0"


def test_indexes_manifest_models_fields_and_artifacts(tmp_path):
    project = _project_with_registry(tmp_path)
    addon = _write_demo_addon(tmp_path / "addons")

    result = RegistryIndexer(project).index(addon, odoo_version="v18")

    assert result.odoo_version == "18.0"
    assert result.module_names == ["demo_helpdesk"]
    assert result.registry_changed is True
    assert result.index_changed is True

    index = json.loads((project / ".factory" / "registry_index.json").read_text())
    module = index["modules"]["demo_helpdesk"]

    assert module["manifest"]["name"] == "Demo Helpdesk"
    assert module["depends"] == ["base", "mail"]
    assert {m["name"] for m in module["models"]} == {"demo.ticket", "demo.ticket.wizard"}
    ticket = next(m for m in module["models"] if m["name"] == "demo.ticket")
    assert {f["name"] for f in ticket["fields"]} == {"amount", "name", "partner_id"}
    assert next(f for f in ticket["fields"] if f["name"] == "partner_id")["relation"] == "res.partner"
    assert {v["type"] for v in module["views"]} == {"form", "list"}
    assert module["controllers"][0]["routes"][0]["routes"] == ["/demo/ticket"]
    assert module["reports"]
    assert module["crons"]
    assert module["wizards"][0]["name"] == "demo.ticket.wizard"
    assert len(module["owl_components"]) == 2
    assert module["security"]["access_rights"][0]["model_id:id"] == "model_demo_ticket"
    assert "security/ir.model.access.csv" in module["security"]["files"]
    assert module["data_files"]
    assert module["demo_files"] == ["demo/demo_ticket.xml"]


def test_updates_compatible_module_registry_with_new_priority(tmp_path):
    project = _project_with_registry(tmp_path)
    addon = _write_demo_addon(tmp_path / "addons")

    RegistryIndexer(project).index(addon, odoo_version="18.0")

    registry = json.loads((project / ".factory" / "module_registry.json").read_text())
    assert registry["registry_version"] == "1.0"
    assert registry["modules"]["base"]["models"] == ["res.partner"]
    assert registry["modules"]["demo_helpdesk"]["models"] == ["demo.ticket", "demo.ticket.wizard"]
    assert registry["modules"]["demo_helpdesk"]["registry_index"] == "registry_index.json"

    loaded = ModuleRegistry(project)
    assert loaded.lookup("demo.ticket")["module"] == "demo_helpdesk"


def test_reindex_unchanged_addon_does_not_rewrite(tmp_path):
    project = _project_with_registry(tmp_path)
    addon = _write_demo_addon(tmp_path / "addons")

    first = RegistryIndexer(project).index(addon, odoo_version="18.0")
    registry_before = (project / ".factory" / "module_registry.json").read_text()
    index_before = (project / ".factory" / "registry_index.json").read_text()

    second = RegistryIndexer(project).index(addon, odoo_version="18.0")

    assert first.registry_changed is True
    assert first.index_changed is True
    assert second.registry_changed is False
    assert second.index_changed is False
    assert (project / ".factory" / "module_registry.json").read_text() == registry_before
    assert (project / ".factory" / "registry_index.json").read_text() == index_before


def test_indexes_addons_directory_with_multiple_modules(tmp_path):
    project = _project_with_registry(tmp_path)
    addons = tmp_path / "addons"
    _write_demo_addon(addons, "demo_helpdesk")
    _write_demo_addon(addons, "demo_sales")

    result = RegistryIndexer(project).index(addons, odoo_version="18")

    assert result.module_names == ["demo_helpdesk", "demo_sales"]
    index = json.loads((project / ".factory" / "registry_index.json").read_text())
    assert sorted(index["modules"]) == ["demo_helpdesk", "demo_sales"]


def test_registry_cli_index_and_inspect(tmp_path):
    project = _project_with_registry(tmp_path)
    addon = _write_demo_addon(tmp_path / "addons")
    runner = CliRunner()

    index_result = runner.invoke(
        main,
        ["registry", "index", str(addon), "--odoo-version", "18", "-d", str(project)],
    )
    assert index_result.exit_code == 0
    assert "Registry index completed" in index_result.output
    assert "demo_helpdesk" in index_result.output

    inspect_result = runner.invoke(
        main,
        ["registry", "inspect", "demo_helpdesk", "-d", str(project)],
    )
    assert inspect_result.exit_code == 0
    assert "Module: demo_helpdesk" in inspect_result.output
    assert "Odoo version: 18.0" in inspect_result.output
    assert "models: 2" in inspect_result.output
    assert "demo.ticket" in inspect_result.output

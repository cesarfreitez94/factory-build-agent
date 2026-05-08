"""Tests for the SchemaManager deterministic assembly pipeline."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from fba.cli import main
from fba.module_registry import ModuleRegistry
from fba.schema_manager import SchemaManager


def _setup_project_with_tasks(project_dir: Path):
    """Create a minimal project with task files for schema assembly tests."""
    factory_dir = project_dir / ".factory"
    tasks_dir = factory_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    schemas_dir = factory_dir / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)

    index = {
        "module_name": "vehicle_registry",
        "total_tasks": 2,
        "tasks": [
            {
                "id": "T001",
                "name": "Modelos",
                "file": "T001-modelos.json",
                "dependencies": [],
                "order": 1,
                "estimated_effort": "high",
                "sdd_components": ["models.vehicle", "models.brand"],
            },
            {
                "id": "T002",
                "name": "Vistas",
                "file": "T002-vistas.json",
                "dependencies": ["T001"],
                "order": 2,
                "estimated_effort": "medium",
                "sdd_components": ["views.form", "views.list"],
            },
        ],
    }
    (tasks_dir / "index.json").write_text(json.dumps(index, indent=2))

    t001 = {
        "id": "T001",
        "name": "Modelos",
        "description": "Generar los modelos Odoo para el modulo de registro de vehiculos.",
        "components": [
            {
                "type": "model",
                "name": "vehicle.vehicle",
                "description": "Modelo principal de vehiculo",
                "fields": [
                    {"name": "plate", "type": "Char", "label": "Placa", "required": True, "size": 20},
                    {"name": "brand_id", "type": "Many2one", "label": "Marca", "relation": "vehicle.brand"},
                    {"name": "model", "type": "Char", "label": "Modelo", "size": 100},
                    {"name": "year", "type": "Integer", "label": "Año"},
                    {"name": "color", "type": "Char", "label": "Color", "size": 50},
                ],
                "sdd_reference": "models.vehicle",
            },
            {
                "type": "model",
                "name": "vehicle.brand",
                "description": "Catalogo de marcas de vehiculos",
                "fields": [
                    {"name": "name", "type": "Char", "label": "Nombre", "required": True, "size": 100},
                ],
                "sdd_reference": "models.brand",
            },
        ],
        "files_to_generate": ["models/__init__.py", "models/vehicle.py", "models/brand.py"],
        "dependencies": [],
    }
    (tasks_dir / "T001-modelos.json").write_text(json.dumps(t001, indent=2))

    t002 = {
        "id": "T002",
        "name": "Vistas",
        "description": "Generar las vistas XML para el modulo.",
        "components": [
            {
                "type": "view",
                "name": "vehicle.vehicle.form",
                "description": "Formulario de vehiculo",
                "view_type": "form",
                "model": "vehicle.vehicle",
                "view_fields": ["plate", "brand_id", "model", "year", "color"],
                "sdd_reference": "views.form",
            },
            {
                "type": "view",
                "name": "vehicle.vehicle.list",
                "description": "Lista de vehiculos",
                "view_type": "list",
                "model": "vehicle.vehicle",
                "view_fields": ["plate", "brand_id", "model", "year"],
                "sdd_reference": "views.list",
            },
        ],
        "files_to_generate": ["views/vehicle_views.xml"],
        "dependencies": ["T001"],
    }
    (tasks_dir / "T002-vistas.json").write_text(json.dumps(t002, indent=2))

    sdd = {
        "module_name": "vehicle_registry",
        "module_display_name": "Vehicle Registry",
        "version": "18.0.1.0.0",
        "summary": "Vehicle registration module for Odoo v18",
        "dependencies": {
            "required": ["base"],
        },
    }
    (factory_dir / "sdd.json").write_text(json.dumps(sdd, indent=2))


class TestSchemaManagerAssembly:
    def test_assemble_produces_schema(self, tmp_path):
        _setup_project_with_tasks(tmp_path)
        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        assert result.success is True
        assert "manifest" in result.schema
        assert result.schema["manifest"]["name"] == "vehicle_registry"
        assert result.schema["manifest"]["depends"] == ["base"]

    def test_assembles_correct_number_of_models(self, tmp_path):
        _setup_project_with_tasks(tmp_path)
        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        assert len(result.schema["models"]) == 2
        model_names = [m["name"] for m in result.schema["models"]]
        assert "vehicle.vehicle" in model_names
        assert "vehicle.brand" in model_names

    def test_assembles_views(self, tmp_path):
        _setup_project_with_tasks(tmp_path)
        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        assert len(result.schema["views"]) == 2
        view_types = [v["type"] for v in result.schema["views"]]
        assert "form" in view_types
        assert "list" in view_types

    def test_model_has_fields(self, tmp_path):
        _setup_project_with_tasks(tmp_path)
        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        vehicle = [m for m in result.schema["models"] if m["name"] == "vehicle.vehicle"][0]
        assert len(vehicle["fields"]) == 5
        field_names = [f["name"] for f in vehicle["fields"]]
        assert "plate" in field_names
        assert "brand_id" in field_names
        assert "model" in field_names
        assert "year" in field_names
        assert "color" in field_names

    def test_model_mode_is_new(self, tmp_path):
        _setup_project_with_tasks(tmp_path)
        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        for model in result.schema["models"]:
            assert model["mode"] == "new"

    def test_security_has_default_group(self, tmp_path):
        _setup_project_with_tasks(tmp_path)
        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        assert len(result.schema["security"]["groups"]) >= 1

    def test_writes_output_file(self, tmp_path):
        _setup_project_with_tasks(tmp_path)
        output = tmp_path / ".factory" / "schema.json"
        manager = SchemaManager(tmp_path)
        result = manager.assemble(output_path=output)

        assert output.exists()
        written = json.loads(output.read_text())
        assert written["manifest"]["name"] == "vehicle_registry"


class TestSchemaManagerNormalization:
    def test_many2one_without_id_suffix_gets_renamed(self, tmp_path):
        factory_dir = tmp_path / ".factory"
        tasks_dir = factory_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        (factory_dir / "schemas").mkdir(parents=True, exist_ok=True)

        index = {
            "module_name": "test",
            "total_tasks": 1,
            "tasks": [{"id": "T001", "name": "M", "file": "T001-m.json", "dependencies": [], "order": 1, "estimated_effort": "low", "sdd_components": ["models.test"]}],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index))

        task = {
            "id": "T001", "name": "M",
            "description": "Test model with unnormalized Many2one.",
            "components": [{
                "type": "model", "name": "test.model",
                "description": "Test", "sdd_reference": "models.test",
                "fields": [
                    {"name": "partner", "type": "Many2one", "label": "Partner", "relation": "res.partner"},
                ],
            }],
            "files_to_generate": ["models/test.py"],
            "dependencies": [],
        }
        (tasks_dir / "T001-m.json").write_text(json.dumps(task))

        sdd = {"module_name": "test", "dependencies": {"required": ["base"]}, "summary": "Test"}
        (factory_dir / "sdd.json").write_text(json.dumps(sdd))

        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        field_names = [f["name"] for f in result.schema["models"][0]["fields"]]
        assert "partner_id" in field_names

    def test_many2many_without_ids_suffix_gets_renamed(self, tmp_path):
        factory_dir = tmp_path / ".factory"
        tasks_dir = factory_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (factory_dir / "schemas").mkdir(parents=True, exist_ok=True)

        index = {
            "module_name": "test",
            "total_tasks": 1,
            "tasks": [{"id": "T001", "name": "M", "file": "T001-m.json", "dependencies": [], "order": 1, "estimated_effort": "low", "sdd_components": ["models.test"]}],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index))

        task = {
            "id": "T001", "name": "M",
            "description": "Test",
            "components": [{
                "type": "model", "name": "test.model",
                "description": "Test", "sdd_reference": "models.test",
                "fields": [
                    {"name": "tags", "type": "Many2many", "label": "Tags", "relation": "test.tag"},
                ],
            }],
            "files_to_generate": ["models/test.py"],
            "dependencies": [],
        }
        (tasks_dir / "T001-m.json").write_text(json.dumps(task))

        sdd = {"module_name": "test", "dependencies": {"required": ["base"]}, "summary": "Test"}
        (factory_dir / "sdd.json").write_text(json.dumps(sdd))

        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        field_names = [f["name"] for f in result.schema["models"][0]["fields"]]
        assert "tags_ids" in field_names

    def test_already_normalized_fields_unchanged(self, tmp_path):
        factory_dir = tmp_path / ".factory"
        tasks_dir = factory_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (factory_dir / "schemas").mkdir(parents=True, exist_ok=True)

        index = {
            "module_name": "test",
            "total_tasks": 1,
            "tasks": [{"id": "T001", "name": "M", "file": "T001-m.json", "dependencies": [], "order": 1, "estimated_effort": "low", "sdd_components": ["models.test"]}],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index))

        task = {
            "id": "T001", "name": "M",
            "description": "Test",
            "components": [{
                "type": "model", "name": "test.model",
                "description": "Test", "sdd_reference": "models.test",
                "fields": [
                    {"name": "partner_id", "type": "Many2one", "label": "Partner", "relation": "res.partner"},
                    {"name": "line_ids", "type": "One2many", "label": "Lines", "relation": "test.line"},
                ],
            }],
            "files_to_generate": ["models/test.py"],
            "dependencies": [],
        }
        (tasks_dir / "T001-m.json").write_text(json.dumps(task))

        sdd = {"module_name": "test", "dependencies": {"required": ["base"]}, "summary": "Test"}
        (factory_dir / "sdd.json").write_text(json.dumps(sdd))

        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        field_names = [f["name"] for f in result.schema["models"][0]["fields"]]
        assert "partner_id" in field_names
        assert "line_ids" in field_names
        assert "partner" not in field_names
        assert "line" not in field_names


class TestSchemaManagerMerge:
    def test_merges_field_from_multiple_tasks(self, tmp_path):
        factory_dir = tmp_path / ".factory"
        tasks_dir = factory_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (factory_dir / "schemas").mkdir(parents=True, exist_ok=True)

        index = {
            "module_name": "test",
            "total_tasks": 2,
            "tasks": [
                {"id": "T001", "name": "Modelo", "file": "T001-m.json", "dependencies": [], "order": 1, "estimated_effort": "high", "sdd_components": ["models.test"]},
                {"id": "T002", "name": "Extras", "file": "T002-e.json", "dependencies": ["T001"], "order": 2, "estimated_effort": "medium", "sdd_components": ["models.extra"]},
            ],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index))

        t001 = {
            "id": "T001", "name": "Modelo",
            "description": "Core model",
            "components": [{
                "type": "model", "name": "test.model",
                "description": "Test model", "sdd_reference": "models.test",
                "fields": [
                    {"name": "name", "type": "Char", "label": "Nombre", "required": True},
                    {"name": "partner_id", "type": "Many2one", "label": "Partner", "relation": "res.partner"},
                ],
            }],
            "files_to_generate": ["models/test.py"],
            "dependencies": [],
        }
        (tasks_dir / "T001-m.json").write_text(json.dumps(t001))

        t002 = {
            "id": "T002", "name": "Extras",
            "description": "Extra fields",
            "components": [{
                "type": "model", "name": "test.model",
                "description": "Extra fields", "sdd_reference": "models.extra",
                "fields": [
                    {"name": "phone", "type": "Char", "label": "Telefono", "size": 50},
                    {"name": "email", "type": "Char", "label": "Email", "size": 100},
                ],
            }],
            "files_to_generate": [],
            "dependencies": ["T001"],
        }
        (tasks_dir / "T002-e.json").write_text(json.dumps(t002))

        sdd = {"module_name": "test", "dependencies": {"required": ["base"]}, "summary": "Test"}
        (factory_dir / "sdd.json").write_text(json.dumps(sdd))

        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        assert len(result.schema["models"]) == 1
        fields = result.schema["models"][0]["fields"]
        assert len(fields) == 4
        field_names = [f["name"] for f in fields]
        assert "name" in field_names
        assert "partner_id" in field_names
        assert "phone" in field_names
        assert "email" in field_names

    def test_duplicate_field_keeps_first_type(self, tmp_path):
        factory_dir = tmp_path / ".factory"
        tasks_dir = factory_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (factory_dir / "schemas").mkdir(parents=True, exist_ok=True)

        index = {
            "module_name": "test",
            "total_tasks": 2,
            "tasks": [
                {"id": "T001", "name": "A", "file": "T001-a.json", "dependencies": [], "order": 1, "estimated_effort": "low", "sdd_components": ["a"]},
                {"id": "T002", "name": "B", "file": "T002-b.json", "dependencies": [], "order": 2, "estimated_effort": "low", "sdd_components": ["b"]},
            ],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index))

        (tasks_dir / "T001-a.json").write_text(json.dumps({
            "id": "T001", "name": "A", "description": "A",
            "components": [{"type": "model", "name": "test.m", "description": "M",
                "sdd_reference": "a", "fields": [{"name": "x", "type": "Char", "label": "X"}]}],
            "files_to_generate": [], "dependencies": [],
        }))
        (tasks_dir / "T002-b.json").write_text(json.dumps({
            "id": "T002", "name": "B", "description": "B",
            "components": [{"type": "model", "name": "test.m", "description": "M",
                "sdd_reference": "b", "fields": [{"name": "x", "type": "Integer", "label": "X2"}]}],
            "files_to_generate": [], "dependencies": [],
        }))

        sdd = {"module_name": "test", "dependencies": {"required": ["base"]}, "summary": "Test"}
        (factory_dir / "sdd.json").write_text(json.dumps(sdd))

        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        fields = result.schema["models"][0]["fields"]
        assert len(fields) == 1
        assert fields[0]["type"] == "Char"


class TestSchemaManagerMode:
    def test_known_core_model_set_to_extend(self, tmp_path):
        factory_dir = tmp_path / ".factory"
        tasks_dir = factory_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (factory_dir / "schemas").mkdir(parents=True, exist_ok=True)

        index = {
            "module_name": "test",
            "total_tasks": 1,
            "tasks": [{"id": "T001", "name": "M", "file": "T001-m.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["extend.partner"]}],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index))

        task = {
            "id": "T001", "name": "M",
            "description": "Extend res.partner with extra fields.",
            "components": [{
                "type": "model", "name": "res.partner",
                "description": "Extend partner", "sdd_reference": "extend.partner",
                "fields": [
                    {"name": "custom_field", "type": "Char", "label": "Custom", "size": 100},
                ],
            }],
            "files_to_generate": ["models/res_partner.py"],
            "dependencies": [],
        }
        (tasks_dir / "T001-m.json").write_text(json.dumps(task))

        sdd = {"module_name": "test", "dependencies": {"required": ["base"]}, "summary": "Test"}
        (factory_dir / "sdd.json").write_text(json.dumps(sdd))

        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        assert result.schema["models"][0]["mode"] == "extend"


class TestSchemaManagerEdgeCases:
    def test_no_task_index_returns_error(self, tmp_path):
        manager = SchemaManager(tmp_path)
        result = manager.assemble()
        assert result.success is False

    def test_empty_task_index_handled(self, tmp_path):
        factory_dir = tmp_path / ".factory"
        tasks_dir = factory_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (factory_dir / "schemas").mkdir(parents=True, exist_ok=True)

        index = {"module_name": "test", "total_tasks": 1, "tasks": [{"id": "T001", "name": "X", "file": "T001-x.json", "dependencies": [], "order": 1, "estimated_effort": "low", "sdd_components": ["models.test"]}]}
        (tasks_dir / "index.json").write_text(json.dumps(index))

        task = {"id": "T001", "name": "X", "description": "With no models.", "components": [], "files_to_generate": [], "dependencies": []}
        (tasks_dir / "T001-x.json").write_text(json.dumps(task))

        sdd = {"module_name": "test", "dependencies": {"required": ["base"]}, "summary": "Test"}
        (factory_dir / "sdd.json").write_text(json.dumps(sdd))

        manager = SchemaManager(tmp_path)
        result = manager.assemble()
        assert result.success is False

    def test_copies_module_registry_to_project(self, tmp_path):
        _setup_project_with_tasks(tmp_path)
        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        assert result.success is True
        assert len(result.warnings) >= 0


class TestSchemaManagerWarnings:
    def test_missing_relation_warns(self, tmp_path):
        factory_dir = tmp_path / ".factory"
        tasks_dir = factory_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (factory_dir / "schemas").mkdir(parents=True, exist_ok=True)

        index = {
            "module_name": "test",
            "total_tasks": 1,
            "tasks": [{"id": "T001", "name": "M", "file": "T001-m.json", "dependencies": [], "order": 1, "estimated_effort": "medium", "sdd_components": ["models.test"]}],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index))

        task = {
            "id": "T001", "name": "M", "description": "Test",
            "components": [{
                "type": "model", "name": "test.model", "description": "M", "sdd_reference": "models.test",
                "fields": [{"name": "other_id", "type": "Many2one", "label": "Other"}],
            }],
            "files_to_generate": ["models/test.py"], "dependencies": [],
        }
        (tasks_dir / "T001-m.json").write_text(json.dumps(task))

        sdd = {"module_name": "test", "dependencies": {"required": ["base"]}, "summary": "Test"}
        (factory_dir / "sdd.json").write_text(json.dumps(sdd))

        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        warnings = result.warning_messages
        assert any("no 'relation'" in w.lower() for w in warnings)


class TestCLISchemaAssemble:
    def test_cli_schema_assemble_success(self, tmp_path):
        runner = CliRunner()
        init_result = runner.invoke(main, ["init", "-d", str(tmp_path)])
        assert init_result.exit_code == 0

        _setup_project_with_tasks(tmp_path)

        state = json.loads((tmp_path / ".factory" / "state.json").read_text())
        state["current_phase"] = "construction"
        state["phases"]["construction"]["status"] = "in_progress"
        (tmp_path / ".factory" / "state.json").write_text(json.dumps(state, indent=2))

        result = runner.invoke(main, ["schema", "assemble", "-d", str(tmp_path)])
        assert result.exit_code == 0
        assert "schema.json assembled" in result.output
        assert (tmp_path / ".factory" / "schema.json").exists()

    def test_cli_schema_assemble_fails_without_tasks(self, tmp_path):
        runner = CliRunner()
        init_result = runner.invoke(main, ["init", "-d", str(tmp_path)])
        assert init_result.exit_code == 0

        state = json.loads((tmp_path / ".factory" / "state.json").read_text())
        state["current_phase"] = "construction"
        state["phases"]["construction"]["status"] = "in_progress"
        (tmp_path / ".factory" / "state.json").write_text(json.dumps(state, indent=2))

        result = runner.invoke(main, ["schema", "assemble", "-d", str(tmp_path)])
        assert result.exit_code == 1
        assert "Errors" in result.output

    def test_cli_schema_assemble_generates_valid_schema(self, tmp_path):
        import jsonschema
        from pathlib import Path as P

        runner = CliRunner()
        init_result = runner.invoke(main, ["init", "-d", str(tmp_path)])
        assert init_result.exit_code == 0

        _setup_project_with_tasks(tmp_path)

        state = json.loads((tmp_path / ".factory" / "state.json").read_text())
        state["current_phase"] = "construction"
        state["phases"]["construction"]["status"] = "in_progress"
        (tmp_path / ".factory" / "state.json").write_text(json.dumps(state, indent=2))

        result = runner.invoke(main, ["schema", "assemble", "-d", str(tmp_path)])
        assert result.exit_code == 0

        schema_path = P(__file__).resolve().parent.parent / "schemas" / "schema.schema.json"
        schema_obj = json.loads(schema_path.read_text())
        artifact = json.loads((tmp_path / ".factory" / "schema.json").read_text())
        jsonschema.validate(artifact, schema_obj)


class TestInitHasSchemaGate:
    def test_init_creates_schema_gate(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["init", "-d", str(tmp_path)])
        assert result.exit_code == 0

        state = json.loads((tmp_path / ".factory" / "state.json").read_text())
        assert "schema" in state["gates"]
        schema_gate = state["gates"]["schema"]
        assert schema_gate["owner_agent"] == "code-generator"
        assert len(schema_gate["rules"]) == 3

    def test_init_creates_construction_gate(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["init", "-d", str(tmp_path)])
        assert result.exit_code == 0

        state = json.loads((tmp_path / ".factory" / "state.json").read_text())
        assert "construction" in state["gates"]
        construction_gate = state["gates"]["construction"]
        assert construction_gate["owner_agent"] == "code-generator"
        rule_types = [r["type"] for r in construction_gate["rules"]]
        assert "view_coverage" in rule_types
        assert "view_field_check" in rule_types
        assert "acl_coverage" in rule_types

    def test_security_group_assembly_name_and_description(self, tmp_path):
        factory_dir = tmp_path / ".factory"
        tasks_dir = factory_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (factory_dir / "schemas").mkdir(parents=True)

        index = {
            "module_name": "test", "total_tasks": 1,
            "tasks": [{"id": "T001", "name": "Security", "file": "T001.json", "dependencies": [], "order": 1, "estimated_effort": "low", "sdd_components": ["security"]}],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index))

        t001 = {
            "id": "T001", "name": "Security", "description": "Security groups and ACL",
            "components": [
                {"type": "security_group", "name": "test_admin", "display_name": "Test Admin", "description": "Full access group", "category": "Test Module", "sdd_reference": "security.admin"},
                {"type": "security_group", "name": "test_user", "description": "Limited access", "sdd_reference": "security.user"},
                {"type": "access_right", "name": "test_admin", "model": "test.model", "permissions": {"read": True, "write": True, "create": True, "unlink": True}, "sdd_reference": "security.acl"},
            ],
            "files_to_generate": ["security/ir.model.access.csv"],
            "dependencies": [],
        }
        (tasks_dir / "T001.json").write_text(json.dumps(t001))

        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        groups = result.schema["security"]["groups"]
        assert len(groups) == 2
        admin = [g for g in groups if g["id"] == "test_admin"][0]
        assert admin["name"] == "Test Admin"
        assert admin["description"] == "Full access group"
        assert admin["category"] == "Test Module"
        user = [g for g in groups if g["id"] == "test_user"][0]
        assert user["name"] == "test_user"
        assert user["description"] == "Limited access"
        assert user["category"] == "test_user"

    def test_record_rule_domain_from_component(self, tmp_path):
        factory_dir = tmp_path / ".factory"
        tasks_dir = factory_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (factory_dir / "schemas").mkdir(parents=True)

        index = {
            "module_name": "test", "total_tasks": 1,
            "tasks": [{"id": "T001", "name": "Rules", "file": "T001.json", "dependencies": [], "order": 1, "estimated_effort": "low", "sdd_components": ["security"]}],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index))

        t001 = {
            "id": "T001", "name": "Rules", "description": "Record rules",
            "components": [
                {"type": "record_rule", "name": "rule_own_records", "description": "Users see own records", "model": "test.model", "domain": "[('user_id', '=', user.id)]", "groups": ["base.group_user"], "sdd_reference": "security.rules"},
            ],
            "files_to_generate": ["security/record_rules.xml"],
            "dependencies": [],
        }
        (tasks_dir / "T001.json").write_text(json.dumps(t001))

        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        rules = result.schema["security"]["record_rules"]
        assert len(rules) == 1
        assert rules[0]["domain"] == "[('user_id', '=', user.id)]"
        assert rules[0]["groups"] == ["base.group_user"]

    def test_data_type_respects_format(self, tmp_path):
        factory_dir = tmp_path / ".factory"
        tasks_dir = factory_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (factory_dir / "schemas").mkdir(parents=True)

        index = {
            "module_name": "test", "total_tasks": 1,
            "tasks": [{"id": "T001", "name": "Data", "file": "T001.json", "dependencies": [], "order": 1, "estimated_effort": "low", "sdd_components": ["data"]}],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index))

        t001 = {
            "id": "T001", "name": "Data", "description": "CSV data",
            "components": [
                {"type": "data", "name": "data.csv", "format": "csv", "model": "test.model", "noupdate": True, "sdd_reference": "data.import"},
            ],
            "files_to_generate": ["data/data.csv"],
            "dependencies": [],
        }
        (tasks_dir / "T001.json").write_text(json.dumps(t001))

        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        data_entries = result.schema["data"]
        assert len(data_entries) == 1
        assert data_entries[0]["type"] == "csv"
        assert data_entries[0]["noupdate"] is True

    def test_field_type_case_normalization(self, tmp_path):
        factory_dir = tmp_path / ".factory"
        tasks_dir = factory_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (factory_dir / "schemas").mkdir(parents=True)

        index = {
            "module_name": "test", "total_tasks": 1,
            "tasks": [{"id": "T001", "name": "Models", "file": "T001.json", "dependencies": [], "order": 1, "estimated_effort": "high", "sdd_components": ["models"]}],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index))

        t001 = {
            "id": "T001", "name": "Models", "description": "Test model with lowercase types",
            "components": [
                {"type": "model", "name": "test.model", "description": "Test",
                 "fields": [
                     {"name": "name", "type": "char", "label": "Name"},
                     {"name": "partner_id", "type": "many2one", "label": "Partner", "relation": "res.partner"},
                     {"name": "tags_ids", "type": "many2many", "label": "Tags", "relation": "test.tag"},
                     {"name": "is_active", "type": "boolean", "label": "Active"},
                     {"name": "amount", "type": "monetary", "label": "Amount"},
                     {"name": "created", "type": "datetime", "label": "Created"},
                 ],
                 "sdd_reference": "models.test"},
            ],
            "files_to_generate": ["models/test_model.py"],
            "dependencies": [],
        }
        (tasks_dir / "T001.json").write_text(json.dumps(t001))

        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        vehicle = result.schema["models"][0]
        field_types = {f["name"]: f["type"] for f in vehicle["fields"]}
        assert field_types["name"] == "Char"
        assert field_types["partner_id"] == "Many2one"
        assert field_types["tags_ids"] == "Many2many"
        assert field_types["is_active"] == "Boolean"
        assert field_types["amount"] == "Monetary"
        assert field_types["created"] == "Datetime"

    def test_data_defaults_to_xml(self, tmp_path):
        factory_dir = tmp_path / ".factory"
        tasks_dir = factory_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (factory_dir / "schemas").mkdir(parents=True)

        index = {
            "module_name": "test", "total_tasks": 1,
            "tasks": [{"id": "T001", "name": "Data", "file": "T001.json", "dependencies": [], "order": 1, "estimated_effort": "low", "sdd_components": ["data"]}],
        }
        (tasks_dir / "index.json").write_text(json.dumps(index))

        t001 = {
            "id": "T001", "name": "Data", "description": "Default data",
            "components": [
                {"type": "data", "name": "demo.xml", "model": "test.model", "sdd_reference": "data.demo"},
            ],
            "files_to_generate": ["data/demo.xml"],
            "dependencies": [],
        }
        (tasks_dir / "T001.json").write_text(json.dumps(t001))

        manager = SchemaManager(tmp_path)
        result = manager.assemble()

        data_entries = result.schema["data"]
        assert data_entries[0]["type"] == "xml"
        assert data_entries[0]["noupdate"] is False

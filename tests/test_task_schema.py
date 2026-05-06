"""Tests for Task Index and Task Item schema validation."""

import json
from pathlib import Path

import jsonschema
import pytest

INDEX_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "task_index.schema.json"
ITEM_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "task_item.schema.json"


@pytest.fixture
def index_schema():
    return json.loads(INDEX_SCHEMA_PATH.read_text())


@pytest.fixture
def item_schema():
    return json.loads(ITEM_SCHEMA_PATH.read_text())


def _valid_index():
    return {
        "module_name": "vehicle_registry",
        "total_tasks": 4,
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
                "sdd_components": ["views.form", "views.tree"],
            },
            {
                "id": "T003",
                "name": "Seguridad",
                "file": "T003-seguridad.json",
                "dependencies": ["T001"],
                "order": 3,
                "estimated_effort": "medium",
                "sdd_components": ["security.groups", "security.acl"],
            },
            {
                "id": "T004",
                "name": "Datos demo",
                "file": "T004-datos-demo.json",
                "dependencies": ["T001", "T002", "T003"],
                "order": 4,
                "estimated_effort": "low",
                "sdd_components": ["data.demo"],
            },
        ],
    }


def _valid_item():
    return {
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
                ],
                "sdd_reference": "models.vehicle",
            },
            {
                "type": "model",
                "name": "vehicle.brand",
                "description": "Catalogo de marcas",
                "fields": [
                    {"name": "name", "type": "Char", "label": "Nombre", "required": True, "size": 100},
                ],
                "sdd_reference": "models.brand",
            },
        ],
        "files_to_generate": [
            "models/__init__.py",
            "models/vehicle.py",
            "models/brand.py",
        ],
        "dependencies": [],
    }


class TestTaskIndexSchema:
    def test_valid_index_passes(self, index_schema):
        data = _valid_index()
        jsonschema.validate(data, index_schema)

    def test_missing_required_field(self, index_schema):
        data = _valid_index()
        del data["total_tasks"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, index_schema)

    def test_module_name_too_short(self, index_schema):
        data = _valid_index()
        data["module_name"] = "ab"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, index_schema)

    def test_zero_tasks(self, index_schema):
        data = _valid_index()
        data["total_tasks"] = 0
        data["tasks"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, index_schema)

    def test_empty_tasks_array(self, index_schema):
        data = _valid_index()
        data["total_tasks"] = 0
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, index_schema)

    def test_task_id_pattern_invalid(self, index_schema):
        data = _valid_index()
        data["tasks"][0]["id"] = "1"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, index_schema)

    def test_task_id_pattern_valid_formats(self, index_schema):
        data = _valid_index()
        for tid in ["T001", "T999", "T9999"]:
            data_copy = json.loads(json.dumps(data))
            data_copy["tasks"][0]["id"] = tid
            jsonschema.validate(data_copy, index_schema)

    def test_task_file_pattern_invalid(self, index_schema):
        data = _valid_index()
        data["tasks"][0]["file"] = "task1.txt"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, index_schema)

    def test_task_file_pattern_valid(self, index_schema):
        data = _valid_index()
        data["tasks"][0]["file"] = "T001-modelos.json"
        jsonschema.validate(data, index_schema)

    def test_missing_required_task_field(self, index_schema):
        data = _valid_index()
        del data["tasks"][0]["sdd_components"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, index_schema)

    def test_dependencies_invalid_format(self, index_schema):
        data = _valid_index()
        data["tasks"][1]["dependencies"] = ["1"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, index_schema)

    def test_estimated_effort_invalid_enum(self, index_schema):
        data = _valid_index()
        data["tasks"][0]["estimated_effort"] = "extreme"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, index_schema)

    def test_estimated_effort_valid_values(self, index_schema):
        for effort in ["low", "medium", "high"]:
            data = json.loads(json.dumps(_valid_index()))
            data["tasks"][0]["estimated_effort"] = effort
            jsonschema.validate(data, index_schema)

    def test_order_negative(self, index_schema):
        data = _valid_index()
        data["tasks"][0]["order"] = -1
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, index_schema)

    def test_order_zero(self, index_schema):
        data = _valid_index()
        data["tasks"][0]["order"] = 0
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, index_schema)


class TestTaskItemSchema:
    def test_valid_item_passes(self, item_schema):
        data = _valid_item()
        jsonschema.validate(data, item_schema)

    def test_missing_required_field(self, item_schema):
        data = _valid_item()
        del data["description"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, item_schema)

    def test_description_too_short(self, item_schema):
        data = _valid_item()
        data["description"] = "short"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, item_schema)

    def test_id_pattern_invalid(self, item_schema):
        data = _valid_item()
        data["id"] = "1"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, item_schema)

    def test_empty_components(self, item_schema):
        data = _valid_item()
        data["components"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, item_schema)

    def test_component_missing_required(self, item_schema):
        data = _valid_item()
        del data["components"][0]["sdd_reference"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, item_schema)

    def test_component_type_invalid_enum(self, item_schema):
        data = _valid_item()
        data["components"][0]["type"] = "invalid_type"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, item_schema)

    def test_component_type_valid_values(self, item_schema):
        for ctype in ["model", "view", "security_group", "access_right", "record_rule", "data", "report", "workflow", "wizard", "controller"]:
            data = json.loads(json.dumps(_valid_item()))
            data["components"][0]["type"] = ctype
            if ctype != "model":
                del data["components"][0]["fields"]
            jsonschema.validate(data, item_schema)

    def test_empty_files_to_generate(self, item_schema):
        data = _valid_item()
        data["files_to_generate"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, item_schema)

    def test_files_to_generate_invalid_pattern(self, item_schema):
        data = _valid_item()
        data["files_to_generate"] = ["models/secret file.py"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, item_schema)

    def test_field_name_invalid(self, item_schema):
        data = _valid_item()
        data["components"][0]["fields"][0]["name"] = "1plate"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, item_schema)

    def test_field_type_invalid_enum(self, item_schema):
        data = _valid_item()
        data["components"][0]["fields"][0]["type"] = "Unknown"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, item_schema)

    def test_field_selection_valid(self, item_schema):
        data = _valid_item()
        data["components"][0]["fields"] = [
            {"name": "state", "type": "Selection", "label": "Estado",
             "selection": [["draft", "Borrador"], ["done", "Completado"]]}
        ]
        jsonschema.validate(data, item_schema)

    def test_dependencies_valid(self, item_schema):
        data = _valid_item()
        data["dependencies"] = ["T001", "T002"]
        jsonschema.validate(data, item_schema)

    def test_dependencies_invalid_format(self, item_schema):
        data = _valid_item()
        data["dependencies"] = ["001", "abc"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, item_schema)

    def test_view_type_invalid(self, item_schema):
        data = _valid_item()
        data["components"][0]["type"] = "view"
        data["components"][0]["view_type"] = "invalid_type"
        del data["components"][0]["fields"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, item_schema)

"""Tests for the schema.schema.json JSON Schema validation."""

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "schema.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid_schema():
    return {
        "manifest": {
            "name": "vehicle_registry",
            "version": "18.0.1.0.0",
            "summary": "Vehicle registration module",
            "depends": ["base"],
            "license": "LGPL-3",
        },
        "models": [
            {
                "name": "vehicle.vehicle",
                "description": "Main vehicle record",
                "mode": "new",
                "fields": [
                    {
                        "name": "plate",
                        "type": "Char",
                        "label": "Placa",
                        "required": True,
                        "size": 20,
                    },
                    {
                        "name": "brand_id",
                        "type": "Many2one",
                        "label": "Marca",
                        "relation": "vehicle.brand",
                    },
                ],
            },
            {
                "name": "vehicle.brand",
                "description": "Vehicle brand catalog",
                "mode": "new",
                "fields": [
                    {
                        "name": "name",
                        "type": "Char",
                        "label": "Nombre",
                        "required": True,
                        "size": 100,
                    },
                ],
            },
        ],
        "views": [
            {
                "name": "vehicle.vehicle.form",
                "type": "form",
                "model": "vehicle.vehicle",
                "fields": ["plate", "brand_id"],
            },
            {
                "name": "vehicle.vehicle.list",
                "type": "list",
                "model": "vehicle.vehicle",
                "fields": ["plate", "brand_id"],
            },
        ],
        "security": {
            "groups": [
                {
                    "id": "vehicle_user",
                    "name": "Vehicle User",
                    "description": "Can view and manage vehicle records",
                    "category": "Vehicle Registry",
                },
            ],
            "access_rights": [
                {
                    "model": "vehicle.vehicle",
                    "group": "vehicle_user",
                    "perm_read": True,
                    "perm_write": True,
                    "perm_create": True,
                    "perm_unlink": True,
                },
            ],
            "record_rules": [],
        },
        "data": [],
    }


class TestSchemaValidation:
    def test_valid_schema_passes(self, schema):
        data = _valid_schema()
        jsonschema.validate(data, schema)

    def test_missing_manifest(self, schema):
        data = _valid_schema()
        del data["manifest"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_missing_models(self, schema):
        data = _valid_schema()
        del data["models"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_missing_views(self, schema):
        data = _valid_schema()
        del data["views"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_missing_security(self, schema):
        data = _valid_schema()
        del data["security"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_missing_data(self, schema):
        data = _valid_schema()
        del data["data"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_empty_models(self, schema):
        data = _valid_schema()
        data["models"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_empty_views(self, schema):
        data = _valid_schema()
        data["views"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_empty_groups_allowed(self, schema):
        data = _valid_schema()
        data["security"]["groups"] = []
        jsonschema.validate(data, schema)

    def test_empty_access_rights_allowed(self, schema):
        data = _valid_schema()
        data["security"]["access_rights"] = []
        jsonschema.validate(data, schema)


class TestManifestValidation:
    def test_manifest_name_invalid_pattern(self, schema):
        data = _valid_schema()
        data["manifest"]["name"] = "VehicleRegistry"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_manifest_name_too_short(self, schema):
        data = _valid_schema()
        data["manifest"]["name"] = "ab"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_manifest_missing_required(self, schema):
        data = _valid_schema()
        del data["manifest"]["depends"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_manifest_empty_depends(self, schema):
        data = _valid_schema()
        data["manifest"]["depends"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_manifest_version_invalid(self, schema):
        data = _valid_schema()
        data["manifest"]["version"] = "1.0"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_manifest_version_valid(self, schema):
        data = _valid_schema()
        data["manifest"]["version"] = "18.0.1.0.0"
        jsonschema.validate(data, schema)


class TestModelValidation:
    def test_model_missing_mode(self, schema):
        data = _valid_schema()
        del data["models"][0]["mode"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_model_mode_invalid(self, schema):
        data = _valid_schema()
        data["models"][0]["mode"] = "create"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_model_mode_valid(self, schema):
        data = _valid_schema()
        data["models"][0]["mode"] = "extend"
        jsonschema.validate(data, schema)

    def test_model_name_invalid_pattern(self, schema):
        data = _valid_schema()
        data["models"][0]["name"] = "Model"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_model_empty_fields(self, schema):
        data = _valid_schema()
        data["models"][0]["fields"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_field_missing_label(self, schema):
        data = _valid_schema()
        del data["models"][0]["fields"][0]["label"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_field_type_invalid(self, schema):
        data = _valid_schema()
        data["models"][0]["fields"][0]["type"] = "Unknown"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_field_name_invalid_pattern(self, schema):
        data = _valid_schema()
        data["models"][0]["fields"][0]["name"] = "1plate"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_field_relation_valid(self, schema):
        data = _valid_schema()
        data["models"][0]["fields"] = [
            {"name": "line_ids", "type": "One2many", "label": "Lineas",
             "relation": "vehicle.line", "comodel_name": "vehicle.line",
             "inverse_name": "vehicle_id"}
        ]
        jsonschema.validate(data, schema)

    def test_field_selection_valid(self, schema):
        data = _valid_schema()
        data["models"][0]["fields"] = [
            {"name": "state", "type": "Selection", "label": "Estado",
             "selection": [["draft", "Borrador"], ["done", "Completado"]]}
        ]
        jsonschema.validate(data, schema)


class TestViewValidation:
    def test_view_missing_model(self, schema):
        data = _valid_schema()
        del data["views"][0]["model"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_view_type_invalid(self, schema):
        data = _valid_schema()
        data["views"][0]["type"] = "report"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_view_empty_fields(self, schema):
        data = _valid_schema()
        data["views"][0]["fields"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_view_with_filters(self, schema):
        data = _valid_schema()
        data["views"][0]["type"] = "search"
        data["views"][0]["filters"] = [
            {"name": "By State", "domain_type": "filter", "field_name": "state"}
        ]
        jsonschema.validate(data, schema)


class TestSecurityValidation:
    def test_security_group_missing_description(self, schema):
        data = _valid_schema()
        del data["security"]["groups"][0]["description"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_access_right_missing_model(self, schema):
        data = _valid_schema()
        del data["security"]["access_rights"][0]["model"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_access_right_missing_group(self, schema):
        data = _valid_schema()
        del data["security"]["access_rights"][0]["group"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_record_rules_optional(self, schema):
        data = _valid_schema()
        data["security"]["record_rules"] = [
            {"name": "own_records", "model": "vehicle.vehicle",
             "domain": "[('user_id', '=', user.id)]"}
        ]
        jsonschema.validate(data, schema)


class TestDataValidation:
    def test_data_can_be_empty(self, schema):
        data = _valid_schema()
        data["data"] = []
        jsonschema.validate(data, schema)

    def test_data_with_records(self, schema):
        data = _valid_schema()
        data["data"] = [
            {
                "file": "demo/demo.xml",
                "type": "xml",
                "model": "vehicle.vehicle",
                "records": [
                    {"model": "vehicle.vehicle", "id": "vehicle_001",
                     "fields": {"plate": "ABC123", "brand_id": 1}}
                ],
            }
        ]
        jsonschema.validate(data, schema)

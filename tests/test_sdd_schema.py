"""Tests for SDD schema validation."""

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "sdd.schema.json"


@pytest.fixture
def sdd_schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid_sdd():
    return {
        "module_name": "vehicle_registry",
        "module_display_name": "Vehicle Registry",
        "version": "18.0.1.0.0",
        "summary": "Module for managing vehicle records in Odoo v18",
        "architecture": {
            "description": "The module uses a single model with basic CRUD views and security groups for access control.",
            "diagram_notes": "Standard Odoo v18 module architecture with MVC separation."
        },
        "models": [
            {
                "name": "vehicle.registry",
                "display_name": "Vehicle",
                "description": "Main vehicle registry model for storing vehicle data",
                "inherit": None,
                "fields": [
                    {
                        "name": "plate",
                        "type": "char",
                        "display_name": "License Plate",
                        "required": True,
                        "unique": True,
                        "size": 20,
                        "description": "Unique vehicle license plate number",
                        "traceability": ["RF-01"]
                    },
                    {
                        "name": "brand",
                        "type": "char",
                        "display_name": "Brand",
                        "required": True,
                        "description": "Vehicle manufacturer brand",
                        "traceability": ["RF-01"]
                    },
                ],
                "relations": [
                    {
                        "type": "Many2one",
                        "model": "res.partner",
                        "field": "owner_id",
                        "description": "Vehicle owner contact"
                    }
                ],
                "traceability": ["RF-01", "RF-02"]
            }
        ],
        "views": [
            {
                "model": "vehicle.registry",
                "type": "form",
                "name": "vehicle.registry.form",
                "description": "Main vehicle form view",
                "fields": ["plate", "brand"],
                "traceability": ["RF-01"]
            },
            {
                "model": "vehicle.registry",
                "type": "list",
                "name": "vehicle.registry.list",
                "description": "Vehicle list view",
                "fields": ["plate", "brand"],
                "traceability": ["RF-01"]
            },
            {
                "model": "vehicle.registry",
                "type": "search",
                "name": "vehicle.registry.search",
                "description": "Vehicle search view",
                "fields": ["plate", "brand"],
                "traceability": ["RF-03"]
            }
        ],
        "security": {
            "groups": [
                {
                    "name": "vehicle_user",
                    "display_name": "Vehicle User",
                    "description": "Can view and create vehicles",
                    "implied_ids": ["base.group_user"]
                }
            ],
            "access_rights": [
                {
                    "model": "vehicle.registry",
                    "group": "vehicle_user",
                    "perm_read": True,
                    "perm_write": True,
                    "perm_create": True,
                    "perm_unlink": False
                }
            ],
            "record_rules": []
        },
        "dependencies": {
            "required": ["base"],
            "optional": ["mail"],
            "reason": "base is required for all Odoo modules, mail for activity tracking"
        },
        "workflows": [
            {
                "name": "vehicle_status",
                "model": "vehicle.registry",
                "states": ["draft", "active", "inactive"],
                "description": "Vehicle lifecycle status workflow",
                "traceability": ["RF-04"]
            }
        ],
        "reporting": [],
        "file_structure": {
            "module": "vehicle_registry",
            "files": [
                "__manifest__.py",
                "__init__.py",
                "models/__init__.py",
                "models/vehicle_registry.py",
                "views/vehicle_registry_views.xml",
                "security/ir.model.access.csv"
            ]
        },
        "traceability_matrix": {
            "description": "Maps PRD requirements to SDD design components for full traceability",
            "mappings": [
                {
                    "requirement": "RF-01",
                    "sdD_components": ["vehicle.registry model", "vehicle.registry.form view"],
                    "description": "CRUD operations for vehicle records"
                },
                {
                    "requirement": "RNF-01",
                    "sdD_components": ["security section"],
                    "description": "Access control"
                }
            ]
        }
    }


class TestSDDSchemaValid:
    """Valid SDD documents pass validation."""

    def test_valid_sdd_passes(self, sdd_schema):
        jsonschema.validate(_valid_sdd(), sdd_schema)

    def test_minimal_sdd_passes(self, sdd_schema):
        sdd = {
            "module_name": "test",
            "module_display_name": "Test Module",
            "version": "18.0.1.0.0",
            "architecture": {
                "description": "Simple test module architecture description here"
            },
            "models": [
                {
                    "name": "test.model",
                    "display_name": "Test",
                    "description": "A test model",
                    "fields": [
                        {
                            "name": "name",
                            "type": "char",
                            "display_name": "Name",
                            "description": "Record name field",
                            "traceability": ["RF-01"]
                        }
                    ],
                    "traceability": ["RF-01"]
                }
            ],
            "views": [
                {
                    "model": "test.model",
                    "type": "form",
                    "name": "test.model.form",
                    "description": "Test form view",
                    "fields": ["name"],
                    "traceability": ["RF-01"]
                }
            ],
            "security": {
                "groups": [
                    {
                        "name": "test_user",
                        "display_name": "Test User",
                        "description": "Basic user group for testing"
                    }
                ],
                "access_rights": [
                    {
                        "model": "test.model",
                        "group": "test_user",
                        "perm_read": True,
                        "perm_write": False,
                        "perm_create": False,
                        "perm_unlink": False
                    }
                ]
            },
            "dependencies": {
                "required": ["base"]
            },
            "file_structure": {
                "module": "test",
                "files": ["__manifest__.py"]
            },
            "traceability_matrix": {
                "mappings": [
                    {
                        "requirement": "RF-01",
                        "sdD_components": ["test.model"],
                        "description": "Basic model mapping"
                    }
                ]
            }
        }
        jsonschema.validate(sdd, sdd_schema)

    def test_sdd_with_optional_fields_passes(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["workflows"] = [
            {
                "name": "state_flow",
                "model": "vehicle.registry",
                "states": ["draft", "done"],
                "description": "Simple state flow for testing",
                "traceability": ["RF-01"]
            }
        ]
        sdd["reporting"] = [
            {
                "name": "vehicle_report",
                "type": "pdf",
                "model": "vehicle.registry",
                "description": "Vehicle record PDF report"
            }
        ]
        jsonschema.validate(sdd, sdd_schema)


class TestSDDSchemaRequiredFields:
    """Missing required fields fail validation."""

    def test_missing_module_name_fails(self, sdd_schema):
        sdd = _valid_sdd()
        del sdd["module_name"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_missing_models_fails(self, sdd_schema):
        sdd = _valid_sdd()
        del sdd["models"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_missing_views_fails(self, sdd_schema):
        sdd = _valid_sdd()
        del sdd["views"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_missing_security_fails(self, sdd_schema):
        sdd = _valid_sdd()
        del sdd["security"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_missing_dependencies_fails(self, sdd_schema):
        sdd = _valid_sdd()
        del sdd["dependencies"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_missing_file_structure_fails(self, sdd_schema):
        sdd = _valid_sdd()
        del sdd["file_structure"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_missing_traceability_matrix_fails(self, sdd_schema):
        sdd = _valid_sdd()
        del sdd["traceability_matrix"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_missing_architecture_fails(self, sdd_schema):
        sdd = _valid_sdd()
        del sdd["architecture"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_missing_display_name_fails(self, sdd_schema):
        sdd = _valid_sdd()
        del sdd["module_display_name"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)


class TestSDDSchemaEmptyArrays:
    """Empty required arrays fail validation."""

    def test_empty_models_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["models"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_empty_views_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["views"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_empty_security_groups_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["security"]["groups"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_empty_access_rights_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["security"]["access_rights"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_empty_dependencies_required_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["dependencies"]["required"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_empty_file_structure_files_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["file_structure"]["files"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_empty_traceability_mappings_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["traceability_matrix"]["mappings"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)


class TestSDDSchemaInvalidTypes:
    """Invalid field types fail validation."""

    def test_invalid_model_field_type_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["models"][0]["fields"][0]["type"] = "invalid_type"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_invalid_view_type_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["views"][0]["type"] = "invalid_type"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_invalid_relation_type_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["models"][0]["relations"][0]["type"] = "InvalidRel"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_invalid_version_format_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["version"] = "abc"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)


class TestSDDSchemaTraceability:
    """Traceability requirements fail correctly."""

    def test_model_without_traceability_fails(self, sdd_schema):
        sdd = _valid_sdd()
        del sdd["models"][0]["traceability"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_field_without_traceability_fails(self, sdd_schema):
        sdd = _valid_sdd()
        del sdd["models"][0]["fields"][0]["traceability"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_view_without_traceability_fails(self, sdd_schema):
        sdd = _valid_sdd()
        del sdd["views"][0]["traceability"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_workflow_without_traceability_fails(self, sdd_schema):
        sdd = _valid_sdd()
        del sdd["workflows"][0]["traceability"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_traceability_mapping_missing_sdd_components_fails(self, sdd_schema):
        sdd = _valid_sdd()
        del sdd["traceability_matrix"]["mappings"][0]["sdD_components"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)


class TestSDDSchemaMinLength:
    """String fields must meet minimum length requirements."""

    def test_module_name_too_short_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["module_name"] = "ab"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_architecture_description_too_short_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["architecture"]["description"] = "Short"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_model_description_too_short_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["models"][0]["description"] = "Sho"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_field_description_too_short_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["models"][0]["fields"][0]["description"] = "Sh"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_view_description_too_short_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["views"][0]["description"] = "Sho"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_traceability_description_too_short_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["traceability_matrix"]["description"] = "Short"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)


class TestSDDSchemaPatterns:
    """Pattern validations work correctly."""

    def test_invalid_model_name_pattern_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["models"][0]["name"] = "Invalid Model Name!"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_invalid_field_name_pattern_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["models"][0]["fields"][0]["name"] = "1invalid"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_traceability_rf_pattern_fails_with_invalid_id(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["models"][0]["fields"][0]["traceability"] = ["RF-1"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_valid_traceability_with_rnf_passes(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["traceability_matrix"]["mappings"][0]["requirement"] = "RNF-01"
        jsonschema.validate(sdd, sdd_schema)


class TestSDDAdditionalProperties:
    """Additional properties are rejected."""

    def test_sdd_extra_property_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["extra_field"] = "not allowed"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_model_extra_property_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["models"][0]["extra"] = "not allowed"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

    def test_security_extra_property_fails(self, sdd_schema):
        sdd = _valid_sdd()
        sdd["security"]["extra"] = "not allowed"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sdd, sdd_schema)

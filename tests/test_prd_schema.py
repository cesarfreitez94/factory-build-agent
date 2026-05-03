"""Tests for PRD schema validation."""

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "prd.schema.json"


@pytest.fixture
def prd_schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid_prd():
    return {
        "vision": "Build a vehicle registration module for Odoo v18 that allows tracking cars, owners, and maintenance records.",
        "stakeholders": [
            {"name": "Desarrollador Odoo", "role": "Implementador", "interest": "Modulo funcional y bien documentado"},
            {"name": "Gerente de Flota", "role": "Usuario final", "interest": "Registro rapido y busqueda de vehiculos"},
        ],
        "objectives": [
            "Reducir tiempo de registro de vehiculos de 10 a 2 minutos",
            "Proveer busqueda avanzada por placa, marca y modelo",
        ],
        "functional_requirements": [
            {
                "id": "RF-01",
                "description": "El sistema debe permitir crear, leer, actualizar y eliminar registros de vehiculos.",
                "priority": "high",
                "acceptance_criteria": [
                    "Se puede crear un vehiculo con campos obligatorios completos",
                    "Se puede buscar y visualizar un vehiculo existente",
                ],
            },
            {
                "id": "RF-02",
                "description": "El sistema debe validar que la placa del vehiculo sea unica.",
                "priority": "medium",
            },
        ],
        "non_functional_requirements": [
            {
                "id": "RNF-01",
                "description": "La busqueda de vehiculos debe devolver resultados en menos de 2 segundos.",
                "category": "performance",
                "priority": "high",
            },
            {
                "id": "RNF-02",
                "description": "Solo usuarios autenticados con permisos pueden modificar vehiculos.",
                "category": "security",
                "priority": "high",
            },
        ],
        "acceptance_criteria": [
            {
                "id": "CA-01",
                "criterion": "Un usuario con permisos puede registrar un nuevo vehiculo en menos de 1 minuto.",
                "related_requirements": ["RF-01"],
            },
            {
                "id": "CA-02",
                "criterion": "El sistema rechaza placas duplicadas con un mensaje de error claro.",
                "related_requirements": ["RF-02"],
            },
        ],
        "constraints": [
            "El modulo debe ser compatible con Odoo v18 Community Edition",
            "La base de datos existente no debe ser modificada",
        ],
        "dependencies": [
            "Modulo base de Odoo (base)",
            "Modulo de contactos (contacts) para duenos de vehiculos",
        ],
        "glossary": [
            {"term": "Placa", "definition": "Identificador unico alfanumerico del vehiculo"},
            {"term": "CRUD", "definition": "Create, Read, Update, Delete - operaciones basicas de persistencia"},
        ],
    }


class TestPRDSchemaValidation:
    """Valid PRD documents must pass schema validation."""

    def test_valid_prd_passes(self, prd_schema):
        jsonschema.validate(_valid_prd(), prd_schema)

    def test_valid_prd_without_optionals_passes(self, prd_schema):
        prd = _valid_prd()
        del prd["constraints"]
        del prd["dependencies"]
        for rf in prd["functional_requirements"]:
            rf.pop("acceptance_criteria", None)
        for ca in prd["acceptance_criteria"]:
            ca.pop("related_requirements", None)
        jsonschema.validate(prd, prd_schema)

    def test_minimal_valid_prd_passes(self, prd_schema):
        prd = {
            "vision": "A simple Odoo module for tracking inventory items.",
            "stakeholders": [
                {"name": "Admin", "role": "User", "interest": "Track stock"}
            ],
            "objectives": ["Automate inventory tracking"],
            "functional_requirements": [
                {
                    "id": "RF-01",
                    "description": "CRUD operations for inventory items",
                    "priority": "high",
                }
            ],
            "non_functional_requirements": [
                {
                    "id": "RNF-01",
                    "description": "Must respond under 1 second for list views",
                    "category": "performance",
                    "priority": "medium",
                }
            ],
            "acceptance_criteria": [
                {
                    "id": "CA-01",
                    "criterion": "User can create an inventory item with name and quantity",
                }
            ],
            "glossary": [
                {"term": "Stock", "definition": "Available inventory quantity"}
            ],
        }
        jsonschema.validate(prd, prd_schema)

    def test_prd_with_extra_properties_fails(self, prd_schema):
        prd = _valid_prd()
        prd["extra_field"] = "should not be here"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)


class TestPRDSchemaMissingRequired:
    """Missing required top-level fields must fail validation."""

    def test_missing_vision_fails(self, prd_schema):
        prd = _valid_prd()
        del prd["vision"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_missing_stakeholders_fails(self, prd_schema):
        prd = _valid_prd()
        del prd["stakeholders"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_missing_objectives_fails(self, prd_schema):
        prd = _valid_prd()
        del prd["objectives"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_missing_functional_requirements_fails(self, prd_schema):
        prd = _valid_prd()
        del prd["functional_requirements"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_missing_non_functional_requirements_fails(self, prd_schema):
        prd = _valid_prd()
        del prd["non_functional_requirements"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_missing_acceptance_criteria_fails(self, prd_schema):
        prd = _valid_prd()
        del prd["acceptance_criteria"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_missing_glossary_fails(self, prd_schema):
        prd = _valid_prd()
        del prd["glossary"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)


class TestPRDSchemaFormatErrors:
    """Invalid field formats must fail validation."""

    def test_invalid_rf_id_format_fails(self, prd_schema):
        prd = _valid_prd()
        prd["functional_requirements"][0]["id"] = "REQ-01"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_invalid_rnf_id_format_fails(self, prd_schema):
        prd = _valid_prd()
        prd["non_functional_requirements"][0]["id"] = "NFR01"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_invalid_ca_id_format_fails(self, prd_schema):
        prd = _valid_prd()
        prd["acceptance_criteria"][0]["id"] = "C-1"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_invalid_rf_priority_fails(self, prd_schema):
        prd = _valid_prd()
        prd["functional_requirements"][0]["priority"] = "critical"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_invalid_rnf_category_fails(self, prd_schema):
        prd = _valid_prd()
        prd["non_functional_requirements"][0]["category"] = "cost"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_invalid_related_requirement_id_fails(self, prd_schema):
        prd = _valid_prd()
        prd["acceptance_criteria"][0]["related_requirements"] = ["BAD-01"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)


class TestPRDSchemaMinItems:
    """Arrays with minItems must be non-empty."""

    def test_empty_stakeholders_fails(self, prd_schema):
        prd = _valid_prd()
        prd["stakeholders"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_empty_objectives_fails(self, prd_schema):
        prd = _valid_prd()
        prd["objectives"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_empty_functional_requirements_fails(self, prd_schema):
        prd = _valid_prd()
        prd["functional_requirements"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_empty_non_functional_requirements_fails(self, prd_schema):
        prd = _valid_prd()
        prd["non_functional_requirements"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_empty_acceptance_criteria_fails(self, prd_schema):
        prd = _valid_prd()
        prd["acceptance_criteria"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_empty_glossary_fails(self, prd_schema):
        prd = _valid_prd()
        prd["glossary"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_empty_acceptance_criteria_in_rf_fails(self, prd_schema):
        prd = _valid_prd()
        prd["functional_requirements"][0]["acceptance_criteria"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)


class TestPRDSchemaStakeholderFields:
    """Stakeholder objects must have all required fields."""

    def test_stakeholder_missing_role_fails(self, prd_schema):
        prd = _valid_prd()
        del prd["stakeholders"][0]["role"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_stakeholder_missing_interest_fails(self, prd_schema):
        prd = _valid_prd()
        del prd["stakeholders"][0]["interest"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_stakeholder_extra_field_fails(self, prd_schema):
        prd = _valid_prd()
        prd["stakeholders"][0]["email"] = "test@example.com"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)


class TestPRDSchemaMinLength:
    """String fields must meet minimum length requirements."""

    def test_vision_too_short_fails(self, prd_schema):
        prd = _valid_prd()
        prd["vision"] = "Short"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_rf_description_too_short_fails(self, prd_schema):
        prd = _valid_prd()
        prd["functional_requirements"][0]["description"] = "Too short"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

    def test_glossary_term_empty_fails(self, prd_schema):
        prd = _valid_prd()
        prd["glossary"][0]["term"] = ""
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(prd, prd_schema)

"""Integration tests simulating the full M1 flow: elicit -> specify."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from fba.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def project(tmp_path):
    """Initialize a fresh FBA project in a temp directory."""
    runner = CliRunner()
    result = runner.invoke(main, ["init", "-d", str(tmp_path)])
    assert result.exit_code == 0
    return tmp_path


def _create_elicitation_context(project_dir: Path):
    """Simulate the Elicitador agent output."""
    context_dir = project_dir / ".factory" / "context"
    context_dir.mkdir(parents=True, exist_ok=True)

    elicitation = {
        "initial_description": "Modulo de registro de vehiculos para Odoo v18 con marca, modelo, ano y placa",
        "business_context": "Empresa de gestion de flotas necesita control de vehiculos con datos basicos y busqueda avanzada",
        "stakeholders": [
            {"name": "Gerente de Flota", "role": "Usuario principal", "interest": "Registro y busqueda rapida de vehiculos"},
            {"name": "Mecanico", "role": "Usuario secundario", "interest": "Consultar datos tecnicos del vehiculo"},
            {"name": "Desarrollador Odoo", "role": "Implementador", "interest": "Modulo bien documentado y mantenible"},
        ],
        "objectives": [
            "Reducir el tiempo de registro de vehiculos de 10 a 2 minutos",
            "Proveer busqueda por placa, marca, modelo y ano",
            "Estandarizar la captura de datos de vehiculos en toda la empresa",
        ],
        "functional_requirements": [
            {
                "id": "RF-01",
                "description": "CRUD de vehiculos con campos: marca, modelo, ano, placa, color, tipo",
                "priority": "high",
                "acceptance_criteria": [
                    "Usuario puede crear vehiculo con campos obligatorios",
                    "Usuario puede editar campos de un vehiculo existente",
                    "Usuario puede eliminar un vehiculo si tiene permisos",
                ],
            },
            {
                "id": "RF-02",
                "description": "Validar unicidad de placa al crear o editar vehiculo",
                "priority": "high",
            },
            {
                "id": "RF-03",
                "description": "Busqueda y filtrado por placa, marca, modelo y ano en vista tree",
                "priority": "medium",
            },
            {
                "id": "RF-04",
                "description": "Vista kanban agrupada por marca para visualizacion rapida",
                "priority": "low",
            },
        ],
        "non_functional_requirements": [
            {
                "id": "RNF-01",
                "description": "Busqueda debe devolver resultados en menos de 2 segundos con hasta 10000 registros",
                "category": "performance",
                "priority": "high",
            },
            {
                "id": "RNF-02",
                "description": "Solo usuarios del grupo Flota pueden modificar registros de vehiculos",
                "category": "security",
                "priority": "high",
            },
            {
                "id": "RNF-03",
                "description": "Interfaz debe ser responsive y funcionar en tablets para uso en taller",
                "category": "usability",
                "priority": "medium",
            },
        ],
        "constraints": [
            "Odoo v18 Community Edition",
            "No dependencia de modulos de pago de Odoo Enterprise",
            "Debe funcionar con PostgreSQL 14+",
        ],
        "dependencies": [
            "Modulo base de Odoo (base)",
            "Modulo de contactos (contacts)",
        ],
        "acceptance_criteria": [
            {
                "id": "CA-01",
                "criterion": "Usuario con permisos crea un vehiculo completo en menos de 1 minuto",
                "related_requirements": ["RF-01"],
            },
            {
                "id": "CA-02",
                "criterion": "El sistema rechaza placas duplicadas con mensaje de error en espanol",
                "related_requirements": ["RF-02"],
            },
            {
                "id": "CA-03",
                "criterion": "Busqueda por placa devuelve el vehiculo correcto en lista de resultados",
                "related_requirements": ["RF-03"],
            },
        ],
        "glossary": [
            {"term": "Placa", "definition": "Identificador alfanumerico unico del vehiculo asignado por la autoridad de transito"},
            {"term": "CRUD", "definition": "Create, Read, Update, Delete - operaciones basicas de persistencia de datos"},
            {"term": "Kanban", "definition": "Vista de tarjetas en Odoo para visualizacion agrupada de registros"},
        ],
    }

    (context_dir / "elicitation.json").write_text(
        json.dumps(elicitation, indent=2, ensure_ascii=False)
    )
    return elicitation


class TestFullElicitationFlow:
    def test_elicitation_creates_context(self, project):
        """Simulate the full elicitation flow: create context and transition."""
        _create_elicitation_context(project)

        context_path = project / ".factory" / "context" / "elicitation.json"
        assert context_path.is_file()

        data = json.loads(context_path.read_text())
        assert data["initial_description"]
        assert len(data["stakeholders"]) == 3
        assert len(data["functional_requirements"]) == 4
        assert len(data["non_functional_requirements"]) == 3

    def test_state_transition_init_to_elicitation(self, runner, project):
        """Transition from init to elicitation."""
        result = runner.invoke(main, ["transition", "elicitation", "-d", str(project)])
        assert result.exit_code == 0

        state = json.loads((project / ".factory" / "state.json").read_text())
        assert state["current_phase"] == "elicitation"
        assert state["phases"]["elicitation"]["status"] == "in_progress"
        assert state["phases"]["init"]["status"] == "complete"

    def test_state_transition_elicitation_to_documentation(self, runner, project):
        """Full chain: init -> elicitation -> documentation."""
        runner.invoke(main, ["transition", "elicitation", "-d", str(project)])
        result = runner.invoke(main, ["transition", "documentation", "-d", str(project), "--force"])
        assert result.exit_code == 0

        state = json.loads((project / ".factory" / "state.json").read_text())
        assert state["current_phase"] == "documentation"
        assert state["phases"]["documentation"]["status"] == "in_progress"

    def test_record_events_through_flow(self, project):
        """Events are recorded during the flow."""
        runner = CliRunner()
        runner.invoke(main, ["transition", "elicitation", "-d", str(project)])

        events_path = project / ".factory" / "events.jsonl"
        events = [
            json.loads(line)
            for line in events_path.read_text().strip().split("\n")
            if line
        ]
        event_types = [e["type"] for e in events]
        assert "init" in event_types
        assert "phase_transition" in event_types

    def test_prd_validation_with_generated_data(self, runner, project):
        """Create elicitation context, then validate a PRD generated from it."""
        _create_elicitation_context(project)

        prd = {
            "vision": "Modulo de registro de vehiculos para gestion de flotas en Odoo v18 con busqueda avanzada y control de datos basicos.",
            "stakeholders": [
                {"name": "Gerente de Flota", "role": "Usuario principal", "interest": "Registro rapido y busqueda"},
                {"name": "Mecanico", "role": "Usuario secundario", "interest": "Consulta de datos tecnicos"},
                {"name": "Desarrollador Odoo", "role": "Implementador", "interest": "Modulo mantenible y documentado"},
            ],
            "objectives": [
                "Reducir tiempo de registro de 10 a 2 minutos",
                "Busqueda por placa, marca, modelo y ano",
            ],
            "functional_requirements": [
                {
                    "id": "RF-01",
                    "description": "CRUD de vehiculos con campos marca, modelo, ano, placa, color, tipo",
                    "priority": "high",
                },
                {
                    "id": "RF-02",
                    "description": "Validar unicidad de placa al crear o editar vehiculo",
                    "priority": "high",
                },
            ],
            "non_functional_requirements": [
                {
                    "id": "RNF-01",
                    "description": "Busqueda en menos de 2 segundos con hasta 10000 registros",
                    "category": "performance",
                    "priority": "high",
                },
                {
                    "id": "RNF-02",
                    "description": "Solo usuarios del grupo Flota pueden modificar vehiculos",
                    "category": "security",
                    "priority": "high",
                },
            ],
            "acceptance_criteria": [
                {
                    "id": "CA-01",
                    "criterion": "Usuario crea un vehiculo completo en menos de 1 minuto",
                    "related_requirements": ["RF-01"],
                },
                {
                    "id": "CA-02",
                    "criterion": "Sistema rechaza placas duplicadas con mensaje de error",
                    "related_requirements": ["RF-02"],
                },
            ],
            "constraints": ["Odoo v18 CE", "No modulos de pago"],
            "dependencies": ["Modulo base", "contacts"],
            "glossary": [
                {"term": "Placa", "definition": "Identificador unico del vehiculo"},
                {"term": "CRUD", "definition": "Create, Read, Update, Delete"},
            ],
        }
        (project / ".factory" / "prd.json").write_text(
            json.dumps(prd, indent=2, ensure_ascii=False)
        )

        result = runner.invoke(main, ["validate", "prd", "-d", str(project)])
        assert result.exit_code == 0
        assert "valid" in result.output

    def test_prd_validation_fails_with_invalid_data(self, runner, project):
        """PRD with missing fields fails validation."""
        _create_elicitation_context(project)

        invalid_prd = {
            "vision": "Short",
        }
        (project / ".factory" / "prd.json").write_text(
            json.dumps(invalid_prd)
        )

        result = runner.invoke(main, ["validate", "prd", "-d", str(project)])
        assert result.exit_code == 1
        assert "validation failed" in result.output

    def test_sdd_validation_via_cli(self, runner, project):
        """Validate an SDD artifact via fba validate sdd."""
        runner.invoke(main, ["init", "-d", str(project)])

        sdd = {
            "module_name": "vehicle_registry",
            "module_display_name": "Vehicle Registry",
            "version": "18.0.1.0.0",
            "summary": "Vehicle management module for Odoo v18",
            "architecture": {
                "description": "Simple module with one model, basic views, and security for vehicle management"
            },
            "models": [
                {
                    "name": "vehicle.registry",
                    "display_name": "Vehicle",
                    "description": "Main vehicle registry model for storing vehicle data",
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
                        }
                    ],
                    "traceability": ["RF-01"]
                }
            ],
            "views": [
                {
                    "model": "vehicle.registry",
                    "type": "form",
                    "name": "vehicle.registry.form",
                    "description": "Main vehicle form view",
                    "fields": ["plate"],
                    "traceability": ["RF-01"]
                }
            ],
            "security": {
                "groups": [
                    {
                        "name": "vehicle_user",
                        "display_name": "Vehicle User",
                        "description": "Can view and create vehicles"
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
                ]
            },
            "dependencies": {
                "required": ["base"],
                "reason": "base module is required for all Odoo addons"
            },
            "file_structure": {
                "module": "vehicle_registry",
                "files": ["__manifest__.py", "__init__.py", "models/vehicle_registry.py"]
            },
            "traceability_matrix": {
                "mappings": [
                    {
                        "requirement": "RF-01",
                        "sdD_components": ["vehicle.registry model", "vehicle.registry.form view"],
                        "description": "CRUD operations for vehicle records"
                    }
                ]
            }
        }
        (project / ".factory" / "sdd.json").write_text(
            json.dumps(sdd, indent=2, ensure_ascii=False)
        )

        result = runner.invoke(main, ["validate", "sdd", "-d", str(project)])
        assert result.exit_code == 0
        assert "valid" in result.output

    def test_sdd_traceability_verification_passes(self, runner, project):
        """Validate SDD with complete PRD→SDD traceability passes."""
        runner.invoke(main, ["init", "-d", str(project)])

        prd = {
            "vision": "Vehicle management module for Odoo v18.",
            "stakeholders": [
                {"name": "Admin", "role": "Manager", "interest": "Vehicle tracking"}
            ],
            "objectives": ["Track vehicles"],
            "functional_requirements": [
                {"id": "RF-01", "description": "CRUD vehicle records", "priority": "high"},
                {"id": "RF-02", "description": "Search by plate", "priority": "medium"},
            ],
            "non_functional_requirements": [
                {"id": "RNF-01", "description": "Search under 2 seconds", "category": "performance", "priority": "high"},
            ],
            "acceptance_criteria": [
                {"id": "CA-01", "criterion": "User creates vehicle in under 1 minute", "related_requirements": ["RF-01"]}
            ],
            "glossary": [{"term": "CRUD", "definition": "Create Read Update Delete"}]
        }
        (project / ".factory" / "prd.json").write_text(json.dumps(prd, indent=2))

        sdd = {
            "module_name": "vehicle_registry",
            "module_display_name": "Vehicle Registry",
            "version": "18.0.1.0.0",
            "architecture": {"description": "Simple vehicle management module"},
            "models": [{
                "name": "vehicle.registry",
                "display_name": "Vehicle",
                "description": "Main vehicle model",
                "fields": [{
                    "name": "plate", "type": "char", "display_name": "Plate",
                    "description": "License plate number",
                    "traceability": ["RF-01"]
                }],
                "traceability": ["RF-01", "RF-02"]
            }],
            "views": [{
                "model": "vehicle.registry", "type": "form", "name": "vehicle.form",
                "description": "Vehicle form view", "fields": ["plate"],
                "traceability": ["RF-01"]
            }],
            "security": {
                "groups": [{
                    "name": "vehicle_user", "display_name": "Vehicle User",
                    "description": "Basic vehicle access"
                }],
                "access_rights": [{
                    "model": "vehicle.registry", "group": "vehicle_user",
                    "perm_read": True, "perm_write": True,
                    "perm_create": True, "perm_unlink": False
                }]
            },
            "dependencies": {"required": ["base"]},
            "file_structure": {
                "module": "vehicle_registry",
                "files": ["__manifest__.py"]
            },
            "traceability_matrix": {
                "mappings": [
                    {
                        "requirement": "RF-01",
                        "sdD_components": ["vehicle.registry model", "vehicle.form view"],
                        "description": "CRUD vehicle records"
                    },
                    {
                        "requirement": "RF-02",
                        "sdD_components": ["vehicle.registry model"],
                        "description": "Search by plate"
                    },
                    {
                        "requirement": "RNF-01",
                        "sdD_components": ["security section"],
                        "description": "Performance requirement"
                    }
                ]
            }
        }
        (project / ".factory" / "sdd.json").write_text(json.dumps(sdd, indent=2))

        result = runner.invoke(main, ["validate", "sdd", "-d", str(project)])
        assert result.exit_code == 0
        assert "3 requirements mapped" in result.output

    def test_sdd_traceability_verification_fails_on_unmapped(self, runner, project):
        """Validate SDD fails traceability check when requirements not mapped."""
        runner.invoke(main, ["init", "-d", str(project)])

        prd = {
            "vision": "Vehicle management module for Odoo v18.",
            "stakeholders": [
                {"name": "Admin", "role": "Manager", "interest": "Vehicle tracking"}
            ],
            "objectives": ["Track vehicles"],
            "functional_requirements": [
                {"id": "RF-01", "description": "CRUD vehicle records", "priority": "high"},
                {"id": "RF-02", "description": "Search by plate", "priority": "medium"},
            ],
            "non_functional_requirements": [],
            "acceptance_criteria": [
                {"id": "CA-01", "criterion": "User creates vehicle", "related_requirements": ["RF-01"]}
            ],
            "glossary": [{"term": "CRUD", "definition": "Create Read Update Delete"}]
        }
        (project / ".factory" / "prd.json").write_text(json.dumps(prd, indent=2))

        sdd = {
            "module_name": "vehicle_registry",
            "module_display_name": "Vehicle Registry",
            "version": "18.0.1.0.0",
            "architecture": {"description": "Simple vehicle management module"},
            "models": [{
                "name": "vehicle.registry",
                "display_name": "Vehicle",
                "description": "Main vehicle model",
                "fields": [{
                    "name": "plate", "type": "char", "display_name": "Plate",
                    "description": "License plate number",
                    "traceability": ["RF-01"]
                }],
                "traceability": ["RF-01"]
            }],
            "views": [{
                "model": "vehicle.registry", "type": "form", "name": "vehicle.form",
                "description": "Vehicle form view", "fields": ["plate"],
                "traceability": ["RF-01"]
            }],
            "security": {
                "groups": [{
                    "name": "vehicle_user", "display_name": "Vehicle User",
                    "description": "Basic vehicle access"
                }],
                "access_rights": [{
                    "model": "vehicle.registry", "group": "vehicle_user",
                    "perm_read": True, "perm_write": True,
                    "perm_create": True, "perm_unlink": False
                }]
            },
            "dependencies": {"required": ["base"]},
            "file_structure": {
                "module": "vehicle_registry",
                "files": ["__manifest__.py"]
            },
            "traceability_matrix": {
                "mappings": [
                    {
                        "requirement": "RF-01",
                        "sdD_components": ["vehicle.registry model"],
                        "description": "CRUD vehicle records"
                    }
                ]
            }
        }
        (project / ".factory" / "sdd.json").write_text(json.dumps(sdd, indent=2))

        result = runner.invoke(main, ["validate", "sdd", "-d", str(project)])
        assert result.exit_code == 1
        assert "not mapped" in result.output
        assert "RF-02" in result.output

    def test_complete_m1_flow(self, runner, project):
        """End-to-end simulation of the M1 flow: elicit -> specify."""
        _create_elicitation_context(project)

        runner.invoke(main, ["transition", "elicitation", "-d", str(project)])
        runner.invoke(main, ["record", "elicitation_complete",
                             "--data", '{"methodology":"BABOK","rf_count":4}', "-d", str(project)])

        runner.invoke(main, ["transition", "documentation", "-d", str(project)])
        runner.invoke(main, ["record", "specification_complete",
                             "--data", '{"artifacts":["prd.json","prd.md"]}', "-d", str(project)])

        state = json.loads((project / ".factory" / "state.json").read_text())
        assert state["current_phase"] == "documentation"
        assert state["phases"]["init"]["status"] == "complete"
        assert state["phases"]["elicitation"]["status"] == "complete"
        assert state["phases"]["documentation"]["status"] == "in_progress"

        events = [
            json.loads(line)
            for line in (project / ".factory" / "events.jsonl").read_text().strip().split("\n")
            if line
        ]
        event_types = [e["type"] for e in events]
        assert "init" in event_types
        assert "elicitation_complete" in event_types
        assert "specification_complete" in event_types
        assert event_types.count("phase_transition") == 2

# Factory Build Agent

Framework multi-agente para desarrollo de modulos Odoo v18 con IA.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenCode](https://img.shields.io/badge/runs_on-OpenCode-orange.svg)](https://opencode.ai)

## Que es FBA?

Factory Build Agent es un framework de desarrollo por agentes de IA que automatiza
el ciclo completo de creacion de modulos Odoo v18:

- **Elicita** requisitos usando metodologia BABOK (Business Analysis Body of Knowledge)
- **Genera** PRD (Product Requirements Document) y SDD (Software Design Document)
- **Construye** modulos Odoo v18 automaticamente (modelos, vistas, seguridad, datos)
- **Prueba** los modulos generados con tests unitarios y de integracion
- **Revisa** la calidad del codigo generado
- **Integra** CI/CD con GitHub Actions para despliegue continuo

Se ejecuta sobre **OpenCode** como runtime, aprovechando su sistema de agentes,
slash commands y soporte multi-modelo.

Inspirado en los conceptos de **OpenSpec** (Fission-AI) y **SpecKit** (GitHub).
Compatible con sus formatos de artefactos.

## Instalacion

```bash
pip install fba
```

## Uso Rapido

```bash
# 1. Inicializar un proyecto Odoo para usar FBA
cd mi-proyecto-odoo
fba init

# 2. Abrir con OpenCode y empezar el flujo
opencode .

# 3. Dentro de OpenCode, elicitar requisitos
# > /fba:elicit "Quiero un modulo de facturacion electronica para Odoo 18"

# 4. Seguir el flujo completo
# > /fba:specify
# > /fba:plan
# > /fba:tasks
# > /fba:construct
# > /fba:test
# > /fba:review
# > /fba:ship
```

## Flujo de Desarrollo

```
/fba:init ──► /fba:elicit ──► /fba:specify ──► /fba:plan ──► /fba:tasks
                                                                    │
/fba:ship ◄── /fba:review ◄── /fba:test ◄── /fba:construct ◄───────────┘
```

## Arquitectura

Factory Build Agent esta compuesto por un **orquestador** y **9 sub-agentes**
especializados, cada uno definido declarativamente en Markdown:

| Agente | Responsabilidad |
|--------|----------------|
| Elicitador | Elicitar requisitos con metodologia BABOK |
| Documentador | Generar PRD.md y SDD.md |
| Planificador | Crear plan tecnico y arquitectura Odoo v18 |
| Revisor de Artefactos | Validar artefactos contra schemas y coherencia cross-artifact |
| Validador Semantico | Validar alineacion semantica contra solicitud original |
| Code Generator | Generar codigo del modulo Odoo v18 |
| Tester/QA | Generar y ejecutar pruebas |
| Revisor de Codigo | Revisar calidad, seguridad y adherencia |
| CI/CD Manager | Generar workflows de GitHub Actions |

Los agentes se comunican mediante un sistema hibrido: artefactos en archivos
(.factory/) + registro de eventos (events.jsonl) + git.

## Documentacion

| Documento | Descripcion |
|-----------|-------------|
| [ROADMAP.md](ROADMAP.md) | Estado del proyecto y plan de hitos |
| [docs/PRD.md](docs/PRD.md) | PRD del propio framework |
| [AGENTS.md](AGENTS.md) | Contexto tecnico para asistentes AI (OpenCode) |

## Estructura del Proyecto

```
factory-build-agent/
├── AGENTS.md              # Contexto para OpenCode
├── CONTRIBUTING.md        # Workflow de desarrollo
├── README.md              # Este archivo
├── ROADMAP.md             # Hitos y progreso
├── CHANGELOG.md           # Registro de cambios
├── LICENSE                # Licencia MIT
├── pyproject.toml         # Configuracion del paquete Python
├── .github/               # CI/CD del framework (workflows, templates)
├── src/fba/               # Codigo fuente del framework
├── templates/             # Plantillas que `fba init` copia al proyecto Odoo
├── schemas/               # JSON Schemas para validacion de artefactos
├── tests/                 # Tests del framework
└── docs/                  # Documentacion del framework
    └── testing/           # Guias de testing por milestone
```

## Requisitos

- Python 3.11 o superior
- OpenCode ([opencode.ai](https://opencode.ai))

## Licencia

MIT - Ver [LICENSE](LICENSE)

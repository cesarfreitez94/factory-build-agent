# Factory Build Agent - Product Requirements Document

> **Proposito**: Este documento define los requisitos del framework Factory Build Agent en si mismo.
> **Metodologia**: BABOK (Business Analysis Body of Knowledge)
> **Version**: 0.1.0

---

## Vision

Factory Build Agent (FBA) es un framework de desarrollo multi-agente que automatiza
el ciclo completo de creacion de modulos Odoo v18. Se ejecuta sobre OpenCode como
runtime y utiliza agentes de IA especializados coordinados por un orquestador.

El framework permite a un desarrollador de Odoo describir su idea en lenguaje natural
y obtener como resultado un modulo Odoo v18 completo, probado y listo para produccion,
con toda la documentacion (PRD, SDD) generada automaticamente.

## Stakeholders

| Stakeholder | Rol | Interes |
|-------------|-----|---------|
| Desarrollador Odoo | Usuario final | Crear modulos Odoo v18 rapidamente con calidad asegurada |
| Tech Lead | Supervisor | Control de calidad, revision de especificaciones |
| Comunidad Odoo | Beneficiarios | Framework open source que acelera el desarrollo |

## Objetivos

1. Reducir el tiempo de desarrollo de modulos Odoo v18
2. Estandarizar el proceso de elicitacion y documentacion con BABOK
3. Garantizar calidad mediante testing automatizado y code review
4. Integrar CI/CD nativamente con GitHub Actions
5. Ser extensible para nuevas metodologias y tipos de modulos

## Requisitos Funcionales

### RF-01: Inicializacion de Proyecto
El CLI `fba init` debe crear la estructura completa de directorios y archivos
necesarios para que un proyecto Odoo use el framework.

### RF-02: Definicion Declarativa de Agentes
Los agentes deben definirse en archivos YAML independientes.
Agregar un nuevo agente no debe requerir modificar el codigo del framework.

### RF-03: Gestion de Estado
El framework debe mantener un archivo de estado (state.json) que refleje
la fase actual del desarrollo, los artefactos generados y su estado.

### RF-04: Registro de Eventos
Todas las transiciones y acciones deben registrarse en un log de eventos
inmutable (events.jsonl) para trazabilidad completa.

### RF-05: Elicitacion BABOK
El flujo de elicitacion debe seguir la metodologia BABOK, incluyendo:
- Identificacion de stakeholders
- Elicitacion de requisitos funcionales y no funcionales
- Definicion de criterios de aceptacion
- Gestion del ciclo de vida de requisitos

### RF-06: Generacion de PRD
El framework debe generar un documento PRD.md estructurado con:
- Vision y objetivos
- Stakeholders
- Requisitos funcionales
- Requisitos no funcionales
- Criterios de aceptacion
- Glosario

### RF-07: Generacion de SDD
El framework debe generar un documento SDD.md con:
- Arquitectura Odoo v18 (modulos, modelos, vistas)
- Diseno de seguridad (grupos, permisos, ACLs)
- Dependencias entre modulos
- Estructura de archivos del modulo

### RF-08: Plan Tecnico
Debe generarse un plan.md con la secuencia de implementacion,
riesgos identificados y estimaciones.

### RF-09: Generacion de Codigo Odoo v18
El constructor debe generar:
- `__manifest__.py` completo
- Modelos Python con campos, relaciones y metodos
- Vistas XML (tree, form, search, kanban)
- Archivos de seguridad (ir.model.access.csv)
- Datos demo y configuracion inicial

### RF-10: Testing Automatico
El agente de QA debe generar tests Odoo (Odoo TestCase) y ejecutarlos,
generando un reporte de resultados.

### RF-11: Code Review
El revisor debe analizar el codigo generado verificando:
- Adherencia a las especificaciones (PRD + SDD)
- Calidad del codigo (estilo Odoo, PEP8)
- Seguridad (permisos, inyeccion, exposicion de datos)
- Completitud (todas las tareas implementadas)

### RF-12: CI/CD con GitHub Actions
El CI/CD Manager debe generar un workflow de GitHub Actions que:
- Ejecute tests automaticamente en PRs
- Genere el modulo empaquetado
- Cree un release tag siguiendo semantic versioning

## Requisitos No Funcionales

### RNF-01: Extensibilidad
El framework debe permitir agregar nuevos agentes, metodologias y tipos
de artefactos sin modificar el codigo del nucleo.

### RNF-02: Compatibilidad
Los artefactos generados (PRD, SDD) deben ser compatibles con los formatos
usados por OpenSpec y SpecKit.

### RNF-03: Rendimiento
El ciclo completo (elicitacion -> ship) para un modulo CRUD simple debe
completarse en menos de 30 minutos con un modelo de IA adecuado.

### RNF-04: Testing del Framework
El framework mismo debe tener cobertura de tests >= 80%.

### RNF-05: Documentacion
Todo comando slash y agente debe estar documentado.
El framework debe incluir su propio PRD generado con el mismo framework.

## Criterios de Aceptacion

| ID | Criterio | Milestone |
|----|----------|-----------|
| CA-01 | `pip install fba` instala el CLI | M0 |
| CA-02 | `fba init` crea estructura completa | M0 |
| CA-03 | `pytest` pasa todos los tests | Todos |
| CA-04 | PRD.md generado pasa validacion de schema | M1 |
| CA-05 | SDD.md incluye trazabilidad a PRD | M2 |
| CA-06 | Modulo Odoo generado se instala sin errores | M3 |
| CA-07 | Tests Odoo del modulo generado pasan | M3 |
| CA-08 | Code review no encuentra issues criticos | M3 |
| CA-09 | Workflow CI/CD se ejecuta correctamente en GitHub | M3 |

## Glosario

| Termino | Definicion |
|---------|-----------|
| FBA | Factory Build Agent - El framework mismo |
| OpenCode | Agente CLI open source que ejecuta los comandos slash |
| BABOK | Business Analysis Body of Knowledge - Metodologia de analisis de negocio |
| PRD | Product Requirements Document - Documento de requisitos del producto |
| SDD | Software Design Document - Documento de diseno del software |
| Odoo v18 | Version 18 de Odoo ERP, target del framework |
| Slash Command | Comando que se ejecuta dentro de OpenCode (ej: `/fba:elicit`) |
| Orquestador | Agente principal que coordina las fases y sub-agentes |

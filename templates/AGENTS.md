# Factory Build Agent

> Este archivo es el contexto del proyecto para OpenCode y los agentes de IA.
> Fue generado automaticamente al ejecutar `fba init`.

## Project Overview

Este proyecto usa Factory Build Agent para el desarrollo de modulos Odoo v18.

## Agent Workflow

El flujo de desarrollo sigue estas fases:

1. **Elicitacion** (`/fba:elicit`) - Elicitacion de requisitos usando BABOK
2. **Especificacion** (`/fba:specify`) - Generacion de PRD.md
3. **Planificacion** (`/fba:plan`) - Generacion de SDD.md y plan tecnico
4. **Tareas** (`/fba:tasks`) - Desglose de tareas implementables
5. **Construccion** (`/fba:build`) - Generacion de codigo Odoo v18
6. **Testing** (`/fba:test`) - Generacion y ejecucion de pruebas
7. **Revision** (`/fba:review`) - Revision de calidad y seguridad
8. **Despliegue** (`/fba:ship`) - CI/CD y preparacion de release

## Estado del Proyecto

El estado actual del proyecto se encuentra en `.factory/state.json`.
El registro de eventos esta en `.factory/events.jsonl`.

## Artefactos

Los artefactos generados se almacenan en `.factory/`:
- `constitution.md` - Principios y directrices del proyecto
- `prd.md` - Documento de Requisitos del Producto
- `sdd.md` - Documento de Diseno del Software
- `plan.md` - Plan tecnico
- `tasks.md` - Lista de tareas implementables

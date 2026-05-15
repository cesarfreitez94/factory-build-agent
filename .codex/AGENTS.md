# Contexto local de .codex

Esta carpeta contiene el marco de colaboracion entre Codex y el desarrollo del
framework FBA. No forma parte del runtime de `fba`, no se copia a proyectos
Odoo con `fba init`, y no reemplaza `.opencode/`.

## Reglas

- Mantener estos archivos como documentacion operativa para Codex.
- No introducir dependencias, scripts runtime ni configuracion de producto aqui.
- Respetar siempre las fuentes de verdad del repositorio:
  - `AGENTS.md`
  - `CONTRIBUTING.md`
  - `ROADMAP.md`
  - `CHANGELOG.md`
- Si un cambio en `.codex` modifica el modo de trabajo del agente, registrar el
  cambio en `CHANGELOG.md`.
- Escribir en espanol, con identificadores tecnicos en ingles cuando aplique.

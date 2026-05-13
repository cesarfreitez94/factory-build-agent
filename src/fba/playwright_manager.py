import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from fba.state import _atomic_write


class PlaywrightError(Exception):
    """Raised when Playwright artifact generation cannot continue."""


@dataclass
class PlaywrightViewCase:
    name: str
    model: str
    view_type: str
    fields: list[str]


@dataclass
class PlaywrightReport:
    spec_path: Path
    json_path: Path
    md_path: Path
    cases: list[PlaywrightViewCase] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_cases(self) -> int:
        return len(self.cases)


class PlaywrightManager:
    """Generates browser automation specs for Odoo views from schema.json."""

    SUPPORTED_VIEW_TYPES = {"form", "list", "kanban"}

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.factory_dir = self.project_dir / ".factory"

    def generate(self, base_url: str = "http://localhost:8069", output_dir: Path | None = None) -> PlaywrightReport:
        schema = self._load_schema()
        output_dir = output_dir or self.factory_dir / "playwright"
        output_dir.mkdir(parents=True, exist_ok=True)

        cases, warnings = self._collect_cases(schema)
        spec_path = output_dir / "odoo_views.spec.ts"
        json_path = output_dir / "playwright_report.json"
        md_path = output_dir / "playwright_report.md"

        _atomic_write(spec_path, self._render_spec(cases, base_url))
        report = PlaywrightReport(spec_path=spec_path, json_path=json_path, md_path=md_path, cases=cases, warnings=warnings)
        _atomic_write(json_path, self._render_json_report(report))
        _atomic_write(md_path, self._render_md_report(report))
        return report

    def _load_schema(self) -> dict[str, Any]:
        schema_path = self.factory_dir / "schema.json"
        if not schema_path.exists():
            raise PlaywrightError(f"schema.json not found at {schema_path}")
        try:
            return cast(dict[str, Any], json.loads(schema_path.read_text()))
        except json.JSONDecodeError as e:
            raise PlaywrightError(f"schema.json is invalid JSON: {e}") from e

    def _collect_cases(self, schema: dict[str, Any]) -> tuple[list[PlaywrightViewCase], list[str]]:
        cases: list[PlaywrightViewCase] = []
        warnings: list[str] = []
        for view in schema.get("views", []):
            view_type = str(view.get("type", ""))
            if view_type not in self.SUPPORTED_VIEW_TYPES:
                continue
            fields = [str(f) for f in view.get("fields", []) if str(f)]
            if not fields:
                warnings.append(f"View {view.get('name', 'unnamed')} has no fields and was skipped")
                continue
            cases.append(PlaywrightViewCase(
                name=str(view.get("name", "")),
                model=str(view.get("model", "")),
                view_type=view_type,
                fields=fields,
            ))
        if not cases:
            warnings.append("No form, list, or kanban views found in schema.json")
        return cases, warnings

    def _render_spec(self, cases: list[PlaywrightViewCase], base_url: str) -> str:
        cases_json = json.dumps([
            {
                "name": c.name,
                "model": c.model,
                "viewType": c.view_type,
                "fields": c.fields,
            }
            for c in cases
        ], indent=2, ensure_ascii=False)
        return f"""import {{ expect, test }} from '@playwright/test';

const baseUrl = process.env.ODOO_URL || {json.dumps(base_url)};
const viewCases = {cases_json};

for (const viewCase of viewCases) {{
  test(`${{viewCase.viewType}} view renders for ${{viewCase.model}}`, async ({{ page }}) => {{
    const actionUrl = `${{baseUrl}}/web#model=${{viewCase.model}}&view_type=${{viewCase.viewType}}`;
    await page.goto(actionUrl);
    await expect(page.locator('.o_web_client')).toBeVisible();

    for (const field of viewCase.fields) {{
      await expect(page.locator(`[name="${{field}}"], [data-name="${{field}}"]`).first()).toBeVisible();
    }}
  }});
}}
"""

    def _render_json_report(self, report: PlaywrightReport) -> str:
        payload = {
            "spec_path": str(report.spec_path),
            "total_cases": report.total_cases,
            "warnings": report.warnings,
            "cases": [
                {
                    "name": c.name,
                    "model": c.model,
                    "view_type": c.view_type,
                    "fields": c.fields,
                }
                for c in report.cases
            ],
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _render_md_report(self, report: PlaywrightReport) -> str:
        lines = [
            "# Playwright QA Report",
            "",
            f"- Spec: `{report.spec_path}`",
            f"- Casos generados: {report.total_cases}",
            "",
            "## Casos",
            "",
        ]
        if report.cases:
            for case in report.cases:
                lines.append(f"- `{case.view_type}` `{case.model}`: {', '.join(case.fields)}")
        else:
            lines.append("- No se generaron casos.")
        if report.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- {warning}" for warning in report.warnings)
        lines.append("")
        return "\n".join(lines)

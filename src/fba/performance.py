import json
import time
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from fba.schema_manager import SchemaManager
from fba.state import _atomic_write


class PerformanceError(Exception):
    """Raised when performance benchmarks cannot run."""


@dataclass
class BenchmarkMetric:
    name: str
    duration_ms: float
    peak_kb: float
    status: str
    detail: str = ""


@dataclass
class PerformanceReport:
    output_dir: Path
    json_path: Path
    md_path: Path
    metrics: list[BenchmarkMetric] = field(default_factory=list)

    @property
    def total_benchmarks(self) -> int:
        return len(self.metrics)

    @property
    def warning_count(self) -> int:
        return sum(1 for metric in self.metrics if metric.status == "warning")


class PerformanceRunner:
    """Runs deterministic performance checks for generated FBA artifacts."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.factory_dir = self.project_dir / ".factory"

    def run(self, output_dir: Path | None = None) -> PerformanceReport:
        if not self.factory_dir.exists():
            raise PerformanceError(f"No .factory/ found in {self.project_dir}")

        output_dir = output_dir or self.factory_dir / "perf"
        output_dir.mkdir(parents=True, exist_ok=True)

        metrics = [
            self._measure("schema_load", self._schema_load),
            self._measure("schema_generation", lambda: self._schema_generation(output_dir)),
            self._measure("artifact_scan", self._artifact_scan),
        ]

        report = PerformanceReport(
            output_dir=output_dir,
            json_path=output_dir / "perf_report.json",
            md_path=output_dir / "perf_report.md",
            metrics=metrics,
        )
        _atomic_write(report.json_path, self._render_json(report))
        _atomic_write(report.md_path, self._render_md(report))
        return report

    def _measure(self, name: str, fn: Callable[[], tuple[str, str]]) -> BenchmarkMetric:
        tracemalloc.start()
        start = time.perf_counter()
        try:
            status, detail = fn()
        except Exception as e:
            status = "error"
            detail = str(e)
        duration_ms = (time.perf_counter() - start) * 1000
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return BenchmarkMetric(
            name=name,
            duration_ms=round(duration_ms, 3),
            peak_kb=round(peak / 1024, 3),
            status=status,
            detail=detail,
        )

    def _schema_load(self) -> tuple[str, str]:
        schema_path = self.factory_dir / "schema.json"
        if not schema_path.exists():
            return "warning", "schema.json not found"
        schema = json.loads(schema_path.read_text())
        models = len(schema.get("models", []))
        views = len(schema.get("views", []))
        return "ok", f"{models} models, {views} views"

    def _schema_generation(self, output_dir: Path) -> tuple[str, str]:
        if not (self.factory_dir / "tasks" / "index.json").exists():
            return "warning", "task index not found; generation benchmark skipped"
        result = SchemaManager(self.project_dir).assemble(output_path=output_dir / "schema.benchmark.json")
        if result.errors:
            return "error", "; ".join(result.error_messages)
        if result.warnings:
            return "warning", "; ".join(result.warning_messages)
        return "ok", f"{len(result.schema.get('models', []))} models generated"

    def _artifact_scan(self) -> tuple[str, str]:
        files = [p for p in self.project_dir.rglob("*") if p.is_file() and ".git" not in p.parts]
        total_bytes = sum(p.stat().st_size for p in files)
        return "ok", f"{len(files)} files, {total_bytes} bytes"

    def _render_json(self, report: PerformanceReport) -> str:
        payload: dict[str, Any] = {
            "total_benchmarks": report.total_benchmarks,
            "warnings": report.warning_count,
            "metrics": [
                {
                    "name": metric.name,
                    "duration_ms": metric.duration_ms,
                    "peak_kb": metric.peak_kb,
                    "status": metric.status,
                    "detail": metric.detail,
                }
                for metric in report.metrics
            ],
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _render_md(self, report: PerformanceReport) -> str:
        lines = [
            "# Performance QA Report",
            "",
            "| Benchmark | Status | Time (ms) | Peak KB | Detail |",
            "|-----------|--------|-----------|---------|--------|",
        ]
        for metric in report.metrics:
            lines.append(
                f"| {metric.name} | {metric.status} | {metric.duration_ms} | {metric.peak_kb} | {metric.detail} |"
            )
        lines.append("")
        return "\n".join(lines)

"""Tests for M15 feat/15.2: performance benchmark suite."""

import json
from pathlib import Path

from click.testing import CliRunner

from fba.cli import main
from fba.performance import PerformanceRunner


def _write_schema(project_dir: Path) -> None:
    factory_dir = project_dir / ".factory"
    factory_dir.mkdir(parents=True, exist_ok=True)
    (factory_dir / "schema.json").write_text(json.dumps({
        "manifest": {"name": "bench_module", "version": "18.0.1.0.0", "depends": ["base"], "license": "LGPL-3"},
        "models": [{"name": "bench.model", "fields": [{"name": "name", "type": "Char", "label": "Name"}]}],
        "views": [{"name": "bench.model.form", "type": "form", "model": "bench.model", "fields": ["name"]}],
        "security": {"groups": [], "access_rights": [], "record_rules": []},
        "data": [],
    }, indent=2))


def _write_tasks(project_dir: Path) -> None:
    factory_dir = project_dir / ".factory"
    tasks_dir = factory_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (factory_dir / "sdd.json").write_text(json.dumps({
        "module_name": "bench_module",
        "dependencies": {"required": ["base"]},
    }))
    (tasks_dir / "index.json").write_text(json.dumps({
        "module_name": "bench_module",
        "tasks": [{"id": "T001", "file": "T001.json"}],
    }))
    (tasks_dir / "T001.json").write_text(json.dumps({
        "id": "T001",
        "components": [
            {
                "type": "model",
                "name": "bench.model",
                "description": "Bench model",
                "fields": [{"name": "name", "type": "Char", "label": "Name"}],
            },
            {
                "type": "view",
                "name": "bench.model.form",
                "view_type": "form",
                "model": "bench.model",
                "fields": ["name"],
            },
        ],
    }))


def test_performance_runner_writes_reports(tmp_path):
    _write_schema(tmp_path)

    report = PerformanceRunner(tmp_path).run()

    assert report.total_benchmarks == 3
    assert report.json_path.exists()
    assert report.md_path.exists()
    payload = json.loads(report.json_path.read_text())
    assert payload["total_benchmarks"] == 3
    assert {metric["name"] for metric in payload["metrics"]} == {"schema_load", "schema_generation", "artifact_scan"}


def test_performance_runner_generates_schema_when_tasks_exist(tmp_path):
    _write_schema(tmp_path)
    _write_tasks(tmp_path)

    report = PerformanceRunner(tmp_path).run()

    generation = next(metric for metric in report.metrics if metric.name == "schema_generation")
    assert generation.status in {"ok", "warning"}
    assert (tmp_path / ".factory" / "perf" / "schema.benchmark.json").exists()


def test_cli_perf_outputs_summary(tmp_path):
    _write_schema(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["perf", "-d", str(tmp_path)])

    assert result.exit_code == 0
    assert "Performance benchmarks completed" in result.output
    assert (tmp_path / ".factory" / "perf" / "perf_report.json").exists()


def test_cli_perf_json_outputs_report(tmp_path):
    _write_schema(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["perf", "-d", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["total_benchmarks"] == 3

"""Tests for Odoo dependency integrity analysis."""

from pathlib import Path

import pytest

from fba.dependency_analyzer import (
    DependencyAnalyzer,
    DependencyError,
    DependencyResult,
)


def _make_module(base_path: Path, name: str, depends=None, python_files=None):
    """Create a minimal Odoo module directory."""
    mod_dir = base_path / name
    mod_dir.mkdir(parents=True, exist_ok=True)

    deps_list = depends or ["base"]
    manifest = (
        "{\n"
        f"    'name': '{name}',\n"
        f"    'depends': {deps_list!r},\n"
        "    'data': [],\n"
        "}"
    )
    (mod_dir / "__manifest__.py").write_text(manifest)

    if python_files:
        for rel_path, content in python_files.items():
            py_path = mod_dir / rel_path
            py_path.parent.mkdir(parents=True, exist_ok=True)
            py_path.write_text(content)
    else:
        (mod_dir / "__init__.py").write_text("")
        (mod_dir / "models").mkdir(exist_ok=True)
        (mod_dir / "models" / "__init__.py").write_text("from . import my_model\n")
        (mod_dir / "models" / "my_model.py").write_text(
            "from odoo import models, fields\n\n"
            "class MyModel(models.Model):\n"
            "    _name = 'my.model'\n"
            "    name = fields.Char()\n"
        )

    return mod_dir


class TestDependencyAnalyzerBasics:
    """Basic dependency analysis tests."""

    def test_clean_module_no_issues(self, tmp_path):
        mod = _make_module(tmp_path, "my_module", depends=["base"])
        analyzer = DependencyAnalyzer()
        result = analyzer.analyze_module(mod)

        assert result.is_clean
        assert result.summary["total_issues"] == 0

    def test_manifest_not_found(self, tmp_path):
        mod_dir = tmp_path / "no_manifest"
        mod_dir.mkdir()
        analyzer = DependencyAnalyzer()

        with pytest.raises(DependencyError, match="__manifest__.py not found"):
            analyzer.analyze_module(mod_dir)

    def test_malformed_manifest_handled_gracefully(self, tmp_path):
        mod_dir = tmp_path / "bad_module"
        mod_dir.mkdir()
        (mod_dir / "__manifest__.py").write_text("this is not valid python {{")
        analyzer = DependencyAnalyzer()
        # Should not crash — malformed manifests are handled gracefully
        result = analyzer.analyze_module(mod_dir)
        assert result.summary["declared_deps"] == []
        assert not result.has_issues

    def test_module_path_not_found(self, tmp_path):
        analyzer = DependencyAnalyzer()
        with pytest.raises(DependencyError, match="not found"):
            analyzer.analyze_module(tmp_path / "nonexistent")


class TestUnusedDependencies:
    """Tests for detecting unused dependencies."""

    def test_unused_dependency_detected(self, tmp_path):
        mod = _make_module(tmp_path, "my_module", depends=["base", "unused_mod"])
        analyzer = DependencyAnalyzer()
        result = analyzer.analyze_module(mod)

        assert not result.is_clean
        unused = [i for i in result.issues if i["type"] == "unused_dependency"]
        assert len(unused) >= 1
        assert any("unused_mod" in i["module"] for i in unused)

    def test_core_odoo_modules_not_flagged(self, tmp_path):
        mod = _make_module(tmp_path, "my_module", depends=["base", "web", "mail"])
        analyzer = DependencyAnalyzer()
        result = analyzer.analyze_module(mod)

        unused = [i for i in result.issues if i["type"] == "unused_dependency"]
        assert len(unused) == 0

    def test_summary_counts_unused_correctly(self, tmp_path):
        mod = _make_module(tmp_path, "my_module", depends=["base", "unused_a", "unused_b"])
        analyzer = DependencyAnalyzer()
        result = analyzer.analyze_module(mod)

        assert result.summary["unused_count"] >= 2


class TestMissingDependencies:
    """Tests for detecting missing dependencies."""

    def test_missing_dependency_detected(self, tmp_path):
        mod = _make_module(
            tmp_path,
            "my_module",
            depends=["base"],
            python_files={
                "models/my_model.py": (
                    "from odoo import models, fields\n"
                    "from odoo.addons.sale.models.sale_order import SaleOrder\n\n"
                    "class MyModel(models.Model):\n"
                    "    _name = 'my.model'\n"
                    "    _inherit = ['sale.order']\n"
                    "    name = fields.Char()\n"
                ),
            },
        )
        analyzer = DependencyAnalyzer()
        result = analyzer.analyze_module(mod)

        missing = [i for i in result.issues if i["type"] == "missing_dependency"]
        assert len(missing) >= 1
        assert any("sale" in i["module"] for i in missing)

    def test_stdlib_modules_not_flagged(self, tmp_path):
        mod = _make_module(
            tmp_path,
            "my_module",
            depends=["base"],
            python_files={
                "models/my_model.py": (
                    "import os, json, re\n"
                    "from odoo import models, fields\n\n"
                    "class MyModel(models.Model):\n"
                    "    _name = 'my.model'\n"
                    "    name = fields.Char()\n"
                ),
            },
        )
        analyzer = DependencyAnalyzer()
        result = analyzer.analyze_module(mod)

        missing = [i for i in result.issues if i["type"] == "missing_dependency"]
        assert len(missing) == 0

    def test_many2one_reference_detected(self, tmp_path):
        mod = _make_module(
            tmp_path,
            "my_module",
            depends=["base"],
            python_files={
                "models/my_model.py": (
                    "from odoo import models, fields\n\n"
                    "class MyModel(models.Model):\n"
                    "    _name = 'my.model'\n"
                    "    partner_id = fields.Many2one('res.partner')\n"
                ),
            },
        )
        analyzer = DependencyAnalyzer()
        result = analyzer.analyze_module(mod)

        missing = [i for i in result.issues if i["type"] == "missing_dependency"]
        assert any("res" in i["module"] or "partner" in i["module"] for i in missing)


class TestCircularDependencies:
    """Tests for detecting circular dependencies."""

    def test_circular_simple_detected(self, tmp_path):
        mod_a = _make_module(tmp_path, "module_a", depends=["base", "module_b"])
        mod_b = _make_module(tmp_path, "module_b", depends=["base", "module_a"])

        analyzer = DependencyAnalyzer()
        result = analyzer.analyze_module(
            mod_a, project_modules={"module_a", "module_b"}
        )

        circular = [i for i in result.issues if i["type"] == "circular_dependency"]
        assert len(circular) >= 1

    def test_circular_transitive_detected(self, tmp_path):
        mod_a = _make_module(tmp_path, "module_a", depends=["base", "module_b"])
        mod_b = _make_module(tmp_path, "module_b", depends=["base", "module_c"])
        mod_c = _make_module(tmp_path, "module_c", depends=["base", "module_a"])

        analyzer = DependencyAnalyzer()
        result = analyzer.analyze_module(
            mod_a, project_modules={"module_a", "module_b", "module_c"}
        )

        circular = [i for i in result.issues if i["type"] == "circular_dependency"]
        assert len(circular) >= 1

    def test_no_circular_when_clean(self, tmp_path):
        mod_a = _make_module(tmp_path, "module_a", depends=["base", "module_b"])
        mod_b = _make_module(tmp_path, "module_b", depends=["base"])

        analyzer = DependencyAnalyzer()
        result = analyzer.analyze_module(
            mod_a, project_modules={"module_a", "module_b"}
        )

        circular = [i for i in result.issues if i["type"] == "circular_dependency"]
        assert len(circular) == 0


class TestAnalyzeProject:
    """Tests for project-wide dependency analysis."""

    def test_analyze_project_multiple_modules(self, tmp_path):
        _make_module(tmp_path, "module_a", depends=["base", "module_b"])
        _make_module(tmp_path, "module_b", depends=["base"])

        analyzer = DependencyAnalyzer()
        results = analyzer.analyze_project(tmp_path)

        assert len(results) == 2
        assert "module_a" in results
        assert "module_b" in results

    def test_analyze_project_no_modules(self, tmp_path):
        analyzer = DependencyAnalyzer()
        with pytest.raises(DependencyError, match="No Odoo modules found"):
            analyzer.analyze_project(tmp_path)

    def test_analyze_project_not_found(self, tmp_path):
        analyzer = DependencyAnalyzer()
        with pytest.raises(DependencyError, match="not found"):
            analyzer.analyze_project(tmp_path / "nonexistent")


class TestDiffDependencies:
    """Tests for dependency diffing between manifest versions."""

    def test_diff_added_dependency(self, tmp_path):
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        import json
        v1.write_text(json.dumps({"depends": ["base"]}))
        v2.write_text(json.dumps({"depends": ["base", "mail"]}))

        analyzer = DependencyAnalyzer()
        diff = analyzer.diff_dependencies(v1, v2)

        assert "mail" in diff["added"]
        assert diff["removed"] == []
        assert diff["total_changes"] == 1

    def test_diff_removed_dependency(self, tmp_path):
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        import json
        v1.write_text(json.dumps({"depends": ["base", "mail"]}))
        v2.write_text(json.dumps({"depends": ["base"]}))

        analyzer = DependencyAnalyzer()
        diff = analyzer.diff_dependencies(v1, v2)

        assert "mail" in diff["removed"]
        assert diff["added"] == []
        assert diff["total_changes"] == 1

    def test_diff_no_changes(self, tmp_path):
        v1 = tmp_path / "v1.json"
        v2 = tmp_path / "v2.json"
        import json
        v1.write_text(json.dumps({"depends": ["base", "mail"]}))
        v2.write_text(json.dumps({"depends": ["mail", "base"]}))

        analyzer = DependencyAnalyzer()
        diff = analyzer.diff_dependencies(v1, v2)

        assert diff["added"] == []
        assert diff["removed"] == []
        assert diff["total_changes"] == 0


class TestDependencyResult:
    """Tests for DependencyResult class."""

    def test_result_clean(self):
        result = DependencyResult(
            summary={"module": "test", "total_issues": 0, "declared_deps": [], "actual_usage": [], "unused_count": 0, "missing_count": 0, "circular_count": 0},
            issues=[],
            manifest_deps=set(),
            code_usage=set(),
        )
        assert result.is_clean
        assert not result.has_issues

    def test_result_with_issues(self):
        result = DependencyResult(
            summary={"module": "test", "total_issues": 2, "declared_deps": [], "actual_usage": [], "unused_count": 2, "missing_count": 0, "circular_count": 0},
            issues=[{"type": "unused_dependency", "module": "x", "message": "test"}],
            manifest_deps=set(),
            code_usage=set(),
        )
        assert not result.is_clean
        assert result.has_issues


class TestDependencyCli:
    """Tests for the fba deps check CLI command."""

    def test_deps_check_clean(self, tmp_path):
        from click.testing import CliRunner
        from fba.cli import main

        factory = tmp_path / ".factory"
        factory.mkdir()
        _make_module(tmp_path, "my_module", depends=["base"])

        runner = CliRunner()
        result = runner.invoke(main, ["deps", "check", "--project-dir", str(tmp_path)])

        assert result.exit_code == 0
        assert "clean" in result.output.lower() or "✅" in result.output

    def test_deps_check_with_issues(self, tmp_path):
        from click.testing import CliRunner
        from fba.cli import main

        factory = tmp_path / ".factory"
        factory.mkdir()
        _make_module(tmp_path, "my_module", depends=["base", "unused_xyz"])

        runner = CliRunner()
        result = runner.invoke(main, ["deps", "check", "--project-dir", str(tmp_path)])

        assert result.exit_code != 0
        assert "unused_xyz" in result.output

    def test_deps_check_no_modules(self, tmp_path):
        from click.testing import CliRunner
        from fba.cli import main

        factory = tmp_path / ".factory"
        factory.mkdir()

        runner = CliRunner()
        result = runner.invoke(main, ["deps", "check", "--project-dir", str(tmp_path)])

        assert result.exit_code != 0

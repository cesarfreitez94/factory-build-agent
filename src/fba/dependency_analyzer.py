"""Odoo dependency integrity analyzer.

Analyzes __manifest__.py dependency declarations against actual code usage.
Detects: unused dependencies, missing dependencies, and circular dependencies.
Uses the diff engine to compare dependency changes between versions.
"""

import json
import re
from pathlib import Path
from typing import Optional


class DependencyError(Exception):
    """Raised when dependency analysis fails."""


class DependencyAnalyzer:
    """Analyzes Odoo module dependencies for integrity issues.

    Checks:
    - Unused dependencies: modules in 'depends' not referenced in code
    - Missing dependencies: modules used in code but missing from 'depends'
    - Circular dependencies: cycles in the module dependency graph

    Usage:
        analyzer = DependencyAnalyzer()
        result = analyzer.analyze_module(Path("my_addon"))
        if result.has_issues:
            for issue in result.issues:
                print(issue)
    """

    ODOO_IMPORT_RE = re.compile(
        r"(?:from|import)\s+odoo\.addons\.(\w+)",
    )
    INHERIT_RE = re.compile(
        r"_inherit\s*=\s*\[?\s*['\"]([\w.]+)['\"]",
    )
    MANY2ONE_REF_RE = re.compile(
        r"(?:Many2one|One2many|Many2many)\s*\(\s*['\"]([\w.]+)['\"]",
    )
    DEPENDS_REF_RE = re.compile(
        r"['\"]([\w]+)['\"]",
    )

    CORE_ODOO_MODULES = {
        "base", "web", "mail", "stock", "sale", "purchase",
        "account", "crm", "hr", "product", "uom", "report",
    }

    def analyze_module(
        self,
        module_path: Path,
        project_modules: Optional[set] = None,
        deps_map: Optional[dict] = None,
    ):
        """Analyze a single Odoo module for dependency issues.

        Args:
            module_path: Path to the Odoo module directory.
            project_modules: Set of module names that are part of the
                same project (for circular dependency detection).
            deps_map: Optional dict mapping module_name -> set of
                declared dependencies (for accurate cycle detection).
        """
        if not module_path.exists():
            raise DependencyError(f"Module path not found: {module_path}")

        manifest = self._load_manifest(module_path)
        declared_deps = set(manifest.get("depends", []))
        actual_usage = self._scan_code_usage(module_path)

        issues = []

        unused = declared_deps - actual_usage - self.CORE_ODOO_MODULES
        for mod in sorted(unused):
            issues.append({
                "type": "unused_dependency",
                "module": mod,
                "message": f"Dependency '{mod}' is declared but not referenced in code",
            })

        missing = actual_usage - declared_deps
        for mod in sorted(missing):
            if not self._is_stdlib_module(mod):
                issues.append({
                    "type": "missing_dependency",
                    "module": mod,
                    "message": f"Module '{mod}' is used in code but not in 'depends'",
                })

        circular = []
        if project_modules:
            if deps_map is None:
                deps_map = self._build_deps_map_from_siblings(module_path, project_modules)
            circular = self._detect_circular_deps(
                module_path.name, declared_deps, project_modules,
                deps_map=deps_map,
            )
            for cycle in circular:
                issues.append({
                    "type": "circular_dependency",
                    "cycle": cycle,
                    "message": f"Circular dependency detected: {' → '.join(cycle)}",
                })

        summary = {
            "module": manifest.get("name", module_path.name),
            "declared_deps": sorted(declared_deps),
            "actual_usage": sorted(actual_usage),
            "unused_count": len(unused),
            "missing_count": len(missing),
            "circular_count": len(circular),
            "total_issues": len(issues),
        }

        return DependencyResult(
            summary=summary,
            issues=issues,
            manifest_deps=declared_deps,
            code_usage=actual_usage,
        )

    def analyze_project(self, project_path: Path):
        """Analyze all modules in a project for dependency issues.

        Args:
            project_path: Path to the project containing Odoo modules.

        Returns:
            Dict mapping module name to DependencyResult.
        """
        if not project_path.exists():
            raise DependencyError(f"Project path not found: {project_path}")

        module_dirs = self._find_odoo_modules(project_path)
        if not module_dirs:
            raise DependencyError(f"No Odoo modules found in {project_path}")

        all_module_names = {d.name for d in module_dirs}

        deps_map = {}
        for mod_dir in module_dirs:
            try:
                manifest = self._load_manifest(mod_dir)
                deps_map[mod_dir.name] = set(manifest.get("depends", []))
            except DependencyError:
                deps_map[mod_dir.name] = set()

        results = {}
        for mod_dir in sorted(module_dirs):
            result = self.analyze_module(
                mod_dir, project_modules=all_module_names, deps_map=deps_map
            )
            results[mod_dir.name] = result

        return results

    def diff_dependencies(
        self, old_manifest_path: Path, new_manifest_path: Path
    ) -> dict:
        """Compare dependency declarations between two manifest versions.

        Uses the diff engine from feat/12.1 to produce a structured
        changelog of dependency changes.
        """
        from fba.diff_engine import DiffEngine, DiffError

        try:
            old_data = json.loads(old_manifest_path.read_text()) if old_manifest_path.suffix == ".json" else {}
            new_data = json.loads(new_manifest_path.read_text()) if new_manifest_path.suffix == ".json" else {}
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise DependencyError(f"Cannot read manifest files: {e}")

        old_deps = set(old_data.get("depends", []))
        new_deps = set(new_data.get("depends", []))

        added = sorted(new_deps - old_deps)
        removed = sorted(old_deps - new_deps)
        unchanged = sorted(old_deps & new_deps)

        return {
            "added": added,
            "removed": removed,
            "unchanged": unchanged,
            "total_changes": len(added) + len(removed),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_manifest(self, module_path: Path) -> dict:
        """Load __manifest__.py from a module directory."""
        manifest_path = module_path / "__manifest__.py"
        if not manifest_path.exists():
            raise DependencyError(f"__manifest__.py not found in {module_path}")

        try:
            content = manifest_path.read_text()
            return self._parse_manifest(content)
        except Exception as e:
            raise DependencyError(f"Failed to parse {manifest_path}: {e}")

    def _parse_manifest(self, content: str) -> dict:
        """Parse __manifest__.py content into a dict.

        Handles the common Odoo manifest format: a dict literal.
        Uses regex to extract 'depends' list.
        """
        result = {"depends": []}

        depends_match = re.search(
            r"['\"]depends['\"]\s*:\s*\[(.*?)\]",
            content, re.DOTALL,
        )
        if depends_match:
            deps_str = depends_match.group(1)
            result["depends"] = re.findall(r"['\"]([\w]+)['\"]", deps_str)

        name_match = re.search(
            r"['\"]name['\"]\s*:\s*['\"]([\w.]+)['\"]",
            content,
        )
        if name_match:
            result["name"] = name_match.group(1)

        return result

    def _scan_code_usage(self, module_path: Path) -> set:
        """Scan all Python files in a module for external module references."""
        usage = set()

        for py_file in module_path.rglob("*.py"):
            if py_file.name == "__manifest__.py":
                continue

            try:
                content = py_file.read_text()
            except Exception:
                continue

            for match in self.ODOO_IMPORT_RE.finditer(content):
                usage.add(match.group(1))

            for match in self.INHERIT_RE.finditer(content):
                module_name = match.group(1).split(".")[0]
                usage.add(module_name)

            for match in self.MANY2ONE_REF_RE.finditer(content):
                module_name = match.group(1).split(".")[0]
                usage.add(module_name)

        return usage

    def _detect_circular_deps(
        self,
        current_module: str,
        declared_deps: set,
        all_modules: set,
        visited: Optional[set] = None,
        path: Optional[list] = None,
        deps_map: Optional[dict] = None,
    ) -> list[list[str]]:
        """Detect circular dependencies in the module graph.

        Uses DFS to find cycles. Returns list of cycles found.
        deps_map is a dict mapping module_name -> set of its declared deps.
        """
        if visited is None:
            visited = set()
        if path is None:
            path = []

        cycles = []

        if current_module in path:
            cycle_start = path.index(current_module)
            cycles.append(path[cycle_start:] + [current_module])
            return cycles

        if current_module in visited:
            return cycles

        visited.add(current_module)
        path.append(current_module)

        deps_to_check = declared_deps
        if deps_map and current_module in deps_map:
            deps_to_check = deps_map[current_module]

        for dep in deps_to_check:
            if dep in all_modules:
                sub_cycles = self._detect_circular_deps(
                    dep, set(), all_modules, visited, list(path), deps_map
                )
                cycles.extend(sub_cycles)

        return cycles

    def _build_deps_map_from_siblings(
        self, module_path: Path, project_modules: set
    ) -> dict:
        """Build a deps_map from sibling module directories."""
        deps_map = {}
        parent = module_path.parent
        for mod_name in project_modules:
            mod_dir = parent / mod_name
            if mod_dir.exists():
                try:
                    manifest = self._load_manifest(mod_dir)
                    deps_map[mod_name] = set(manifest.get("depends", []))
                except DependencyError:
                    deps_map[mod_name] = set()
            else:
                deps_map[mod_name] = set()
        return deps_map

    @staticmethod
    def _is_stdlib_module(name: str) -> bool:
        """Check if a module name is a Python stdlib module."""
        stdlib_modules = {
            "os", "sys", "re", "json", "datetime", "logging",
            "pathlib", "collections", "itertools", "functools",
            "typing", "io", "csv", "xml", "hashlib", "base64",
            "copy", "math", "random", "string", "time", "uuid",
            "enum", "textwrap", "argparse", "configparser",
        }
        return name in stdlib_modules

    @staticmethod
    def _find_odoo_modules(project_path: Path) -> list[Path]:
        """Find Odoo module directories in a project path."""
        modules = []
        for child in sorted(project_path.iterdir()):
            if child.is_dir() and (child / "__manifest__.py").exists():
                modules.append(child)
        return modules


class DependencyResult:
    """Result of a dependency analysis."""

    def __init__(
        self,
        summary: dict,
        issues: list[dict],
        manifest_deps: set,
        code_usage: set,
    ):
        self.summary = summary
        self.issues = issues
        self.manifest_deps = manifest_deps
        self.code_usage = code_usage

    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0

    @property
    def is_clean(self) -> bool:
        return len(self.issues) == 0

    def __repr__(self):
        return (
            f"DependencyResult(module={self.summary['module']}, "
            f"issues={self.summary['total_issues']})"
        )

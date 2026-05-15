import ast
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast
from xml.etree import ElementTree

from fba.state import _atomic_write

REGISTRY_VERSION = "1.0"


class RegistryIndexError(Exception):
    """Raised when an Odoo addon cannot be indexed."""


@dataclass
class RegistryIndexResult:
    odoo_version: str
    module_names: list[str]
    registry_path: Path
    index_path: Path
    registry_changed: bool
    index_changed: bool


class RegistryIndexer:
    """Indexes existing Odoo addons into FBA registry artifacts."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.factory_dir = self.project_dir / ".factory"
        self.registry_path = self.factory_dir / "module_registry.json"
        self.index_path = self.factory_dir / "registry_index.json"

    def index(self, addon_path: Path, odoo_version: str = "18.0") -> RegistryIndexResult:
        version = normalize_odoo_version(odoo_version)
        source_path = self._resolve_addon_path(addon_path)
        addon_dirs = self._discover_addons(source_path)
        if not addon_dirs:
            raise RegistryIndexError(
                f"No Odoo addons found at {source_path}. Expected __manifest__.py."
            )

        modules = {
            addon_dir.name: self._index_addon(addon_dir, version)
            for addon_dir in addon_dirs
        }

        timestamp = datetime.now(timezone.utc).isoformat()
        registry_changed = self._merge_module_registry(modules, version, timestamp)
        index_changed = self._merge_registry_index(modules, version, source_path, timestamp)

        return RegistryIndexResult(
            odoo_version=version,
            module_names=sorted(modules),
            registry_path=self.registry_path,
            index_path=self.index_path,
            registry_changed=registry_changed,
            index_changed=index_changed,
        )

    def _resolve_addon_path(self, addon_path: Path) -> Path:
        candidate = Path(addon_path)
        if not candidate.is_absolute() and not candidate.exists():
            candidate = self.project_dir / candidate
        candidate = candidate.resolve()
        if not candidate.exists():
            raise RegistryIndexError(f"Addon path not found: {candidate}")
        if not candidate.is_dir():
            raise RegistryIndexError(f"Addon path must be a directory: {candidate}")
        return candidate

    def _discover_addons(self, source_path: Path) -> list[Path]:
        if (source_path / "__manifest__.py").exists():
            return [source_path]

        addon_dirs = []
        for manifest_path in sorted(source_path.rglob("__manifest__.py")):
            if any(part.startswith(".") for part in manifest_path.relative_to(source_path).parts):
                continue
            addon_dirs.append(manifest_path.parent)
        return addon_dirs

    def _index_addon(self, addon_dir: Path, odoo_version: str) -> dict[str, Any]:
        manifest = self._load_manifest(addon_dir)
        python_scan = self._scan_python(addon_dir)
        xml_scan = self._scan_xml(addon_dir)
        security = self._scan_security(addon_dir, xml_scan)
        owl_components = self._scan_owl(addon_dir)

        data_files = _string_list(manifest.get("data", []))
        demo_files = _string_list(manifest.get("demo", []))
        security_files = sorted({
            rel
            for rel in data_files + demo_files + [p.as_posix() for p in security["csv_files"]]
            if rel.startswith("security/")
        })

        models = python_scan["models"]
        artifact_counts = {
            "models": len(models),
            "fields": sum(len(m.get("fields", [])) for m in models),
            "views": len(xml_scan["views"]),
            "controllers": len(python_scan["controllers"]),
            "routes": sum(len(c.get("routes", [])) for c in python_scan["controllers"]),
            "reports": len(xml_scan["reports"]),
            "security": (
                len(security["access_rights"])
                + len(security["groups"])
                + len(security["record_rules"])
            ),
            "data_files": len(data_files),
            "demo_files": len(demo_files),
            "crons": len(xml_scan["crons"]),
            "wizards": len([m for m in models if m.get("model_type") == "models.TransientModel"]),
            "owl_components": len(owl_components),
        }

        return {
            "technical_name": addon_dir.name,
            "display_name": str(manifest.get("name", addon_dir.name)),
            "odoo_version": odoo_version,
            "manifest": _json_safe(manifest),
            "depends": _string_list(manifest.get("depends", [])),
            "models": models,
            "views": xml_scan["views"],
            "controllers": python_scan["controllers"],
            "reports": xml_scan["reports"],
            "security": {
                "access_rights": security["access_rights"],
                "groups": security["groups"],
                "record_rules": security["record_rules"],
                "files": security_files,
            },
            "data_files": data_files,
            "demo_files": demo_files,
            "crons": xml_scan["crons"],
            "wizards": [m for m in models if m.get("model_type") == "models.TransientModel"],
            "owl_components": owl_components,
            "artifact_counts": artifact_counts,
        }

    def _load_manifest(self, addon_dir: Path) -> dict[str, Any]:
        manifest_path = addon_dir / "__manifest__.py"
        try:
            tree = ast.parse(manifest_path.read_text())
        except SyntaxError as e:
            raise RegistryIndexError(f"Invalid manifest Python syntax in {manifest_path}: {e}") from e

        for node in tree.body:
            value_node: ast.AST | None = None
            if isinstance(node, ast.Expr):
                value_node = node.value
            elif isinstance(node, ast.Assign):
                value_node = node.value

            if value_node is None:
                continue
            try:
                value = ast.literal_eval(value_node)
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict):
                return cast(dict[str, Any], value)

        raise RegistryIndexError(f"Could not read manifest dictionary from {manifest_path}")

    def _scan_python(self, addon_dir: Path) -> dict[str, Any]:
        models = []
        controllers = []

        for py_path in sorted(addon_dir.rglob("*.py")):
            if py_path.name in {"__init__.py", "__manifest__.py"}:
                continue
            try:
                tree = ast.parse(py_path.read_text())
            except SyntaxError:
                continue

            rel_path = py_path.relative_to(addon_dir).as_posix()
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue

                base_names = [_node_name(base) for base in node.bases]
                model_info = self._parse_model_class(node, base_names, rel_path)
                if model_info is not None:
                    models.append(model_info)

                controller_info = self._parse_controller_class(node, base_names, rel_path)
                if controller_info is not None:
                    controllers.append(controller_info)

        models.sort(key=lambda m: (m.get("name", ""), m.get("class_name", "")))
        controllers.sort(key=lambda c: (c.get("class_name", ""), c.get("file", "")))
        return {"models": models, "controllers": controllers}

    def _parse_model_class(
        self, node: ast.ClassDef, base_names: list[str], rel_path: str
    ) -> dict[str, Any] | None:
        model_type = next(
            (
                base
                for base in base_names
                if base in {"models.Model", "models.TransientModel", "models.AbstractModel"}
            ),
            "",
        )
        attrs = self._class_attrs(node)
        model_name = _first_string(attrs.get("_name"))
        inherits = _string_list(attrs.get("_inherit"))
        fields = self._parse_fields(node)

        if not model_type and not model_name and not inherits:
            return None

        effective_name = model_name or (inherits[0] if inherits else "")
        mode = "defined" if model_name else "extension"
        return {
            "name": effective_name,
            "class_name": node.name,
            "file": rel_path,
            "model_type": model_type or "unknown",
            "mode": mode,
            "inherits": inherits,
            "description": _first_string(attrs.get("_description")),
            "fields": fields,
        }

    def _parse_controller_class(
        self, node: ast.ClassDef, base_names: list[str], rel_path: str
    ) -> dict[str, Any] | None:
        routes = []
        is_controller = any(base.endswith("Controller") for base in base_names)

        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in item.decorator_list:
                route = self._parse_route_decorator(decorator, item.name)
                if route:
                    routes.append(route)

        if not is_controller and not routes:
            return None
        return {
            "class_name": node.name,
            "file": rel_path,
            "routes": routes,
        }

    def _class_attrs(self, node: ast.ClassDef) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        for item in node.body:
            if not isinstance(item, ast.Assign):
                continue
            value = _literal(item.value)
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id.startswith("_"):
                    attrs[target.id] = value
        return attrs

    def _parse_fields(self, node: ast.ClassDef) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = []
        for item in node.body:
            assignments: list[tuple[str, ast.AST]] = []
            if isinstance(item, ast.Assign):
                assignments.extend(
                    (target.id, item.value)
                    for target in item.targets
                    if isinstance(target, ast.Name)
                )
            elif (
                isinstance(item, ast.AnnAssign)
                and isinstance(item.target, ast.Name)
                and item.value is not None
            ):
                assignments.append((item.target.id, item.value))

            for field_name, value in assignments:
                if value is None or not isinstance(value, ast.Call):
                    continue
                call_name = _node_name(value.func)
                if not call_name.startswith("fields."):
                    continue

                field_type = call_name.split(".")[-1]
                field: dict[str, Any] = {
                    "name": field_name,
                    "type": field_type,
                }
                if value.args:
                    relation = _literal(value.args[0])
                    if isinstance(relation, str):
                        field["relation"] = relation

                for keyword in value.keywords:
                    if keyword.arg is None:
                        continue
                    literal = _literal(keyword.value)
                    if literal is not None:
                        field[keyword.arg] = _json_safe(literal)

                fields.append(field)

        fields.sort(key=lambda f: f["name"])
        return fields

    def _parse_route_decorator(
        self, decorator: ast.AST, method_name: str
    ) -> dict[str, Any] | None:
        if not isinstance(decorator, ast.Call):
            return None
        call_name = _node_name(decorator.func)
        if call_name not in {"http.route", "route"} and not call_name.endswith(".route"):
            return None

        route_value: Any = None
        if decorator.args:
            route_value = _literal(decorator.args[0])
        routes = _string_list(route_value)
        if isinstance(route_value, str):
            routes = [route_value]

        route_info: dict[str, Any] = {
            "method": method_name,
            "routes": routes,
        }
        for keyword in decorator.keywords:
            if keyword.arg is None:
                continue
            literal = _literal(keyword.value)
            if literal is not None:
                route_info[keyword.arg] = _json_safe(literal)
        return route_info

    def _scan_xml(self, addon_dir: Path) -> dict[str, Any]:
        views = []
        reports = []
        crons = []
        groups = []
        record_rules = []

        for xml_path in sorted(addon_dir.rglob("*.xml")):
            try:
                root = ElementTree.parse(xml_path).getroot()
            except ElementTree.ParseError:
                continue
            rel_path = xml_path.relative_to(addon_dir).as_posix()

            for record in root.iter():
                if _local_name(record.tag) != "record":
                    continue
                model = record.attrib.get("model", "")
                record_id = record.attrib.get("id", "")
                fields = _xml_record_fields(record)

                if model == "ir.ui.view":
                    views.append({
                        "id": record_id,
                        "name": _xml_value(fields, "name"),
                        "model": _xml_value(fields, "model"),
                        "type": _normalize_view_type(
                            _xml_value(fields, "type") or _arch_view_type(fields.get("arch"))
                        ),
                        "file": rel_path,
                    })
                elif model == "ir.actions.report":
                    reports.append({
                        "id": record_id,
                        "name": _xml_value(fields, "name"),
                        "model": _xml_value(fields, "model"),
                        "report_name": _xml_value(fields, "report_name"),
                        "file": rel_path,
                    })
                elif model == "ir.cron":
                    crons.append({
                        "id": record_id,
                        "name": _xml_value(fields, "name"),
                        "model": _xml_value(fields, "model_id"),
                        "file": rel_path,
                    })
                elif model == "res.groups":
                    groups.append({
                        "id": record_id,
                        "name": _xml_value(fields, "name"),
                        "file": rel_path,
                    })
                elif model == "ir.rule":
                    record_rules.append({
                        "id": record_id,
                        "name": _xml_value(fields, "name"),
                        "model": _xml_value(fields, "model_id"),
                        "file": rel_path,
                    })

            for template in root.iter():
                if _local_name(template.tag) == "template" and template.attrib.get("id"):
                    reports.append({
                        "id": template.attrib["id"],
                        "name": template.attrib.get("name", template.attrib["id"]),
                        "model": "",
                        "report_name": template.attrib["id"],
                        "file": rel_path,
                    })

        return {
            "views": sorted(views, key=lambda v: (v.get("model", ""), v.get("id", ""))),
            "reports": sorted(reports, key=lambda r: (r.get("id", ""), r.get("file", ""))),
            "crons": sorted(crons, key=lambda c: (c.get("id", ""), c.get("file", ""))),
            "groups": sorted(groups, key=lambda g: (g.get("id", ""), g.get("file", ""))),
            "record_rules": sorted(record_rules, key=lambda r: (r.get("id", ""), r.get("file", ""))),
        }

    def _scan_security(self, addon_dir: Path, xml_scan: dict[str, Any]) -> dict[str, Any]:
        access_rights = []
        csv_files = []

        for csv_path in sorted((addon_dir / "security").glob("*.csv")):
            rel_path = csv_path.relative_to(addon_dir)
            csv_files.append(rel_path)
            try:
                with csv_path.open(newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        item = {k: v for k, v in row.items() if k is not None and v != ""}
                        item["file"] = rel_path.as_posix()
                        access_rights.append(item)
            except OSError:
                continue

        return {
            "access_rights": access_rights,
            "groups": xml_scan["groups"],
            "record_rules": xml_scan["record_rules"],
            "csv_files": csv_files,
        }

    def _scan_owl(self, addon_dir: Path) -> list[dict[str, Any]]:
        components: list[dict[str, Any]] = []
        static_dir = addon_dir / "static" / "src"
        if not static_dir.exists():
            return components

        for js_path in sorted(static_dir.rglob("*.js")):
            content = js_path.read_text(errors="ignore")
            if "Component" not in content and "registry.category" not in content:
                continue
            components.append({
                "name": js_path.stem,
                "type": "javascript",
                "file": js_path.relative_to(addon_dir).as_posix(),
            })

        for xml_path in sorted(static_dir.rglob("*.xml")):
            try:
                root = ElementTree.parse(xml_path).getroot()
            except ElementTree.ParseError:
                continue
            for node in root.iter():
                template_name = node.attrib.get("t-name")
                if template_name:
                    components.append({
                        "name": template_name,
                        "type": "template",
                        "file": xml_path.relative_to(addon_dir).as_posix(),
                    })

        return sorted(components, key=lambda c: (c["type"], c["name"], c["file"]))

    def _merge_module_registry(
        self, modules: dict[str, dict[str, Any]], odoo_version: str, timestamp: str
    ) -> bool:
        registry = self._load_json(self.registry_path)
        registry.setdefault(
            "$schema",
            "https://opencode.ai/fba/schemas/module_registry.schema.json",
        )
        registry.setdefault(
            "description",
            "Registry of Odoo modules and their canonical models.",
        )
        registry["registry_version"] = REGISTRY_VERSION
        registry["odoo_version"] = odoo_version
        registry_modules = registry.setdefault("modules", {})
        if not isinstance(registry_modules, dict):
            registry_modules = {}
            registry["modules"] = registry_modules

        changed = False
        for module_name, module in modules.items():
            next_entry = self._module_registry_entry(module)
            if registry_modules.get(module_name) != next_entry:
                registry_modules[module_name] = next_entry
                changed = True

        if changed or "indexed_at" not in registry:
            registry["indexed_at"] = timestamp

        return self._write_json_if_changed(self.registry_path, registry)

    def _merge_registry_index(
        self,
        modules: dict[str, dict[str, Any]],
        odoo_version: str,
        source_path: Path,
        timestamp: str,
    ) -> bool:
        index = self._load_json(self.index_path)
        index["registry_version"] = REGISTRY_VERSION
        index["odoo_version"] = odoo_version
        index["source_path"] = source_path.as_posix()
        indexed_modules = index.setdefault("modules", {})
        if not isinstance(indexed_modules, dict):
            indexed_modules = {}
            index["modules"] = indexed_modules

        changed = False
        for module_name, module in modules.items():
            if indexed_modules.get(module_name) != module:
                indexed_modules[module_name] = module
                changed = True

        if changed or "indexed_at" not in index:
            index["indexed_at"] = timestamp

        return self._write_json_if_changed(self.index_path, index)

    def _module_registry_entry(self, module: dict[str, Any]) -> dict[str, Any]:
        model_names = sorted({
            str(model.get("name"))
            for model in module.get("models", [])
            if model.get("name")
        })
        manifest = module.get("manifest", {})
        description = (
            manifest.get("summary")
            or manifest.get("description")
            or module.get("display_name")
            or module.get("technical_name")
            or ""
        )
        return {
            "description": str(description),
            "models": model_names,
            "depends": module.get("depends", []),
            "artifact_counts": module.get("artifact_counts", {}),
            "registry_index": "registry_index.json",
        }

    def _load_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            return {}
        if isinstance(data, dict):
            return cast(dict[str, Any], data)
        return {}

    def _write_json_if_changed(self, path: Path, data: dict[str, Any]) -> bool:
        content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        if path.exists() and path.read_text() == content:
            return False
        _atomic_write(path, content)
        return True


def normalize_odoo_version(value: str) -> str:
    raw = value.strip().lower()
    if raw.startswith("odoo"):
        raw = raw.removeprefix("odoo").strip("-_ ")
    if raw.startswith("v"):
        raw = raw[1:]
    parts = [p for p in raw.split(".") if p]
    if not parts:
        return "18.0"
    if len(parts) == 1:
        return f"{parts[0]}.0"
    return f"{parts[0]}.{parts[1]}"


def _node_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _node_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _literal(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return None


def _first_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                return item
    return ""


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if isinstance(item, str)]
    return []


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _xml_record_fields(record: ElementTree.Element) -> dict[str, ElementTree.Element]:
    fields = {}
    for child in record:
        if _local_name(child.tag) == "field" and child.attrib.get("name"):
            fields[child.attrib["name"]] = child
    return fields


def _xml_value(fields: dict[str, ElementTree.Element], name: str) -> str:
    field = fields.get(name)
    if field is None:
        return ""
    if field.attrib.get("ref"):
        return field.attrib["ref"]
    if field.attrib.get("eval"):
        return field.attrib["eval"]
    return (field.text or "").strip()


def _arch_view_type(field: ElementTree.Element | None) -> str:
    if field is None:
        return ""
    for child in field:
        tag = _local_name(child.tag)
        if tag:
            return tag
    return ""


def _normalize_view_type(view_type: str) -> str:
    if view_type == "tree":
        return "list"
    return view_type

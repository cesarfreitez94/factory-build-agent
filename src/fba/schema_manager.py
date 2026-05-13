import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from fba.module_registry import ModuleRegistry
from fba.state import _atomic_write


@dataclass
class AssemblyWarning:
    level: str
    message: str
    detail: str = ""


@dataclass
class AssemblyResult:
    schema: dict[str, Any]
    warnings: list[AssemblyWarning] = field(default_factory=list)
    errors: list[AssemblyWarning] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def warning_messages(self) -> list[str]:
        return [w.message for w in self.warnings]

    @property
    def error_messages(self) -> list[str]:
        return [e.message for e in self.errors]


class SchemaManager:
    """Deterministic assembly of schema.json (SSOT) from task files, SDD, and module registry.

    The Schema Manager is the single source of truth assembly layer. It produces
    ``schema.json`` — a normalized, validated structure that all downstream
    code rendering consumes with zero interpretation.
    """

    IMPLEMENTED_TYPES = frozenset({
        "model", "view", "security_group", "access_right", "record_rule", "data",
    })

    RELATIONAL_TYPES = {"Many2one", "One2many", "Many2many"}

    NAMING_RULES = {
        "Many2one": "_id",
        "One2many": "_ids",
        "Many2many": "_ids",
    }

    SUFFIX_REQUIRED = {
        "Many2one": "_id",
        "One2many": "_ids",
        "Many2many": "_ids",
    }

    TYPE_NORMALIZATION = {
        "boolean": "Boolean",
        "integer": "Integer",
        "float": "Float",
        "monetary": "Monetary",
        "char": "Char",
        "text": "Text",
        "html": "Html",
        "date": "Date",
        "datetime": "Datetime",
        "binary": "Binary",
        "selection": "Selection",
        "many2one": "Many2one",
        "one2many": "One2many",
        "many2many": "Many2many",
    }

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.factory_dir = self.project_dir / ".factory"
        self.tasks_dir = self.factory_dir / "tasks"
        self.registry = ModuleRegistry(project_dir)
        self._warnings: list[AssemblyWarning] = []
        self._errors: list[AssemblyWarning] = []
        self._emitted_warnings: set[str] = set()

    def assemble(self, output_path: Path | None = None) -> AssemblyResult:
        """Execute the full assembly pipeline and write schema.json.

        Returns an AssemblyResult with the schema dict, warnings, and errors.
        """
        self._warnings = []
        self._errors = []

        task_index = self._load_task_index()
        if task_index is None:
            return AssemblyResult({}, warnings=self._warnings, errors=self._errors)

        tasks_data = self._load_all_tasks(task_index)
        sdd_data = self._load_sdd()

        self._detect_unknown_types(tasks_data)

        models = self._assemble_models(tasks_data)
        views = self._assemble_views(tasks_data)
        security = self._assemble_security(tasks_data)
        data_entries = self._assemble_data(tasks_data)
        manifest = self._assemble_manifest(sdd_data, task_index)

        self._validate_relations(models)

        schema = {
            "manifest": manifest,
            "models": models,
            "views": views,
            "security": security,
            "data": data_entries,
        }

        if output_path:
            output_path = Path(output_path)
            _atomic_write(output_path, json.dumps(schema, indent=2, ensure_ascii=False))

        return AssemblyResult(schema, warnings=self._warnings, errors=self._errors)

    def _load_task_index(self) -> dict[str, Any] | None:
        index_path = self.tasks_dir / "index.json"
        if not index_path.exists():
            self._errors.append(AssemblyWarning(
                "error", "Task index not found",
                f"Expected at: {index_path}",
            ))
            return None
        try:
            return cast(dict[str, Any], json.loads(index_path.read_text()))
        except json.JSONDecodeError as e:
            self._errors.append(AssemblyWarning(
                "error", "Task index is invalid JSON",
                f"{index_path}: {e}",
            ))
            return None

    def _load_all_tasks(self, task_index: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Load all individual task files keyed by task ID."""
        tasks: dict[str, dict[str, Any]] = {}
        for entry in task_index.get("tasks", []):
            task_id = entry.get("id", "")
            file_name = entry.get("file", "")
            task_path = self.tasks_dir / file_name
            if not task_path.exists():
                self._warnings.append(AssemblyWarning(
                    "warning", "Task file not found",
                    f"{file_name} (task {task_id})",
                ))
                continue
            try:
                tasks[task_id] = cast(dict[str, Any], json.loads(task_path.read_text()))
            except json.JSONDecodeError as e:
                self._warnings.append(AssemblyWarning(
                    "warning", "Task file is invalid JSON",
                    f"{file_name}: {e}",
                ))
        return tasks

    def _load_sdd(self) -> dict[str, Any]:
        sdd_path = self.factory_dir / "sdd.json"
        if not sdd_path.exists():
            self._warnings.append(AssemblyWarning(
                "warning", "SDD not found",
                f"Expected at: {sdd_path}",
            ))
            return {}
        try:
            return cast(dict[str, Any], json.loads(sdd_path.read_text()))
        except json.JSONDecodeError:
            self._warnings.append(AssemblyWarning(
                "warning", "SDD is invalid JSON",
                f"Path: {sdd_path}",
            ))
            return {}

    def _detect_unknown_types(self, tasks_data: dict[str, dict[str, Any]]) -> None:
        """Warn about component types that are in the schema enum but not yet implemented."""
        for task_id, task in tasks_data.items():
            for component in task.get("components", []):
                ctype = component.get("type", "")
                if ctype and ctype not in self.IMPLEMENTED_TYPES:
                    self._warnings.append(AssemblyWarning(
                        "warning",
                        f"component type '{ctype}' is declared in schema "
                        f"but not yet implemented by SchemaManager",
                        f"Task: {task_id}, component: {component.get('name', 'unnamed')}",
                    ))

    def _assemble_manifest(self, sdd_data: dict[str, Any], task_index: dict[str, Any]) -> dict[str, Any]:
        module_name = sdd_data.get("module_name", "") or task_index.get("module_name", "unknown")
        manifest = {
            "name": module_name,
            "version": sdd_data.get("version", "18.0.1.0.0"),
            "summary": sdd_data.get("summary", f"{module_name} Odoo module"),
            "depends": sdd_data.get("dependencies", {}).get("required", ["base"]),
            "license": "LGPL-3",
            "installable": True,
            "auto_install": False,
        }
        if sdd_data.get("module_display_name"):
            manifest["description"] = sdd_data.get("summary", "")
        return manifest

    def _assemble_models(self, tasks_data: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract model components from all tasks, merge, normalize, and set mode."""
        models_raw: dict[str, dict[str, Any]] = {}

        for task_id, task in tasks_data.items():
            for component in task.get("components", []):
                if component.get("type") != "model":
                    continue
                model_name = component.get("name", "")
                if not model_name:
                    self._warnings.append(AssemblyWarning(
                        "warning", f"Component with empty name in task {task_id}",
                    ))
                    continue

                fields = self._normalize_fields(
                    component.get("fields", []), model_name, task_id
                )

                if model_name in models_raw:
                    existing = models_raw[model_name]
                    existing["fields"] = self._merge_fields(
                        existing["fields"], fields,
                        model_name, task_id,
                    )
                    existing_sdd = existing.get("sdd_reference", "")
                    new_sdd = component.get("sdd_reference", "")
                    if new_sdd and new_sdd not in existing_sdd:
                        models_raw[model_name]["sdd_reference"] = (
                            f"{existing_sdd},{new_sdd}" if existing_sdd else new_sdd
                        )
                else:
                    models_raw[model_name] = {
                        "name": model_name,
                        "description": component.get("description", ""),
                        "inherit": None,
                        "mode": "new",
                        "fields": fields,
                        "sdd_reference": component.get("sdd_reference", ""),
                    }

        models = []
        for model_name, model_data in models_raw.items():
            lookup = self.registry.lookup(model_name)
            model_data["mode"] = self._determine_mode(model_name, lookup)
            models.append(model_data)

        models.sort(key=lambda m: m["name"])
        if not models:
            self._errors.append(AssemblyWarning(
                "error", "No models found in task components",
                "At least one model component is required",
            ))

        return models

    def _normalize_fields(
        self, fields: list[dict[str, Any]], model_name: str, task_id: str
    ) -> list[dict[str, Any]]:
        """Normalize field names following Odoo conventions."""
        normalized = []
        for f in fields:
            field = dict(f)
            ftype = field.get("type", "")
            fname = field.get("name", "")

            if not fname:
                self._warnings.append(AssemblyWarning(
                    "warning", f"Field with empty name in model {model_name}",
                    f"Task: {task_id}",
                ))
                continue

            lower_type = ftype.lower()
            if lower_type in self.TYPE_NORMALIZATION and ftype != self.TYPE_NORMALIZATION[lower_type]:
                field["type"] = self.TYPE_NORMALIZATION[lower_type]

            if field["type"] in self.SUFFIX_REQUIRED:
                required_suffix = self.SUFFIX_REQUIRED[field["type"]]
                if not fname.endswith(required_suffix):
                    old_name = fname
                    new_name = fname + required_suffix
                    self._warnings.append(AssemblyWarning(
                        "warning",
                        f"Field '{old_name}' ({ftype}) in model {model_name} "
                        f"renamed to '{new_name}' per Odoo conventions",
                        f"Task: {task_id}",
                    ))
                    field["name"] = new_name

            if ftype in self.RELATIONAL_TYPES and "relation" not in field:
                existing_relation = field.get("relation", "")
                if not existing_relation:
                    self._warnings.append(AssemblyWarning(
                        "warning",
                        f"Field '{fname}' ({ftype}) in model {model_name} "
                        f"has no 'relation' specified",
                        f"Task: {task_id}",
                    ))

            normalized.append(field)

        return normalized

    def _merge_fields(
        self, existing: list[dict[str, Any]], incoming: list[dict[str, Any]],
        model_name: str, task_id: str,
    ) -> list[dict[str, Any]]:
        """Merge incoming fields into existing, deduplicating by name."""
        merged = {f["name"]: dict(f) for f in existing}

        for f in incoming:
            fname = f["name"]
            if fname in merged:
                if merged[fname].get("type") != f.get("type"):
                    self._warnings.append(AssemblyWarning(
                        "warning",
                        f"Field '{fname}' in model {model_name} has type mismatch "
                        f"({merged[fname].get('type')} vs {f.get('type')}). "
                        f"Keeping first definition.",
                        f"From task: {task_id}",
                    ))
                    continue
                for key, value in f.items():
                    if key not in merged[fname] or merged[fname][key] is None:
                        merged[fname][key] = value
            else:
                merged[fname] = dict(f)

        return list(merged.values())

    def _determine_mode(self, model_name: str, lookup: dict[str, Any] | None) -> str:
        """Determine if a model is new or extends a core Odoo model."""
        if self.registry.is_core(model_name):
            if lookup is not None:
                self._warnings.append(AssemblyWarning(
                    "warning",
                    f"Model '{model_name}' extends core model from module "
                    f"'{lookup['module']}' — mode set to 'extend'",
                ))
            return "extend"
        if not self.registry.modules and "registry_empty" not in self._emitted_warnings:
            self._emitted_warnings.add("registry_empty")
            self._warnings.append(AssemblyWarning(
                "warning",
                "ModuleRegistry is empty. All models classified as 'new'.",
                "No core modules found in registry.",
            ))
        return "new"

    def _validate_relations(self, models: list[dict[str, Any]]) -> None:
        """Validate that all relational fields reference existing models."""
        all_models = {m["name"] for m in models}

        for model in models:
            model_name = model["name"]
            for _field in model.get("fields", []):
                ftype = _field.get("type", "")
                if ftype not in self.RELATIONAL_TYPES:
                    continue

                relation = _field.get("relation", "")
                if not relation:
                    continue

                if relation in all_models:
                    continue

                if self.registry.is_core(relation):
                    continue

                self._warnings.append(AssemblyWarning(
                    "warning",
                    f"Field '{field.get('name')}' ({ftype}) in model "
                    f"'{model_name}' references '{relation}' which is not "
                    f"found in schema models or module registry",
                ))

    def _assemble_views(self, tasks_data: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract view components from all tasks."""
        views = []
        seen = set()

        for task_id, task in tasks_data.items():
            for component in task.get("components", []):
                if component.get("type") != "view":
                    continue

                view_name = component.get("name", "")
                view_type = component.get("view_type", "form")
                model = component.get("model", "")
                view_fields = component.get("view_fields", [])

                key = (view_name, view_type, model)
                if key in seen:
                    continue
                seen.add(key)

                views.append({
                    "name": view_name or f"{model}.{view_type}",
                    "type": view_type,
                    "model": model,
                    "fields": view_fields,
                    "sdd_reference": component.get("sdd_reference", ""),
                })

        if not views:
            self._warnings.append(AssemblyWarning(
                "warning", "No view components found in tasks",
                "At least one view component is recommended",
            ))

        return views

    def _assemble_security(self, tasks_data: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Extract security components from all tasks."""
        groups = []
        access_rights = []
        record_rules = []

        for task_id, task in tasks_data.items():
            for component in task.get("components", []):
                ctype = component.get("type", "")

                if ctype == "security_group":
                    groups.append({
                        "id": component.get("name", ""),
                        "name": component.get("display_name", component.get("name", "")),
                        "description": component.get("description", ""),
                        "category": component.get("category", component.get("name", "")),
                        "sdd_reference": component.get("sdd_reference", ""),
                    })

                elif ctype == "access_right":
                    perms = component.get("permissions", {})
                    access_rights.append({
                        "model": component.get("model", ""),
                        "group": component.get("name", ""),
                        "perm_read": perms.get("read", True),
                        "perm_write": perms.get("write", True),
                        "perm_create": perms.get("create", True),
                        "perm_unlink": perms.get("unlink", True),
                        "sdd_reference": component.get("sdd_reference", ""),
                    })

                elif ctype == "record_rule":
                    record_rules.append({
                        "name": component.get("name", ""),
                        "model": component.get("model", ""),
                        "domain": component.get("domain", "[]"),
                        "groups": component.get("groups", []),
                        "sdd_reference": component.get("sdd_reference", ""),
                    })

        if not groups:
            groups.append({
                "id": "user",
                "name": "User",
                "description": "Default user group for the module",
                "category": "Module",
            })

        if not access_rights:
            self._warnings.append(AssemblyWarning(
                "warning", "No access rights defined",
                "A default access right entry is recommended",
            ))

        return {
            "groups": groups,
            "access_rights": access_rights,
            "record_rules": record_rules,
        }

    def _assemble_data(self, tasks_data: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract data components from all tasks."""
        data_entries = []

        for task_id, task in tasks_data.items():
            for component in task.get("components", []):
                if component.get("type") != "data":
                    continue
                data_entries.append({
                    "file": component.get("name", "data.xml"),
                    "type": component.get("format", "xml"),
                    "model": component.get("model", ""),
                    "noupdate": component.get("noupdate", False),
                    "sdd_reference": component.get("sdd_reference", ""),
                })

        return data_entries

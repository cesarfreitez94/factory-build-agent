import json
from pathlib import Path


class ModuleRegistry:
    """Registry of Odoo v18 core modules and their canonical models.

    Used by the Schema Manager to determine whether a model being created
    should be ``new`` (original) or ``extend`` (inherits a core model).
    """

    def __init__(self, project_dir: Path | None = None):
        self._modules: dict[str, dict] = {}
        self._model_index: dict[str, str] = {}

        registry_path = self._find_registry(project_dir)
        if registry_path:
            self._load(registry_path)

    def _find_registry(self, project_dir: Path | None) -> Path | None:
        if project_dir:
            project_path = Path(project_dir) / ".factory" / "module_registry.json"
            if project_path.exists():
                return project_path

        framework_path = (
            Path(__file__).resolve().parent.parent.parent
            / "templates"
            / ".factory"
            / "module_registry.json"
        )
        if framework_path.exists():
            return framework_path

        return None

    def _load(self, path: Path) -> None:
        data = json.loads(path.read_text())
        self._modules = data.get("modules", {})
        self._odoo_version = data.get("odoo_version", "18.0")
        self._build_index()

    def _build_index(self) -> None:
        self._model_index.clear()
        for module_name, module_info in self._modules.items():
            for model_name in module_info.get("models", []):
                self._model_index[model_name] = module_name

    @property
    def odoo_version(self) -> str:
        return getattr(self, "_odoo_version", "18.0")

    @property
    def modules(self) -> dict:
        return dict(self._modules)

    def lookup(self, model_name: str) -> dict | None:
        """Return the module info that owns the given model name, or None."""
        module_name = self._model_index.get(model_name)
        if module_name:
            return {
                "module": module_name,
                "module_info": self._modules.get(module_name, {}),
            }
        return None

    def is_core(self, model_name: str) -> bool:
        """Return True if the model belongs to a core Odoo module."""
        return self.lookup(model_name) is not None

    def get_models(self, module_name: str) -> list[str]:
        """Return the list of models for a given core module, or empty list."""
        module = self._modules.get(module_name, {})
        return list(module.get("models", []))

    def resolve_relation(self, model_name: str) -> str | None:
        """Return the module name if model belongs to a core module, else None.
        
        If the model is NOT in the core registry, it is assumed to belong
        to the module being built."""
        return self._model_index.get(model_name)

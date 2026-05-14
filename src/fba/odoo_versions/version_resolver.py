import json
import re
from pathlib import Path
from typing import Any


_VERSION_DIR_PATTERN = re.compile(r"^v\d+/?$")


class VersionKnowledgeError(Exception):
    """Raised when knowledge layer cannot be loaded."""


class VersionKnowledgeResolver:
    """Loads and merges version-layered Odoo knowledge entries.

    The resolver loads JSON files from `base/` (version-agnostic) and from a
    version-specific layer (e.g. `v18/`). Entries from the version layer
    override entries with the same key from the base layer.

    Constructor:
        VersionKnowledgeResolver(odoo_version: str = "18.0")

    Properties:
        odoo_version: str — the configured Odoo version (e.g. "18.0").
        available_versions: list[str] — detected version layers on disk.

    Methods:
        query(key) -> dict | None
        list_keys(category=None) -> list[str]
        list_categories() -> list[str]
    """

    CATEGORY_FILES = ("patterns.json", "deprecations.json", "novelties.json")

    def __init__(self, odoo_version: str = "18.0") -> None:
        self._odoo_version = odoo_version
        self._root = Path(__file__).resolve().parent
        self._base_dir = self._root / "base"

        self._available_versions = self._detect_versions()

        self._entries: dict[str, dict[str, Any]] = {}
        self._load_base()
        self._load_version()

    # ── public properties ──────────────────────────────────────────────

    @property
    def odoo_version(self) -> str:
        return self._odoo_version

    @property
    def available_versions(self) -> list[str]:
        return list(self._available_versions)

    # ── public query interface ─────────────────────────────────────────

    def query(self, key: str) -> dict[str, Any] | None:
        """Return the knowledge entry for *key*, or None."""
        return self._entries.get(key)

    def list_keys(self, category: str | None = None) -> list[str]:
        """Return all keys, optionally filtered by *category*."""
        if category is None:
            return sorted(self._entries)
        return sorted(
            k for k, v in self._entries.items() if v.get("category") == category
        )

    def list_categories(self) -> list[str]:
        """Return distinct categories that have at least one entry."""
        cats: set[str] = set()
        for entry in self._entries.values():
            cat = entry.get("category")
            if cat:
                cats.add(cat)
        return sorted(cats)

    # ── internal loading ───────────────────────────────────────────────

    def _detect_versions(self) -> list[str]:
        versions: list[str] = []
        for child in sorted(self._root.iterdir()):
            if child.is_dir() and _VERSION_DIR_PATTERN.match(child.name):
                versions.append(child.name)
        return versions

    def _load_base(self) -> None:
        self._merge_dir(self._base_dir)

    def _load_version(self) -> None:
        version_str = self._odoo_version_to_dir(self._odoo_version)
        version_dir = self._root / version_str
        if version_dir.is_dir():
            self._merge_dir(version_dir)

    def _merge_dir(self, directory: Path) -> None:
        """Load all category JSON files from *directory* and merge into self._entries."""
        for filename in self.CATEGORY_FILES:
            filepath = directory / filename
            if not filepath.is_file():
                continue
            try:
                data = json.loads(filepath.read_text())
            except json.JSONDecodeError as exc:
                raise VersionKnowledgeError(
                    f"Invalid JSON in {filepath}: {exc}"
                ) from exc
            if not isinstance(data, dict):
                raise VersionKnowledgeError(
                    f"Expected a JSON object in {filepath}, got {type(data).__name__}"
                )
            for key, entry in data.items():
                if not isinstance(entry, dict):
                    raise VersionKnowledgeError(
                        f"Entry '{key}' in {filepath} must be a JSON object, "
                        f"got {type(entry).__name__}"
                    )
                self._entries[key] = entry

    @staticmethod
    def _odoo_version_to_dir(odoo_version: str) -> str:
        """Normalize an Odoo version string to a directory name.

        Examples:
            "18.0" -> "v18"
            "17.0" -> "v17"
            "v18"  -> "v18"
        """
        odoo_version = odoo_version.strip()
        if odoo_version.lower().startswith("v"):
            return odoo_version.lower()
        parts = odoo_version.split(".")
        if parts:
            return f"v{parts[0]}"
        return f"v{odoo_version}"

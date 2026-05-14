"""Tests for the Odoo Pattern Knowledge Base content (feat/16.3)."""

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_ROOT = ROOT / "src" / "fba" / "odoo_versions"
SCHEMA_PATH = ROOT / "schemas" / "knowledge_entry.schema.json"

CATEGORY_BY_FILENAME = {
    "patterns.json": "patterns",
    "deprecations.json": "deprecations",
    "novelties.json": "novelties",
}

CONTENT_FILES = [
    KNOWLEDGE_ROOT / "base" / "patterns.json",
    KNOWLEDGE_ROOT / "base" / "deprecations.json",
    KNOWLEDGE_ROOT / "base" / "novelties.json",
    KNOWLEDGE_ROOT / "v18" / "patterns.json",
    KNOWLEDGE_ROOT / "v18" / "deprecations.json",
    KNOWLEDGE_ROOT / "v18" / "novelties.json",
]


def _load_json_no_duplicate_keys(path: Path) -> dict[str, Any]:
    duplicates: list[str] = []

    def object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: dict[str, Any] = {}
        for key, value in pairs:
            if key in seen:
                duplicates.append(key)
            seen[key] = value
        return seen

    data = json.loads(path.read_text(), object_pairs_hook=object_pairs_hook)
    assert not duplicates, f"Duplicate JSON keys in {path}: {sorted(set(duplicates))}"
    assert isinstance(data, dict)
    return data


def _load(path: Path) -> dict[str, dict[str, Any]]:
    data = _load_json_no_duplicate_keys(path)
    return {key: value for key, value in data.items() if isinstance(value, dict)}


def _entries(paths: Iterable[Path] = CONTENT_FILES) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for path in paths:
        entries.update(_load(path))
    return entries


def test_every_entry_validates_against_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)

    for path in CONTENT_FILES:
        for key, entry in _load(path).items():
            errors = sorted(validator.iter_errors(entry), key=lambda error: error.path)
            assert not errors, f"{path}:{key} failed schema validation: {errors}"


def test_entry_key_matches_json_key() -> None:
    for path in CONTENT_FILES:
        for key, entry in _load(path).items():
            assert entry["key"] == key, f"{path}:{key} has mismatched entry key"


def test_category_matches_source_file() -> None:
    for path in CONTENT_FILES:
        expected = CATEGORY_BY_FILENAME[path.name]
        for key, entry in _load(path).items():
            assert entry["category"] == expected, f"{path}:{key} should be {expected}"


def test_related_keys_exist_in_base_and_v18_corpus() -> None:
    entries = _entries()
    missing: list[str] = []

    for key, entry in entries.items():
        for related_key in entry["related_keys"]:
            if related_key not in entries:
                missing.append(f"{key} -> {related_key}")

    assert not missing, "Missing related knowledge keys: " + ", ".join(sorted(missing))


def test_base_related_keys_are_self_contained() -> None:
    base_entries = _entries([
        KNOWLEDGE_ROOT / "base" / "patterns.json",
        KNOWLEDGE_ROOT / "base" / "deprecations.json",
        KNOWLEDGE_ROOT / "base" / "novelties.json",
    ])
    missing: list[str] = []

    for key, entry in base_entries.items():
        for related_key in entry["related_keys"]:
            if related_key not in base_entries:
                missing.append(f"{key} -> {related_key}")

    assert not missing, "Base layer has version-specific related keys: " + ", ".join(sorted(missing))


def test_existing_seed_entries_are_preserved() -> None:
    assert "model.naming" in _load(KNOWLEDGE_ROOT / "base" / "patterns.json")
    assert "view.form.structure" in _load(KNOWLEDGE_ROOT / "base" / "patterns.json")
    assert "model.naming" in _load(KNOWLEDGE_ROOT / "v18" / "patterns.json")
    assert "ir.actions.todo" in _load(KNOWLEDGE_ROOT / "v18" / "deprecations.json")
    assert "orm.batch.operations" in _load(KNOWLEDGE_ROOT / "v18" / "novelties.json")


def test_v18_overrides_have_version_marker() -> None:
    base_patterns = _load(KNOWLEDGE_ROOT / "base" / "patterns.json")
    v18_patterns = _load(KNOWLEDGE_ROOT / "v18" / "patterns.json")
    overrides = sorted(set(base_patterns) & set(v18_patterns))

    assert overrides == ["model.naming"]
    for key in overrides:
        assert v18_patterns[key]["since_version"] == "18.0"


def test_expected_content_distribution() -> None:
    base_patterns = _load(KNOWLEDGE_ROOT / "base" / "patterns.json")
    v18_patterns = _load(KNOWLEDGE_ROOT / "v18" / "patterns.json")
    v18_deprecations = _load(KNOWLEDGE_ROOT / "v18" / "deprecations.json")
    v18_novelties = _load(KNOWLEDGE_ROOT / "v18" / "novelties.json")

    assert 30 <= len(base_patterns) <= 60
    assert 10 <= len(v18_patterns) <= 15
    assert 5 <= len(v18_deprecations) <= 10
    assert 5 <= len(v18_novelties) <= 10


def test_v18_resolved_knowledge_has_expected_size() -> None:
    from fba.odoo_versions import VersionKnowledgeResolver

    keys = VersionKnowledgeResolver("18.0").list_keys()
    assert 50 <= len(keys) <= 80
    assert "wizard.confirmation" in keys
    assert "security.combined.access.methods" in keys

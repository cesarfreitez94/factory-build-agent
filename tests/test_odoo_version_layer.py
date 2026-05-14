"""Tests for the Odoo version-aware knowledge layer (feat/16.2)."""

import json

import pytest
from click.testing import CliRunner

from fba.cli import main
from fba.odoo_versions import VersionKnowledgeResolver
from fba.odoo_versions.version_resolver import VersionKnowledgeError


class TestVersionKnowledgeResolver:
    """Unit tests for the VersionKnowledgeResolver class."""

    def test_loads_base_entries(self) -> None:
        """Resolver loads entries from base/ (version-agnostic)."""
        resolver = VersionKnowledgeResolver(odoo_version="18.0")
        entry = resolver.query("model.naming")
        assert entry is not None
        assert entry["key"] == "model.naming"
        assert entry["category"] == "patterns"

    def test_version_overrides_base(self) -> None:
        """Version layer overrides base entries where key conflicts."""
        resolver = VersionKnowledgeResolver(odoo_version="18.0")
        entry = resolver.query("model.naming")
        assert entry is not None
        assert entry["since_version"] == "18.0"
        assert "mi_modulo.mi_modelo" in entry["examples"]

    def test_version_specific_entry_available(self) -> None:
        """Version-specific entries that only exist in the version layer are available."""
        resolver = VersionKnowledgeResolver(odoo_version="18.0")
        entry = resolver.query("ir.actions.todo")
        assert entry is not None
        assert entry["category"] == "deprecations"
        assert entry["deprecated_in"] == "18.0"

    def test_v17_resolver_independent(self) -> None:
        """Resolver for v17 loads base entries but NOT v18-specific entries."""
        resolver = VersionKnowledgeResolver(odoo_version="17.0")
        assert resolver.query("model.naming") is not None
        assert resolver.query("view.form.structure") is not None
        assert resolver.query("ir.actions.todo") is None
        assert resolver.query("orm.batch.operations") is None

    def test_query_nonexistent_key_returns_none(self) -> None:
        """query() returns None for a key that doesn't exist."""
        resolver = VersionKnowledgeResolver(odoo_version="18.0")
        assert resolver.query("nonexistent.key") is None

    def test_list_keys_all(self) -> None:
        """list_keys() returns all keys for the resolved version."""
        resolver = VersionKnowledgeResolver(odoo_version="18.0")
        keys = resolver.list_keys()
        assert "model.naming" in keys
        assert "view.form.structure" in keys
        assert "ir.actions.todo" in keys
        assert "orm.batch.operations" in keys

    def test_list_keys_filtered_by_category(self) -> None:
        """list_keys(category=...) filters correctly."""
        resolver = VersionKnowledgeResolver(odoo_version="18.0")
        pattern_keys = resolver.list_keys(category="patterns")
        assert "model.naming" in pattern_keys
        assert "view.form.structure" in pattern_keys
        assert "ir.actions.todo" not in pattern_keys

        deprecation_keys = resolver.list_keys(category="deprecations")
        assert "ir.actions.todo" in deprecation_keys
        assert "model.naming" not in deprecation_keys

        novelty_keys = resolver.list_keys(category="novelties")
        assert "orm.batch.operations" in novelty_keys

    def test_list_categories(self) -> None:
        """list_categories() returns distinct categories with entries."""
        resolver = VersionKnowledgeResolver(odoo_version="18.0")
        categories = resolver.list_categories()
        assert "patterns" in categories
        assert "deprecations" in categories
        assert "novelties" in categories

    def test_available_versions_detected(self) -> None:
        """available_versions auto-detects v17/ and v18/."""
        resolver = VersionKnowledgeResolver(odoo_version="18.0")
        versions = resolver.available_versions
        assert "v17" in versions
        assert "v18" in versions

    def test_odoo_version_property(self) -> None:
        """odoo_version property returns the configured version."""
        resolver = VersionKnowledgeResolver(odoo_version="17.0")
        assert resolver.odoo_version == "17.0"

    def test_v17_no_own_patterns_preserves_base(self) -> None:
        """v17 has empty patterns so the base entry is preserved as-is."""
        resolver = VersionKnowledgeResolver(odoo_version="17.0")
        entry = resolver.query("model.naming")
        assert entry is not None
        assert entry["since_version"] is None
        assert "x_custom.model" in entry["examples"]

    def test_merge_version_adds_new_entries(self) -> None:
        """Entries that only exist in the version layer are added to the merged dict."""
        resolver = VersionKnowledgeResolver(odoo_version="18.0")
        # v18 has orm.batch.operations (novelty) — base doesn't
        entry = resolver.query("orm.batch.operations")
        assert entry is not None
        assert entry["category"] == "novelties"

    def test_odoo_version_to_dir_normalization(self) -> None:
        """Version strings are normalized correctly to directory names."""
        from fba.odoo_versions.version_resolver import VersionKnowledgeResolver as VKR
        assert VKR._odoo_version_to_dir("18.0") == "v18"
        assert VKR._odoo_version_to_dir("17.0") == "v17"
        assert VKR._odoo_version_to_dir("v18") == "v18"
        assert VKR._odoo_version_to_dir("V18") == "v18"

    def test_unknown_version_graceful(self) -> None:
        """Resolver for an unknown version (e.g. 14.0) loads only base entries."""
        resolver = VersionKnowledgeResolver(odoo_version="14.0")
        assert resolver.query("model.naming") is not None
        # No v14 dir exists, so only base entries are loaded
        assert resolver.query("ir.actions.todo") is None
        assert "v14" not in resolver.available_versions


class TestVersionKnowledgeResolverErrors:
    """Tests for error handling in VersionKnowledgeResolver."""

    def test_invalid_json_raises_error(self, tmp_path) -> None:
        """Loading a file with invalid JSON raises VersionKnowledgeError.

        Constructs a resolver pointing to a temp dir with bad JSON.
        """
        bad_dir = tmp_path / "bad_base"
        bad_dir.mkdir()
        (bad_dir / "patterns.json").write_text("{not valid json")

        resolver = VersionKnowledgeResolver.__new__(VersionKnowledgeResolver)
        resolver._odoo_version = "18.0"
        resolver._root = tmp_path
        resolver._base_dir = bad_dir
        resolver._entries = {}
        resolver._available_versions = []

        with pytest.raises(VersionKnowledgeError, match="Invalid JSON"):
            resolver._load_base()


class TestPatternsCLI:
    """Integration tests for fba patterns CLI commands."""

    def test_query_existing_key_text(self) -> None:
        """fba patterns query <key> shows entry in text format."""
        runner = CliRunner()
        result = runner.invoke(main, ["patterns", "query", "model.naming"])
        assert result.exit_code == 0
        assert "model.naming" in result.output
        assert "patterns" in result.output.lower() or "Pattern" in result.output

    def test_query_existing_key_json(self) -> None:
        """fba patterns query <key> --format json returns valid JSON."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["patterns", "query", "model.naming", "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["key"] == "model.naming"
        assert data["category"] == "patterns"

    def test_query_nonexistent_key_fails(self) -> None:
        """fba patterns query <nonexistent> exits with error."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["patterns", "query", "nonexistent.key"]
        )
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "no se" in result.output.lower()

    def test_list_all_keys_text(self) -> None:
        """fba patterns list shows all keys."""
        runner = CliRunner()
        result = runner.invoke(main, ["patterns", "list"])
        assert result.exit_code == 0
        assert "model.naming" in result.output
        assert "view.form.structure" in result.output

    def test_list_filtered_by_category(self) -> None:
        """fba patterns list --category deprecations filters correctly."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["patterns", "list", "--category", "deprecations"]
        )
        assert result.exit_code == 0
        assert "ir.actions.todo" in result.output
        assert "model.naming" not in result.output

    def test_list_with_v17_version(self) -> None:
        """fba patterns list --odoo-version 17.0 uses v17 resolver."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["patterns", "list", "--odoo-version", "17.0"]
        )
        assert result.exit_code == 0
        assert "model.naming" in result.output
        assert "view.form.structure" in result.output
        # v18-specific entries should not appear
        assert "ir.actions.todo" not in result.output
        assert "orm.batch.operations" not in result.output

    def test_list_json_format(self) -> None:
        """fba patterns list --format json returns valid JSON array."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["patterns", "list", "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert "model.naming" in data

    def test_query_with_odoo_version_option(self) -> None:
        """fba patterns query <key> --odoo-version 17.0 uses v17 resolver."""
        runner = CliRunner()
        # In v17, ir.actions.todo doesn't exist
        result = runner.invoke(
            main, ["patterns", "query", "ir.actions.todo", "--odoo-version", "17.0"]
        )
        assert result.exit_code == 1

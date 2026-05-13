"""Tests for the ModuleRegistry class."""

from pathlib import Path

import pytest

from fba.module_registry import ModuleRegistry

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class TestModuleRegistryLoad:
    def test_loads_from_default_path(self):
        registry = ModuleRegistry()
        assert len(registry.modules) > 0
        assert registry.odoo_version == "18.0"

    def test_has_base_module(self):
        registry = ModuleRegistry()
        assert "base" in registry.modules

    def test_has_expected_modules(self):
        registry = ModuleRegistry()
        for expected in ["base", "mail", "product", "sale", "account", "stock", "hr", "crm"]:
            assert expected in registry.modules, f"Module '{expected}' not found in registry"


class TestModuleRegistryLookup:
    @pytest.fixture
    def registry(self):
        return ModuleRegistry()

    def test_lookup_core_model(self, registry):
        result = registry.lookup("res.partner")
        assert result is not None
        assert result["module"] == "base"

    def test_lookup_unknown_model(self, registry):
        result = registry.lookup("nonexistent.model")
        assert result is None

    def test_lookup_product_model(self, registry):
        result = registry.lookup("product.product")
        assert result is not None
        assert result["module"] == "product"

    def test_lookup_account_model(self, registry):
        result = registry.lookup("account.move")
        assert result is not None
        assert result["module"] == "account"

    def test_lookup_stock_model(self, registry):
        result = registry.lookup("stock.picking")
        assert result is not None
        assert result["module"] == "stock"


class TestModuleRegistryIsCore:
    @pytest.fixture
    def registry(self):
        return ModuleRegistry()

    def test_core_model_is_core(self, registry):
        assert registry.is_core("res.partner") is True
        assert registry.is_core("res.users") is True

    def test_non_core_model_is_not_core(self, registry):
        assert registry.is_core("vehicle.vehicle") is False
        assert registry.is_core("my_module.my_model") is False

    def test_fleet_model_is_core(self, registry):
        assert registry.is_core("fleet.vehicle") is True
        assert registry.is_core("fleet.vehicle.model") is True


class TestModuleRegistryGetModels:
    @pytest.fixture
    def registry(self):
        return ModuleRegistry()

    def test_get_models_for_base(self, registry):
        models = registry.get_models("base")
        assert "res.partner" in models
        assert "res.users" in models
        assert len(models) > 5

    def test_get_models_unknown_module(self, registry):
        models = registry.get_models("nonexistent")
        assert models == []


class TestModuleRegistryResolveRelation:
    @pytest.fixture
    def registry(self):
        return ModuleRegistry()

    def test_resolve_core_model(self, registry):
        module = registry.resolve_relation("res.partner")
        assert module == "base"

    def test_resolve_unknown_model(self, registry):
        module = registry.resolve_relation("custom.model")
        assert module is None

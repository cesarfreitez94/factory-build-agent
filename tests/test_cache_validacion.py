"""Tests for hash-based validation cache in .factory/.cache/

Tests:
- Cache hit/skip: when artifact hash hasn't changed, validation is skipped
- Cache miss: when artifact is new or hash changed, validation runs and cache is populated
- Cache invalidation: when artifact hash changes, old cache entry is invalidated
"""

import hashlib
import json
from pathlib import Path

import pytest

from fba.cache_validacion import ValidationCache, ValidationCacheError


@pytest.fixture
def cache_dir(tmp_path):
    cache = tmp_path / ".factory" / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


@pytest.fixture
def project_dir(tmp_path):
    factory = tmp_path / ".factory"
    factory.mkdir(exist_ok=True)
    artifacts = factory / "artifacts"
    artifacts.mkdir(exist_ok=True)
    return tmp_path


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


class TestValidationCache:
    def test_cache_miss_regenerates(self, cache_dir, project_dir):
        artifact_path = project_dir / ".factory" / "artifacts" / "test.json"
        artifact_path.write_text('{"key": "value1"}')

        cache = ValidationCache(cache_dir)
        result1 = cache.get_or_validate(
            artifact_path=artifact_path,
            validator=lambda: "validation_result_1",
        )
        assert result1 == "validation_result_1"
        assert cache.has_cached(artifact_path)

    def test_cache_hit_skips_validation(self, cache_dir, project_dir):
        artifact_path = project_dir / ".factory" / "artifacts" / "test.json"
        artifact_path.write_text('{"key": "value1"}')

        cache = ValidationCache(cache_dir)
        call_count = 0

        def validator():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        result1 = cache.get_or_validate(artifact_path=artifact_path, validator=validator)
        assert result1 == "result_1"
        assert call_count == 1

        result2 = cache.get_or_validate(artifact_path=artifact_path, validator=validator)
        assert result2 == "result_1"
        assert call_count == 1

    def test_cache_miss_after_hash_change(self, cache_dir, project_dir):
        artifact_path = project_dir / ".factory" / "artifacts" / "test.json"
        artifact_path.write_text('{"key": "value1"}')

        cache = ValidationCache(cache_dir)
        call_count = 0

        def validator():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        result1 = cache.get_or_validate(artifact_path=artifact_path, validator=validator)
        assert result1 == "result_1"
        assert call_count == 1

        artifact_path.write_text('{"key": "value2"}')

        result2 = cache.get_or_validate(artifact_path=artifact_path, validator=validator)
        assert result2 == "result_2"
        assert call_count == 2

    def test_cache_invalidation_on_hash_change(self, cache_dir, project_dir):
        artifact_path = project_dir / ".factory" / "artifacts" / "test.json"
        artifact_path.write_text('{"original": true}')

        cache = ValidationCache(cache_dir)
        assert not cache.has_cached(artifact_path)

        cache.get_or_validate(artifact_path=artifact_path, validator=lambda: "ok")
        assert cache.has_cached(artifact_path)

        artifact_path.write_text('{"modified": true}')

        assert not cache.has_cached(artifact_path)

    def test_cache_stores_hash(self, cache_dir, project_dir):
        artifact_path = project_dir / ".factory" / "artifacts" / "test.json"
        content = '{"test": "data"}'
        artifact_path.write_text(content)

        expected_hash = compute_hash(content)

        cache = ValidationCache(cache_dir)
        cache.get_or_validate(artifact_path=artifact_path, validator=lambda: "result")

        stored = cache._get_stored_hash(artifact_path)
        assert stored == expected_hash

    def test_has_cached_false_for_missing_artifact(self, cache_dir, project_dir):
        artifact_path = project_dir / ".factory" / "artifacts" / "nonexistent.json"

        cache = ValidationCache(cache_dir)
        assert not cache.has_cached(artifact_path)

    def test_has_cached_false_when_no_cache_entry(self, cache_dir, project_dir):
        artifact_path = project_dir / ".factory" / "artifacts" / "test.json"
        artifact_path.write_text('{"test": true}')

        cache = ValidationCache(cache_dir)
        assert not cache.has_cached(artifact_path)

    def test_invalidate_removes_cache(self, cache_dir, project_dir):
        artifact_path = project_dir / ".factory" / "artifacts" / "test.json"
        artifact_path.write_text('{"key": "value"}')

        cache = ValidationCache(cache_dir)
        cache.get_or_validate(artifact_path=artifact_path, validator=lambda: "ok")
        assert cache.has_cached(artifact_path)

        cache.invalidate(artifact_path)
        assert not cache.has_cached(artifact_path)

    def test_invalidate_nonexistent_does_not_error(self, cache_dir, project_dir):
        artifact_path = project_dir / ".factory" / "artifacts" / "nonexistent.json"

        cache = ValidationCache(cache_dir)
        cache.invalidate(artifact_path)

    def test_clear_removes_all_cache(self, cache_dir, project_dir):
        artifact1 = project_dir / ".factory" / "artifacts" / "test1.json"
        artifact2 = project_dir / ".factory" / "artifacts" / "test2.json"
        artifact1.write_text('{"id": 1}')
        artifact2.write_text('{"id": 2}')

        cache = ValidationCache(cache_dir)
        cache.get_or_validate(artifact_path=artifact1, validator=lambda: "r1")
        cache.get_or_validate(artifact_path=artifact2, validator=lambda: "r2")
        assert cache.has_cached(artifact1)
        assert cache.has_cached(artifact2)

        cache.clear()

        assert not cache.has_cached(artifact1)
        assert not cache.has_cached(artifact2)


class TestValidationCacheIntegration:
    def test_coexists_with_diff_engine(self, cache_dir, project_dir):
        from fba.diff_engine import DiffEngine

        artifact_path = project_dir / ".factory" / "artifacts" / "prd.json"
        v1 = {"vision": "test v1", "stakeholders": [], "functional_requirements": []}
        v2 = {"vision": "test v2", "stakeholders": [], "functional_requirements": []}

        artifact_path.write_text(json.dumps(v1))

        cache = ValidationCache(cache_dir)
        result1 = cache.get_or_validate(artifact_path=artifact_path, validator=lambda: "validated_v1")
        assert result1 == "validated_v1"

        diff = DiffEngine()
        changelog = diff.diff(artifact_path, artifact_path)
        assert "No changes detected" in changelog

        artifact_path.write_text(json.dumps(v2))

        result2 = cache.get_or_validate(artifact_path=artifact_path, validator=lambda: "validated_v2")
        assert result2 == "validated_v2"

    def test_cache_does_not_break_gates(self, project_dir):
        from fba.gate import GateRunner

        factory = project_dir / ".factory"
        schemas_dir = factory / "schemas"
        schemas_dir.mkdir(parents=True)

        (schemas_dir / "test.schema.json").write_text(json.dumps({
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        }))

        state = {
            "project": "test",
            "current_phase": "test_phase",
            "methodology": "BABOK",
            "phases": {},
            "valid_transitions": {},
            "gates": {
                "test_phase": {
                    "description": "Test gate",
                    "owner_agent": "tester",
                    "rules": [
                        {"type": "schema", "rule_name": "schema_test", "schema": "test.schema.json", "path": ".factory/artifact.json"},
                    ],
                },
            },
            "artifacts": {},
        }
        (factory / "state.json").write_text(json.dumps(state, indent=2))

        artifact = factory / "artifact.json"
        artifact.write_text('{"name": "hello"}')

        cache_dir = factory / ".cache"
        cache_dir.mkdir()

        runner = GateRunner(project_dir)
        result = runner.check_phase("test_phase")
        assert result.passed is True

        cache = ValidationCache(cache_dir)
        result2 = cache.get_or_validate(artifact_path=artifact, validator=lambda: "cached_result")
        assert result2 == "cached_result"

        result3 = runner.check_phase("test_phase")
        assert result3.passed is True


class TestValidationCacheErrors:
    def test_validator_returning_none_is_valid(self, cache_dir, project_dir):
        artifact_path = project_dir / ".factory" / "artifacts" / "test.json"
        artifact_path.write_text('{"test": true}')

        cache = ValidationCache(cache_dir)
        result = cache.get_or_validate(artifact_path=artifact_path, validator=lambda: None)
        assert result is None

    def test_hash_computation_deterministic(self):
        content = '{"key": "value with unicode éàü"}'
        h1 = compute_hash(content)
        h2 = compute_hash(content)
        assert h1 == h2
        assert len(h1) == 64

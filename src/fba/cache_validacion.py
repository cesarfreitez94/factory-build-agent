"""Hash-based validation cache for FBA artifacts.

Stores SHA-256 hashes of validated artifacts to enable skip of re-validation
when artifact content hasn't changed. Cache lives in `.factory/.cache/` and
coexists with the diff engine from M12.
"""

import hashlib
import json
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")


class ValidationCacheError(Exception):
    """Raised when cache operations fail."""


class ValidationCache:
    """Hash-based validation cache for project artifacts.

    Stores artifact hashes and validation results in `.factory/.cache/`.
    When `get_or_validate` is called, the cache checks if the artifact's
    current hash matches the stored hash. If so, returns the cached result
    without calling the validator. Otherwise, calls the validator, stores
    the new hash and result, and returns the result.

    Cache entry format (one file per artifact):
        .cache/<artifact_relative_path_hash>.json
        {
            "artifact_hash": "<sha256 hex>",
            "result": <cached result>,
            "cached_at": "<ISO timestamp>"
        }
    """

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _artifact_cache_path(self, artifact_path: Path) -> Path:
        normalized = str(artifact_path.resolve())
        hashed = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return self.cache_dir / f"{hashed}.json"

    @staticmethod
    def _compute_hash(artifact_path: Path) -> str:
        return hashlib.sha256(artifact_path.read_bytes()).hexdigest()

    def _get_stored_hash(self, artifact_path: Path) -> str | None:
        cache_path = self._artifact_cache_path(artifact_path)
        if not cache_path.exists():
            return None
        try:
            entry = json.loads(cache_path.read_text())
            hash_value = entry.get("artifact_hash")
            if isinstance(hash_value, str):
                return hash_value
            return None
        except (json.JSONDecodeError, OSError):
            return None

    def has_cached(self, artifact_path: Path) -> bool:
        if not artifact_path.exists():
            return False
        stored_hash = self._get_stored_hash(artifact_path)
        if stored_hash is None:
            return False
        current_hash = self._compute_hash(artifact_path)
        return stored_hash == current_hash

    def get_or_validate(
        self,
        artifact_path: Path,
        validator: Callable[[], T],
    ) -> T:
        if not artifact_path.exists():
            raise ValidationCacheError(f"Artifact not found: {artifact_path}")

        current_hash = self._compute_hash(artifact_path)
        cache_path = self._artifact_cache_path(artifact_path)

        if cache_path.exists():
            try:
                entry = json.loads(cache_path.read_text())
                if entry.get("artifact_hash") == current_hash:
                    result_data: T = entry["result"]
                    return result_data
            except (json.JSONDecodeError, OSError):
                pass

        result = validator()

        entry = {
            "artifact_hash": current_hash,
            "result": result,
            "cached_at": artifact_path.stat().st_mtime,
        }
        try:
            cache_path.write_text(json.dumps(entry, indent=2, ensure_ascii=False))
        except OSError as e:
            raise ValidationCacheError(f"Failed to write cache for {artifact_path}: {e}") from e

        return result

    def invalidate(self, artifact_path: Path) -> None:
        cache_path = self._artifact_cache_path(artifact_path)
        if cache_path.exists():
            cache_path.unlink()

    def clear(self) -> None:
        for cache_file in self.cache_dir.iterdir():
            if cache_file.suffix == ".json":
                cache_file.unlink()

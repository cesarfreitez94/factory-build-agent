"""Stable ID system using UUID v4 for key entities across the pipeline.

Assigns UUIDs to: functional requirements (RF-*), non-functional requirements
(RNF-*), Odoo models, and model fields. IDs are assigned at entity creation time
and are immutable once set.
"""

import json
import uuid
from pathlib import Path
from typing import Any, Optional


ENTITY_TYPES = ("requirement", "model", "field")


class StableIdError(Exception):
    """Raised when stable ID operations fail."""


class StableIdManager:
    """Manages UUID v4 stable IDs for traceable entities.

    Usage:
        mgr = StableIdManager()
        entity_id = mgr.assign_id("RF-001", "requirement")
        # Persist in artifact:
        mgr.ensure_id(prd_data, "functional_requirements", "requirement")
        # Trace:
        result = mgr.trace(entity_id, factory_dir)
    """

    @staticmethod
    def generate_id() -> str:
        """Generate a new UUID v4 as a stable ID."""
        return str(uuid.uuid4())

    @staticmethod
    def assign_id(label: str, entity_type: str) -> str:
        """Assign a UUID v4 to an entity.

        Args:
            label: Human-readable label (e.g., "RF-001", "res.partner").
            entity_type: One of 'requirement', 'model', 'field'.

        Returns:
            The generated UUID v4 string.
        """
        if entity_type not in ENTITY_TYPES:
            raise StableIdError(
                f"Unknown entity type: '{entity_type}'. "
                f"Must be one of: {', '.join(ENTITY_TYPES)}"
            )
        return StableIdManager.generate_id()

    @staticmethod
    def ensure_ids_in_array(
        items: list[dict],
        entity_type: str,
        id_field: str = "id",
        stable_id_field: str = "uuid",
    ) -> int:
        """Ensure all items in an array have stable UUIDs.

        If an item already has a UUID in stable_id_field, it is preserved.
        Otherwise, a new UUID is generated and assigned.

        Args:
            items: List of entity dicts.
            entity_type: Type label for error messages.
            id_field: The field used as the item's logical ID.
            stable_id_field: The field where UUID is stored.

        Returns:
            Number of new UUIDs assigned.
        """
        assigned = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            if stable_id_field not in item or not item[stable_id_field]:
                item[stable_id_field] = StableIdManager.generate_id()
                assigned += 1
        return assigned

    @staticmethod
    def validate_immutability(
        old_items: list[dict],
        new_items: list[dict],
        id_field: str = "id",
        stable_id_field: str = "uuid",
    ) -> list[dict]:
        """Check that UUIDs are immutable across versions.

        Args:
            old_items: Previous version of entity list.
            new_items: New version of entity list.
            id_field: Logical ID field.
            stable_id_field: UUID field.

        Returns:
            List of violations. Empty list means all UUIDs are valid.
        """
        violations = []
        old_map = {
            item.get(id_field, ""): item.get(stable_id_field)
            for item in old_items
            if isinstance(item, dict) and item.get(stable_id_field)
        }
        new_map = {
            item.get(id_field, ""): item.get(stable_id_field)
            for item in new_items
            if isinstance(item, dict) and item.get(stable_id_field)
        }

        for logical_id, old_uuid in old_map.items():
            if old_uuid is None:
                continue
            if logical_id in new_map:
                new_uuid = new_map[logical_id]
                if new_uuid is not None and new_uuid != old_uuid:
                    violations.append({
                        "logical_id": logical_id,
                        "old_uuid": old_uuid,
                        "new_uuid": new_uuid,
                        "message": (
                            f"UUID for '{logical_id}' changed from "
                            f"{old_uuid[:8]}... to {new_uuid[:8]}..."
                        ),
                    })

        return violations

    @staticmethod
    def trace(
        entity_id: str,
        factory_dir: Path,
    ) -> Optional[dict]:
        """Trace a UUID across all artifacts in a factory directory.

        Searches PRD, SDD, and schema.json for the given UUID.

        Args:
            entity_id: The UUID to trace.
            factory_dir: Path to the .factory directory.

        Returns:
            A dict with trace results, or None if not found.
        """
        if not factory_dir.exists():
            raise StableIdError(f"Factory directory not found: {factory_dir}")

        artifacts = ["prd.json", "sdd.json", "schema.json"]
        found = []

        for art_name in artifacts:
            art_path = factory_dir / art_name
            if not art_path.exists():
                continue

            try:
                data = json.loads(art_path.read_text())
            except (json.JSONDecodeError, FileNotFoundError):
                continue

            matches = StableIdManager._find_uuid_in_artifact(
                data, entity_id, art_name.replace(".json", "")
            )
            found.extend(matches)

        if not found:
            return None

        return {
            "uuid": entity_id,
            "found_in": len(found),
            "locations": found,
        }

    @staticmethod
    def _find_uuid_in_artifact(
        data: Any, target_uuid: str, artifact_name: str, path: str = "$"
    ) -> list[dict]:
        """Recursively search for a UUID in an artifact dict.

        Returns list of locations where the UUID was found.
        """
        results = []

        if isinstance(data, dict):
            for key, value in data.items():
                if key == "uuid" and isinstance(value, str) and value == target_uuid:
                    entity_id = data.get("id", data.get("name", "?"))
                    entity_type = StableIdManager._infer_entity_type(
                        artifact_name, data, path
                    )
                    results.append({
                        "artifact": artifact_name,
                        "path": path,
                        "entity_id": entity_id,
                        "entity_type": entity_type,
                    })
                elif isinstance(value, (dict, list)):
                    child_path = f"{path}.{key}" if path != "$" else f"$.{key}"
                    results.extend(
                        StableIdManager._find_uuid_in_artifact(
                            value, target_uuid, artifact_name, child_path
                        )
                    )

        elif isinstance(data, list):
            for i, item in enumerate(data):
                child_path = f"{path}[{i}]"
                results.extend(
                    StableIdManager._find_uuid_in_artifact(
                        item, target_uuid, artifact_name, child_path
                    )
                )

        return results

    @staticmethod
    def _infer_entity_type(artifact_name: str, data: dict, path: str) -> str:
        """Infer the entity type from context."""
        if artifact_name == "prd":
            if "functional_requirements" in path:
                return "requirement"
            if "non_functional_requirements" in path:
                return "requirement"
            return "unknown"
        if artifact_name == "sdd":
            if "models" in path and "fields" not in path:
                return "model"
            return "unknown"
        if artifact_name == "schema":
            if "fields" in path and path.count("fields") > path.count("models"):
                return "field"
            if "models" in path and "fields" not in path:
                return "model"
            return "unknown"
        return "unknown"

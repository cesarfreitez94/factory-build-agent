"""Artifact contract validation engine.

Validates JSON artifacts against declarative contracts that define invariants,
ownership rules, and allowed mutations between versions.
"""

import json
from pathlib import Path
from typing import Any, Optional


class ContractError(Exception):
    """Raised when contract validation fails."""


class ContractEngine:
    """Validates artifacts against declarative contracts.

    Contracts are JSON files in schemas/contracts/ that define:
    - Invariants: rules that must always hold for the artifact
    - Ownership: which agent/phase can modify each field
    - Allowed mutations: which changes are valid between versions

    Usage:
        engine = ContractEngine()
        violations = engine.validate_invariants("prd", prd_data)
        if violations:
            for v in violations:
                print(f"  - {v['id']}: {v['description']}")
    """

    CONTRACTS_DIR = Path(__file__).resolve().parent.parent.parent / "schemas" / "contracts"

    SUPPORTED_TYPES = ["prd", "sdd", "schema"]

    def __init__(self, contracts_dir: Optional[Path] = None):
        self._contracts_dir = contracts_dir or self.CONTRACTS_DIR
        self._cache: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_invariants(self, artifact_type: str, data: dict) -> list[dict]:
        """Validate all invariants for the given artifact.

        Returns a list of violations. Empty list means all invariants pass.
        Each violation is a dict with: id, description, field, detail.
        """
        contract = self._load_contract(artifact_type)
        violations = []

        for invariant in contract.get("invariants", []):
            check = invariant["check"]
            field = check["field"]
            op = check["op"]
            value = check.get("value")

            ok, detail = self._check_invariant(data, field, op, value)
            if not ok:
                violations.append({
                    "id": invariant["id"],
                    "description": invariant["description"],
                    "field": field,
                    "detail": detail,
                })

        return violations

    def validate_ownership(
        self, artifact_type: str, field_path: str, agent: str, phase: str
    ) -> Optional[str]:
        """Check if an agent/phase can modify a field.

        Returns None if allowed, otherwise returns the reason.
        """
        contract = self._load_contract(artifact_type)
        ownership = contract.get("ownership", {})

        field_key = field_path.split(".")[0]
        rule = ownership.get(field_key)

        if rule is None:
            return f"Field '{field_path}' has no ownership rule defined"

        if rule.get("agent") != agent:
            return f"Field '{field_path}' can only be modified by '{rule['agent']}', not '{agent}'"
        if rule.get("phase") != phase:
            return f"Field '{field_path}' can only be modified in '{rule['phase']}' phase, not '{phase}'"

        return None

    def validate_mutations(
        self,
        artifact_type: str,
        old_data: dict,
        new_data: dict,
        context: Optional[dict] = None,
    ) -> list[dict]:
        """Validate allowed mutations between two versions.

        Checks that changes between old_data and new_data respect
        the allowed_mutations rules in the contract.

        Args:
            artifact_type: Type of artifact (prd, sdd, schema).
            old_data: Previous version of the artifact.
            new_data: New version of the artifact.
            context: Optional cross-artifact context (e.g., SDD data
                when validating PRD mutations).

        Returns a list of mutation violations.
        """
        contract = self._load_contract(artifact_type)
        violations = []

        for mutation_rule in contract.get("allowed_mutations", []):
            rule_type = mutation_rule["rule"]
            violations.extend(
                self._check_mutation_rule(
                    mutation_rule, old_data, new_data, context
                )
            )

        return violations

    # ------------------------------------------------------------------
    # Internal: contract loading
    # ------------------------------------------------------------------

    def _load_contract(self, artifact_type: str) -> dict:
        """Load a contract definition from disk."""
        if artifact_type not in self.SUPPORTED_TYPES:
            raise ContractError(
                f"Unknown artifact type: '{artifact_type}'. "
                f"Supported: {', '.join(self.SUPPORTED_TYPES)}"
            )

        if artifact_type in self._cache:
            return self._cache[artifact_type]

        contract_path = self._contracts_dir / f"{artifact_type}.contract.json"
        if not contract_path.exists():
            raise ContractError(f"Contract file not found: {contract_path}")

        try:
            contract = json.loads(contract_path.read_text())
        except json.JSONDecodeError as e:
            raise ContractError(f"Invalid contract JSON in {contract_path}: {e}")

        self._cache[artifact_type] = contract
        return contract

    # ------------------------------------------------------------------
    # Internal: invariant checks
    # ------------------------------------------------------------------

    def _check_invariant(
        self, data: dict, field: str, op: str, value: Any
    ) -> tuple[bool, str]:
        """Check a single invariant rule against the data."""
        actual = self._resolve_field(data, field)

        if op == "exists":
            if actual is None:
                return False, f"Field '{field}' does not exist"
            return True, "ok"

        if op == "min_length":
            if not isinstance(actual, str):
                return False, f"Field '{field}' is not a string (got {type(actual).__name__})"
            if len(actual) < value:
                return False, f"Field '{field}' length is {len(actual)}, minimum is {value}"
            return True, "ok"

        if op == "min_items":
            if not isinstance(actual, list):
                return False, f"Field '{field}' is not an array (got {type(actual).__name__})"
            if len(actual) < value:
                return False, f"Field '{field}' has {len(actual)} items, minimum is {value}"
            return True, "ok"

        if op == "all_items_have_field":
            if not isinstance(actual, list):
                return False, f"Field '{field}' is not an array"
            for i, item in enumerate(actual):
                if not isinstance(item, dict) or value not in item:
                    return False, f"Item {i} in '{field}' is missing field '{value}'"
            return True, "ok"

        if op == "all_items_have_fields":
            if not isinstance(actual, list):
                return False, f"Field '{field}' is not an array"
            for i, item in enumerate(actual):
                if not isinstance(item, dict):
                    return False, f"Item {i} in '{field}' is not an object"
                for req_field in value:
                    if req_field not in item:
                        return False, f"Item {i} in '{field}' is missing field '{req_field}'"
            return True, "ok"

        if op == "all_items_have_min_items_field":
            nested_field = value["field"]
            min_items = value["min"]
            if not isinstance(actual, list):
                return False, f"Field '{field}' is not an array"
            for i, item in enumerate(actual):
                if not isinstance(item, dict):
                    return False, f"Item {i} in '{field}' is not an object"
                nested = item.get(nested_field, [])
                if not isinstance(nested, list):
                    return False, f"Item {i} in '{field}'.'{nested_field}' is not an array"
                if len(nested) < min_items:
                    return False, (
                        f"Item {i} in '{field}'.'{nested_field}' has {len(nested)} "
                        f"items, minimum is {min_items}"
                    )
            return True, "ok"

        if op == "all_items_nested_field":
            nested = value["nested"]
            req_field = value["field"]
            if not isinstance(actual, list):
                return False, f"Field '{field}' is not an array"
            for i, item in enumerate(actual):
                if not isinstance(item, dict):
                    return False, f"Item {i} in '{field}' is not an object"
                sub_items = item.get(nested, [])
                if not isinstance(sub_items, list):
                    return False, f"Item {i} in '{field}'.'{nested}' is not an array"
                for j, sub in enumerate(sub_items):
                    if not isinstance(sub, dict) or req_field not in sub:
                        return False, (
                            f"Item {i}.{j} in '{field}'.'{nested}' "
                            f"is missing field '{req_field}'"
                        )
            return True, "ok"

        return False, f"Unknown invariant operation: '{op}'"

    # ------------------------------------------------------------------
    # Internal: mutation checks
    # ------------------------------------------------------------------

    def _check_mutation_rule(
        self,
        rule: dict,
        old_data: dict,
        new_data: dict,
        context: Optional[dict],
    ) -> list[dict]:
        """Check a single mutation rule."""
        rule_type = rule["rule"]
        violations = []

        if rule_type == "no_delete_if_referenced":
            violations.extend(
                self._check_no_delete_if_referenced(rule, old_data, new_data, context)
            )
        elif rule_type == "cross_field_no_delete":
            violations.extend(
                self._check_cross_field_no_delete(rule, old_data, new_data)
            )
        elif rule_type == "uuid_immutability":
            violations.extend(
                self._check_uuid_immutability(rule, old_data, new_data)
            )

        return violations

    def _check_no_delete_if_referenced(
        self,
        rule: dict,
        old_data: dict,
        new_data: dict,
        context: Optional[dict],
    ) -> list[dict]:
        """Check that deleted items are not referenced in another artifact."""
        violations = []
        source_field = rule["source_field"]

        old_items = old_data.get(source_field, [])
        new_items = new_data.get(source_field, [])

        if not isinstance(old_items, list) or not isinstance(new_items, list):
            return []

        old_ids = {item.get("id", item.get("name", "")) for item in old_items if isinstance(item, dict)}
        new_ids = {item.get("id", item.get("name", "")) for item in new_items if isinstance(item, dict)}
        deleted_ids = old_ids - new_ids

        if not deleted_ids:
            return []

        if context is None:
            return []

        ref_artifact = rule.get("reference_artifact")
        ref_field = rule.get("reference_field")

        if ref_artifact and context:
            ref_data = context.get(ref_artifact, {})
            if not ref_data:
                return [
                    {
                        "id": rule["id"],
                        "description": rule["description"],
                        "deleted": sorted(deleted_ids),
                        "detail": f"Cannot verify: {ref_artifact} context not provided",
                    }
                ]

            referenced = self._find_references(ref_data, ref_field, deleted_ids)
            if referenced:
                return [
                    {
                        "id": rule["id"],
                        "description": rule["description"],
                        "deleted": sorted(deleted_ids),
                        "referenced_by": referenced,
                        "detail": f"Deleted items are referenced in {ref_artifact}",
                    }
                ]

        return []

    def _check_cross_field_no_delete(
        self, rule: dict, old_data: dict, new_data: dict
    ) -> list[dict]:
        """Check cross-field constraints within a single artifact."""
        violations = []
        source_field = rule["source_field"]
        cross_field = rule.get("cross_field", "")
        cross_match = rule.get("cross_match", "model")

        old_items = old_data.get(source_field, [])
        new_items = new_data.get(source_field, [])

        if not isinstance(old_items, list) or not isinstance(new_items, list):
            return []

        old_names = {
            item.get("name", item.get("id", ""))
            for item in old_items if isinstance(item, dict)
        }
        new_names = {
            item.get("name", item.get("id", ""))
            for item in new_items if isinstance(item, dict)
        }
        deleted_names = old_names - new_names

        if not deleted_names:
            return []

        cross_data = new_data
        for part in cross_field.split("."):
            if isinstance(cross_data, dict):
                cross_data = cross_data.get(part, [])
            elif isinstance(cross_data, list):
                break
            else:
                cross_data = []

        if isinstance(cross_data, list):
            referenced = []
            for item in cross_data:
                if isinstance(item, dict) and item.get(cross_match) in deleted_names:
                    referenced.append(item.get(cross_match) or item.get("name", "?"))
            if referenced:
                violations.append({
                    "id": rule["id"],
                    "description": rule["description"],
                    "deleted": sorted(deleted_names),
                    "referenced_by": sorted(referenced),
                    "detail": (
                        f"Deleted items from '{source_field}' are still "
                        f"referenced in '{cross_field}'"
                    ),
                })

        return violations

    def _check_uuid_immutability(
        self, rule: dict, old_data: dict, new_data: dict
    ) -> list[dict]:
        """Check that UUID stable IDs are immutable across versions."""
        source_field = rule["source_field"]
        stable_id_field = rule.get("stable_id_field", "uuid")
        id_field = rule.get("id_field", "id")

        old_items = old_data.get(source_field, [])
        new_items = new_data.get(source_field, [])

        if not isinstance(old_items, list) or not isinstance(new_items, list):
            return []

        old_map = {
            item.get(id_field, ""): item.get(stable_id_field)
            for item in old_items
            if isinstance(item, dict) and item.get(stable_id_field)
        }

        violations = []
        for item in new_items:
            if not isinstance(item, dict):
                continue
            logical_id = item.get(id_field, "")
            old_uuid = old_map.get(logical_id)
            new_uuid = item.get(stable_id_field)
            if old_uuid and new_uuid and old_uuid != new_uuid:
                violations.append({
                    "id": rule["id"],
                    "description": rule["description"],
                    "logical_id": logical_id,
                    "old_uuid": old_uuid,
                    "new_uuid": new_uuid,
                    "detail": (
                        f"UUID for '{logical_id}' changed: "
                        f"{old_uuid[:8]}... → {new_uuid[:8]}..."
                    ),
                })

        return violations

    # ------------------------------------------------------------------
    # Internal: helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_field(data: Any, path: str) -> Any:
        """Resolve a dot-separated field path in a nested dict/list."""
        current = data
        for part in path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    current = current[idx] if idx < len(current) else None
                except (ValueError, IndexError):
                    return None
            else:
                return None
            if current is None:
                return None
        return current

    @staticmethod
    def _find_references(
        data: dict, field_path: str, target_ids: set
    ) -> list[str]:
        """Find references to target_ids within data at field_path."""
        current = data
        for part in field_path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                break
            else:
                return []

        if not isinstance(current, list):
            current = [current] if current else []

        found = []
        for item in current:
            if isinstance(item, dict):
                req = item.get("requirement", item.get("id", item.get("name", "")))
                if req in target_ids:
                    found.append(req)

        return found

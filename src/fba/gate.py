import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RuleResult:
    passed: bool
    rule: str
    message: str = ""
    details: dict = field(default_factory=dict)
    requires_agent: bool = False

    def to_dict(self):
        return {
            "passed": self.passed,
            "rule": self.rule,
            "message": self.message,
            "details": self.details,
            "requires_agent": self.requires_agent,
        }


@dataclass
class GateResult:
    passed: bool
    phase: str
    description: str = ""
    results: list = field(default_factory=list)
    owner_agent: str = ""

    @property
    def failures(self):
        return [r for r in self.results if not r.passed]

    @property
    def error_count(self):
        return len(self.failures)

    @property
    def pending_agent_checks(self):
        return [r for r in self.results if r.requires_agent]

    def to_dict(self):
        return {
            "passed": self.passed,
            "phase": self.phase,
            "description": self.description,
            "owner_agent": self.owner_agent,
            "results": [r.to_dict() for r in self.results],
            "error_count": self.error_count,
            "pending_agent_checks": len(self.pending_agent_checks),
        }


class GateError(Exception):
    def __init__(self, gate_result: GateResult):
        self.gate_result = gate_result
        failures = gate_result.failures
        messages = "; ".join(r.message for r in failures[:3])
        if len(failures) > 3:
            messages += f" (+{len(failures) - 3} more)"
        super().__init__(
            f"Gate '{gate_result.phase}' failed: {messages}"
        )


class GateRunner:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self._factory_dir = self.project_dir / ".factory"
        self._state = self._load_state()
        self._gates = self._state.get("gates", {})

    def check_phase(self, phase: str) -> GateResult:
        gate_def = self._gates.get(phase)
        if not gate_def:
            return GateResult(
                passed=True,
                phase=phase,
                description=f"No gates defined for phase '{phase}'",
                owner_agent="",
            )

        results = []
        for rule in gate_def.get("rules", []):
            results.append(self._evaluate_rule(rule))

        passed = all(r.passed for r in results)
        return GateResult(
            passed=passed,
            phase=phase,
            description=gate_def.get("description", ""),
            results=results,
            owner_agent=gate_def.get("owner_agent", ""),
        )

    def check_current_phase(self) -> GateResult:
        current = self._state.get("current_phase", "init")
        return self.check_phase(current)

    def check_all(self) -> dict:
        return {
            phase: self.check_phase(phase)
            for phase in self._gates
        }

    def _load_state(self):
        state_path = self._factory_dir / "state.json"
        if not state_path.exists():
            return {}
        return json.loads(state_path.read_text())

    def _evaluate_rule(self, rule: dict) -> RuleResult:
        rule_type = rule.get("type", "")

        if rule_type == "schema":
            return self._check_schema(rule)
        elif rule_type == "artifact_exists":
            return self._check_artifact_exists(rule)
        elif rule_type == "traceability":
            return self._check_traceability(rule)
        elif rule_type == "content_check":
            return self._check_content(rule)
        elif rule_type == "semantic_check":
            return self._check_semantic(rule)
        elif rule_type == "task_files_exist":
            return self._check_task_files_exist(rule)
        else:
            return RuleResult(
                passed=False,
                rule=rule_type or "unknown",
                message=f"Unknown rule type: {rule_type}",
            )

    def _resolve_path(self, relative_path: str) -> Path:
        return self.project_dir / relative_path

    def _check_artifact_exists(self, rule: dict) -> RuleResult:
        rule_name = rule.get("rule_name", "artifact_exists")
        path_str = rule.get("path", "")
        artifact_path = self._resolve_path(path_str)

        if not artifact_path.exists():
            return RuleResult(
                passed=False,
                rule=rule_name,
                message=f"Artifact not found: {path_str}",
                details={"path": path_str},
            )

        try:
            content = artifact_path.read_text()
            if not content.strip():
                return RuleResult(
                    passed=False,
                    rule=rule_name,
                    message=f"Artifact is empty: {path_str}",
                    details={"path": path_str},
                )
        except Exception as e:
            return RuleResult(
                passed=False,
                rule=rule_name,
                message=f"Error reading artifact {path_str}: {e}",
                details={"path": path_str},
            )

        return RuleResult(
            passed=True,
            rule=rule_name,
            message=f"Artifact exists: {path_str}",
            details={"path": path_str},
        )

    def _check_schema(self, rule: dict) -> RuleResult:
        import jsonschema

        rule_name = rule.get("rule_name", "schema")
        schema_name = rule.get("schema", "")
        artifact_path_str = rule.get("path", "")

        artifact_path = self._resolve_path(artifact_path_str)
        if not artifact_path.exists():
            return RuleResult(
                passed=False,
                rule=rule_name,
                message=f"Artifact for schema check not found: {artifact_path_str}",
                details={"schema": schema_name, "path": artifact_path_str},
            )

        try:
            artifact_data = json.loads(artifact_path.read_text())
        except json.JSONDecodeError as e:
            return RuleResult(
                passed=False,
                rule=rule_name,
                message=f"Artifact is invalid JSON: {artifact_path_str} - {e}",
                details={"schema": schema_name, "path": artifact_path_str},
            )

        schema_path = self._find_schema(schema_name)
        if not schema_path:
            return RuleResult(
                passed=False,
                rule=rule_name,
                message=f"Schema not found: {schema_name}",
                details={"schema": schema_name, "path": artifact_path_str},
            )

        try:
            schema = json.loads(schema_path.read_text())
            jsonschema.validate(artifact_data, schema)
        except jsonschema.ValidationError as e:
            return RuleResult(
                passed=False,
                rule=rule_name,
                message=f"Schema validation failed for {artifact_path_str}: {e.message}",
                details={"schema": schema_name, "path": artifact_path_str, "error": e.message},
            )

        return RuleResult(
            passed=True,
            rule=rule_name,
            message=f"Schema validation passed: {artifact_path_str}",
            details={"schema": schema_name, "path": artifact_path_str},
        )

    def _check_traceability(self, rule: dict) -> RuleResult:
        rule_name = rule.get("rule_name", "traceability")
        prd_path_str = rule.get("prd_path", "")
        sdd_path_str = rule.get("sdd_path", "")

        prd_path = self._resolve_path(prd_path_str)
        sdd_path = self._resolve_path(sdd_path_str)

        if not prd_path.exists():
            return RuleResult(
                passed=False,
                rule=rule_name,
                message=f"PRD not found for traceability check: {prd_path_str}",
                details={"prd_path": prd_path_str, "sdd_path": sdd_path_str},
            )

        if not sdd_path.exists():
            return RuleResult(
                passed=False,
                rule=rule_name,
                message=f"SDD not found for traceability check: {sdd_path_str}",
                details={"prd_path": prd_path_str, "sdd_path": sdd_path_str},
            )

        try:
            prd = json.loads(prd_path.read_text())
            sdd = json.loads(sdd_path.read_text())
        except json.JSONDecodeError as e:
            return RuleResult(
                passed=False,
                rule=rule_name,
                message=f"Invalid JSON in traceability check: {e}",
                details={"prd_path": prd_path_str, "sdd_path": sdd_path_str},
            )

        prd_rfs = {rf["id"] for rf in prd.get("functional_requirements", [])}
        prd_rnfs = {rnf["id"] for rnf in prd.get("non_functional_requirements", [])}
        all_requirements = prd_rfs | prd_rnfs

        if not all_requirements:
            return RuleResult(
                passed=True,
                rule=rule_name,
                message="No requirements in PRD, traceability skipped",
                details={"total_requirements": 0, "mapped": 0, "unmapped": 0},
            )

        mappings = sdd.get("traceability_matrix", {}).get("mappings", [])
        mapped_requirements = set()
        for mapping in mappings:
            req = mapping.get("requirement", "")
            if req:
                mapped_requirements.add(req)

        unmapped = all_requirements - mapped_requirements
        unmapped_list = sorted(unmapped)

        if unmapped:
            return RuleResult(
                passed=False,
                rule=rule_name,
                message=f"Traceability incomplete: {len(unmapped)} PRD requirement(s) not mapped to SDD components",
                details={
                    "total_requirements": len(all_requirements),
                    "mapped": len(mapped_requirements),
                    "unmapped": len(unmapped),
                    "unmapped_requirements": unmapped_list[:20],
                },
            )

        return RuleResult(
            passed=True,
            rule=rule_name,
            message=f"Traceability complete: {len(all_requirements)} requirements mapped",
            details={
                "total_requirements": len(all_requirements),
                "mapped": len(mapped_requirements),
                "unmapped": 0,
            },
        )

    def _check_content(self, rule: dict) -> RuleResult:
        rule_name = rule.get("rule_name", "content_check")
        path_str = rule.get("path", "")
        checks = rule.get("checks", {})

        artifact_path = self._resolve_path(path_str)
        if not artifact_path.exists():
            return RuleResult(
                passed=False,
                rule=rule_name,
                message=f"Artifact for content check not found: {path_str}",
                details={"path": path_str},
            )

        try:
            data = json.loads(artifact_path.read_text())
        except json.JSONDecodeError as e:
            return RuleResult(
                passed=False,
                rule=rule_name,
                message=f"Artifact is invalid JSON: {path_str} - {e}",
                details={"path": path_str},
            )

        failures = []
        for key, min_count in checks.items():
            actual = 0
            if key.startswith("min_"):
                field_name = key[4:]
                actual = len(data.get(field_name, []))

                if actual < min_count:
                    failures.append(
                        f"Expected at least {min_count} {field_name}, got {actual}"
                    )

        if failures:
            return RuleResult(
                passed=False,
                rule=rule_name,
                message="; ".join(failures),
                details={"path": path_str, "failures": failures},
            )

        return RuleResult(
            passed=True,
            rule=rule_name,
            message="All content checks passed",
            details={"path": path_str, "checks_passed": len(checks)},
        )

    def _check_semantic(self, rule: dict) -> RuleResult:
        rule_name = rule.get("rule_name", "semantic_check")
        source_path_str = rule.get("source_path", "")
        target_path_str = rule.get("target_path", "")
        dimensions = rule.get("dimensions", [
            "domain_consistency",
            "objective_alignment",
            "terminology_match",
            "stakeholder_relevance",
            "requirement_relevance",
        ])

        source_path = self._resolve_path(source_path_str)
        if not source_path.exists():
            return RuleResult(
                passed=True,
                rule=rule_name,
                message=f"Semantic check deferred: source artifact not found ({source_path_str})",
                details={"source_path": source_path_str, "target_path": target_path_str},
                requires_agent=False,
            )

        target_path = self._resolve_path(target_path_str)
        if not target_path.exists():
            return RuleResult(
                passed=True,
                rule=rule_name,
                message=f"Semantic check deferred: target artifact not found ({target_path_str})",
                details={"source_path": source_path_str, "target_path": target_path_str},
                requires_agent=False,
            )

        try:
            source_data = json.loads(source_path.read_text())
        except json.JSONDecodeError as e:
            return RuleResult(
                passed=True,
                rule=rule_name,
                message=f"Semantic check deferred: invalid JSON in source ({source_path_str}): {e}",
                details={"source_path": source_path_str, "target_path": target_path_str},
                requires_agent=False,
            )

        try:
            target_data = json.loads(target_path.read_text())
        except json.JSONDecodeError as e:
            return RuleResult(
                passed=True,
                rule=rule_name,
                message=f"Semantic check deferred: invalid JSON in target ({target_path_str}): {e}",
                details={"source_path": source_path_str, "target_path": target_path_str},
                requires_agent=False,
            )

        eval_data = {
            "source_path": source_path_str,
            "target_path": target_path_str,
            "dimensions": dimensions,
            "source_snapshot": {
                "initial_description": source_data.get("initial_description", ""),
                "business_context": source_data.get("business_context", ""),
                "objectives": source_data.get("objectives", [])[:10],
                "stakeholders": [
                    {"name": s.get("name", ""), "role": s.get("role", ""), "interest": s.get("interest", "")}
                    for s in source_data.get("stakeholders", [])[:10]
                ],
                "functional_requirements": [
                    {"id": r["id"], "description": r.get("description", "")}
                    for r in source_data.get("functional_requirements", [])[:20]
                ],
                "non_functional_requirements": [
                    {"id": r["id"], "description": r.get("description", ""), "category": r.get("category", "")}
                    for r in source_data.get("non_functional_requirements", [])[:10]
                ],
                "glossary": [
                    {"term": g.get("term", ""), "definition": g.get("definition", "")}
                    for g in source_data.get("glossary", [])[:10]
                ],
            },
            "target_snapshot": {
                "vision": target_data.get("vision", ""),
                "module_name": target_data.get("module_name", ""),
                "module_display_name": target_data.get("module_display_name", ""),
                "summary": target_data.get("summary", ""),
                "objectives": target_data.get("objectives", [])[:10],
                "stakeholders": [
                    {"name": s.get("name", ""), "role": s.get("role", ""), "interest": s.get("interest", "")}
                    for s in target_data.get("stakeholders", [])[:10]
                ],
                "functional_requirements": [
                    {"id": r["id"], "description": r.get("description", ""), "priority": r.get("priority", "")}
                    for r in target_data.get("functional_requirements", [])[:20]
                ],
                "non_functional_requirements": [
                    {"id": r["id"], "description": r.get("description", ""), "category": r.get("category", "")}
                    for r in target_data.get("non_functional_requirements", [])[:10]
                ],
                "glossary": [
                    {"term": g.get("term", ""), "definition": g.get("definition", "")}
                    for g in target_data.get("glossary", [])[:10]
                ],
                "constraints": target_data.get("constraints", [])[:10],
                "dependencies": target_data.get("dependencies", {}) if isinstance(target_data.get("dependencies"), dict) else target_data.get("dependencies", [])[:10],
            },
        }

        return RuleResult(
            passed=True,
            rule=rule_name,
            message=f"Semantic check pending: comparing {source_path_str} → {target_path_str} across {len(dimensions)} dimensions — requires agent evaluation",
            details={"eval_data": eval_data},
            requires_agent=True,
        )

    def _check_task_files_exist(self, rule: dict) -> RuleResult:
        import jsonschema

        rule_name = rule.get("rule_name", "task_files_exist")
        index_path_str = rule.get("index_path", "")

        index_path = self._resolve_path(index_path_str)
        if not index_path.exists():
            return RuleResult(
                passed=False,
                rule=rule_name,
                message=f"Task index not found: {index_path_str}",
                details={"index_path": index_path_str},
            )

        try:
            index_data = json.loads(index_path.read_text())
        except json.JSONDecodeError as e:
            return RuleResult(
                passed=False,
                rule=rule_name,
                message=f"Task index is invalid JSON: {index_path_str} - {e}",
                details={"index_path": index_path_str},
            )

        tasks = index_data.get("tasks", [])
        if not tasks:
            return RuleResult(
                passed=False,
                rule=rule_name,
                message=f"Task index has no tasks defined: {index_path_str}",
                details={"index_path": index_path_str},
            )

        task_item_schema = self._find_schema("task_item.schema.json")
        missing_files = []
        invalid_json = []
        empty_files = []
        schema_failures = []

        for task_entry in tasks:
            file_name = task_entry.get("file", "")
            if not file_name:
                missing_files.append(f"(no file field for task {task_entry.get('id', 'unknown')})")
                continue

            task_path = self._factory_dir / "tasks" / file_name
            if not task_path.exists():
                missing_files.append(file_name)
                continue

            try:
                task_content = task_path.read_text()
            except Exception as e:
                missing_files.append(f"{file_name} (read error: {e})")
                continue

            if not task_content.strip():
                empty_files.append(file_name)
                continue

            try:
                task_data = json.loads(task_content)
            except json.JSONDecodeError as e:
                invalid_json.append(f"{file_name}: {e}")
                continue

            if task_item_schema:
                try:
                    schema = json.loads(task_item_schema.read_text())
                    jsonschema.validate(task_data, schema)
                except jsonschema.ValidationError as e:
                    schema_failures.append(f"{file_name}: {e.message}")

        failures = []
        details = {
            "index_path": index_path_str,
            "total_tasks": len(tasks),
            "missing_files": missing_files,
            "invalid_json": invalid_json,
            "empty_files": empty_files,
            "schema_failures": schema_failures,
        }

        if missing_files:
            failures.append(f"Missing task files: {', '.join(missing_files[:5])}")
        if invalid_json:
            failures.append(f"Invalid JSON: {', '.join(invalid_json[:5])}")
        if empty_files:
            failures.append(f"Empty task files: {', '.join(empty_files[:5])}")
        if schema_failures:
            failures.append(f"Schema validation failed: {', '.join(schema_failures[:5])}")

        if failures:
            return RuleResult(
                passed=False,
                rule=rule_name,
                message="; ".join(failures),
                details=details,
            )

        return RuleResult(
            passed=True,
            rule=rule_name,
            message=f"All {len(tasks)} task files exist and are valid",
            details=details,
        )

    def _find_schema(self, schema_name: str) -> Path | None:
        project_schema = self._factory_dir / "schemas" / schema_name
        if project_schema.exists():
            return project_schema

        schemas_dir = Path(__file__).resolve().parent.parent.parent / "schemas"
        framework_schema = schemas_dir / schema_name
        if framework_schema.exists():
            return framework_schema

        return None

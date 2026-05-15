"""Pure utility for V2 intent generation.

The V1 framework state remains authoritative. This module only reads explicit
inputs, validates them against the intent schema, and can write a shadow intent
artifact under .factory/meta/artifacts.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence, cast

import jsonschema


DEFAULT_SCOPE_EXCLUDES = [
    ".factory/framework-state.json",
    ".factory/state.json",
    ".factory/events.jsonl",
    ".opencode/plugins/fba-agent-observer.ts",
]
INTENT_PATH_PREFIXES = ("src/", "tests/", "docs/", "schemas/")
NEGATIVE_MARKERS = (
    "no modificar",
    "no tocar",
    "no cambiar",
    "no alterar",
    "do not modify",
    "do not touch",
    "never modify",
    "avoid changing",
    "without touching",
    "sin tocar",
    "sin modificar",
    "no activar",
    "do not execute",
    "no ejecutar",
)
PHASE_KEYWORDS = {
    "diseño": ("diseño", "diseno", "disena", "design", "schema", "schemas", "esquema", "arquitectura", "architecture", "plan"),
    "implementación": (
        "implementa",
        "implementar",
        "implementacion",
        "implementación",
        "implementation",
        "build",
        "codigo",
        "código",
        "code",
        "write",
        "add",
        "fix",
    ),
    "review": ("review", "revisa", "revision", "revisión", "revisor", "audit", "auditar"),
    "testing": ("test", "tests", "pytest", "qa", "playwright", "verificar", "verify"),
    "docs": ("docs", "doc", "documenta", "documentación", "documentacion", "readme", "changelog"),
    "agentes": ("agentes", "agents", ".opencode/agents", "subagent"),
    "comandos": ("comandos", "commands", ".opencode/commands", "slash command"),
    "generador odoo": ("generador odoo", "odoo generator", "src/fba/generator", "renderer", "odoo generator"),
    "git": ("git", "commit", "push", "pull request", "merge", "branch"),
}
PHASE_PRIORITY = [
    "implementación",
    "diseño",
    "review",
    "testing",
    "docs",
    "agentes",
    "comandos",
    "generador odoo",
    "git",
]
PHASE_REQUESTED_OUTPUTS = {
    "diseño": ["intent_spec"],
    "implementación": ["src/fba/meta_intent_builder.py", "tests/test_meta_intent_builder.py"],
    "review": ["review_notes"],
    "testing": ["test_plan"],
    "docs": ["documentation_update"],
    "agentes": ["agent_change_request"],
    "comandos": ["command_change_request"],
    "generador odoo": ["odoo_generator_change_request"],
    "git": ["git_operation_request"],
}
PHASE_CONSTRAINTS = {
    "diseño": "dominant_phase:design",
    "implementación": "dominant_phase:implementation",
    "review": "dominant_phase:review",
    "testing": "dominant_phase:testing",
    "docs": "dominant_phase:docs",
    "agentes": "dominant_phase:agents",
    "comandos": "dominant_phase:commands",
    "generador odoo": "dominant_phase:odoo_generator",
    "git": "dominant_phase:git",
}
PHASE_CORE_KEYWORDS = {
    "diseño": {"diseño", "diseno", "disena", "design"},
    "implementación": {"implementa", "implementar", "implementacion", "implementación", "implementation", "build"},
}


@dataclass(frozen=True)
class IntentBuilderResult:
    artifact_path: Path
    validation_path: Path | None
    intent: dict[str, Any]
    schema_valid: bool


class IntentBuilderError(Exception):
    """Raised when an intent cannot be built safely."""


def build_intent(
    user_message: str,
    framework_state: Mapping[str, Any] | None = None,
    recent_artifacts: Sequence[Mapping[str, Any] | str] | None = None,
    *,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    """Build a V2 intent instance without writing files."""

    root = _repo_root()
    timestamp = _normalize_timestamp(now)
    stamp = timestamp[:10].replace("-", "")

    if not isinstance(user_message, str) or not user_message.strip():
        raise IntentBuilderError("user_message is required")

    framework_state_map = framework_state if isinstance(framework_state, Mapping) else None
    artifact_items = _normalize_artifacts(recent_artifacts)

    message_text = user_message.strip()
    request_text = _request_text(message_text)
    normalized_text = _normalize_text(message_text)
    request_positive_text = _positive_text(request_text)

    exclusions = _detect_exclusions(normalized_text)
    phase = _dominant_phase(request_text, artifact_items, framework_state_map)
    phase_signals = _phase_signals(request_positive_text)
    milestone_ids = _milestone_ids(message_text, artifact_items, framework_state_map)
    related_milestone = _related_milestone(milestone_ids, framework_state_map, artifact_items, normalized_text)
    requires_user_confirmation = _requires_confirmation(phase_signals, milestone_ids, _normalize_text(request_text))

    include = _build_scope_include(message_text, artifact_items, phase, exclusions)
    requested_outputs = _build_requested_outputs(include, phase, message_text, artifact_items, exclusions)
    constraints = _build_constraints(phase, exclusions, requires_user_confirmation)
    non_goals = _build_non_goals(exclusions, phase, requires_user_confirmation)

    intent: dict[str, Any] = {
        "contract_name": "intent",
        "contract_version": "2.0",
        "intent_id": _intent_id(stamp, artifact_items),
        "created_at": timestamp,
        "source": "user",
        "objective": _objective(request_text),
        "scope": {
            "include": include,
            "exclude": _scope_excludes(exclusions),
        },
        "constraints": constraints,
        "requested_outputs": requested_outputs,
        "non_goals": non_goals,
        "urgency": _urgency(phase, normalized_text, requires_user_confirmation),
        "related_milestone": related_milestone,
        "requires_user_confirmation": requires_user_confirmation,
        "human_summary": _human_summary(phase, include, exclusions, related_milestone, requires_user_confirmation),
    }

    _validate_output(root, intent)
    return intent


def generate_intent(
    project_dir: Path,
    user_message: str,
    framework_state: Mapping[str, Any] | None = None,
    recent_artifacts: Sequence[Mapping[str, Any] | str] | None = None,
    *,
    now: datetime | str | None = None,
    write_validation_report: bool = True,
) -> IntentBuilderResult:
    """Generate, validate, and write a V2 intent artifact."""

    root = Path(project_dir).resolve()
    timestamp = _normalize_timestamp(now)
    existing_artifacts = _load_existing_intent_artifacts(root)
    merged_recent_artifacts = list(recent_artifacts or []) + existing_artifacts
    intent = build_intent(user_message, framework_state, merged_recent_artifacts, now=timestamp)

    artifact_dir = root / ".factory" / "meta" / "artifacts" / "intents"
    artifact_path = artifact_dir / f"{intent['intent_id']}.json"
    _write_json(artifact_path, intent)

    validation_report_path: Path | None = None
    if write_validation_report:
        validation_path = root / ".factory" / "meta" / "validation" / "last_intent.json"
        validation_report = {
            "contract_name": "intent_validation",
            "contract_version": "2.0",
            "validated_at": timestamp,
            "artifact_path": str(artifact_path.relative_to(root)),
            "schema_path": "schemas/meta/intent.schema.json",
            "schema_valid": True,
        }
        _write_json(validation_path, validation_report)
        validation_report_path = validation_path

    return IntentBuilderResult(
        artifact_path=artifact_path,
        validation_path=validation_report_path,
        intent=intent,
        schema_valid=True,
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _validate_output(root: Path, intent: Mapping[str, Any]) -> None:
    schema_path = root / "schemas" / "meta" / "intent.schema.json"
    schema = cast(dict[str, Any], json.loads(_read_text(schema_path)))
    try:
        jsonschema.Draft7Validator(schema).validate(intent)
    except jsonschema.ValidationError as exc:
        raise IntentBuilderError(f"Invalid intent output: {exc.message}") from exc


def _read_text(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError as exc:
        raise IntentBuilderError(f"Required file not found: {path}") from exc


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _normalize_timestamp(value: datetime | str | None) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, str) and value:
        return value
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_artifacts(value: Sequence[Mapping[str, Any] | str] | None) -> list[dict[str, Any]]:
    if not value:
        return []
    artifacts: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            artifacts.append(dict(item))
        elif isinstance(item, str) and item.strip():
            artifacts.append({"text": item.strip()})
    return artifacts


def _request_text(message_text: str) -> str:
    for marker in ("\nContexto:", "\nContext:", "\nRequisitos:", "\nRequirements:"):
        if marker in message_text:
            return message_text.split(marker, 1)[0].strip()
    return message_text.strip()


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _positive_text(message_text: str) -> str:
    parts: list[str] = []
    for line in message_text.splitlines():
        normalized = _normalize_text(line)
        if any(marker in normalized for marker in NEGATIVE_MARKERS):
            continue
        parts.append(line)
    return _normalize_text(" ".join(parts))


def _detect_exclusions(normalized_text: str) -> list[str]:
    exclusions: list[str] = []
    if _contains_negative(normalized_text, ("agentes", "agents", ".opencode/agents")):
        exclusions.append("agents")
    if _contains_negative(normalized_text, ("comandos", "commands", ".opencode/commands")):
        exclusions.append("commands")
    if _contains_negative(normalized_text, ("generador odoo", "odoo generator", "src/fba/generator", "renderer")):
        exclusions.append("odoo_generator")
    if _contains_negative(normalized_text, ("schema", "schemas", "esquema")):
        exclusions.append("schemas")
    if _contains_negative(normalized_text, ("framework-state.json", "state.json", "events.jsonl", "runtime v1", "v1 runtime")):
        exclusions.append("v1_runtime")
    if _contains_negative(normalized_text, ("fba-agent-observer", "agent-observer", "agent observer")):
        exclusions.append("fba_agent_observer")
    return _ordered_unique(exclusions)


def _contains_negative(normalized_text: str, keywords: Sequence[str]) -> bool:
    for keyword in keywords:
        if keyword not in normalized_text:
            continue
        index = normalized_text.index(keyword)
        prefix = normalized_text[max(0, index - 48) : index]
        if any(marker in prefix for marker in NEGATIVE_MARKERS):
            return True
    return False


def _dominant_phase(request_text: str, recent_artifacts: list[dict[str, Any]], framework_state: Mapping[str, Any] | None) -> str:
    scores: dict[str, int] = {phase: 0 for phase in PHASE_PRIORITY}
    normalized_request = _normalize_text(request_text)

    for phase, keywords in PHASE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized_request:
                scores[phase] += 2 if keyword in PHASE_CORE_KEYWORDS.get(phase, set()) else 1

    if not any(scores.values()):
        for artifact in recent_artifacts:
            artifact_text = _normalize_text(" ".join(str(value) for value in _iter_strings(artifact)))
            for phase, keywords in PHASE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in artifact_text:
                        scores[phase] += 1

    if not any(scores.values()) and isinstance(framework_state, Mapping):
        phase_hint = _normalize_text(str(framework_state.get("current_phase", "")))
        aliases = {
            "implementación": ("implementation", "implementacion", "implementación"),
            "diseño": ("design", "diseno", "diseño"),
            "review": ("review",),
            "testing": ("testing", "test"),
            "docs": ("docs", "documentation"),
            "agentes": ("agents", "agentes"),
            "comandos": ("commands", "comandos"),
            "generador odoo": ("odoo generator", "generador odoo"),
            "git": ("git",),
        }
        for phase, values in aliases.items():
            if any(value in phase_hint for value in values):
                scores[phase] += 1

    return max(PHASE_PRIORITY, key=lambda phase: (scores[phase], -PHASE_PRIORITY.index(phase)))


def _phase_signals(normalized_text: str) -> set[str]:
    signals: set[str] = set()
    for phase, keywords in PHASE_KEYWORDS.items():
        if any(keyword in normalized_text for keyword in keywords):
            signals.add(phase)
    return signals


def _milestone_ids(message_text: str, recent_artifacts: list[dict[str, Any]], framework_state: Mapping[str, Any] | None) -> list[str]:
    ids: list[str] = []
    for source in (message_text, " ".join(str(value) for artifact in recent_artifacts for value in _iter_strings(artifact))):
        for item in re.findall(r"\bM[0-9]+\b", source.upper()):
            if item not in ids:
                ids.append(item)
    if isinstance(framework_state, Mapping):
        active = framework_state.get("active_milestone")
        if isinstance(active, Mapping):
            milestone_id = active.get("id")
            if isinstance(milestone_id, str) and milestone_id and milestone_id not in ids:
                ids.insert(0, milestone_id)
    return ids


def _related_milestone(
    milestone_ids: list[str],
    framework_state: Mapping[str, Any] | None,
    recent_artifacts: list[dict[str, Any]],
    normalized_text: str,
) -> dict[str, Any]:
    milestone_id = milestone_ids[0] if milestone_ids else "M0"
    status = _milestone_status(normalized_text)
    branch = None

    if isinstance(framework_state, Mapping):
        active = framework_state.get("active_milestone")
        if isinstance(active, Mapping):
            active_id = active.get("id")
            if isinstance(active_id, str) and active_id:
                milestone_id = active_id
            active_status = active.get("status")
            if isinstance(active_status, str) and active_status:
                status = active_status
            active_branch = active.get("branch")
            if isinstance(active_branch, str) and active_branch:
                branch = active_branch

    if branch is None:
        for artifact in recent_artifacts:
            related_milestone_value = artifact.get("related_milestone")
            if isinstance(related_milestone_value, Mapping):
                rel_id = related_milestone_value.get("id")
                if isinstance(rel_id, str) and rel_id and milestone_id == "M0":
                    milestone_id = rel_id
                rel_status = related_milestone_value.get("status")
                if isinstance(rel_status, str) and rel_status:
                    status = rel_status
                rel_branch = related_milestone_value.get("branch")
                if isinstance(rel_branch, str) and rel_branch:
                    branch = rel_branch
                    break

    related_milestone: dict[str, Any] = {"id": milestone_id, "status": status}
    if branch:
        related_milestone["branch"] = branch
    return related_milestone


def _milestone_status(normalized_text: str) -> str:
    if "paused" in normalized_text or "pausado" in normalized_text:
        return "paused"
    if "completed" in normalized_text or "completado" in normalized_text:
        return "completed"
    if "in progress" in normalized_text or "en progreso" in normalized_text:
        return "in_progress"
    return "planned"


def _requires_confirmation(phase_signals: set[str], milestone_ids: list[str], request_text: str) -> bool:
    if len(_ordered_unique(milestone_ids)) > 1:
        return True
    if "diseño" in phase_signals and "implementación" in phase_signals:
        return True
    if "implementación" in phase_signals and "git" in phase_signals:
        return True
    if "git" in phase_signals and re.search(r"\b(commit|push|merge|pr)\b|pull request", request_text):
        return True
    return False


def _build_scope_include(
    message_text: str,
    recent_artifacts: list[dict[str, Any]],
    phase: str,
    exclusions: list[str],
) -> list[str]:
    paths: list[str] = []
    for candidate in _extract_paths(message_text):
        if not candidate.startswith(INTENT_PATH_PREFIXES):
            continue
        if _is_excluded_path(candidate, exclusions):
            continue
        paths.append(candidate)

    for artifact in recent_artifacts:
        for candidate in _extract_paths(" ".join(str(value) for value in _iter_strings(artifact))):
            if not candidate.startswith(INTENT_PATH_PREFIXES):
                continue
            if _is_excluded_path(candidate, exclusions):
                continue
            paths.append(candidate)

    if not paths:
        paths.extend(PHASE_REQUESTED_OUTPUTS.get(phase, ["intent_request"]))

    return _ordered_unique(paths)


def _build_requested_outputs(
    include: list[str],
    phase: str,
    message_text: str,
    recent_artifacts: list[dict[str, Any]],
    exclusions: list[str],
) -> list[str]:
    outputs = list(include)
    if phase in PHASE_REQUESTED_OUTPUTS:
        outputs.extend(PHASE_REQUESTED_OUTPUTS[phase])

    if _normalize_text(message_text).startswith("implementa la utility pura intent builder v2"):
        outputs.extend(["src/fba/meta_intent_builder.py", "tests/test_meta_intent_builder.py"])

    for artifact in recent_artifacts:
        for candidate in _extract_paths(" ".join(str(value) for value in _iter_strings(artifact))):
            if _is_excluded_path(candidate, exclusions):
                continue
            outputs.append(candidate)

    if not outputs:
        outputs.append("intent_request")

    return _ordered_unique(outputs)


def _build_constraints(phase: str, exclusions: list[str], requires_user_confirmation: bool) -> list[str]:
    values: list[str] = []
    values.append(PHASE_CONSTRAINTS.get(phase, "dominant_phase:implementation"))
    if requires_user_confirmation:
        values.append("requires_user_confirmation")
    for exclusion in exclusions:
        values.append(f"exclude:{exclusion}")
    return _ordered_unique(values)


def _build_non_goals(exclusions: list[str], phase: str, requires_user_confirmation: bool) -> list[str]:
    values: list[str] = []
    for exclusion in exclusions:
        if exclusion == "agents":
            values.append("No modificar agentes")
        elif exclusion == "commands":
            values.append("No modificar comandos")
        elif exclusion == "odoo_generator":
            values.append("No modificar generador Odoo")
        elif exclusion == "schemas":
            values.append("No modificar schemas")
        elif exclusion == "v1_runtime":
            values.append("No modificar runtime V1")
        elif exclusion == "fba_agent_observer":
            values.append("No modificar fba-agent-observer")
    if phase == "git":
        values.append("No ejecutar git directamente")
    if requires_user_confirmation:
        values.append("Confirmacion humana requerida antes de continuar")
    return _ordered_unique(values)


def _scope_excludes(exclusions: list[str]) -> list[str]:
    values = list(DEFAULT_SCOPE_EXCLUDES)
    if "agents" in exclusions:
        values.append(".opencode/agents/**")
    if "commands" in exclusions:
        values.append(".opencode/commands/**")
    if "odoo_generator" in exclusions:
        values.append("src/fba/generator/**")
    if "schemas" in exclusions:
        values.append("schemas/**")
    if "fba_agent_observer" in exclusions:
        values.append(".opencode/plugins/fba-agent-observer.ts")
    if "v1_runtime" in exclusions:
        values.extend([".factory/framework-state.json", ".factory/state.json", ".factory/events.jsonl"])
    return _ordered_unique(values)


def _urgency(phase: str, normalized_text: str, requires_user_confirmation: bool) -> str:
    if any(term in normalized_text for term in ("critical", "critico", "crítico", "asap", "urgente", "urgent")):
        return "critical"
    if requires_user_confirmation or phase in {"implementación", "git", "agentes", "comandos", "generador odoo"}:
        return "high"
    if phase in {"testing", "review", "docs"}:
        return "medium"
    return "low"


def _objective(request_text: str) -> str:
    first_line = request_text.splitlines()[0].strip()
    first_sentence = re.split(r"[.!?]\s+", first_line, maxsplit=1)[0].strip()
    return first_sentence or "Intent request"


def _human_summary(
    phase: str,
    include: list[str],
    exclusions: list[str],
    related_milestone: Mapping[str, Any],
    requires_user_confirmation: bool,
) -> str:
    summary = f"Fase dominante: {phase}."
    if include:
        summary += f" Scope: {', '.join(include[:3])}."
    if exclusions:
        summary += f" Exclusiones: {', '.join(exclusions)}."
    milestone_id = related_milestone.get("id")
    if isinstance(milestone_id, str) and milestone_id:
        summary += f" Milestone: {milestone_id}."
    summary += f" Confirmacion: {'si' if requires_user_confirmation else 'no'}."
    return summary


def _intent_id(stamp: str, recent_artifacts: list[dict[str, Any]]) -> str:
    sequence = 1
    for artifact in recent_artifacts:
        for key in ("intent_id", "artifact_id"):
            value = artifact.get(key)
            if not isinstance(value, str):
                continue
            match = re.fullmatch(rf"INTENT-{stamp}-(\d{{3}})", value)
            if match:
                sequence = max(sequence, int(match.group(1)) + 1)
    return f"INTENT-{stamp}-{sequence:03d}"


def _load_existing_intent_artifacts(root: Path) -> list[dict[str, Any]]:
    artifact_dir = root / ".factory" / "meta" / "artifacts" / "intents"
    if not artifact_dir.exists():
        return []

    values: list[dict[str, Any]] = []
    for path in sorted(artifact_dir.glob("INTENT-*.json")):
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            values.append(data)
    return values


def _extract_paths(text: str) -> list[str]:
    candidates: list[str] = []
    pattern = re.compile(r"(?:\.?[A-Za-z0-9_-]+/)+[A-Za-z0-9_.-]+(?:\.[A-Za-z0-9_.-]+)?")
    for match in pattern.finditer(text):
        candidate = match.group(0).rstrip(")].,;:")
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _is_excluded_path(path: str, exclusions: list[str]) -> bool:
    if path in DEFAULT_SCOPE_EXCLUDES:
        return True
    if "agents" in exclusions and path.startswith(".opencode/agents/"):
        return True
    if "commands" in exclusions and path.startswith(".opencode/commands/"):
        return True
    if "odoo_generator" in exclusions and path.startswith("src/fba/generator/"):
        return True
    if "schemas" in exclusions and path.startswith("schemas/"):
        return True
    if "fba_agent_observer" in exclusions and path == ".opencode/plugins/fba-agent-observer.ts":
        return True
    if "v1_runtime" in exclusions and path in {".factory/framework-state.json", ".factory/state.json", ".factory/events.jsonl"}:
        return True
    return False


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str):
                yield key
            yield from _iter_strings(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            yield from _iter_strings(child)
    elif isinstance(value, str):
        yield value


def _ordered_unique(values: Iterable[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique

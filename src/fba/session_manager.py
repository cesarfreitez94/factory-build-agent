from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import json


class ActionType(str, Enum):
    INVOKE_AGENT = "invoke_agent"
    ELICIT_ROUND = "elicit_round"
    TRANSITION = "transition"
    ASK_USER = "ask_user"
    COMPLETE = "complete"


@dataclass
class SessionQuery:
    query: str
    current_phase: str
    phase_status: str | None = None
    gate_result: dict | None = None
    user_choice: str | None = None


@dataclass
class SessionResponse:
    action: ActionType
    agent: str | None = None
    command: str | None = None
    input_files: list[str] | None = None
    questions_file: str | None = None
    answers_file: str | None = None
    to_phase: str | None = None
    gates_required: list[str] | None = None
    user_question: dict | None = None
    summary: str | None = None


class SessionManager:
    def __init__(self, project_dir: Path):
        self._project_dir = project_dir.resolve()
        self._factory_dir = self._project_dir / ".factory"
        self._schemas_dir = Path(__file__).resolve().parent.parent.parent / "schemas"

    def query(self, q: SessionQuery) -> SessionResponse:
        state = self._load_state()
        self._validate_query(q)
        return self._determine_action(state, q)

    def _load_state(self) -> dict:
        state_path = self._factory_dir / "state.json"
        if not state_path.exists():
            raise FileNotFoundError(f"state.json not found at {state_path}")
        return json.loads(state_path.read_text())

    def _validate_query(self, q: SessionQuery):
        schema_path = self._schemas_dir / "session_query.schema.json"
        if not schema_path.exists():
            return
        try:
            from jsonschema import validate
            schema = json.loads(schema_path.read_text())
            validate(instance=asdict(q), schema=schema)
        except Exception:
            pass

    def _determine_action(self, state: dict, q: SessionQuery) -> SessionResponse:
        phase = q.current_phase
        phase_config = state["phases"].get(phase, {})
        phase_type = phase_config.get("type")
        phase_status = q.phase_status or phase_config.get("status")

        if q.query == "user_decision":
            return self._handle_user_decision(q, state, phase, phase_config)

        if phase == "complete":
            return SessionResponse(action=ActionType.COMPLETE, summary="Pipeline completed")

        if phase_type == "interactive":
            return self._handle_interactive_phase(state, phase, phase_config, q)

        if phase_type == "batch":
            return self._handle_batch_phase(state, phase, phase_config, q)

        return SessionResponse(
            action=ActionType.INVOKE_AGENT,
            agent=phase_config.get("agent"),
            command=phase_config.get("command"),
        )

    def _handle_user_decision(self, q, state, phase, phase_config):
        if q.user_choice == "force":
            next_phase = self._find_next_phase(state, phase)
            return SessionResponse(
                action=ActionType.TRANSITION,
                to_phase=next_phase,
                summary=f"Force transition to {next_phase}",
            )
        elif q.user_choice == "retry":
            return SessionResponse(
                action=ActionType.INVOKE_AGENT,
                agent=phase_config.get("agent"),
                command=phase_config.get("command"),
                summary=f"Retrying {phase_config.get('agent')}",
            )
        else:
            return SessionResponse(
                action=ActionType.COMPLETE,
                summary="Pipeline cancelled by user",
            )

    def _handle_interactive_phase(self, state, phase, phase_config, q):
        questions_file = phase_config.get("questions_file")
        answers_file = phase_config.get("answers_file")
        output_file = phase_config.get("output_file")

        qf_exists = questions_file and (self._project_dir / questions_file).exists()
        af_exists = answers_file and (self._project_dir / answers_file).exists()
        of_exists = output_file and (self._project_dir / output_file).exists()

        if not of_exists:
            if not qf_exists:
                return SessionResponse(
                    action=ActionType.INVOKE_AGENT,
                    agent=phase_config.get("agent"),
                    command=phase_config.get("command"),
                    summary=f"Invoking {phase_config.get('agent')} to generate elicitation questions",
                )
            elif not af_exists:
                return SessionResponse(
                    action=ActionType.ELICIT_ROUND,
                    questions_file=questions_file,
                    answers_file=answers_file,
                    summary="Present questions to user and save answers",
                )
            else:
                return SessionResponse(
                    action=ActionType.INVOKE_AGENT,
                    agent=phase_config.get("agent"),
                    command=phase_config.get("command"),
                    input_files=[answers_file],
                    summary=f"Invoking {phase_config.get('agent')} to process user answers",
                )
        else:
            next_phase = self._find_next_phase(state, phase)
            return SessionResponse(
                action=ActionType.TRANSITION,
                to_phase=next_phase,
                summary=f"Interactive phase {phase} complete, transition to {next_phase}",
            )

    def _handle_batch_phase(self, state, phase, phase_config, q):
        phase_status = q.phase_status or phase_config.get("status")

        if phase_status == "pending":
            return SessionResponse(
                action=ActionType.INVOKE_AGENT,
                agent=phase_config.get("agent"),
                command=phase_config.get("command"),
                summary=f"Invoking {phase_config.get('agent')} for {phase} phase",
            )

        if phase_status in ("complete", "completed"):
            if q.query == "gate_failure" or (q.gate_result and not q.gate_result.get("passed", True)):
                return SessionResponse(
                    action=ActionType.ASK_USER,
                    user_question={
                        "header": f"Gate failed: {phase}",
                        "question": f"Gate validation for '{phase}' phase failed. What would you like to do?",
                        "options": [
                            {"label": "Force transition", "description": "Skip gate check and advance anyway"},
                            {"label": "Retry agent", "description": f"Re-invoke {phase_config.get('agent')} to fix issues"},
                            {"label": "Cancel", "description": "Stop the pipeline"},
                        ],
                    },
                    summary=f"Gate {phase} failed, asking user for decision",
                )
            else:
                next_phase = self._find_next_phase(state, phase)
                return SessionResponse(
                    action=ActionType.TRANSITION,
                    to_phase=next_phase,
                    gates_required=list(state.get("gates", {}).get(phase, {}).get("rules", [])),
                    summary=f"Batch phase {phase} complete, transition to {next_phase}",
                )

        return SessionResponse(
            action=ActionType.INVOKE_AGENT,
            agent=phase_config.get("agent"),
            command=phase_config.get("command"),
        )

    def _find_next_phase(self, state: dict, phase: str) -> str | None:
        transitions = state.get("valid_transitions", {})
        next_phases = transitions.get(phase, [])
        if next_phases:
            return next_phases[0]
        return None

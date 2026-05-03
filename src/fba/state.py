import json
from datetime import datetime, timezone
from pathlib import Path

import yaml


class StateManager:
    """Manages the Factory Build Agent state machine for a project."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self._factory_dir = self.project_dir / ".factory"
        self._opencode_dir = self.project_dir / ".opencode"

    @property
    def state_path(self) -> Path:
        return self._factory_dir / "state.json"

    @property
    def events_path(self) -> Path:
        return self._factory_dir / "events.jsonl"

    @property
    def orchestrator_path(self) -> Path:
        return self._opencode_dir / "agents" / "orchestrator.yaml"

    @property
    def current_phase(self) -> str:
        state = self.load()
        return state["current_phase"]

    def load(self) -> dict:
        if not self.state_path.exists():
            raise FileNotFoundError(
                f"State file not found: {self.state_path}. Run 'fba init' first."
            )
        return json.loads(self.state_path.read_text())

    def save(self, state: dict) -> None:
        self._factory_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False))

    def transition_to(self, phase: str) -> dict:
        state = self.load()
        current = state["current_phase"]
        valid = self._get_valid_transitions()

        if current not in valid:
            raise ValueError(f"No transitions defined from phase '{current}'")
        if phase not in valid[current]:
            allowed = ", ".join(valid[current])
            raise ValueError(
                f"Invalid transition: '{current}' -> '{phase}'."
                f" Allowed: {allowed}"
            )

        if current in state["phases"]:
            state["phases"][current]["status"] = "complete"

        state["current_phase"] = phase
        if phase in state["phases"]:
            state["phases"][phase]["status"] = "in_progress"
        self.save(state)

        self.record_event(
            "phase_transition",
            {"from": current, "to": phase},
        )

        return state

    def record_event(self, event_type: str, data: dict = None) -> None:
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
        }
        if data:
            event["data"] = data

        self._factory_dir.mkdir(parents=True, exist_ok=True)
        with open(self.events_path, "a") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def mark_phase(self, phase: str, status: str) -> None:
        state = self.load()
        if phase not in state["phases"]:
            raise ValueError(f"Unknown phase: {phase}")
        state["phases"][phase]["status"] = status
        self.save(state)

    def add_artifact(self, name: str, status: str = "draft") -> None:
        state = self.load()
        state["artifacts"][name] = {"status": status, "version": 1}
        self.save(state)

    def add_artifact_version(self, name: str) -> None:
        state = self.load()
        if name not in state["artifacts"]:
            raise ValueError(f"Unknown artifact: {name}")
        current = state["artifacts"][name].get("version", 0)
        state["artifacts"][name]["version"] = current + 1
        self.save(state)

    def _get_valid_transitions(self) -> dict:
        if not self.orchestrator_path.exists():
            return {}
        orchestrator = yaml.safe_load(self.orchestrator_path.read_text())
        return orchestrator.get("valid_transitions", {})

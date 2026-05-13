import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast


def _atomic_write(dest: Path, content: str) -> None:
    """Write content atomically using temp file + fsync + os.replace.

    If the process dies mid-write, the original file remains intact.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=str(dest.parent), prefix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(dest))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


class StateManager:
    """Manages the Factory Build Agent state machine for a project."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self._factory_dir = self.project_dir / ".factory"

    @property
    def state_path(self) -> Path:
        return self._factory_dir / "state.json"

    @property
    def events_path(self) -> Path:
        return self._factory_dir / "events.jsonl"

    @property
    def current_phase(self) -> str:
        state = self.load()
        return cast(str, state["current_phase"])

    def load(self) -> dict[str, Any]:
        if not self.state_path.exists():
            raise FileNotFoundError(
                f"State file not found: {self.state_path}. Run 'fba init' first."
            )
        return cast(dict[str, Any], json.loads(self.state_path.read_text()))

    def save(self, state: dict[str, Any]) -> None:
        content = json.dumps(state, indent=2, ensure_ascii=False)
        _atomic_write(self.state_path, content)

    def transition_to(self, phase: str, skip_gates: bool = False) -> dict[str, Any]:
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

        if not skip_gates:
            from fba.gate import GateError, GateRunner

            runner = GateRunner(self.project_dir)
            gate_result = runner.check_phase(current)
            if not gate_result.passed:
                raise GateError(gate_result)

        rollback_path = self._factory_dir / ".rollback_state.json"
        backup_made = False
        try:
            if self.state_path.exists():
                rollback_path.write_text(self.state_path.read_text())
                backup_made = True

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

            if backup_made and rollback_path.exists():
                rollback_path.unlink()

            return state

        except Exception as _exc:
            if backup_made and rollback_path.exists():
                try:
                    _atomic_write(self.state_path, rollback_path.read_text())
                    rollback_path.unlink()
                except Exception as rollback_error:
                    try:
                        error_log = self._factory_dir / ".rollback_error.log"
                        error_msg = (
                            f"CRITICAL: Rollback failed during transition "
                            f"'{current}' -> '{phase}'. "
                            f"Original error: {_exc}. "
                            f"Rollback error: {rollback_error}"
                        )
                        error_log.write_text(
                            f"[{datetime.now(timezone.utc).isoformat()}] {error_msg}\n"
                        )
                    except OSError:
                        pass
            raise

    def has_gate_passed(self, phase: str | None = None) -> bool:
        if phase is None:
            phase = self.current_phase
        from fba.gate import GateRunner

        runner = GateRunner(self.project_dir)
        result = runner.check_phase(phase)
        return result.passed

    def record_event(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        event: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
        }
        if data:
            event["data"] = data

        self._factory_dir.mkdir(parents=True, exist_ok=True)
        with open(self.events_path, "a") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

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

    def _get_valid_transitions(self) -> dict[str, list[str]]:
        state = self.load()
        return cast(dict[str, list[str]], state.get("valid_transitions", {}))

"""Tests for agent definition YAML files."""

from pathlib import Path

import pytest
import yaml

AGENTS_DIR = Path(__file__).resolve().parent.parent / "templates" / ".opencode" / "agents"


def _agent_paths():
    """Yield (agent_name, path) for all agent YAML files."""
    if not AGENTS_DIR.is_dir():
        raise FileNotFoundError(f"Agents directory not found: {AGENTS_DIR}")
    for yaml_file in sorted(AGENTS_DIR.glob("*.yaml")):
        yield yaml_file.stem, yaml_file


def _load_agents():
    """Load all agent YAML definitions."""
    agents = {}
    for name, path in _agent_paths():
        agents[name] = yaml.safe_load(path.read_text())
    return agents


REQUIRED_FIELDS = {"name", "role", "description", "methodology", "tools", "prompt"}


class TestAgentDefinitionsExist:
    def test_orchestrator_exists(self):
        assert (AGENTS_DIR / "orchestrator.yaml").is_file()

    def test_elicitador_exists(self):
        assert (AGENTS_DIR / "elicitador.yaml").is_file()


class TestAgentYAMLValid:
    @pytest.mark.parametrize("agent_name,agent_def", [
        pytest.param(name, defn, id=name)
        for name, defn in _load_agents().items()
    ])
    def test_agent_has_required_fields(self, agent_name, agent_def):
        missing = REQUIRED_FIELDS - set(agent_def.keys())
        assert not missing, f"Agent '{agent_name}' missing fields: {missing}"

    @pytest.mark.parametrize("agent_name,agent_def", [
        pytest.param(name, defn, id=name)
        for name, defn in _load_agents().items()
    ])
    def test_agent_has_non_empty_prompt(self, agent_name, agent_def):
        assert len(agent_def.get("prompt", "").strip()) > 50, \
            f"Agent '{agent_name}' prompt is too short or empty"

    @pytest.mark.parametrize("agent_name,agent_def", [
        pytest.param(name, defn, id=name)
        for name, defn in _load_agents().items()
    ])
    def test_agent_has_valid_methodology(self, agent_name, agent_def):
        valid = {"BABOK", "JTBD", "DDD", "User Story Mapping", "None"}
        assert agent_def.get("methodology") in valid, \
            f"Agent '{agent_name}' has invalid methodology: {agent_def.get('methodology')}"

    @pytest.mark.parametrize("agent_name,agent_def", [
        pytest.param(name, defn, id=name)
        for name, defn in _load_agents().items()
    ])
    def test_agent_tools_are_known(self, agent_name, agent_def):
        known_tools = {"read", "write", "bash", "glob", "grep", "task", "edit"}
        tools = set(agent_def.get("tools", []))
        unknown = tools - known_tools
        assert not unknown, \
            f"Agent '{agent_name}' has unknown tools: {unknown}"

    @pytest.mark.parametrize("agent_name,agent_def", [
        pytest.param(name, defn, id=name)
        for name, defn in _load_agents().items()
    ])
    def test_agent_name_matches_filename(self, agent_name, agent_def):
        assert agent_def["name"] == agent_name, \
            f"Agent '{agent_name}' has 'name' field '{agent_def['name']}'"


class TestElicitadorAgent:
    def test_elicitador_has_babok_prompt(self):
        agent = yaml.safe_load((AGENTS_DIR / "elicitador.yaml").read_text())
        prompt = agent["prompt"]
        assert "BABOK" in prompt
        assert "elicitation" in prompt.lower()
        assert "Stakeholders" in prompt or "stakeholders" in prompt.lower()
        assert "functional_requirements" in prompt
        assert "non_functional_requirements" in prompt

    def test_elicitador_has_output_phase(self):
        agent = yaml.safe_load((AGENTS_DIR / "elicitador.yaml").read_text())
        assert agent.get("output_phase") == "elicitation"

    def test_elicitador_defines_output_artifacts(self):
        agent = yaml.safe_load((AGENTS_DIR / "elicitador.yaml").read_text())
        assert "output_artifacts" in agent
        artifacts = [a["name"] for a in agent["output_artifacts"]]
        assert "context/elicitation.json" in artifacts


class TestOrchestratorValidTransitions:
    def test_valid_transitions_use_known_phases(self):
        orchestrator = yaml.safe_load(
            (AGENTS_DIR / "orchestrator.yaml").read_text()
        )
        phases = {p["name"] for p in orchestrator["phases"]}
        phase_keys = {p.get("phase_key", p["name"]) for p in orchestrator["phases"]}

        all_phases = phases | phase_keys | {"init", "complete"}

        transitions = orchestrator.get("valid_transitions", {})
        for from_phase, to_list in transitions.items():
            assert from_phase in all_phases, f"Unknown from_phase '{from_phase}'"
            for to_phase in to_list:
                assert to_phase in all_phases | {"complete"}, \
                    f"Unknown to_phase '{to_phase}' in transition"

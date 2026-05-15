"""Tests for the project-local OpenCode agent observer plugin."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_PATH = ROOT / ".opencode" / "plugins" / "fba-agent-observer.ts"


def test_agent_observer_plugin_exists():
    assert PLUGIN_PATH.is_file()


def test_agent_observer_only_indexes_framework_agents():
    text = PLUGIN_PATH.read_text()

    assert 'const OBSERVED_AGENTS_DIRECTORY = ".opencode/agents"' in text
    assert "templates/.opencode/agents" in text
    assert "readdir(observedAgentsPath)" in text
    assert "templates/.opencode/agents/*.md" not in text
    assert "templates/.opencode/agents/`" not in text


def test_agent_observer_keeps_sensitive_capture_disabled_by_default():
    text = PLUGIN_PATH.read_text()

    assert "captureRawEvents: false" in text
    assert "captureToolOutput: false" in text
    assert "captureReasoningText: false" in text
    assert "captureMessageText: false" in text
    assert "captureAgentPromptSnapshots: true" in text


def test_agent_observer_writes_expected_observability_artifacts():
    text = PLUGIN_PATH.read_text()

    assert 'const OBSERVABILITY_DIRECTORY = ".factory/observability"' in text
    assert "agent-index.json" in text
    assert "sessions" in text
    assert "reports" in text
    assert "Cost by Agent" in text
    assert "Invocations" in text

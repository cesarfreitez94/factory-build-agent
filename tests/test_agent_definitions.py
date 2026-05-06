"""Tests for agent definition Markdown files."""

from pathlib import Path

import pytest
import yaml

AGENTS_DIR = Path(__file__).resolve().parent.parent / "templates" / ".opencode" / "agents"


def _agent_paths():
    """Yield (agent_name, path) for all agent .md files."""
    if not AGENTS_DIR.is_dir():
        raise FileNotFoundError(f"Agents directory not found: {AGENTS_DIR}")
    for md_file in sorted(AGENTS_DIR.glob("*.md")):
        yield md_file.stem, md_file


def _load_agent_md(path):
    """Parse frontmatter and body from an agent .md file."""
    text = path.read_text()
    parts = text.split("---", 2)
    if len(parts) < 3 or not parts[0].strip() == "":
        raise ValueError(f"Invalid frontmatter in {path}")
    frontmatter = yaml.safe_load(parts[1])
    body = parts[2].strip()
    return frontmatter, body


def _load_all_agents():
    """Load all agent .md definitions."""
    agents = {}
    for name, path in _agent_paths():
        agents[name] = _load_agent_md(path)
    return agents


EXPECTED_AGENTS = {"elicitador", "documentador", "orchestrator", "planificador", "revisor_artefactos", "validador_semantico", "code-generator", "tester_qa", "revisor_codigo", "ci_cd_manager"}


class TestAgentDefinitionsExist:
    def test_agents_directory_exists(self):
        assert AGENTS_DIR.is_dir()

    def test_no_yaml_files_remain(self):
        yaml_files = list(AGENTS_DIR.glob("*.yaml"))
        assert not yaml_files, f"Stale .yaml files found: {[f.name for f in yaml_files]}"

    def test_orchestrator_md_exists(self):
        assert (AGENTS_DIR / "orchestrator.md").is_file()

    def test_elicitador_md_exists(self):
        assert (AGENTS_DIR / "elicitador.md").is_file()

    def test_documentador_md_exists(self):
        assert (AGENTS_DIR / "documentador.md").is_file()

    def test_planificador_md_exists(self):
        assert (AGENTS_DIR / "planificador.md").is_file()

    def test_tester_qa_md_exists(self):
        assert (AGENTS_DIR / "tester_qa.md").is_file()

    def test_revisor_codigo_md_exists(self):
        assert (AGENTS_DIR / "revisor_codigo.md").is_file()

    def test_only_expected_agents_exist(self):
        found = {f.stem for f in AGENTS_DIR.glob("*.md")}
        assert found == EXPECTED_AGENTS, f"Unexpected agents: {found - EXPECTED_AGENTS}"


class TestAgentFrontmatter:
    @pytest.mark.parametrize("agent_name,frontmatter,body", [
        pytest.param(name, fm, b, id=name)
        for name, (fm, b) in _load_all_agents().items()
    ])
    def test_agent_has_description(self, agent_name, frontmatter, body):
        assert "description" in frontmatter, f"'{agent_name}' missing description"
        assert len(frontmatter["description"]) > 20

    @pytest.mark.parametrize("agent_name,frontmatter,body", [
        pytest.param(name, fm, b, id=name)
        for name, (fm, b) in _load_all_agents().items()
    ])
    def test_agent_has_mode(self, agent_name, frontmatter, body):
        assert "mode" in frontmatter, f"'{agent_name}' missing mode"
        assert frontmatter["mode"] in ("primary", "subagent", "all")

    @pytest.mark.parametrize("agent_name,frontmatter,body", [
        pytest.param(name, fm, b, id=name)
        for name, (fm, b) in _load_all_agents().items()
    ])
    def test_agent_has_permissions(self, agent_name, frontmatter, body):
        assert "permission" in frontmatter, f"'{agent_name}' missing permission"

    @pytest.mark.parametrize("agent_name,frontmatter,body", [
        pytest.param(name, fm, b, id=name)
        for name, (fm, b) in _load_all_agents().items()
    ])
    def test_agent_has_body_content(self, agent_name, frontmatter, body):
        assert len(body) > 100, \
            f"Agent '{agent_name}' body is too short ({len(body)} chars)"


class TestAgentModes:
    def test_orchestrator_is_primary(self):
        frontmatter, _ = _load_agent_md(AGENTS_DIR / "orchestrator.md")
        assert frontmatter["mode"] == "primary"

    def test_elicitador_is_subagent(self):
        frontmatter, _ = _load_agent_md(AGENTS_DIR / "elicitador.md")
        assert frontmatter["mode"] == "subagent"

    def test_documentador_is_subagent(self):
        frontmatter, _ = _load_agent_md(AGENTS_DIR / "documentador.md")
        assert frontmatter["mode"] == "subagent"


class TestElicitadorAgent:
    def test_elicitador_has_babok_prompt(self):
        _, body = _load_agent_md(AGENTS_DIR / "elicitador.md")
        assert "BABOK" in body
        assert "elicitation" in body.lower()
        assert "Stakeholders" in body or "stakeholders" in body.lower()
        assert "functional_requirements" in body
        assert "non_functional_requirements" in body

    def test_elicitador_mentions_elicitation_json(self):
        _, body = _load_agent_md(AGENTS_DIR / "elicitador.md")
        assert ".factory/context/elicitation.json" in body

    def test_elicitador_mentions_transition(self):
        _, body = _load_agent_md(AGENTS_DIR / "elicitador.md")
        assert "fba transition elicitation" in body
        assert "fba record elicitation_complete" in body


class TestDocumentadorAgent:
    def test_documentador_has_prd_prompt(self):
        _, body = _load_agent_md(AGENTS_DIR / "documentador.md")
        assert "prd.json" in body
        assert "prd.md" in body
        assert "validation" in body.lower()
        assert "functional_requirements" in body

    def test_documentador_mentions_prd_json(self):
        _, body = _load_agent_md(AGENTS_DIR / "documentador.md")
        assert ".factory/prd.json" in body

    def test_documentador_mentions_validate(self):
        _, body = _load_agent_md(AGENTS_DIR / "documentador.md")
        assert "fba validate prd" in body

    def test_documentador_mentions_transition(self):
        _, body = _load_agent_md(AGENTS_DIR / "documentador.md")
        assert "fba transition documentation" in body


class TestPlanificadorAgent:
    def test_planificador_has_sdd_prompt(self):
        _, body = _load_agent_md(AGENTS_DIR / "planificador.md")
        assert "sdd.json" in body
        assert "sdd.md" in body
        assert "plan.md" in body
        assert "Odoo v18" in body
        assert "traceability" in body.lower()

    def test_planificador_mentions_sdd_json(self):
        _, body = _load_agent_md(AGENTS_DIR / "planificador.md")
        assert ".factory/sdd.json" in body

    def test_planificador_mentions_validate(self):
        _, body = _load_agent_md(AGENTS_DIR / "planificador.md")
        assert "fba validate sdd" in body

    def test_planificador_mentions_transition(self):
        _, body = _load_agent_md(AGENTS_DIR / "planificador.md")
        assert "fba transition planning" in body

    def test_planificador_has_odoo_conventions(self):
        _, body = _load_agent_md(AGENTS_DIR / "planificador.md")
        assert "models" in body.lower()
        assert "views" in body.lower()
        assert "security" in body.lower()
        assert "dependencies" in body.lower()

    def test_planificador_has_traceability_rules(self):
        _, body = _load_agent_md(AGENTS_DIR / "planificador.md")
        assert "traceability_matrix" in body
        assert "PRD requirement" in body

    def test_planificador_mentions_prd_input(self):
        _, body = _load_agent_md(AGENTS_DIR / "planificador.md")
        assert ".factory/prd.json" in body


class TestOrchestratorAgent:
    def test_orchestrator_has_phase_flow(self):
        _, body = _load_agent_md(AGENTS_DIR / "orchestrator.md")
        assert "Phase Flow" in body or "phase" in body.lower()
        assert "elicitation" in body.lower()
        assert "construction" in body.lower()

    def test_orchestrator_has_milestone_completion_protocol(self):
        _, body = _load_agent_md(AGENTS_DIR / "orchestrator.md")
        assert "Milestone Completion Protocol" in body
        assert "DO NOT open the PR" in body
        assert "explicitly confirms" in body

    def test_orchestrator_mentions_state_json(self):
        _, body = _load_agent_md(AGENTS_DIR / "orchestrator.md")
        assert ".factory/state.json" in body


class TestTesterQAAgent:
    def test_tester_qa_has_test_prompt(self):
        _, body = _load_agent_md(AGENTS_DIR / "tester_qa.md")
        assert "schema.json" in body
        assert "TestCase" in body
        assert "test_report.json" in body
        assert "test_report.md" in body
        assert "test_models.py" in body
        assert "test_views.py" in body
        assert "test_security.py" in body
        assert "test_integration.py" in body

    def test_tester_qa_mentions_test_report_json(self):
        _, body = _load_agent_md(AGENTS_DIR / "tester_qa.md")
        assert ".factory/test_report.json" in body

    def test_tester_qa_mentions_state_update(self):
        _, body = _load_agent_md(AGENTS_DIR / "tester_qa.md")
        assert "testing" in body

    def test_tester_qa_mentions_events(self):
        _, body = _load_agent_md(AGENTS_DIR / "tester_qa.md")
        assert "test_complete" in body

    def test_tester_qa_has_odoo_conventions(self):
        _, body = _load_agent_md(AGENTS_DIR / "tester_qa.md")
        assert "TransactionCase" in body
        assert "setUp" in body
        assert "sudo" in body
        assert "with_user" in body


class TestRevisorCodigoAgent:
    def test_revisor_codigo_has_review_prompt(self):
        _, body = _load_agent_md(AGENTS_DIR / "revisor_codigo.md")
        assert "schema.json" in body
        assert "prd.json" in body
        assert "sdd.json" in body
        assert "review_report.json" in body
        assert "review_report.md" in body
        assert "quality" in body.lower()
        assert "security" in body.lower()
        assert "spec" in body.lower()

    def test_revisor_codigo_mentions_review_report_json(self):
        _, body = _load_agent_md(AGENTS_DIR / "revisor_codigo.md")
        assert ".factory/review_report.json" in body

    def test_revisor_codigo_mentions_odoo_v18_conventions(self):
        _, body = _load_agent_md(AGENTS_DIR / "revisor_codigo.md")
        assert "Odoo v18" in body
        assert "PEP8" in body
        assert "list" in body
        assert "ACL" in body

    def test_revisor_codigo_has_severity_classification(self):
        _, body = _load_agent_md(AGENTS_DIR / "revisor_codigo.md")
        assert "critical" in body.lower()
        assert "warning" in body.lower()

    def test_revisor_codigo_mentions_events(self):
        _, body = _load_agent_md(AGENTS_DIR / "revisor_codigo.md")
        assert "review_complete" in body

    def test_revisor_codigo_has_prohibited_patterns(self):
        _, body = _load_agent_md(AGENTS_DIR / "revisor_codigo.md")
        assert "<tree>" in body.replace("</tree>", "") or "tree" in body.lower()
        assert "attrs=" in body

    def test_revisor_codigo_mentions_state_update(self):
        _, body = _load_agent_md(AGENTS_DIR / "revisor_codigo.md")
        assert "review" in body.lower() and "phases" in body


class TestCicdManagerAgent:
    def test_cicd_manager_md_exists(self):
        assert (AGENTS_DIR / "ci_cd_manager.md").is_file()

    def test_cicd_manager_has_ship_prompt(self):
        _, body = _load_agent_md(AGENTS_DIR / "ci_cd_manager.md")
        assert "GitHub Actions" in body
        assert "factory-ci.yml" in body
        assert "ship_report.json" in body
        assert "ship_report.md" in body

    def test_cicd_manager_mentions_ship_report_json(self):
        _, body = _load_agent_md(AGENTS_DIR / "ci_cd_manager.md")
        assert ".factory/ship_report.json" in body

    def test_cicd_manager_mentions_workflow(self):
        _, body = _load_agent_md(AGENTS_DIR / "ci_cd_manager.md")
        assert ".github/workflows/factory-ci.yml" in body

    def test_cicd_manager_mentions_complete(self):
        _, body = _load_agent_md(AGENTS_DIR / "ci_cd_manager.md")
        assert "complete" in body.lower()
        assert "current_phase" in body

    def test_cicd_manager_has_release_readiness_check(self):
        _, body = _load_agent_md(AGENTS_DIR / "ci_cd_manager.md")
        assert "release readiness" in body.lower() or "release ready" in body.lower()
        assert "test_report.json" in body
        assert "review_report.json" in body

    def test_cicd_manager_mentions_events(self):
        _, body = _load_agent_md(AGENTS_DIR / "ci_cd_manager.md")
        assert "ship_complete" in body

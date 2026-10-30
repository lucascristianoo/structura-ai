"""
Automated Tests for Autonomous Multi-Agent Council (User, Engineer, Market Research).
"""
import pytest
from httpx import AsyncClient, ASGITransport
from structura_ai.main import app
from structura_ai.agents.user_agent import UserAdversarialAgent
from structura_ai.agents.engineer_agent import EngineerCuratorAgent
from structura_ai.agents.agent_council import AgentCouncilOrchestrator


def test_user_adversarial_agent_run():
    """Validates that User Agent executes adversarial tests and logs complaints."""
    agent = UserAdversarialAgent()
    report = agent.run_comprehensive_audit()

    assert report["total_benchmarks_evaluated"] >= 6
    assert report["total_complaints_filed"] >= 3
    assert len(report["tested_features"]) >= 4
    assert "cloning_feasibility_score" in report["ip_probe_status"]


def test_engineer_curator_agent_decisions():
    """Validates that Engineer Agent reviews complaints and applies 'Menos é Mais'."""
    user_agent = UserAdversarialAgent()
    user_report = user_agent.run_comprehensive_audit()

    eng_agent = EngineerCuratorAgent()
    eng_report = eng_agent.review_user_agent_feedback(user_report)

    assert eng_report["calibration_status"] == "STABLE & ACCURATE"
    assert eng_report["statistics"]["features_kept"] > 0
    assert eng_report["statistics"]["features_pruned"] > 0
    assert len(eng_report["curator_decisions"]) == len(user_report["complaints"])


def test_agent_council_orchestrator():
    """Validates full council session orchestration and markdown report generation."""
    session = AgentCouncilOrchestrator.run_council_session()

    assert session["status"] == "success"
    assert "markdown_dossier" in session
    assert "Conselho de Agentes" in session["markdown_dossier"]
    assert session["summary_verdict"]["core_20_percent_integrity"] == "100% PRESERVED & VALIDATED"


@pytest.mark.asyncio
async def test_council_api_routes():
    """Validates /api/agents/council/run and /api/agents/council/report endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # POST run
        resp = await client.post("/api/agents/council/run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "user_adversarial_report" in data
        assert "engineer_curator_report" in data

        # GET markdown report
        rep_resp = await client.get("/api/agents/council/report")
        assert rep_resp.status_code == 200
        assert "# 🏛️ Conselho de Agentes" in rep_resp.text

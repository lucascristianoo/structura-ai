"""
API Routes for Autonomous Multi-Agent Council (User, Engineer, Market Research).
"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from structura_ai.agents.agent_council import AgentCouncilOrchestrator

router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.post("/council/run")
async def run_council_deliberation():
    """
    Triggers autonomous deliberation loop between User Adversarial Agent,
    Engineer Curator Agent, and Market Research Agent.
    """
    session = AgentCouncilOrchestrator.run_council_session()
    return session


@router.get("/council/report", response_class=PlainTextResponse)
async def get_council_markdown_report():
    """
    Returns the latest synthesized markdown audit dossier from the Agent Council.
    """
    session = AgentCouncilOrchestrator.run_council_session()
    return session["markdown_dossier"]

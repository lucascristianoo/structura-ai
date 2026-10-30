"""
Automated Tests for Solow Productivity Matrix & Pareto (20/60) Service.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from structura_ai.main import app
from structura_ai.services.solow_matrix import SolowMatrixService


def test_solow_growth_model():
    model = SolowMatrixService.get_solow_growth_model()
    assert "production_function" in model
    assert "Y = A(t)" in model["production_function"]
    assert model["solow_residual_gain_tfp"]["traditional_workflow_cycle_days"] == 21.0
    assert model["solow_residual_gain_tfp"]["structura_ai_cycle_seconds"] <= 2.0


def test_competitor_matrix():
    matrix = SolowMatrixService.get_competitor_comparison_matrix()
    names = [c["solution"] for c in matrix]
    assert "Structura.AI" in names
    assert "Finch 3D" in names
    assert "TestFit" in names
    assert "Karamba3D / Grasshopper" in names
    assert "TQS / Eberick" in names


def test_pareto_essential_features():
    pareto = SolowMatrixService.get_pareto_essential_features()
    assert len(pareto["the_essential_20_percent"]) >= 4
    killer = SolowMatrixService.get_signature_killer_feature()
    assert "Instant Structural Truth Slider" in killer["short_brand_name"]


@pytest.mark.asyncio
async def test_solow_matrix_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/analysis/solow-matrix")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "growth_model" in data
        assert "competitor_matrix" in data
        assert "signature_killer_feature" in data

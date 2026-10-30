"""
Automated Tests for BOM, SINAPI 2026 Cost Engine & Embodied Carbon (A1-A3).
"""
import pytest
from httpx import AsyncClient, ASGITransport
from structura_ai.main import app
from structura_ai.physics.cost_carbon_engine import CostCarbonEngine


def test_bom_calculation_standard_rc():
    """Validates baseline material takeoff, cost and carbon emissions."""
    res = CostCarbonEngine.calculate_bom_and_cost(
        span_length_m=10.0,
        beam_height_cm=30.0,
        beam_width_cm=20.0,
        concrete_fck_mpa=30.0,
        system_type="standard_rc"
    )

    assert res["quantities"]["concrete_volume_total_m3"] > 0
    assert res["quantities"]["steel_rebar_ca50_kg"] > 0
    assert res["financial_sinapi_2026"]["total_estimated_brl"] > 1000.0
    assert res["financial_sinapi_2026"]["currency"] == "BRL (R$)"
    assert res["embodied_carbon_a1_a3"]["total_emissions_kg_co2"] > 500.0


def test_bom_variant_savings():
    """Validates that post-tensioning and waffle slabs reflect mass reduction in carbon and materials."""
    standard = CostCarbonEngine.calculate_bom_and_cost(span_length_m=12.0, system_type="standard_rc")
    pt = CostCarbonEngine.calculate_bom_and_cost(span_length_m=12.0, system_type="post_tensioned")
    waffle = CostCarbonEngine.calculate_bom_and_cost(span_length_m=12.0, system_type="waffle")

    # Post-tensioning saves concrete volume compared to standard solid RC
    assert pt["quantities"]["concrete_volume_total_m3"] < standard["quantities"]["concrete_volume_total_m3"]
    # Waffle slab voids reduce slab concrete volume
    assert waffle["quantities"]["concrete_slab_m3"] < standard["quantities"]["concrete_slab_m3"]


@pytest.mark.asyncio
async def test_micro_adjust_sliders_with_bom():
    """Validates the /api/analysis/micro-adjust endpoint returns real-time BOM, cost, and DSM results."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/analysis/micro-adjust", json={
            "span_length_m": 9.0,
            "beam_height_cm": 35.0,
            "beam_width_cm": 20.0,
            "selected_variant": 1
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["selected_variant"] == 1
        assert data["system_type"] == "post_tensioned"
        assert "bom_and_cost" in data
        assert "dsm_analysis" in data
        assert data["bom_and_cost"]["financial_sinapi_2026"]["total_estimated_brl"] > 0

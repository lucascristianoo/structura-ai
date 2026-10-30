"""
Automated Tests for Scenario 1 (Needs Redesign) vs Scenario 2 (Compliant Benchmark) Projects.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from structura_ai.main import app
from structura_ai.physics.structural_core import StructuralCoreEngine
from structura_ai.services.sample_projects import SAMPLE_PRESETS, get_presets_by_scenario
from structura_ai.cad.cad_ingestor import CadIngestor


def test_scenario_1_benchmarks_fail_and_require_redesign():
    """All Scenario 1 presets must fail NBR 6118 limits and trigger failure reasons."""
    s1_presets = get_presets_by_scenario(1)
    assert len(s1_presets) >= 3

    for preset in s1_presets:
        eval_res = StructuralCoreEngine.evaluate_structure(
            span_length_m=preset["span_length_m"],
            cantilever_length_m=preset["cantilever_length_m"],
            beam_height_cm=preset["beam_height_cm"],
            beam_width_cm=preset["beam_width_cm"],
            column_height_m=preset["column_height_m"],
            column_section_cm=preset["column_section_cm"],
            dead_load_kpa=preset["dead_load_kpa"],
            live_load_kpa=preset["live_load_kpa"],
            concrete_fck_mpa=preset["concrete_fck_mpa"]
        )

        assert eval_res["is_physically_viable"] is False, f"Preset {preset['title']} should have failed!"
        assert len(eval_res["failure_reasons"]) > 0
        assert eval_res["structural_score"] < 75.0


def test_scenario_2_benchmarks_pass_with_high_score():
    """All Scenario 2 presets must pass NBR 6118 limits without failure reasons."""
    s2_presets = get_presets_by_scenario(2)
    assert len(s2_presets) >= 3

    for preset in s2_presets:
        eval_res = StructuralCoreEngine.evaluate_structure(
            span_length_m=preset["span_length_m"],
            cantilever_length_m=preset["cantilever_length_m"],
            beam_height_cm=preset["beam_height_cm"],
            beam_width_cm=preset["beam_width_cm"],
            column_height_m=preset["column_height_m"],
            column_section_cm=preset["column_section_cm"],
            dead_load_kpa=preset["dead_load_kpa"],
            live_load_kpa=preset["live_load_kpa"],
            concrete_fck_mpa=preset["concrete_fck_mpa"]
        )

        assert eval_res["is_physically_viable"] is True, f"Preset {preset['title']} should have passed!"
        assert len(eval_res["failure_reasons"]) == 0
        assert eval_res["structural_score"] >= 90.0
        assert eval_res["max_deflection_mm"] <= eval_res["allowable_deflection_mm"]


@pytest.mark.asyncio
async def test_load_scenario_2_cad_sample():
    """Validates loading the Scenario 2 compliant sample DXF from downloads/test_samples/."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/projects/samples/load/sobrado_grid_racional_5m.dxf")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["is_viable"] is True  # 5m span with 45cm beam must pass!
        assert data["score"] >= 90.0

"""
Automated Tests for Direct Stiffness Method (DSM) Frame Matrix Solver & Voronoi Engine.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from structura_ai.main import app
from structura_ai.physics.dsm_solver import DSMSolver


def test_dsm_matrix_solver_portal_frame():
    """Validates 2D portal frame matrix solution with Euler-Bernoulli beam elements."""
    result = DSMSolver.solve_portal_frame(
        span_length_m=10.0,
        cantilever_length_m=0.0,
        beam_height_cm=30.0,
        beam_width_cm=20.0,
        column_height_m=3.2,
        column_section_cm=20.0,
        distributed_load_kn_m=25.0
    )

    assert result["solver"] == "Direct Stiffness Method (DSM) 2D Plane Frame"
    assert result["degrees_of_freedom"] == 6
    assert result["exact_midspan_deflection_mm"] > 0
    assert result["internal_moments_knm"]["midspan_positive_m"] > 0
    assert result["reactions_kn"]["column1_vertical_reaction_kn"] > 0


def test_voronoi_tributary_two_way_slab():
    """Validates 45-degree plastic hinge yield line Voronoi load distribution."""
    # Two-way slab (ratio 10/6 = 1.67 < 2.0)
    res = DSMSolver.calculate_voronoi_tributary(bay_x_m=10.0, bay_y_m=6.0, slab_surface_load_kpa=6.5)
    assert "Duas Direções" in res["behavior"]
    assert res["tributary_areas_m2"]["trapezoidal_long_beam_m2"] > 0
    assert res["tributary_areas_m2"]["triangular_short_beam_m2"] > 0
    assert res["equivalent_uniform_loads_kn_m"]["long_beam_load_kn_m"] > 0


def test_voronoi_tributary_one_way_slab():
    """Validates one-way slab partition when aspect ratio >= 2.0."""
    res = DSMSolver.calculate_voronoi_tributary(bay_x_m=12.0, bay_y_m=5.0, slab_surface_load_kpa=6.5)
    assert "Uma Direção" in res["behavior"]
    assert res["tributary_areas_m2"]["triangular_short_beam_m2"] == 0.0


@pytest.mark.asyncio
async def test_dsm_solve_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/analysis/dsm-solve", json={
            "span_length_m": 8.0,
            "beam_height_cm": 35.0,
            "beam_width_cm": 20.0,
            "distributed_load_kn_m": 22.0
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "dsm_frame_solution" in data
        assert "voronoi_tributary" in data

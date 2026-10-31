"""
Edge Case Tests for Structura.AI Physics, Canvas & Upload Endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from structura_ai.main import app
from structura_ai.physics.structural_core import StructuralCoreEngine


def test_clamped_boundary_values():
    res_zero = StructuralCoreEngine.evaluate_structure(
        span_length_m=0.5,
        cantilever_length_m=0.0,
        beam_height_cm=10.0,
        beam_width_cm=10.0,
    )
    assert res_zero["structural_score"] > 0
    assert res_zero["max_deflection_mm"] >= 0.0


def test_extreme_cantilever_failure():
    res = StructuralCoreEngine.evaluate_structure(
        span_length_m=8.0,
        cantilever_length_m=6.0,
        beam_height_cm=25.0,
        beam_width_cm=20.0,
    )
    assert res["is_physically_viable"] is False
    assert res["cantilever_stability_factor"] < 0.5
    assert any("Balanço crítico" in f for f in res["failure_reasons"])


@pytest.mark.asyncio
async def test_canvas_analysis_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "title": "Planta Baixa Croqui Teste",
            "scale_pixels_per_meter": 40.0,
            "elements": [
                {"id": "c1", "type": "column", "start": {"x": 100, "y": 100}},
                {"id": "c2", "type": "column", "start": {"x": 500, "y": 100}},
                {"id": "b1", "type": "beam", "start": {"x": 100, "y": 100}, "end": {"x": 500, "y": 100}},
                {"id": "cant1", "type": "cantilever", "start": {"x": 500, "y": 100}, "end": {"x": 660, "y": 100}},
            ],
        }
        resp = await client.post("/api/analysis/canvas", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        geom = data["extracted_geometry"]
        assert geom["columns_detected"] == 2
        assert geom["calculated_max_span_m"] == 10.0
        assert geom["calculated_cantilever_m"] == 4.0


@pytest.mark.asyncio
async def test_multipart_upload_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {
            "file": (
                "blueprint_test.png",
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82",
                "image/png",
            )
        }
        data = {
            "title": "Projeto Upload Croqui",
            "author_architect": "Studio Zaha",
            "category": "Residencial",
            "span_length_m": "9.0",
            "cantilever_length_m": "3.0",
            "beam_height_cm": "25.0",
            "beam_width_cm": "20.0",
        }
        resp = await client.post("/api/projects/upload", data=data, files=files)
        assert resp.status_code == 200
        res_data = resp.json()
        assert res_data["status"] == "success"
        assert "project_id" in res_data


@pytest.mark.asyncio
async def test_canvas_zero_cantilever():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "title": "Planta Sem Balanco",
            "scale_pixels_per_meter": 40.0,
            "elements": [
                {"id": "c1", "type": "column", "start": {"x": 100, "y": 100}},
                {"id": "c2", "type": "column", "start": {"x": 420, "y": 100}},
                {"id": "b1", "type": "beam", "start": {"x": 100, "y": 100}, "end": {"x": 420, "y": 100}},
            ],
        }
        resp = await client.post("/api/analysis/canvas", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["extracted_geometry"]["calculated_cantilever_m"] == 0.0


def test_small_dead_load_safety():
    res = StructuralCoreEngine.evaluate_structure(
        span_length_m=6.0,
        cantilever_length_m=0.0,
        beam_height_cm=40.0,
        beam_width_cm=20.0,
        dead_load_kpa=1.0,
        live_load_kpa=1.5,
    )
    assert res["max_deflection_mm"] > 0
    assert res["max_bending_moment_knm"] > 0
    assert res["structural_score"] > 0

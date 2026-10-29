"""
Integration Tests for FastAPI Monolithic Endpoints.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from structura_ai.main import app
from structura_ai.database import init_db

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await init_db()

@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "Structura.AI"

@pytest.mark.asyncio
async def test_quick_calc_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "span_length_m": 10.0,
            "cantilever_length_m": 3.5,
            "beam_height_cm": 25.0,
            "beam_width_cm": 20.0,
            "column_section_cm": 20.0,
            "column_height_m": 3.2,
            "category": "Residencial"
        }
        response = await client.post("/api/analysis/quick-calc", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["evaluation"]["is_physically_viable"] is False
        assert len(data["variants"]) == 5

@pytest.mark.asyncio
async def test_preset_load_and_export():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Load preset
        resp = await client.post("/api/projects/preset/residencia_vao_livre_critico")
        assert resp.status_code == 200
        data = resp.json()
        project_id = data["project_id"]

        # View project page
        view_resp = await client.get(f"/project/{project_id}")
        assert view_resp.status_code == 200
        assert "Laudo Técnico" in view_resp.text

        # Export HTML report
        export_resp = await client.get(f"/api/export/{project_id}/report.html")
        assert export_resp.status_code == 200
        assert "STRUCTURA.AI — Laudo de Compatibilização Físico-Arquitetônica" in export_resp.text

        # Export Variant 1 SVG
        svg_resp = await client.get(f"/api/export/{project_id}/variant/1/svg")
        assert svg_resp.status_code == 200
        assert "<svg" in svg_resp.text

"""
Testes para o endpoint de amostras oficiais CAD/BIM.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from structura_ai.main import app


@pytest.mark.asyncio
async def test_list_samples():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/projects/samples/list")
        assert resp.status_code == 200
        samples = resp.json()
        assert len(samples) >= 4
        filenames = [s["filename"] for s in samples]
        assert "residencia_horizon_10m.dxf" in filenames
        assert "pavilhao_estrutural_bim.ifc" in filenames
        assert "residencia_horizon_3d.obj" in filenames
        assert "cobertura_balanco_critico.dxf" in filenames


@pytest.mark.asyncio
async def test_load_sample_dxf():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/projects/samples/load/residencia_horizon_10m.dxf")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "project_id" in data
        assert data["studio_url"].startswith("/projects/")


@pytest.mark.asyncio
async def test_load_sample_ifc():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/projects/samples/load/pavilhao_estrutural_bim.ifc")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "project_id" in data

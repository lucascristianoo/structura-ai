"""
Integration Tests for FastAPI Backend Endpoints (Arquitetura Enxuta + Padrão Lembry).
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
async def test_health_and_root_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "Structura.AI"

        root_resp = await client.get("/")
        assert root_resp.status_code == 200
        assert "viewer-workspace" in root_resp.text
        assert "version-bar-container" in root_resp.text
        assert "software-format-select" in root_resp.text
        assert "chat-suggestions-bar" in root_resp.text

        info_resp = await client.get("/api/info")
        assert info_resp.status_code == 200
        assert "/api/v1/files" in info_resp.json()["endpoints"]["files_and_versions"]


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
            "category": "Residencial",
        }
        response = await client.post("/api/analysis/quick-calc", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["evaluation"]["is_physically_viable"] is False
        assert "section_optimization" in data


@pytest.mark.asyncio
async def test_canvas_base64_upload_and_bim_export():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        data = {
            "title": "Projeto Croqui Base64",
            "author_architect": "Arquiteto Studio",
            "category": "Residencial",
            "canvas_image": data_url,
        }
        resp = await client.post("/api/projects/upload", data=data)
        assert resp.status_code == 200
        project_id = resp.json()["project_id"]

        proj_resp = await client.get(f"/api/projects/{project_id}")
        assert proj_resp.status_code == 200
        proj_data = proj_resp.json()
        assert proj_data["image_path"] is not None
        assert "croqui_arquiteto.png" in proj_data["image_path"]

        dxf_resp = await client.get(f"/api/export/{project_id}/cad.dxf")
        assert dxf_resp.status_code == 200
        assert "SECTION" in dxf_resp.text

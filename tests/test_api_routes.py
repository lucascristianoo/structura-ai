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

        # Single-page viewer at '/' serves the unified frontend
        home_resp = await client.get("/")
        assert home_resp.status_code == 200
        assert "fake-login-form" in home_resp.text
        assert "viewer-workspace" in home_resp.text
        assert "copilot-chat-box" in home_resp.text

        # Legacy /viewer redirects to '/' and removed pages return 404
        legacy_viewer = await client.get("/viewer", follow_redirects=False)
        assert legacy_viewer.status_code == 307
        assert legacy_viewer.headers["location"] == "/"
        assert (await client.get("/analyzer")).status_code == 404
        assert (await client.get("/council")).status_code == 404
        assert (await client.get(f"/project/{project_id}")).status_code == 404

        # Export HTML report
        export_resp = await client.get(f"/api/export/{project_id}/report.html")
        assert export_resp.status_code == 200
        assert "STRUCTURA.AI — Laudo de Compatibilização Físico-Arquitetônica" in export_resp.text

        # Export Variant 1 SVG
        svg_resp = await client.get(f"/api/export/{project_id}/variant/1/svg")
        assert svg_resp.status_code == 200
        assert "<svg" in svg_resp.text

        # Verify HTML report contains embedded SVGs for the variants
        assert "<svg" in export_resp.text

@pytest.mark.asyncio
async def test_preset_not_found_404():
    """Requesting an unknown preset must return HTTP 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/projects/preset/inexistent_preset_key_123")
        assert resp.status_code == 404
        assert "não encontrado" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_canvas_base64_upload_flow():
    """Submitting a base64 canvas drawing saves the image and associates image_path."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1x1 transparent PNG data URL
        data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        data = {
            "title": "Projeto Croqui Base64",
            "author_architect": "Arquiteto Studio",
            "category": "Residencial",
            "canvas_image": data_url
        }
        resp = await client.post("/api/projects/upload", data=data)
        assert resp.status_code == 200
        project_id = resp.json()["project_id"]

        # Fetch project details and verify image_path is populated
        proj_resp = await client.get(f"/api/projects/{project_id}")
        assert proj_resp.status_code == 200
        proj_data = proj_resp.json()
        assert proj_data["image_path"] is not None
        assert "croqui_arquiteto.png" in proj_data["image_path"]


@pytest.mark.asyncio
async def test_copilot_debate_flow():
    """Verifies chatbot diagnostic debate endpoint with project context and multi-turn history."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "message": "Por que reprovou no ELS e qual altura de viga resolveria?",
            "project_context": {
                "title": "Residência Horizon",
                "span_length_m": 10.0,
                "cantilever_length_m": 0.0,
                "beam_width_cm": 20.0,
                "beam_height_cm": 28.0,
                "concrete_fck_mpa": 30.0,
                "is_physically_viable": False,
                "structural_score": 42.0,
                "max_deflection_mm": 48.2,
                "allowable_deflection_mm": 40.0,
                "max_bending_moment_knm": 285.4,
                "failure_reasons": ["Flecha excessiva acima de L/250"]
            },
            "history": [
                {"role": "user", "content": "Enviei o arquivo residencia_horizon_10m.dxf."},
                {"role": "assistant", "content": "Diagnóstico emitido: flecha acima do limite."}
            ]
        }
        resp = await client.post("/api/analysis/copilot", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert len(body["reply"]) > 20

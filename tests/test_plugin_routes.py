"""
Testes automatizados para a API de plugins (Blender, Grasshopper, Desktop Bridge).
"""
import pytest
from httpx import AsyncClient, ASGITransport
from structura_ai.main import app


@pytest.mark.asyncio
async def test_plugin_status_handshake():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/plugins/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert data["version"] == "2.0.0"
        assert "Blender 3.x/4.x" in data["supported_plugins"]
        assert ".dxf" in data["supported_formats"]
        assert ".ifc" in data["supported_formats"]


@pytest.mark.asyncio
async def test_plugin_sync_payload_rejection_and_redesign():
    """Simula o plugin do Blender enviando um vão crítico de 11m com viga delgada de 28cm."""
    payload = {
        "project_name": "Blender Concept Test",
        "source_software": "Blender 3D",
        "span_meters": 11.0,
        "cantilever_meters": 0.0,
        "beam_width_cm": 20.0,
        "beam_height_cm": 28.0,
        "column_height_m": 3.2,
        "column_section_cm": 20.0,
        "fck_mpa": 30.0,
        "dead_load_kn_m": 24.0,
        "live_load_kn_m": 3.0,
        "geometry_metadata": {"author": "Lucas Architect", "scene": "Living Panoramico"}
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/plugins/sync", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "project_id" in data
        assert data["studio_url"].startswith("/projects/")

        diag = data["deterministic_diagnosis"]
        assert diag["is_feasible"] is False  # 11m com 28cm viola L/250!
        assert diag["calculated_deflection_mm"] > diag["normative_limit_mm"]

        # Deve retornar as 5 alternativas de redesign
        assert len(data["redesign_variants"]) == 5
        variants = data["redesign_variants"]
        strategies = [v["strategy"] for v in variants]
        assert "Protensão Não-Aderente" in strategies
        assert "Treliça Rígida Integrada à Fachada" in strategies


@pytest.mark.asyncio
async def test_geometry_3d_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Primeiro cria ou pega projeto existente via preset
        create_resp = await client.post("/api/projects/preset/residencia_vao_livre_critico")
        assert create_resp.status_code == 200
        proj_id = create_resp.json()["project_id"]

        # Busca dados 3D para o Three.js
        g3d_resp = await client.get(f"/api/projects/{proj_id}/geometry-3d")
        assert g3d_resp.status_code == 200
        g3d = g3d_resp.json()
        assert g3d["project_id"] == proj_id
        assert "elements" in g3d
        assert len(g3d["elements"]) >= 3  # Pilares + Viga + Laje
        assert "deflection_curve" in g3d
        assert len(g3d["deflection_curve"]) == 21  # 21 pontos discretizados da elástica
        assert "bounding_box" in g3d

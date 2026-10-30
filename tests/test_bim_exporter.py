"""
Automated Tests for Native BIM & CAD Roundtrip Exporters (IFC4 & DXF).
"""
import pytest
from httpx import AsyncClient, ASGITransport
from structura_ai.main import app
from structura_ai.cad.bim_exporter import BimExporter


def test_ifc4_direct_generation():
    """Validates IFC4 schema and entities generation."""
    params = {
        "span_length_m": 10.0,
        "beam_height_cm": 30.0,
        "beam_width_cm": 20.0,
        "column_height_m": 3.2,
        "column_section_cm": 20.0,
        "concrete_fck_mpa": 30.0
    }
    ifc_str = BimExporter.export_project_ifc("Residencia_Teste", params)

    assert "FILE_SCHEMA(('IFC4'))" in ifc_str
    assert "IFCBEAM" in ifc_str
    assert "IFCCOLUMN" in ifc_str
    assert "Pset_BeamCommon" in ifc_str
    assert "Pset_StructuraCompliance" in ifc_str


def test_dxf_direct_generation():
    """Validates AutoCAD DXF format and normative layers."""
    params = {
        "span_length_m": 8.0,
        "cantilever_length_m": 2.0,
        "beam_height_cm": 40.0,
        "beam_width_cm": 20.0,
        "column_section_cm": 20.0
    }
    dxf_str = BimExporter.export_project_dxf("Prancha_Teste", params)

    assert "SECTION" in dxf_str
    assert "ESTRUTURA_PILARES" in dxf_str
    assert "ESTRUTURA_VIGAS" in dxf_str
    assert "COTAS_DIMENSOES" in dxf_str


@pytest.mark.asyncio
async def test_export_ifc_and_dxf_endpoints():
    """Validates the GET /api/export/{id}/bim.ifc and /cad.dxf routes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Load preset first
        resp = await client.post("/api/projects/preset/residencia_vao_livre_critico")
        assert resp.status_code == 200
        proj_id = resp.json()["project_id"]

        # Test IFC4 export
        ifc_resp = await client.get(f"/api/export/{proj_id}/bim.ifc")
        assert ifc_resp.status_code == 200
        assert "IFC4" in ifc_resp.text
        assert "IFCBEAM" in ifc_resp.text

        # Test DXF export
        dxf_resp = await client.get(f"/api/export/{proj_id}/cad.dxf")
        assert dxf_resp.status_code == 200
        assert "SECTION" in dxf_resp.text
        assert "ESTRUTURA_VIGAS" in dxf_resp.text

        # Test Variant 1 IFC export
        var_ifc_resp = await client.get(f"/api/export/{proj_id}/variant/1/bim.ifc")
        assert var_ifc_resp.status_code == 200
        assert "IFC4" in var_ifc_resp.text

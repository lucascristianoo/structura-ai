"""
Testes automatizados para o subsistema de ingestão CAD/BIM do Structura.AI.
"""
from pathlib import Path
from structura_ai.cad import CadIngestor, UnifiedProjectData
from structura_ai.cad.bim_exporter import BimExporter


def test_cad_supported_formats():
    assert CadIngestor.is_cad_format("projeto.dxf") is True
    assert CadIngestor.is_cad_format("modelo.ifc") is True
    assert CadIngestor.is_cad_format("cena.obj") is True
    assert CadIngestor.is_cad_format("malha.gltf") is True
    assert CadIngestor.is_cad_format("desenho.png") is False


def test_dxf_ingestion_roundtrip(tmp_path: Path):
    dxf_content = BimExporter.export_project_dxf(
        "Residencia_Horizon",
        {"span_length_m": 10.0, "cantilever_length_m": 3.5, "beam_height_cm": 35.0, "beam_width_cm": 20.0},
    )
    dxf_path = tmp_path / "residencia_horizon_10m.dxf"
    dxf_path.write_text(dxf_content, encoding="utf-8")

    data = CadIngestor.ingest(dxf_path)
    assert isinstance(data, UnifiedProjectData)
    assert data.source_format == "dxf"
    assert data.max_span_m >= 9.0
    assert data.mesh_3d is not None


def test_ifc_ingestion_roundtrip(tmp_path: Path):
    ifc_content = BimExporter.export_project_ifc(
        "Pavilhao_BIM",
        {"span_length_m": 10.5, "cantilever_length_m": 2.0, "beam_height_cm": 45.0, "beam_width_cm": 25.0},
    )
    ifc_path = tmp_path / "pavilhao_estrutural_bim.ifc"
    ifc_path.write_text(ifc_content, encoding="utf-8")

    data = CadIngestor.ingest(ifc_path)
    assert isinstance(data, UnifiedProjectData)
    assert data.source_format == "ifc"
    assert data.max_span_m >= 9.0
    assert data.metadata.get("schema") in ("IFC4", "IFC2X3")


def test_obj_3d_mesh_ingestion(tmp_path: Path):
    obj_content = """# Structura 3D OBJ Test
v 0.0 0.0 0.0
v 12.0 0.0 0.0
v 12.0 4.0 3.2
v 0.0 4.0 3.2
f 1 2 3
f 1 3 4
"""
    obj_path = tmp_path / "residencia_horizon_3d.obj"
    obj_path.write_text(obj_content, encoding="utf-8")

    data = CadIngestor.ingest(obj_path)
    assert isinstance(data, UnifiedProjectData)
    assert data.source_format == "obj"
    assert data.max_span_m >= 10.0
    assert data.mesh_3d is not None
    assert len(data.mesh_3d.vertices) > 0

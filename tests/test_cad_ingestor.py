"""
Testes automatizados para o subsistema de ingestão CAD/BIM do Structura.AI.
"""
from pathlib import Path
import pytest
from structura_ai.cad import CadIngestor, UnifiedProjectData


SAMPLES_DIR = Path(__file__).resolve().parent.parent / "downloads" / "test_samples"


def test_cad_supported_formats():
    assert CadIngestor.is_cad_format("projeto.dxf") is True
    assert CadIngestor.is_cad_format("modelo.ifc") is True
    assert CadIngestor.is_cad_format("cena.obj") is True
    assert CadIngestor.is_cad_format("malha.gltf") is True
    assert CadIngestor.is_cad_format("desenho.png") is False


def test_dxf_horizon_ingestion():
    dxf_path = SAMPLES_DIR / "residencia_horizon_10m.dxf"
    assert dxf_path.exists(), f"Amostra não encontrada: {dxf_path}"

    data = CadIngestor.ingest(dxf_path)
    assert isinstance(data, UnifiedProjectData)
    assert data.source_format == "dxf"
    assert data.max_span_m >= 9.5
    assert len(data.spans) > 0
    assert len(data.columns) > 0
    assert data.suggested_beam_height_cm > 20.0
    assert data.mesh_3d is not None
    assert len(data.mesh_3d.element_meshes) > 0


def test_ifc_pavilhao_ingestion():
    ifc_path = SAMPLES_DIR / "pavilhao_estrutural_bim.ifc"
    assert ifc_path.exists(), f"Amostra não encontrada: {ifc_path}"

    data = CadIngestor.ingest(ifc_path)
    assert isinstance(data, UnifiedProjectData)
    assert data.source_format == "ifc"
    assert data.max_span_m >= 10.0
    assert len(data.beams) > 0
    assert len(data.columns) >= 2
    assert data.metadata.get("schema") in ("IFC4", "IFC2X3")


def test_obj_3d_mesh_ingestion():
    obj_path = SAMPLES_DIR / "residencia_horizon_3d.obj"
    assert obj_path.exists(), f"Amostra não encontrada: {obj_path}"

    data = CadIngestor.ingest(obj_path)
    assert isinstance(data, UnifiedProjectData)
    assert data.source_format == "obj"
    assert data.max_span_m >= 10.0
    assert data.mesh_3d is not None
    assert len(data.mesh_3d.vertices) > 0
    assert len(data.mesh_3d.faces) > 0


def test_dxf_balanco_critico_ingestion():
    dxf_path = SAMPLES_DIR / "cobertura_balanco_critico.dxf"
    assert dxf_path.exists(), f"Amostra não encontrada: {dxf_path}"

    data = CadIngestor.ingest(dxf_path)
    assert isinstance(data, UnifiedProjectData)
    assert data.source_format == "dxf"
    assert data.max_span_m >= 4.0

"""
Testes automatizados para o subsistema de ingestão CAD/BIM do Structura.AI.
"""
from pathlib import Path
import pytest
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


def test_cad_validate_file_integrity(tmp_path: Path):
    """Valida rejeição de arquivos inexistentes, vazios ou sem cabeçalhos válidos."""
    import pytest

    # 1. Arquivo inexistente
    with pytest.raises(ValueError, match="não encontrado"):
        CadIngestor.validate_file_integrity(tmp_path / "nao_existe.dxf")

    # 2. Arquivo vazio (0 bytes)
    empty_f = tmp_path / "vazio.dxf"
    empty_f.write_bytes(b"")
    with pytest.raises(ValueError, match="0 bytes"):
        CadIngestor.validate_file_integrity(empty_f)

    # 3. Arquivo com extensão inválida
    inv_ext = tmp_path / "projeto.exe"
    inv_ext.write_bytes(b"corrompido")
    with pytest.raises(ValueError, match="não suportado"):
        CadIngestor.validate_file_integrity(inv_ext)

    # 4. Arquivo DXF com lixo binário sem SECTION
    corrupt_dxf = tmp_path / "lixo.dxf"
    corrupt_dxf.write_bytes(b"\x00\xff\xfe\x12\x34\x56\x78")
    with pytest.raises(ValueError, match="DXF corrompido"):
        CadIngestor.validate_file_integrity(corrupt_dxf)


def test_dxf_polyline_3d_and_closed_loop(tmp_path: Path):
    """Valida parsing de entidades POLYLINE 3D clássicas e fechamento de anéis poligonais."""
    import ezdxf

    doc = ezdxf.new("R2000")
    msp = doc.modelspace()
    doc.layers.add("VIGAS", color=3)

    # Cria uma POLYLINE 3D com 3 vértices inclinados (rampa com desnível Z)
    p3d = msp.add_polyline3d(
        [(0.0, 0.0, 0.0), (10.0, 0.0, 2.5), (10.0, 5.0, 2.5)],
        dxfattribs={"layer": "VIGAS"}
    )
    p3d.close(True)

    dxf_file = tmp_path / "rampa_3d.dxf"
    doc.saveas(str(dxf_file))

    data = CadIngestor.ingest(dxf_file)
    assert len(data.beams) >= 3, f"Esperado 3 segmentos da polilinhas fechada 3D, obteve {len(data.beams)}"
    # Verifica que cota Z foi preservada e vão 3D inclui hipotenusa com Z
    # sqrt(10^2 + 0^2 + 2.5^2) = sqrt(106.25) ~= 10.31m
    first_beam = data.beams[0]
    assert first_beam.span_m == pytest.approx(10.31, abs=0.1)


def test_dxf_insert_column_no_duplication(tmp_path: Path):
    """Garante que a descompactação virtual de blocos INSERT não duplica os pilares nas 4 quinas."""
    import ezdxf

    doc = ezdxf.new("R2000")
    msp = doc.modelspace()
    doc.layers.add("PILARES", color=1)

    # Cria bloco de pilar 20x40cm com 4 linhas
    blk = doc.blocks.new(name="PILAR_PADRAO")
    blk.add_line((0, 0), (0.2, 0), dxfattribs={"layer": "PILARES"})
    blk.add_line((0.2, 0), (0.2, 0.4), dxfattribs={"layer": "PILARES"})
    blk.add_line((0.2, 0.4), (0, 0.4), dxfattribs={"layer": "PILARES"})
    blk.add_line((0, 0.4), (0, 0), dxfattribs={"layer": "PILARES"})

    # Insere 2 pilares no desenho
    msp.add_blockref("PILAR_PADRAO", (0.0, 0.0), dxfattribs={"layer": "PILARES"})
    msp.add_blockref("PILAR_PADRAO", (8.0, 0.0), dxfattribs={"layer": "PILARES"})

    dxf_file = tmp_path / "dois_pilares_insert.dxf"
    doc.saveas(str(dxf_file))

    data = CadIngestor.ingest(dxf_file)
    # Anteriormente: 2 blocos geravam 8 pilares duplicados nas quinas
    # Com a correção: exatamente 2 pilares
    assert len(data.columns) == 2, f"Esperado exatamente 2 pilares, mas obteve {len(data.columns)} (duplicação detectada)"


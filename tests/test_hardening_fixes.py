"""
Testes de validação para as correções de robustez:
1. Suporte a blocos INSERT no parser DXF.
2. Detecção inteligente de escala por mediana de comprimentos.
3. Tratamento de DWG binário com mensagem instrutiva.
4. Blindagem legal em structural_core (Concepção Viável + Disclaimer ART).
"""
from pathlib import Path
import pytest
import ezdxf

from structura_ai.cad import CadIngestor, UnifiedProjectData
from structura_ai.physics.structural_core import StructuralCoreEngine


def test_dxf_insert_block_unpacked_and_columns_detected(tmp_path: Path):
    """Garante que blocos INSERT aninhados de pilares e vigas sejam extraídos corretamente."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Cria definição de bloco de pilar 20x40 cm
    blk_col = doc.blocks.new(name="BLOCO_PILAR_P1")
    blk_col.add_line((0, 0), (0.2, 0), dxfattribs={"layer": "0"})
    blk_col.add_line((0.2, 0), (0.2, 0.4), dxfattribs={"layer": "0"})
    blk_col.add_line((0.2, 0.4), (0, 0.4), dxfattribs={"layer": "0"})
    blk_col.add_line((0, 0.4), (0, 0), dxfattribs={"layer": "0"})

    # Cria definição de bloco de viga de 6 metros
    blk_beam = doc.blocks.new(name="BLOCO_VIGA_V1")
    blk_beam.add_line((0, 0), (6.0, 0), dxfattribs={"layer": "0"})

    # Insere pilar na coordenada (2.0, 3.0) sob layer PILARES
    msp.add_blockref("BLOCO_PILAR_P1", (2.0, 3.0), dxfattribs={"layer": "PILARES"})
    # Insere pilar na coordenada (8.0, 3.0) sob layer PILARES
    msp.add_blockref("BLOCO_PILAR_P1", (8.0, 3.0), dxfattribs={"layer": "PILARES"})
    # Insere viga ligando os dois pilares
    msp.add_blockref("BLOCO_VIGA_V1", (2.0, 3.0), dxfattribs={"layer": "VIGAS"})

    dxf_file = tmp_path / "projeto_com_blocos.dxf"
    doc.saveas(str(dxf_file))

    data = CadIngestor.ingest(dxf_file)
    assert isinstance(data, UnifiedProjectData)
    assert len(data.columns) >= 2, f"Esperado pelo menos 2 pilares dos blocos INSERT, obtido {len(data.columns)}"
    assert len(data.beams) >= 1, f"Esperado pelo menos 1 viga do bloco INSERT, obtido {len(data.beams)}"
    assert data.max_span_m == pytest.approx(6.0, abs=0.2)


def test_dwg_binary_graceful_rejection(tmp_path: Path):
    """Garante que arquivos DWG binários gerem aviso explicativo em vez de quebra críptica."""
    fake_dwg = tmp_path / "planta_obra.dwg"
    fake_dwg.write_bytes(b"AC1032\x00\x00\x00BinaryDWGPayloadMock")

    with pytest.raises(ValueError) as exc:
        CadIngestor.ingest(fake_dwg)
    assert "DWG binário" in str(exc.value)
    assert "exporte ou salve o arquivo como DXF" in str(exc.value)


def test_structural_core_legal_compliance_shield():
    """Garante que o status não emita falso atestado de aprovação e contenha o disclaimer da ART."""
    result = StructuralCoreEngine.evaluate_structure(
        span_length_m=6.0,
        cantilever_length_m=1.0,
        beam_height_cm=50.0,
        beam_width_cm=25.0,
        column_height_m=3.0,
        column_section_cm=25.0,
    )
    assert result["is_physically_viable"] is True
    assert result["compliance_level"] == "Concepção Viável (Pré-Dimensionamento)"
    assert "Aprovado para Detalhamento" not in result["compliance_level"]
    assert "NOTA LEGAL" in result["structural_diagnosis_text"]
    assert "ART/CREA" in result["structural_diagnosis_text"]

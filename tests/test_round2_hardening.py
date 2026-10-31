"""
Testes automatizados para a Rodada 2 de Hardening:
1. Normalização de Coordenadas Astronômicas UTM (SIRGAS 2000).
2. Discretização de Curvas DXF (ARC, CIRCLE, SPLINE).
3. Auditor de Escopo (ScopeGuard) para edifícios altos e protensão.
4. Análise de Sensibilidade Geotécnica ao Latossolo Colapsível (DSM Solver).
"""
from pathlib import Path
import pytest
import ezdxf

from structura_ai.cad import CadIngestor, UnifiedProjectData
from structura_ai.physics.scope_guard import ScopeGuard
from structura_ai.physics.dsm_solver import DSMSolver
from structura_ai.physics.structural_core import StructuralCoreEngine


def test_utm_georeferenced_coordinates_normalized(tmp_path: Path):
    """Garante que coordenadas UTM astronômicas de Goiânia sejam transladadas para origem local."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Coordenadas UTM SIRGAS 2000 Fuso 22S típicas de Goiânia (Easting ~ 685.000m, Northing ~ 8.155.000m)
    utm_x = 685420.0
    utm_y = 8155310.0

    # Adiciona pórtico com vão de 8m georreferenciado
    msp.add_line((utm_x, utm_y), (utm_x, utm_y + 3.0), dxfattribs={"layer": "PILARES"})
    msp.add_line((utm_x + 8.0, utm_y), (utm_x + 8.0, utm_y + 3.0), dxfattribs={"layer": "PILARES"})
    msp.add_line((utm_x, utm_y + 3.0), (utm_x + 8.0, utm_y + 3.0), dxfattribs={"layer": "VIGAS"})

    dxf_file = tmp_path / "topografia_georreferenciada_goiania.dxf"
    doc.saveas(str(dxf_file))

    data = CadIngestor.ingest(dxf_file)
    assert isinstance(data, UnifiedProjectData)
    assert data.max_span_m == pytest.approx(8.0, abs=0.15)

    # Verifica se os nós foram transladados para perto de 0,0 para visualização limpa no Three.js
    assert data.mesh_3d is not None
    assert data.bounding_box["max_x"] == pytest.approx(8.0, abs=0.5)
    assert data.metadata.get("is_georeferenced_utm") is True
    assert data.metadata.get("utm_origin_offset")["x"] == pytest.approx(utm_x, abs=1.0)


def test_dxf_curve_discretization_arc_circle(tmp_path: Path):
    """Garante que entidades ARC e CIRCLE de fachadas orgânicas sejam ingeridas e discretizadas."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Pilar circular na origem
    msp.add_circle(center=(0.0, 0.0), radius=0.25, dxfattribs={"layer": "PILARES"})
    # Pilar circular a 7m
    msp.add_circle(center=(7.0, 0.0), radius=0.25, dxfattribs={"layer": "PILARES"})
    # Viga curva (Arco) ligando os dois pilares
    msp.add_arc(center=(3.5, -2.0), radius=4.5, start_angle=45, end_angle=135, dxfattribs={"layer": "VIGAS"})

    dxf_file = tmp_path / "fachada_organica_curva.dxf"
    doc.saveas(str(dxf_file))

    data = CadIngestor.ingest(dxf_file)
    assert isinstance(data, UnifiedProjectData)
    assert len(data.columns) >= 2, "Pilares circulares devem ser reconhecidos"
    assert len(data.beams) >= 1 or len(data.raw_2d_entities) >= 5, "Arco deve ser discretizado em segmentos de viga"


def test_scope_guard_rules():
    """Valida as travas determinísticas de escopo do ScopeGuard."""
    # 1. Edificação alta (> 4 pavimentos) deve sofrer HARD_BLOCK
    tall = ScopeGuard.audit_project_scope(max_span_m=7.0, total_height_m=18.0, num_storeys=6)
    assert tall.is_within_scope is False
    assert tall.severity == "HARD_BLOCK"
    assert tall.scope_category == "OUT_OF_SCOPE_TALL_BUILDING"
    assert "NBR 6123" in tall.description

    # 2. Vão excessivo (> 12m) deve indicar Protensão
    long_span = ScopeGuard.audit_project_scope(max_span_m=14.0, total_height_m=3.0, num_storeys=1)
    assert long_span.is_within_scope is True
    assert long_span.severity == "WARNING"
    assert long_span.scope_category == "POST_TENSIONING_ZONE"
    assert "Protendido" in long_span.description

    # 3. Residência padrão (6m, 1 pavimento) deve passar como INFO
    safe = ScopeGuard.audit_project_scope(max_span_m=6.0, total_height_m=3.0, num_storeys=1)
    assert safe.is_within_scope is True
    assert safe.severity == "INFO"
    assert safe.scope_category == "STANDARD_LOW_RISE"


def test_dsm_geotechnical_sensitivity_to_collapsible_soil():
    """Valida cálculo de sensibilidade a recalque diferencial em Latossolo de Goiás."""
    res = DSMSolver.solve_portal_frame(
        span_length_m=8.0,
        cantilever_length_m=0.0,
        beam_height_cm=50.0,
        beam_width_cm=20.0,
        column_height_m=3.0,
        distributed_load_kn_m=20.0,
    )
    assert "geotechnical_sensitivity" in res
    geo = res["geotechnical_sensitivity"]
    assert geo["imposed_differential_settlement_mm"] > 0
    assert geo["induced_additional_moment_knm"] > 0
    assert geo["moment_increase_percentage"] > 0
    assert "Latossolo Vermelho" in geo["soil_context"]
    assert "estacas" in geo["geotechnical_advice"].lower()

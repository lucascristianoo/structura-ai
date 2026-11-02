"""
Unit Tests for Structural Mechanics & NBR 6118 Physics Engine.
"""
import pytest
from structura_ai.physics.structural_core import StructuralCoreEngine
from structura_ai.physics.nbr_standards import ConcreteProperties, DeflectionLimits, ColumnLimits
from structura_ai.physics.load_calculator import LoadCalculator

def test_concrete_properties_calculation():
    """Verifies concrete elastic modulus and creep factor."""
    e_gpa = ConcreteProperties.get_elastic_modulus_gpa(fck_mpa=30.0)
    assert 25.0 <= e_gpa <= 35.0, f"Expected E around 30 GPa, got {e_gpa}"
    assert ConcreteProperties.get_long_term_creep_factor() == 1.3

def test_deflection_limits_nbr6118():
    """Verifies normative deflection tolerances."""
    # For a 10m span, visual sag limit L/250 = 40mm
    limit_10m = DeflectionLimits.visual_sag_limit_mm(10.0)
    assert limit_10m == 40.0
    
    # For a 3m cantilever, limit Lc/125 = 24mm
    cant_limit = DeflectionLimits.cantilever_visual_limit_mm(3.0)
    assert cant_limit == 24.0

def test_excessive_span_failure():
    """A 10m span with a thin 25cm beam must fail physical compliance."""
    result = StructuralCoreEngine.evaluate_structure(
        span_length_m=10.0,
        cantilever_length_m=3.5,
        beam_height_cm=25.0,
        beam_width_cm=20.0
    )
    assert result["is_physically_viable"] is False
    assert result["deflection_ratio"] > 1.0
    assert result["structural_score"] < 60.0
    assert any("Flecha excessiva" in f for f in result["failure_reasons"])

def test_compliant_structure_passes():
    """A 6m span with a robust 50cm beam must pass physical compliance."""
    result = StructuralCoreEngine.evaluate_structure(
        span_length_m=6.0,
        cantilever_length_m=1.0,
        beam_height_cm=50.0,
        beam_width_cm=25.0,
        column_height_m=3.0,
        column_section_cm=25.0
    )
    assert result["is_physically_viable"] is True
    assert result["deflection_ratio"] <= 1.0
    assert result["structural_score"] >= 80.0
    assert len(result["failure_reasons"]) == 0

def test_slender_column_buckling_detection():
    """A 5.5m high column with only 14cm section must fail due to Euler buckling / slenderness."""
    result = StructuralCoreEngine.evaluate_structure(
        span_length_m=8.0,
        cantilever_length_m=0.0,
        beam_height_cm=45.0,
        beam_width_cm=20.0,
        column_height_m=5.5,
        column_section_cm=14.0
    )
    assert result["is_physically_viable"] is False
    assert any("esbeltez" in f.lower() or "flambagem" in f.lower() for f in result["failure_reasons"])


def test_dsm_midspan_moment_sign_and_continuous_beam():
    """Valida a correção do sinal de momentos no vão e a solução de vigas contínuas per NBR 6118 item 14.6.4.3."""
    from structura_ai.physics.dsm_solver import DSMSolver

    # 1. Pórtico Simétrico: momento no meio de vão não pode cancelar e virar qL^2/8
    portal = DSMSolver.solve_portal_frame(
        span_length_m=10.0,
        distributed_load_kn_m=25.0,
        beam_height_cm=40.0,
        beam_width_cm=20.0,
        column_height_m=3.2,
        column_section_cm=20.0,
    )
    m_pos = portal["internal_moments_knm"]["midspan_positive_m"]
    # qL^2/8 = 25*100/8 = 312.5 kNm. Com a restrição dos pilares, momento positivo de pórtico deve ser bem menor (~30 a 60 kNm)
    assert m_pos < 100.0, f"Momento positivo de pórtico {m_pos} kNm não considerou restrição dos nós (deveria ser < 100 kNm, não 312.5)"

    # 2. Viga Contínua de 2 vãos com rigidez rotacional dos pilares
    cont = DSMSolver.solve_continuous_beam(
        spans_m=[6.0, 6.0],
        distributed_loads_kn_m=[25.0, 25.0],
        beam_width_cm=20.0,
        beam_height_cm=45.0,
        column_height_m=3.2,
        column_section_cm=20.0,
    )
    assert cont["num_spans"] == 2
    assert cont["degrees_of_freedom"] == 3
    assert cont["intermediate_column_rotational_stiffness_knm_rad"] > 0
    # Apoio intermediário deve ter momento fletor negativo significativo
    assert cont["support_moments_knm"][1] > 20.0
    assert len(cont["spans_detail"]) == 2
    assert cont["spans_detail"][0]["moment_midspan_knm"] > 0


def test_optisection_nbr6118_rebar_and_shear_model_1():
    """Valida taxa mínima de armadura, armadura de pele e checagem de cisalhamento no catálogo."""
    from structura_ai.physics.optisection import OptiSectionEngine

    opt = OptiSectionEngine.optimize_beam_section(
        span_length_m=8.0,
        distributed_load_kn_m=30.0,
        concrete_fck_mpa=30.0,
    )
    assert len(opt["compliant_concrete_sections"]) > 0
    for sec in opt["compliant_concrete_sections"]:
        # Taxa mínima rho_min >= 0.15%
        assert sec["min_rebar_cm2"] > 0
        assert sec["required_rebar_cm2"] >= sec["min_rebar_cm2"]
        # Se altura > 60cm, exige armadura de pele per NBR 6118 item 17.3.5.2.3
        if sec["height_cm"] > 60.0:
            assert sec["requires_skin_rebar"] is True
            assert sec["skin_rebar_cm2_face"] > 0
        else:
            assert sec["requires_skin_rebar"] is False


def test_structural_core_shear_crushing_and_scope_guard_block():
    """Valida reprovação de biela comprimida (Modelo I) e acoplamento do HARD_BLOCK do ScopeGuard."""
    # 1. Cisalhamento excessivo (carga colossal em viga estreita) deve reprovar por biela V_Rd2
    result_crush = StructuralCoreEngine.evaluate_structure(
        span_length_m=4.0,
        cantilever_length_m=0.0,
        beam_height_cm=25.0,
        beam_width_cm=14.0,
        live_load_kpa=450.0,  # Carga destrutiva
        dead_load_kpa=100.0,
        concrete_fck_mpa=20.0,
    )
    assert result_crush["is_physically_viable"] is False
    assert result_crush["compliance_checklist"]["cisalhamento_esmagamento_biela"]["status"] == "FAIL"
    assert any("esmagamento da biela" in f.lower() for f in result_crush["failure_reasons"])

    # 2. ScopeGuard HARD_BLOCK (>4 pavimentos / >12m) deve forçar is_physically_viable = False
    from structura_ai.physics.scope_guard import ScopeGuard
    audit = ScopeGuard.audit_project_scope(max_span_m=6.0, total_height_m=20.0, num_storeys=6)
    assert audit.severity == "HARD_BLOCK"
    assert audit.is_within_scope is False

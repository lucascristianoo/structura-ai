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

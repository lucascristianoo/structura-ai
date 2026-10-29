"""
Unit Tests for the 5-Variant Generative Redesign Engine.
"""
from structura_ai.physics.structural_core import StructuralCoreEngine
from structura_ai.physics.generator import RedesignGenerator

def test_generates_exactly_5_variants():
    """Engine must generate exactly 5 distinct variants with specific strategies."""
    eval_result = StructuralCoreEngine.evaluate_structure(
        span_length_m=10.0,
        cantilever_length_m=4.0,
        beam_height_cm=28.0,
        beam_width_cm=20.0
    )
    variants = RedesignGenerator.generate_5_variants(eval_result)
    
    assert len(variants) == 5, f"Expected 5 redesign proposals, got {len(variants)}"
    
    # Check variant numbers 1 to 5
    numbers = [v["variant_number"] for v in variants]
    assert numbers == [1, 2, 3, 4, 5]

    # Verify that each variant provides valid SVG render and pitch narrative
    for v in variants:
        assert "<svg" in v["svg_render"]
        assert "</svg>" in v["svg_render"]
        assert len(v["title"]) > 10
        assert len(v["architectural_concept"]) > 20
        assert len(v["engineering_solution"]) > 20
        assert v["metrics_delta"]["deflection_reduction_pct"] > 50
        assert v["metrics_delta"]["safety_factor"] >= 1.8

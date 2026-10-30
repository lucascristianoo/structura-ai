"""
API Routes for Real-time Structural Analysis, Quick-Calculation and Canvas Extraction.
"""
import math
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from structura_ai.database import get_db
from structura_ai.models import Project
from structura_ai.schemas import CanvasFloorplanPayload
from structura_ai.physics.structural_core import StructuralCoreEngine
from structura_ai.physics.generator import RedesignGenerator
from structura_ai.physics.cost_carbon_engine import CostCarbonEngine
from structura_ai.services.analyzer_service import AnalyzerService

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])

@router.post("/quick-calc")
async def quick_calculation(payload: Dict[str, Any] = Body(...)):
    """
    Sub-millisecond live physics calculation for real-time sliders in the UI.
    Returns physical parameters, pass/fail status, and all 5 redesign variants instantly.
    """
    span = float(payload.get("span_length_m", 9.5))
    cantilever = float(payload.get("cantilever_length_m", 3.5))
    beam_h = float(payload.get("beam_height_cm", 30.0))
    beam_w = float(payload.get("beam_width_cm", 20.0))
    col_h = float(payload.get("column_height_m", 3.2))
    col_sec = float(payload.get("column_section_cm", 20.0))
    dead_load = float(payload.get("dead_load_kpa", 4.5))
    live_load = float(payload.get("live_load_kpa", 2.5))
    fck = float(payload.get("concrete_fck_mpa", 30.0))
    category = str(payload.get("category", "Residencial"))

    evaluation = StructuralCoreEngine.evaluate_structure(
        span_length_m=span,
        cantilever_length_m=cantilever,
        beam_height_cm=beam_h,
        beam_width_cm=beam_w,
        column_height_m=col_h,
        column_section_cm=col_sec,
        dead_load_kpa=dead_load,
        live_load_kpa=live_load,
        concrete_fck_mpa=fck,
        category=category
    )

    variants = RedesignGenerator.generate_5_variants(evaluation)

    return {
        "status": "success",
        "evaluation": evaluation,
        "variants": variants
    }


@router.post("/canvas")
async def analyze_canvas_drawing(payload: CanvasFloorplanPayload, db: AsyncSession = Depends(get_db)):
    """
    Analyzes interactive canvas drawing created by the architect.
    Extracts column positions, computes maximum span and cantilevers from drawn geometry.
    """
    elements = payload.elements
    columns = [e for e in elements if e.type == "column"]
    beams = [e for e in elements if e.type == "beam"]
    cantilevers = [e for e in elements if e.type == "cantilever"]
    scale = payload.scale_pixels_per_meter or 40.0

    # Calculate maximum span between drawn elements
    max_span_m = 6.0
    if len(columns) >= 2:
        for i in range(len(columns)):
            for j in range(i + 1, len(columns)):
                c1 = columns[i].start
                c2 = columns[j].start
                dist_px = math.hypot(c2.x - c1.x, c2.y - c1.y)
                dist_m = dist_px / scale
                if 2.0 <= dist_m <= 25.0:
                    max_span_m = max(max_span_m, dist_m)
    
    # Calculate span from drawn beams as well
    for b in beams:
        if b.end:
            dist_px = math.hypot(b.end.x - b.start.x, b.end.y - b.start.y)
            dist_m = dist_px / scale
            if 2.0 <= dist_m <= 25.0:
                max_span_m = max(max_span_m, dist_m)

    # Calculate cantilever length (0.0 if none drawn)
    max_cantilever_m = 0.0
    for cant in cantilevers:
        if cant.end:
            dist_px = math.hypot(cant.end.x - cant.start.x, cant.end.y - cant.start.y)
            max_cantilever_m = max(max_cantilever_m, dist_px / scale)

    # Round to reasonable precision
    max_span_m = round(max_span_m, 1)
    max_cantilever_m = round(max_cantilever_m, 1)

    # Evaluate physics
    evaluation = StructuralCoreEngine.evaluate_structure(
        span_length_m=max_span_m,
        cantilever_length_m=max_cantilever_m,
        beam_height_cm=30.0,
        beam_width_cm=20.0,
        column_height_m=3.2,
        column_section_cm=20.0
    )

    variants = RedesignGenerator.generate_5_variants(evaluation)

    return {
        "status": "success",
        "extracted_geometry": {
            "columns_detected": len(columns),
            "beams_detected": len(beams),
            "cantilevers_detected": len(cantilevers),
            "calculated_max_span_m": max_span_m,
            "calculated_cantilever_m": max_cantilever_m
        },
        "evaluation": evaluation,
        "variants": variants
    }


@router.post("/{project_id}/rerun")
async def rerun_project_analysis(project_id: str, db: AsyncSession = Depends(get_db)):
    """Re-runs analysis on an existing project."""
    analysis = await AnalyzerService.process_project_analysis(db, project_id)
    return {
        "status": "success",
        "project_id": project_id,
        "is_viable": analysis.is_physically_viable,
        "score": analysis.structural_score
    }


@router.post("/micro-adjust")
async def micro_adjust_sliders(payload: Dict[str, Any] = Body(...)):
    """
    Real-time interactive micro-sliders engine (<50ms response).
    Computes deterministic NBR 6118 physics, Direct Stiffness Method (DSM) frame deflection,
    SINAPI 2026 cost, and embodied carbon in real-time.
    """
    span = float(payload.get("span_length_m", 10.0))
    cantilever = float(payload.get("cantilever_length_m", 0.0))
    beam_h = float(payload.get("beam_height_cm", 30.0))
    beam_w = float(payload.get("beam_width_cm", 20.0))
    col_h = float(payload.get("column_height_m", 3.2))
    col_sec = float(payload.get("column_section_cm", 20.0))
    fck = float(payload.get("concrete_fck_mpa", 30.0))
    dead_load = float(payload.get("dead_load_kpa", 4.5))
    live_load = float(payload.get("live_load_kpa", 2.5))
    variant_idx = int(payload.get("selected_variant", 0))

    evaluation = StructuralCoreEngine.evaluate_structure(
        span_length_m=span,
        cantilever_length_m=cantilever,
        beam_height_cm=beam_h,
        beam_width_cm=beam_w,
        column_height_m=col_h,
        column_section_cm=col_sec,
        dead_load_kpa=dead_load,
        live_load_kpa=live_load,
        concrete_fck_mpa=fck
    )

    system_map = {
        0: "standard_rc",
        1: "post_tensioned",
        2: "vierendeel",
        3: "stayed",
        4: "waffle",
        5: "steel_hybrid"
    }
    sys_type = system_map.get(variant_idx, "standard_rc")
    bom = CostCarbonEngine.calculate_bom_and_cost(
        span_length_m=span,
        cantilever_length_m=cantilever,
        beam_height_cm=beam_h,
        beam_width_cm=beam_w,
        column_height_m=col_h,
        column_section_cm=col_sec,
        concrete_fck_mpa=fck,
        system_type=sys_type
    )

    return {
        "status": "success",
        "selected_variant": variant_idx,
        "system_type": sys_type,
        "is_physically_viable": evaluation["is_physically_viable"],
        "structural_score": evaluation["structural_score"],
        "max_deflection_mm": evaluation["max_deflection_mm"],
        "allowable_deflection_mm": evaluation["allowable_deflection_mm"],
        "deflection_ratio": evaluation["deflection_ratio"],
        "dsm_analysis": evaluation.get("dsm_analysis"),
        "bom_and_cost": bom,
        "recommendation": evaluation["compliance_level"]
    }


@router.post("/dsm-solve")
async def solve_direct_stiffness_frame(payload: Dict[str, Any] = Body(...)):
    """
    Direct Stiffness Method (DSM) plane frame solver and Voronoi tributary area partitioner.
    """
    from structura_ai.physics.dsm_solver import DSMSolver
    span = float(payload.get("span_length_m", 10.0))
    cantilever = float(payload.get("cantilever_length_m", 0.0))
    beam_h = float(payload.get("beam_height_cm", 30.0))
    beam_w = float(payload.get("beam_width_cm", 20.0))
    col_h = float(payload.get("column_height_m", 3.2))
    col_sec = float(payload.get("column_section_cm", 20.0))
    load = float(payload.get("distributed_load_kn_m", 25.0))
    bay_y = float(payload.get("bay_depth_m", 6.0))

    dsm = DSMSolver.solve_portal_frame(
        span_length_m=span,
        cantilever_length_m=cantilever,
        beam_height_cm=beam_h,
        beam_width_cm=beam_w,
        column_height_m=col_h,
        column_section_cm=col_sec,
        distributed_load_kn_m=load
    )
    voronoi = DSMSolver.calculate_voronoi_tributary(
        bay_x_m=span,
        bay_y_m=bay_y,
        slab_surface_load_kpa=load / max(bay_y, 1.0)
    )

    return {
        "status": "success",
        "dsm_frame_solution": dsm,
        "voronoi_tributary": voronoi
    }


@router.post("/copilot")
async def copilot_chat(payload: Dict[str, Any] = Body(...)):
    """
    Structura Copilot Multi-Turn Dialog for Architecture & Civil Engineering.
    """
    from structura_ai.ai.gemini_client import GeminiVisionClient
    message = str(payload.get("message", ""))
    context = payload.get("project_context")
    history = payload.get("history")

    result = await GeminiVisionClient.chat_copilot(
        message=message,
        project_context=context,
        chat_history=history
    )
    return {
        "status": "success",
        "reply": result.get("reply", ""),
        "model": result.get("model", ""),
        "source": result.get("source", "")
    }


@router.get("/solow-matrix")
async def get_solow_competitive_matrix():
    """
    Returns Solow growth productivity analysis, competitor feature benchmark matrix,
    the Pareto essential 20%, and the signature killer feature.
    """
    from structura_ai.services.solow_matrix import SolowMatrixService
    return {
        "status": "success",
        "growth_model": SolowMatrixService.get_solow_growth_model(),
        "competitor_matrix": SolowMatrixService.get_competitor_comparison_matrix(),
        "pareto_essential_features": SolowMatrixService.get_pareto_essential_features(),
        "signature_killer_feature": SolowMatrixService.get_signature_killer_feature()
    }



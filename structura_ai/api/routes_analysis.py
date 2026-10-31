"""
API Routes for Real-time Structural Analysis, DSM Frame Solver, and Canvas Extraction.
"""
import math
from typing import Dict, Any
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from structura_ai.database import get_db
from structura_ai.schemas import CanvasFloorplanPayload
from structura_ai.physics.structural_core import StructuralCoreEngine
from structura_ai.physics.dsm_solver import DSMSolver
from structura_ai.physics.optisection import OptiSectionEngine
from structura_ai.services.analyzer_service import AnalyzerService
from structura_ai.workflows.chatbot.runner import run_chat_workflow

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.post("/quick-calc")
async def quick_calculation(payload: Dict[str, Any] = Body(...)):
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
        category=category,
    )

    opti = OptiSectionEngine.optimize_beam_section(
        span_length_m=span,
        concrete_fck_mpa=fck,
        current_beam_height_cm=beam_h,
        current_beam_width_cm=beam_w,
    )

    return {
        "status": "success",
        "evaluation": evaluation,
        "section_optimization": opti,
    }


@router.post("/canvas")
async def analyze_canvas_drawing(payload: CanvasFloorplanPayload):
    elements = payload.elements
    columns = [e for e in elements if e.type == "column"]
    beams = [e for e in elements if e.type == "beam"]
    cantilevers = [e for e in elements if e.type == "cantilever"]
    scale = payload.scale_pixels_per_meter or 40.0

    max_span_m = 6.0
    if len(columns) >= 2:
        for i in range(len(columns)):
            for j in range(i + 1, len(columns)):
                c1 = columns[i].start
                c2 = columns[j].start
                dist_m = math.hypot(c2.x - c1.x, c2.y - c1.y) / scale
                if 2.0 <= dist_m <= 25.0:
                    max_span_m = max(max_span_m, dist_m)

    for b in beams:
        if b.end:
            dist_m = math.hypot(b.end.x - b.start.x, b.end.y - b.start.y) / scale
            if 2.0 <= dist_m <= 25.0:
                max_span_m = max(max_span_m, dist_m)

    max_cantilever_m = 0.0
    for cant in cantilevers:
        if cant.end:
            dist_m = math.hypot(cant.end.x - cant.start.x, cant.end.y - cant.start.y) / scale
            max_cantilever_m = max(max_cantilever_m, dist_m)

    max_span_m = round(max_span_m, 1)
    max_cantilever_m = round(max_cantilever_m, 1)

    evaluation = StructuralCoreEngine.evaluate_structure(
        span_length_m=max_span_m,
        cantilever_length_m=max_cantilever_m,
        beam_height_cm=30.0,
        beam_width_cm=20.0,
        column_height_m=3.2,
        column_section_cm=20.0,
    )

    return {
        "status": "success",
        "extracted_geometry": {
            "columns_detected": len(columns),
            "beams_detected": len(beams),
            "cantilevers_detected": len(cantilevers),
            "calculated_max_span_m": max_span_m,
            "calculated_cantilever_m": max_cantilever_m,
        },
        "evaluation": evaluation,
    }


@router.post("/{project_id}/rerun")
async def rerun_project_analysis(project_id: str, db: AsyncSession = Depends(get_db)):
    analysis = await AnalyzerService.process_project_analysis(db, project_id)
    return {
        "status": "success",
        "project_id": project_id,
        "is_viable": analysis.is_physically_viable,
        "score": analysis.structural_score,
    }


@router.post("/dsm-solve")
async def solve_direct_stiffness_frame(payload: Dict[str, Any] = Body(...)):
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
        distributed_load_kn_m=load,
    )
    voronoi = DSMSolver.calculate_voronoi_tributary(
        bay_x_m=span,
        bay_y_m=bay_y,
        slab_surface_load_kpa=load / max(bay_y, 1.0),
    )

    return {
        "status": "success",
        "dsm_frame_solution": dsm,
        "voronoi_tributary": voronoi,
    }


@router.post("/copilot")
async def copilot_chat_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    Endpoint do Copiloto chamado pelo frontend (viewer_page.js).
    Integra o frontend diretamente com a stack Agno + EverMemOS + RAG Goiás + Tool de Código + LLM Dinâmico.
    Retorna a resposta, os 3 blocos de sugestões do ICP (suggestions), ui_mutations e active_file.
    """
    message = str(payload.get("message", "")).strip() or "Validar estrutura atual"
    user_id = str(payload.get("user_id") or payload.get("username") or "default_user").strip()
    session_id = str(payload.get("session_id") or f"session_{user_id}").strip()
    active_file_id = payload.get("active_file_id") or payload.get("file_id")
    region_country = str(payload.get("region_country") or "BR-GO").strip()
    selected_format = str(payload.get("selected_format") or "autocad").strip()
    force_memory_flush = bool(payload.get("force_memory_flush", False))
    project_context = payload.get("project_context")
    chat_history = payload.get("history")
    api_key = str(payload.get("api_key") or "").strip() or None
    model = str(payload.get("model") or "").strip() or None

    reply, suggestions, ui_mutations, active_file = await run_chat_workflow(
        message=message,
        user_id=user_id,
        session_id=session_id,
        active_file_id=active_file_id,
        region_country=region_country,
        selected_format=selected_format,
        force_memory_flush=force_memory_flush,
        project_context=project_context if isinstance(project_context, dict) else None,
        chat_history=chat_history if isinstance(chat_history, list) else None,
        api_key=api_key,
        model=model,
    )

    return {
        "status": "success",
        "reply": reply,
        "suggestions": suggestions,
        "ui_mutations": [m.model_dump() for m in ui_mutations],
        "active_file": active_file.model_dump() if active_file else None,
        "user_id": user_id,
        "session_id": session_id,
    }


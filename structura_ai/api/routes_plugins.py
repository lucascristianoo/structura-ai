"""
API Routes for Architectural Software Plugins (Blender, Grasshopper, Revit, AutoCAD).
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from structura_ai.database import get_db
from structura_ai.physics.structural_core import StructuralCoreEngine
from structura_ai.physics.generator import RedesignGenerator
from structura_ai.services.analyzer_service import AnalyzerService
from structura_ai.cad.models import UnifiedProjectData, Point3D, BeamElement, ColumnElement, SpanElement, Mesh3DData

router = APIRouter(prefix="/api/plugins", tags=["Plugins"])


class PluginSyncPayload(BaseModel):
    project_name: str = "Projeto Plugin Arquitetura"
    source_software: str = "Blender / CAD"
    span_meters: float = 9.5
    cantilever_meters: float = 0.0
    beam_width_cm: float = 20.0
    beam_height_cm: float = 30.0
    column_height_m: float = 3.0
    column_section_cm: float = 20.0
    fck_mpa: float = 30.0
    dead_load_kn_m: float = 22.0
    live_load_kn_m: float = 3.0
    geometry_metadata: dict[str, Any] = {}


@router.get("/status")
async def plugin_status():
    """Handshake de verificação de status e versão para plugins externos."""
    return {
        "status": "online",
        "service": "Structura.AI Bridge API",
        "version": "2.0.0",
        "standards": ["ABNT NBR 6118:2023", "ABNT NBR 6120:2019"],
        "supported_formats": [".dxf", ".ifc", ".obj", ".gltf", ".glb", ".stl"],
        "supported_plugins": ["Blender 3.x/4.x", "Rhino Grasshopper", "Desktop Hot-Folder Bridge"],
    }


@router.post("/sync")
async def sync_from_plugin(payload: PluginSyncPayload, db: AsyncSession = Depends(get_db)):
    """
    Recebe geometria e parâmetros enviados diretamente de plugins de arquitetura
    e retorna o diagnóstico da física determinística NBR 6118 e os 5 redesigns estruturais.
    """
    diag = StructuralCoreEngine.evaluate_structure(
        span_length_m=payload.span_meters,
        cantilever_length_m=payload.cantilever_meters,
        beam_width_cm=payload.beam_width_cm,
        beam_height_cm=payload.beam_height_cm,
        column_height_m=payload.column_height_m,
        column_section_cm=payload.column_section_cm,
        dead_load_kpa=payload.dead_load_kn_m / 4.0 if payload.dead_load_kn_m > 0 else 4.5,
        live_load_kpa=payload.live_load_kn_m / 2.0 if payload.live_load_kn_m > 0 else 2.5,
        concrete_fck_mpa=payload.fck_mpa,
    )

    variants = []
    if not diag.get("is_physically_viable", False):
        raw_variants = RedesignGenerator.generate_5_variants(diag)
        variants = [
            {
                "variant_number": v.get("variant_number"),
                "variant_name": v.get("title"),
                "strategy": v.get("strategy_name"),
                "concept": v.get("architectural_concept"),
                "solution": v.get("engineering_solution"),
                "metrics_delta": v.get("metrics_delta"),
                "pitch": v.get("pitch_narrative"),
            }
            for v in raw_variants
        ]

    # Criar ou sincronizar projeto no banco de dados para permitir abertura no browser
    project = await AnalyzerService.create_from_preset(db, "horizon_10m")
    project.title = f"[{payload.source_software}] {payload.project_name}"
    project.parameters = {
        "span_length_m": payload.span_meters,
        "cantilever_length_m": payload.cantilever_meters,
        "beam_width_cm": payload.beam_width_cm,
        "beam_height_cm": payload.beam_height_cm,
        "concrete_fck_mpa": payload.fck_mpa,
        "source_software": payload.source_software,
        "geometry_metadata": payload.geometry_metadata,
    }
    await db.commit()
    await db.refresh(project)

    analysis = await AnalyzerService.process_project_analysis(db, project.id)

    return {
        "status": "success",
        "project_id": project.id,
        "studio_url": f"/projects/{project.id}",
        "deterministic_diagnosis": {
            "is_feasible": diag.get("is_physically_viable", False),
            "structural_score": diag.get("structural_score", 0),
            "compliance_level": diag.get("compliance_level", "REPROVADO"),
            "calculated_deflection_mm": diag.get("max_deflection_mm", 0.0),
            "normative_limit_mm": diag.get("allowable_deflection_mm", 0.0),
            "deflection_ratio": diag.get("deflection_ratio", 0.0),
            "failure_reasons": diag.get("failure_reasons", []),
        },
        "redesign_variants": variants,
        "message": "Geometria sincronizada e avaliada com sucesso no Structura.AI",
    }

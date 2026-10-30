"""
Export API Routes for Structural Compliance Dossiers and Vector Blueprints.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from structura_ai.database import get_db
from structura_ai.models import Project, AnalysisResult, RedesignVariant
from structura_ai.services.report_generator import ReportGenerator

router = APIRouter(prefix="/api/export", tags=["Export"])

@router.get("/{project_id}/report.html", response_class=HTMLResponse)
async def export_html_report(project_id: str, db: AsyncSession = Depends(get_db)):
    """Generates and returns printable HTML structural compliance report."""
    stmt = (
        select(Project)
        .options(selectinload(Project.analyses).selectinload(AnalysisResult.variants))
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project or not project.analyses:
        raise HTTPException(status_code=404, detail="Projeto ou análise não encontrados")

    latest_analysis = project.analyses[-1]
    variants_list = [
        {
            "variant_number": v.variant_number,
            "title": v.title,
            "strategy_name": v.strategy_name,
            "architectural_concept": v.architectural_concept,
            "engineering_solution": v.engineering_solution,
            "metrics_delta": v.metrics_delta or {},
            "svg_render": v.svg_render
        }
        for v in latest_analysis.variants
    ]

    analysis_data = {
        "structural_score": latest_analysis.structural_score,
        "is_physically_viable": latest_analysis.is_physically_viable,
        "max_deflection_mm": latest_analysis.max_deflection_mm,
        "allowable_deflection_mm": latest_analysis.allowable_deflection_mm,
        "max_bending_moment_knm": latest_analysis.max_bending_moment_knm,
        "structural_diagnosis_text": latest_analysis.structural_diagnosis_text,
        "failure_reasons": latest_analysis.failure_reasons or [],
        "ai_gemini_review": latest_analysis.ai_gemini_review,
        "ai_model_used": latest_analysis.ai_model_used or "Google Gemini 2.0 Flash"
    }

    project_image_url = project.image_path or (f"/uploads/{project.image_filename}" if project.image_filename else None)

    html_content = ReportGenerator.generate_html_dossier(
        project_title=project.title,
        author=project.author_architect,
        category=project.category,
        analysis_data=analysis_data,
        variants=variants_list,
        project_image_url=project_image_url
    )
    return HTMLResponse(content=html_content)


@router.get("/{project_id}/variant/{variant_number}/svg")
async def export_variant_svg(project_id: str, variant_number: int, db: AsyncSession = Depends(get_db)):
    """Returns raw SVG blueprint for download and CAD import."""
    stmt = (
        select(Project)
        .options(selectinload(Project.analyses).selectinload(AnalysisResult.variants))
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project or not project.analyses:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    latest_analysis = project.analyses[-1]
    variant = next((v for v in latest_analysis.variants if v.variant_number == variant_number), None)
    if not variant or not variant.svg_render:
        raise HTTPException(status_code=404, detail="Blueprint SVG não encontrado para esta variante")

    return Response(content=variant.svg_render, media_type="image/svg+xml")


@router.get("/{project_id}/bim.ifc")
async def export_project_ifc(project_id: str, db: AsyncSession = Depends(get_db)):
    """Exports project geometry and compliance metadata as standard IFC4."""
    from structura_ai.cad.bim_exporter import BimExporter
    stmt = (
        select(Project)
        .options(selectinload(Project.analyses).selectinload(AnalysisResult.variants))
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    latest_analysis = project.analyses[-1] if project.analyses else None
    analysis_dict = {
        "structural_score": latest_analysis.structural_score,
        "max_deflection_mm": latest_analysis.max_deflection_mm,
        "allowable_deflection_mm": latest_analysis.allowable_deflection_mm,
        "is_physically_viable": latest_analysis.is_physically_viable,
    } if latest_analysis else None

    ifc_str = BimExporter.export_project_ifc(
        project_title=project.title,
        parameters=project.parameters or {},
        analysis_data=analysis_dict
    )
    headers = {"Content-Disposition": f'attachment; filename="{project.id}_structura.ifc"'}
    return Response(content=ifc_str, media_type="application/x-step", headers=headers)


@router.get("/{project_id}/cad.dxf")
async def export_project_dxf(project_id: str, db: AsyncSession = Depends(get_db)):
    """Exports project 2D framing blueprint and compliance notes as AutoCAD DXF."""
    from structura_ai.cad.bim_exporter import BimExporter
    stmt = (
        select(Project)
        .options(selectinload(Project.analyses).selectinload(AnalysisResult.variants))
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    latest_analysis = project.analyses[-1] if project.analyses else None
    analysis_dict = {
        "structural_score": latest_analysis.structural_score,
        "max_deflection_mm": latest_analysis.max_deflection_mm,
        "allowable_deflection_mm": latest_analysis.allowable_deflection_mm,
        "is_physically_viable": latest_analysis.is_physically_viable,
    } if latest_analysis else None

    dxf_str = BimExporter.export_project_dxf(
        project_title=project.title,
        parameters=project.parameters or {},
        analysis_data=analysis_dict
    )
    headers = {"Content-Disposition": f'attachment; filename="{project.id}_structura.dxf"'}
    return Response(content=dxf_str, media_type="application/dxf", headers=headers)


@router.get("/{project_id}/variant/{variant_number}/bim.ifc")
async def export_variant_ifc(project_id: str, variant_number: int, db: AsyncSession = Depends(get_db)):
    """Exports a specific redesign variant as standard IFC4."""
    from structura_ai.cad.bim_exporter import BimExporter
    stmt = (
        select(Project)
        .options(selectinload(Project.analyses).selectinload(AnalysisResult.variants))
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project or not project.analyses:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    latest_analysis = project.analyses[-1]
    variant = next((v for v in latest_analysis.variants if v.variant_number == variant_number), None)
    if not variant:
        raise HTTPException(status_code=404, detail=f"Variante {variant_number} não encontrada")

    variant_dict = {
        "variant_number": variant.variant_number,
        "title": variant.title,
        "strategy_name": variant.strategy_name,
        "metrics_delta": variant.metrics_delta or {}
    }
    analysis_dict = {
        "structural_score": latest_analysis.structural_score,
        "max_deflection_mm": latest_analysis.max_deflection_mm,
        "allowable_deflection_mm": latest_analysis.allowable_deflection_mm,
        "is_physically_viable": True,
    }

    ifc_str = BimExporter.export_project_ifc(
        project_title=project.title,
        parameters=project.parameters or {},
        analysis_data=analysis_dict,
        variant=variant_dict
    )
    headers = {"Content-Disposition": f'attachment; filename="{project.id}_variant_{variant_number}.ifc"'}
    return Response(content=ifc_str, media_type="application/x-step", headers=headers)


@router.get("/{project_id}/variant/{variant_number}/cad.dxf")
async def export_variant_dxf(project_id: str, variant_number: int, db: AsyncSession = Depends(get_db)):
    """Exports a specific redesign variant as AutoCAD DXF."""
    from structura_ai.cad.bim_exporter import BimExporter
    stmt = (
        select(Project)
        .options(selectinload(Project.analyses).selectinload(AnalysisResult.variants))
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project or not project.analyses:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    latest_analysis = project.analyses[-1]
    variant = next((v for v in latest_analysis.variants if v.variant_number == variant_number), None)
    if not variant:
        raise HTTPException(status_code=404, detail=f"Variante {variant_number} não encontrada")

    variant_dict = {
        "variant_number": variant.variant_number,
        "title": variant.title,
        "strategy_name": variant.strategy_name,
        "metrics_delta": variant.metrics_delta or {}
    }
    analysis_dict = {
        "structural_score": latest_analysis.structural_score,
        "max_deflection_mm": latest_analysis.max_deflection_mm,
        "allowable_deflection_mm": latest_analysis.allowable_deflection_mm,
        "is_physically_viable": True,
    }

    dxf_str = BimExporter.export_project_dxf(
        project_title=project.title,
        parameters=project.parameters or {},
        analysis_data=analysis_dict,
        variant=variant_dict
    )
    headers = {"Content-Disposition": f'attachment; filename="{project.id}_variant_{variant_number}.dxf"'}
    return Response(content=dxf_str, media_type="application/dxf", headers=headers)


"""
Export API Routes for BIM IFC4 and AutoCAD DXF files.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from structura_ai.database import get_db
from structura_ai.models import Project
from structura_ai.cad.bim_exporter import BimExporter

router = APIRouter(prefix="/api/export", tags=["Export"])


@router.get("/{project_id}/bim.ifc")
async def export_project_ifc(project_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Project)
        .options(selectinload(Project.analyses))
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    latest_analysis = project.analyses[-1] if project.analyses else None
    analysis_dict = (
        {
            "structural_score": latest_analysis.structural_score,
            "max_deflection_mm": latest_analysis.max_deflection_mm,
            "allowable_deflection_mm": latest_analysis.allowable_deflection_mm,
            "is_physically_viable": latest_analysis.is_physically_viable,
        }
        if latest_analysis
        else None
    )

    ifc_str = BimExporter.export_project_ifc(
        project_title=project.title,
        parameters=project.parameters or {},
        analysis_data=analysis_dict,
    )
    headers = {"Content-Disposition": f'attachment; filename="{project.id}_structura.ifc"'}
    return Response(content=ifc_str, media_type="application/x-step", headers=headers)


@router.get("/{project_id}/cad.dxf")
async def export_project_dxf(project_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Project)
        .options(selectinload(Project.analyses))
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    latest_analysis = project.analyses[-1] if project.analyses else None
    analysis_dict = (
        {
            "structural_score": latest_analysis.structural_score,
            "max_deflection_mm": latest_analysis.max_deflection_mm,
            "allowable_deflection_mm": latest_analysis.allowable_deflection_mm,
            "is_physically_viable": latest_analysis.is_physically_viable,
        }
        if latest_analysis
        else None
    )

    dxf_str = BimExporter.export_project_dxf(
        project_title=project.title,
        parameters=project.parameters or {},
        analysis_data=analysis_dict,
    )
    headers = {"Content-Disposition": f'attachment; filename="{project.id}_structura.dxf"'}
    return Response(content=dxf_str, media_type="application/dxf", headers=headers)


@router.get("/{project_id}/report.html")
async def export_project_report_html(project_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Project)
        .options(selectinload(Project.analyses))
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    latest = project.analyses[-1] if project.analyses else None
    params = project.parameters or {}
    status_badge = "APROVADO (NBR 6118)" if (latest and latest.is_physically_viable) else "REPROVADO / REVISÃO NECESSÁRIA"
    html_report = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <title>Memorial Técnico Estrutural — {project.title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1e293b; }}
    h1 {{ color: #0f172a; border-bottom: 2px solid #0284c7; padding-bottom: 0.5rem; }}
    .meta {{ background: #f8fafc; padding: 1rem; border-radius: 8px; border: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <h1>Memorial Descritivo & Validação Físico-Estrutural — {project.title}</h1>
  <div class="meta">
    <p><strong>Arquiteto/Autor:</strong> {project.author_architect}</p>
    <p><strong>Status Normativo:</strong> {status_badge}</p>
    <p><strong>Score Estrutural:</strong> {latest.structural_score if latest else 0.0}/100</p>
    <p><strong>Flecha Máxima Calculada:</strong> {latest.max_deflection_mm if latest else 0.0} mm (Admissível: {latest.allowable_deflection_mm if latest else 0.0} mm)</p>
    <p><strong>Parâmetros Geométricos:</strong> Vão = {params.get('span_length_m')} m | Balanço = {params.get('cantilever_length_m')} m | Viga = {params.get('beam_width_cm')}x{params.get('beam_height_cm')} cm | fck = {params.get('concrete_fck_mpa')} MPa</p>
    <p><strong>Diagnóstico:</strong> {latest.structural_diagnosis_text if latest else 'Sem diagnóstico'}</p>
  </div>
</body>
</html>"""
    return Response(content=html_report, media_type="text/html")


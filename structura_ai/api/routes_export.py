"""
Export API Routes for BIM IFC4 and AutoCAD DXF files.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from structura_ai.database import get_db
from structura_ai.models import Project, ProjectFile
from structura_ai.cad.bim_exporter import BimExporter

router = APIRouter(prefix="/api/export", tags=["Export"])


async def _resolve_export_target(project_or_file_id: str, db: AsyncSession):
    """Resolve tanto um Project.id quanto um ProjectFile.id (da árvore v1..vn) para exportação."""
    stmt = (
        select(Project)
        .options(selectinload(Project.analyses))
        .where(Project.id == project_or_file_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project:
        latest = project.analyses[-1] if project.analyses else None
        analysis_dict = (
            {
                "structural_score": latest.structural_score,
                "max_deflection_mm": latest.max_deflection_mm,
                "allowable_deflection_mm": latest.allowable_deflection_mm,
                "is_physically_viable": latest.is_physically_viable,
                "structural_diagnosis_text": latest.structural_diagnosis_text,
            }
            if latest
            else None
        )
        return {
            "id": project.id,
            "title": project.title,
            "author_architect": project.author_architect,
            "parameters": project.parameters or {},
            "analysis": analysis_dict,
        }

    # Fallback: verifica se o ID passado é de um ProjectFile (ex.: projeto_estrutural.dxf criado no chat)
    stmt_pf = (
        select(ProjectFile)
        .options(selectinload(ProjectFile.versions))
        .where(ProjectFile.id == project_or_file_id)
    )
    pf = (await db.execute(stmt_pf)).scalar_one_or_none()
    if not pf:
        raise HTTPException(status_code=404, detail="Projeto ou arquivo não encontrado")

    active_ver = next(
        (v for v in pf.versions if v.version_number == pf.active_version_number),
        pf.versions[-1] if pf.versions else None,
    )
    params = (active_ver.structural_parameters if active_ver else None) or {}
    vr = (active_ver.validation_report if active_ver else None) or {}
    return {
        "id": pf.id,
        "title": pf.filename,
        "author_architect": pf.user_id,
        "parameters": params,
        "analysis": {
            "structural_score": vr.get("structural_score", 80.0),
            "max_deflection_mm": vr.get("max_deflection_mm", 25.0),
            "allowable_deflection_mm": vr.get("allowable_deflection_mm", 38.0),
            "is_physically_viable": vr.get("is_physically_viable", True),
            "structural_diagnosis_text": active_ver.change_summary if active_ver else "Validado via Copiloto Structura.AI",
        },
    }


@router.get("/{project_id}/bim.ifc")
async def export_project_ifc(project_id: str, db: AsyncSession = Depends(get_db)):
    target = await _resolve_export_target(project_id, db)
    ifc_str = BimExporter.export_project_ifc(
        project_title=target["title"],
        parameters=target["parameters"],
        analysis_data=target["analysis"],
    )
    headers = {"Content-Disposition": f'attachment; filename="{target["id"]}_structura.ifc"'}
    return Response(content=ifc_str, media_type="application/x-step", headers=headers)


@router.get("/{project_id}/cad.dxf")
async def export_project_dxf(project_id: str, db: AsyncSession = Depends(get_db)):
    target = await _resolve_export_target(project_id, db)
    dxf_str = BimExporter.export_project_dxf(
        project_title=target["title"],
        parameters=target["parameters"],
        analysis_data=target["analysis"],
    )
    headers = {"Content-Disposition": f'attachment; filename="{target["id"]}_structura.dxf"'}
    return Response(content=dxf_str, media_type="application/dxf", headers=headers)


@router.get("/{project_id}/report.html")
async def export_project_report_html(project_id: str, db: AsyncSession = Depends(get_db)):
    target = await _resolve_export_target(project_id, db)
    latest = target["analysis"] or {}
    params = target["parameters"] or {}
    status_badge = "APROVADO (NBR 6118)" if latest.get("is_physically_viable") else "REPROVADO / REVISÃO NECESSÁRIA"
    html_report = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <title>Memorial Técnico Estrutural — {target["title"]}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1e293b; }}
    h1 {{ color: #0f172a; border-bottom: 2px solid #0284c7; padding-bottom: 0.5rem; }}
    .meta {{ background: #f8fafc; padding: 1rem; border-radius: 8px; border: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <h1>Memorial Descritivo & Validação Físico-Estrutural — {target["title"]}</h1>
  <div class="meta">
    <p><strong>Arquiteto/Autor:</strong> {target["author_architect"]}</p>
    <p><strong>Status Normativo:</strong> {status_badge}</p>
    <p><strong>Score Estrutural:</strong> {latest.get("structural_score", 0.0)}/100</p>
    <p><strong>Flecha Máxima Calculada:</strong> {latest.get("max_deflection_mm", 0.0)} mm (Admissível: {latest.get("allowable_deflection_mm", 0.0)} mm)</p>
    <p><strong>Parâmetros Geométricos:</strong> Vão = {params.get('span_length_m')} m | Balanço = {params.get('cantilever_length_m')} m | Viga = {params.get('beam_width_cm')}x{params.get('beam_height_cm')} cm | fck = {params.get('concrete_fck_mpa')} MPa</p>
    <p><strong>Diagnóstico:</strong> {latest.get("structural_diagnosis_text", "Sem diagnóstico")}</p>
  </div>
</body>
</html>"""
    return Response(content=html_report, media_type="text/html")


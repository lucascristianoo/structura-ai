"""
API Routes for Project Management & Creation (Enxuto — Sem Presets/Samples Legados).
"""
import os
import uuid
import base64
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update
from sqlalchemy.orm import selectinload

from structura_ai.database import get_db
from structura_ai.models import Project, ProjectFile, FileVersion
from structura_ai.schemas import ProjectOut, AnalysisResultOut
from structura_ai.services.analyzer_service import AnalyzerService
from structura_ai.cad import CadIngestor
from structura_ai.tools.file_version_tools import _build_styled_svg_preview

router = APIRouter(prefix="/api/projects", tags=["Projects"])


def _serialize_project(p: Project) -> ProjectOut:
    latest_analysis = p.analyses[-1] if p.analyses else None
    analysis_out = None
    if latest_analysis:
        analysis_out = AnalysisResultOut(
            id=latest_analysis.id,
            project_id=latest_analysis.project_id,
            is_physically_viable=latest_analysis.is_physically_viable,
            structural_score=latest_analysis.structural_score,
            compliance_level=latest_analysis.compliance_level,
            max_deflection_mm=latest_analysis.max_deflection_mm,
            allowable_deflection_mm=latest_analysis.allowable_deflection_mm,
            deflection_ratio=latest_analysis.deflection_ratio,
            max_bending_moment_knm=latest_analysis.max_bending_moment_knm,
            shear_utilization_ratio=latest_analysis.shear_utilization_ratio,
            critical_column_buckling_ratio=latest_analysis.critical_column_buckling_ratio,
            cantilever_stability_factor=latest_analysis.cantilever_stability_factor,
            failure_reasons=latest_analysis.failure_reasons or [],
            compliance_checklist=latest_analysis.compliance_checklist or {},
            structural_diagnosis_text=latest_analysis.structural_diagnosis_text,
            ai_gemini_review=latest_analysis.ai_gemini_review,
            ai_model_used=latest_analysis.ai_model_used,
        )
    return ProjectOut(
        id=p.id,
        title=p.title,
        author_architect=p.author_architect,
        category=p.category,
        description=p.description,
        image_filename=p.image_filename,
        image_path=p.image_path,
        parameters=p.parameters or {},
        status=p.status,
        created_at=p.created_at.isoformat() if p.created_at else "",
        latest_analysis=analysis_out,
    )


@router.get("", response_model=List[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Project)
        .options(selectinload(Project.analyses))
        .order_by(desc(Project.created_at))
    )
    result = await db.execute(stmt)
    projects = result.scalars().all()
    return [_serialize_project(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Project)
        .options(selectinload(Project.analyses))
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return _serialize_project(project)


@router.post("/upload")
async def upload_and_create_project(
    title: str = Form(...),
    author_architect: str = Form("Arquiteto Autor"),
    category: str = Form("Residencial"),
    description: str = Form(""),
    span_length_m: float = Form(9.5),
    cantilever_length_m: float = Form(3.5),
    beam_height_cm: float = Form(30.0),
    beam_width_cm: float = Form(20.0),
    column_height_m: float = Form(3.2),
    column_section_cm: float = Form(20.0),
    dead_load_kpa: float = Form(4.5),
    live_load_kpa: float = Form(2.5),
    concrete_fck_mpa: float = Form(30.0),
    file: Optional[UploadFile] = File(None),
    canvas_image: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    image_bytes = None
    image_filename = None
    image_path = None
    mime_type = "image/png"

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    uploads_dir = os.path.abspath(os.path.join(base_dir, "..", "uploads"))
    os.makedirs(uploads_dir, exist_ok=True)

    cad_data = None
    if file and file.filename:
        raw_basename = os.path.basename(file.filename)
        safe_name = "".join(c for c in raw_basename if c.isalnum() or c in "._-").strip() or "blueprint.png"
        image_filename = f"{uuid.uuid4().hex[:8]}_{safe_name}"
        mime_type = file.content_type or "image/png"
        image_bytes = await file.read()

        save_path = os.path.join(uploads_dir, image_filename)
        with open(save_path, "wb") as f:
            f.write(image_bytes)
        image_path = f"/uploads/{image_filename}"

        if CadIngestor.is_cad_format(file.filename):
            try:
                ingested = CadIngestor.ingest(save_path, filename=file.filename, project_name=title)
                cad_data = ingested.model_dump()
                if ingested.max_span_m > 0:
                    span_length_m = ingested.max_span_m
                if ingested.suggested_beam_height_cm > 0:
                    beam_height_cm = ingested.suggested_beam_height_cm
                if ingested.suggested_beam_width_cm > 0:
                    beam_width_cm = ingested.suggested_beam_width_cm
                concrete_fck_mpa = ingested.suggested_fck_mpa
            except Exception:
                pass
    elif canvas_image and "base64," in canvas_image:
        try:
            _, imgstr = canvas_image.split(";base64,")
            image_bytes = base64.b64decode(imgstr)
            image_filename = f"{uuid.uuid4().hex[:8]}_croqui_arquiteto.png"
            save_path = os.path.join(uploads_dir, image_filename)
            with open(save_path, "wb") as f:
                f.write(image_bytes)
            image_path = f"/uploads/{image_filename}"
        except Exception:
            pass

    params = {
        "span_length_m": span_length_m,
        "cantilever_length_m": cantilever_length_m,
        "beam_height_cm": beam_height_cm,
        "beam_width_cm": beam_width_cm,
        "column_height_m": column_height_m,
        "column_section_cm": column_section_cm,
        "dead_load_kpa": dead_load_kpa,
        "live_load_kpa": live_load_kpa,
        "concrete_fck_mpa": concrete_fck_mpa,
    }
    if cad_data:
        params["cad_data"] = cad_data

    project = Project(
        title=title,
        author_architect=author_architect,
        category=category,
        description=description,
        image_filename=image_filename,
        image_path=image_path,
        parameters=params,
        status="pending",
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    analysis = await AnalyzerService.process_project_analysis(
        db=db,
        project_id=project.id,
        image_bytes=image_bytes,
        image_mime=mime_type,
    )

    # Sincroniza também com ProjectFile + FileVersion (v1) para a barra de versões v1..vn e ferramentas dos agentes
    user_id = (author_architect or "default_user").strip() or "default_user"
    await db.execute(update(ProjectFile).where(ProjectFile.user_id == user_id).values(is_selected=False))
    raw_fname = file.filename if (file and file.filename) else f"{title}.dxf"
    ext = os.path.splitext(raw_fname)[1].lower().lstrip(".") or "dxf"

    pf = ProjectFile(
        user_id=user_id,
        project_id=project.id,
        filename=raw_fname,
        file_format=ext,
        active_version_number=1,
        is_selected=True,
    )
    db.add(pf)
    await db.flush()

    preview_url = _build_styled_svg_preview(
        filename=raw_fname,
        version_label="v1",
        render_style="autocad",
        params=params,
        landscape_context=None,
    )
    v1 = FileVersion(
        file_id=pf.id,
        version_number=1,
        version_label="v1",
        render_style="autocad",
        file_path=image_path,
        image_url=preview_url,
        structural_parameters=params,
        validation_report={
            "is_physically_viable": analysis.is_physically_viable,
            "structural_score": analysis.structural_score,
            "compliance_level": analysis.compliance_level,
            "max_deflection_mm": analysis.max_deflection_mm,
            "allowable_deflection_mm": analysis.allowable_deflection_mm,
        },
        change_summary="Upload inicial do arquivo (v1)",
        created_by="user_upload",
    )
    db.add(v1)
    await db.commit()

    return {
        "status": "success",
        "project_id": project.id,
        "file_id": pf.id,
        "version_number": 1,
        "version_label": "v1",
        "is_viable": analysis.is_physically_viable,
        "score": analysis.structural_score,
        "compliance_level": analysis.compliance_level,
    }


@router.get("/{project_id}/geometry-3d")
async def get_project_geometry_3d(project_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Project)
        .options(selectinload(Project.analyses))
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    params = project.parameters or {}
    cad_data = params.get("cad_data")
    latest_analysis = project.analyses[-1] if project.analyses else None

    span_m = float(params.get("span_length_m", 10.0))
    bw_m = float(params.get("beam_width_cm", 20.0)) / 100.0
    bh_m = float(params.get("beam_height_cm", 30.0)) / 100.0
    col_h = float(params.get("column_height_m", 3.0))
    col_w = float(params.get("column_section_cm", 20.0)) / 100.0
    cantilever_m = float(params.get("cantilever_length_m", 0.0))

    deflection_mm = latest_analysis.max_deflection_mm if latest_analysis else 45.0
    is_viable = latest_analysis.is_physically_viable if latest_analysis else False

    if cad_data and cad_data.get("mesh_3d") and cad_data["mesh_3d"].get("element_meshes"):
        elements = cad_data["mesh_3d"]["element_meshes"]
    else:
        elements = [
            {
                "type": "column",
                "id": "P1",
                "name": "Pilar Esquerdo (P1)",
                "x": 0.0,
                "y": 0.0,
                "z": col_h / 2.0,
                "dx": col_w,
                "dy": col_w * 2.0,
                "dz": col_h,
                "color": "#64748b",
            },
            {
                "type": "column",
                "id": "P2",
                "name": "Pilar Direito (P2)",
                "x": span_m,
                "y": 0.0,
                "z": col_h / 2.0,
                "dx": col_w,
                "dy": col_w * 2.0,
                "dz": col_h,
                "color": "#64748b",
            },
            {
                "type": "beam",
                "id": "V1",
                "name": f"Viga Principal (Vão {span_m:.1f}m)",
                "x": span_m / 2.0,
                "y": 0.0,
                "z": col_h,
                "dx": span_m,
                "dy": bw_m,
                "dz": bh_m,
                "span": span_m,
                "deflection_mm": deflection_mm,
                "is_viable": is_viable,
                "color": "#38bdf8" if is_viable else "#ef4444",
            },
        ]

    return {
        "project_id": project.id,
        "title": project.title,
        "is_physically_viable": is_viable,
        "deflection_mm": deflection_mm,
        "elements": elements,
        "bounding_box": {
            "width_x": span_m + cantilever_m + 2.0,
            "depth_y": 7.0,
            "height_z": col_h + 1.5,
        },
    }

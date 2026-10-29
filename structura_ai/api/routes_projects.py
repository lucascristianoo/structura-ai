"""
API Routes for Project Management & Creation.
"""
import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from structura_ai.database import get_db
from structura_ai.models import Project, AnalysisResult, RedesignVariant
from structura_ai.schemas import ProjectOut, AnalysisResultOut, RedesignVariantOut
from structura_ai.services.analyzer_service import AnalyzerService
from structura_ai.services.sample_projects import get_preset_list, SAMPLE_PRESETS

router = APIRouter(prefix="/api/projects", tags=["Projects"])

@router.get("", response_model=List[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)):
    """Lists all architectural projects and their latest analysis status."""
    stmt = (
        select(Project)
        .options(
            selectinload(Project.analyses).selectinload(AnalysisResult.variants)
        )
        .order_by(desc(Project.created_at))
    )
    result = await db.execute(stmt)
    projects = result.scalars().all()

    output = []
    for p in projects:
        latest_analysis = p.analyses[-1] if p.analyses else None
        analysis_out = None
        if latest_analysis:
            variants_out = [
                RedesignVariantOut(
                    variant_number=v.variant_number,
                    title=v.title,
                    strategy_name=v.strategy_name,
                    architectural_concept=v.architectural_concept,
                    engineering_solution=v.engineering_solution,
                    metrics_delta=v.metrics_delta or {},
                    svg_render=v.svg_render,
                    visual_features=v.visual_features or [],
                    pitch_narrative=v.pitch_narrative
                )
                for v in latest_analysis.variants
            ]
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
                variants=variants_out
            )

        output.append(
            ProjectOut(
                id=p.id,
                title=p.title,
                author_architect=p.author_architect,
                category=p.category,
                description=p.description,
                image_filename=p.image_filename,
                parameters=p.parameters or {},
                status=p.status,
                created_at=p.created_at.isoformat() if p.created_at else "",
                latest_analysis=analysis_out
            )
        )
    return output


@router.get("/presets")
async def list_presets():
    """Returns curated demo presets for HackTown."""
    return get_preset_list()


@router.post("/preset/{preset_key}")
async def load_preset_project(preset_key: str, db: AsyncSession = Depends(get_db)):
    """Loads a preset project, immediately executes physics analysis and generates 5 redesigns."""
    project = await AnalyzerService.create_from_preset(db, preset_key)
    analysis = await AnalyzerService.process_project_analysis(db, project.id)
    return {
        "status": "success",
        "project_id": project.id,
        "is_viable": analysis.is_physically_viable,
        "score": analysis.structural_score,
        "message": "Projeto pré-configurado analisado com sucesso!"
    }


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Returns details, physical metrics and 5 visual redesigns for a project."""
    stmt = (
        select(Project)
        .options(
            selectinload(Project.analyses).selectinload(AnalysisResult.variants)
        )
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    latest_analysis = project.analyses[-1] if project.analyses else None
    analysis_out = None
    if latest_analysis:
        variants_out = [
            RedesignVariantOut(
                variant_number=v.variant_number,
                title=v.title,
                strategy_name=v.strategy_name,
                architectural_concept=v.architectural_concept,
                engineering_solution=v.engineering_solution,
                metrics_delta=v.metrics_delta or {},
                svg_render=v.svg_render,
                visual_features=v.visual_features or [],
                pitch_narrative=v.pitch_narrative
            )
            for v in latest_analysis.variants
        ]
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
            variants=variants_out
        )

    return ProjectOut(
        id=project.id,
        title=project.title,
        author_architect=project.author_architect,
        category=project.category,
        description=project.description,
        image_filename=project.image_filename,
        parameters=project.parameters or {},
        status=project.status,
        created_at=project.created_at.isoformat() if project.created_at else "",
        latest_analysis=analysis_out
    )


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
    db: AsyncSession = Depends(get_db)
):
    """
    Creates project with file upload (image/blueprint) and runs complete physical & AI analysis.
    """
    image_bytes = None
    image_filename = None
    mime_type = "image/png"

    if file and file.filename:
        image_filename = file.filename
        mime_type = file.content_type or "image/png"
        image_bytes = await file.read()
        
        # Save file to uploads folder
        os.makedirs("./uploads", exist_ok=True)
        save_path = os.path.join("./uploads", image_filename)
        with open(save_path, "wb") as f:
            f.write(image_bytes)

    project = Project(
        title=title,
        author_architect=author_architect,
        category=category,
        description=description,
        image_filename=image_filename,
        parameters={
            "span_length_m": span_length_m,
            "cantilever_length_m": cantilever_length_m,
            "beam_height_cm": beam_height_cm,
            "beam_width_cm": beam_width_cm,
            "column_height_m": column_height_m,
            "column_section_cm": column_section_cm,
            "dead_load_kpa": dead_load_kpa,
            "live_load_kpa": live_load_kpa,
            "concrete_fck_mpa": concrete_fck_mpa,
        },
        status="pending"
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Trigger analysis immediately
    analysis = await AnalyzerService.process_project_analysis(
        db=db,
        project_id=project.id,
        image_bytes=image_bytes,
        image_mime=mime_type
    )

    return {
        "status": "success",
        "project_id": project.id,
        "is_viable": analysis.is_physically_viable,
        "score": analysis.structural_score,
        "compliance_level": analysis.compliance_level
    }

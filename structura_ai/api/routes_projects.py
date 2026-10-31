"""
API Routes for Project Management & Creation.
"""
import os
import shutil
import uuid
import base64
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
from structura_ai.cad import CadIngestor

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
                image_path=p.image_path,
                parameters=p.parameters or {},
                status=p.status,
                created_at=p.created_at.isoformat() if p.created_at else "",
                latest_analysis=analysis_out
            )
        )
    return output


@router.get("/samples/list")
async def list_cad_samples():
    """Retorna lista de amostras CAD/BIM oficiais disponíveis para teste de 1 clique."""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    samples_dir = os.path.join(root_dir, "downloads", "test_samples")
    samples = []
    
    presets_meta = {
        "residencia_horizon_10m.dxf": {
            "name": "Residência Horizon (Vão 10m - DXF)",
            "format": "DXF",
            "scenario": 1,
            "desc": "Prancha CAD 2D de residência com vão livre envidraçado de 10m e viga delgada.",
            "expected_verdict": "Reprovado por flecha excessiva (ELS)"
        },
        "cobertura_balanco_critico.dxf": {
            "name": "Cobertura em Balanço Crítico (4.5m - DXF)",
            "format": "DXF",
            "scenario": 1,
            "desc": "Marquise de entrada com balanço longo sob risco de deformação excessiva.",
            "expected_verdict": "Instabilidade de balanço (Requer tirantes em V)"
        },
        "residencia_horizon_3d.obj": {
            "name": "Residência Horizon 3D (Vão 13m - OBJ)",
            "format": "OBJ 3D",
            "scenario": 1,
            "desc": "Malha tridimensional volumétrica para renderização direta no Three.js.",
            "expected_verdict": "Modelo volumétrico conceitual"
        },
        "sobrado_grid_racional_5m.dxf": {
            "name": "Sobrado Grelha Racional (Vão 5m - DXF)",
            "format": "DXF",
            "scenario": 2,
            "desc": "Prancha CAD 2D de sobrado contemporâneo com modulação racional 5.0m.",
            "expected_verdict": "100% Conforme NBR 6118 (Folga de 59%)"
        },
        "sobrado_conforme_nbr6118.ifc": {
            "name": "Sobrado Racional BIM (Vão 5m - IFC)",
            "format": "IFC",
            "scenario": 2,
            "desc": "Modelo BIM IFC4 de sobrado estruturado com vigas e pilares em conformidade plena.",
            "expected_verdict": "Total conformidade ELS e ELU (Score 98.5)"
        },
        "pavilhao_estrutural_bim.ifc": {
            "name": "Pavilhão Multiuso BIM (Vão 10.5m - IFC)",
            "format": "IFC",
            "scenario": 1,
            "desc": "Modelo BIM IFC4 com entidades IfcBeam e IfcColumn prontas para extração.",
            "expected_verdict": "Requer protensão ou grelha waffle"
        }
    }

    if os.path.exists(samples_dir):
        for f in sorted(os.listdir(samples_dir)):
            if f in presets_meta:
                meta = presets_meta[f]
                samples.append({
                    "id": f,
                    "filename": f,
                    "title": meta["name"],
                    "format": meta["format"],
                    "scenario": meta.get("scenario", 1),
                    "description": meta["desc"],
                    "expected_verdict": meta["expected_verdict"],
                    "download_url": f"/downloads/samples/{f}"
                })
    return samples


@router.post("/samples/load/{sample_id}")
async def load_cad_sample(sample_id: str, db: AsyncSession = Depends(get_db)):
    """Carrega uma amostra CAD/BIM oficial, executa a física determinística e redireciona."""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sample_path = os.path.join(root_dir, "downloads", "test_samples", sample_id)
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail=f"Amostra '{sample_id}' não encontrada.")

    ingested = CadIngestor.ingest(sample_path, filename=sample_id)
    
    project = Project(
        title=f"[Amostra {ingested.source_format.upper()}] {ingested.project_name}",
        author_architect="Studio HackTown 2026",
        category="Residencial Contemporâneo",
        description=f"Projeto importado da amostra oficial '{sample_id}'. Vão máximo detectado: {ingested.max_span_m:.1f}m.",
        parameters={
            "span_length_m": ingested.max_span_m,
            "cantilever_length_m": ingested.max_cantilever_m,
            "beam_height_cm": ingested.suggested_beam_height_cm,
            "beam_width_cm": ingested.suggested_beam_width_cm,
            "column_height_m": 3.2,
            "column_section_cm": 20.0,
            "dead_load_kpa": 4.5,
            "live_load_kpa": 2.5,
            "concrete_fck_mpa": ingested.suggested_fck_mpa,
            "cad_data": ingested.model_dump(),
        },
        status="active"
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    analysis = await AnalyzerService.process_project_analysis(db, project.id)

    return {
        "status": "success",
        "project_id": project.id,
        "is_viable": analysis.is_physically_viable,
        "score": analysis.structural_score,
        "studio_url": f"/projects/{project.id}",
        "message": f"Amostra {sample_id} carregada e calculada com sucesso!"
    }



@router.post("/preset/{preset_key}")
async def load_preset_project(preset_key: str, db: AsyncSession = Depends(get_db)):
    """Loads a preset project, immediately executes physics analysis and generates 5 redesigns."""
    if preset_key not in SAMPLE_PRESETS:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_key}' não encontrado.")
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
        image_path=project.image_path,
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
    canvas_image: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates project with file upload (image/blueprint) or interactive canvas drawing,
    and runs complete physical & AI analysis.
    """
    image_bytes = None
    image_filename = None
    image_path = None
    mime_type = "image/png"

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    uploads_dir = os.path.abspath(os.path.join(base_dir, "..", "uploads"))
    os.makedirs(uploads_dir, exist_ok=True)

    cad_data = None
    if file and file.filename:
        # Sanitize against path traversal attacks (e.g. ../../)
        raw_basename = os.path.basename(file.filename)
        safe_name = "".join(c for c in raw_basename if c.isalnum() or c in "._-").strip() or "blueprint.png"
        image_filename = f"{uuid.uuid4().hex[:8]}_{safe_name}"
        mime_type = file.content_type or "image/png"
        image_bytes = await file.read()
        
        save_path = os.path.join(uploads_dir, image_filename)
        with open(save_path, "wb") as f:
            f.write(image_bytes)
        image_path = f"/uploads/{image_filename}"

        # Ingestão CAD/BIM especializada
        if CadIngestor.is_cad_format(file.filename):
            try:
                ingested = CadIngestor.ingest(save_path, filename=file.filename, project_name=title)
                cad_data = ingested.model_dump()
                if ingested.max_span_m > 0:
                    span_length_m = ingested.max_span_m
                cantilever_length_m = ingested.max_cantilever_m
                if ingested.suggested_beam_height_cm > 0:
                    beam_height_cm = ingested.suggested_beam_height_cm
                if ingested.suggested_beam_width_cm > 0:
                    beam_width_cm = ingested.suggested_beam_width_cm
                concrete_fck_mpa = ingested.suggested_fck_mpa
            except Exception as e:
                print(f"Aviso: Ingestão CAD falhou ({e}), utilizando parâmetros padrão.")
    elif canvas_image and "base64," in canvas_image:
        # Save canvas drawing as image
        try:
            format_meta, imgstr = canvas_image.split(";base64,")
            image_bytes = base64.b64decode(imgstr)
            image_filename = f"{uuid.uuid4().hex[:8]}_croqui_arquiteto.png"
            mime_type = "image/png"
            save_path = os.path.join(uploads_dir, image_filename)
            with open(save_path, "wb") as f:
                f.write(image_bytes)
            image_path = f"/uploads/{image_filename}"
        except Exception:
            image_bytes = None
            image_filename = None
            image_path = None

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


@router.get("/{project_id}/geometry-3d")
async def get_project_geometry_3d(project_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retorna os dados geométricos e a malha 3D formatados para renderização
    direta no Three.js (Sólido, Wireframe, Raio-X e Mapa de Tensões FEA).
    """
    stmt = (
        select(Project)
        .options(selectinload(Project.analyses).selectinload(AnalysisResult.variants))
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    params = project.parameters or {}
    cad_data = params.get("cad_data")
    latest_analysis = project.analyses[-1] if project.analyses else None

    # Parâmetros estruturais
    span_m = float(params.get("span_length_m", 10.0))
    bw_m = float(params.get("beam_width_cm", 20.0)) / 100.0
    bh_m = float(params.get("beam_height_cm", 30.0)) / 100.0
    col_h = float(params.get("column_height_m", 3.0))
    col_w = float(params.get("column_section_cm", 20.0)) / 100.0
    cantilever_m = float(params.get("cantilever_length_m", 0.0))

    deflection_mm = latest_analysis.max_deflection_mm if latest_analysis else 45.0
    is_viable = latest_analysis.is_physically_viable if latest_analysis else False

    # Se já houver malha CAD extraída, utiliza com enriquecimento de tensões
    if cad_data and cad_data.get("mesh_3d") and cad_data["mesh_3d"].get("element_meshes"):
        elements = cad_data["mesh_3d"]["element_meshes"]
    else:
        # Gerar malha paramétrica completa para visualização 3D didática
        elements = [
            # Pilares de apoio
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
            # Viga principal
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
            # Laje de cobertura / piso superior
            {
                "type": "slab",
                "id": "L1",
                "name": "Laje Maciça Panorâmica",
                "x": span_m / 2.0,
                "y": 2.5,
                "z": col_h + (bh_m / 2.0) + 0.06,
                "dx": span_m + (cantilever_m if cantilever_m > 0 else 0.5),
                "dy": 5.0,
                "dz": 0.12,
                "color": "#1e293b",
            }
        ]

        if cantilever_m > 0:
            elements.append({
                "type": "beam",
                "id": "V_BAL",
                "name": f"Balanço em Balanço ({cantilever_m:.1f}m)",
                "x": span_m + (cantilever_m / 2.0),
                "y": 0.0,
                "z": col_h,
                "dx": cantilever_m,
                "dy": bw_m,
                "dz": bh_m,
                "color": "#f97316",
            })

    # Curva da deformada discretizada em 20 pontos ao longo do vão
    deflection_curve = []
    num_pts = 21
    amplification = 25.0  # Fator didático para escala visível da flecha
    for i in range(num_pts):
        xi = (i / (num_pts - 1)) * span_m
        # Equação elástica parabólica aproximada para carga distribuída: f(x) = (16 * f_max / L^2) * x * (L - x)
        delta_z = -(4.0 * (deflection_mm / 1000.0) * amplification / (span_m ** 2)) * xi * (span_m - xi)
        # Tensão relativa (0.0 a 1.0)
        stress_ratio = (4.0 / (span_m ** 2)) * xi * (span_m - xi)
        deflection_curve.append({
            "x": round(xi, 3),
            "y": 0.0,
            "z": round(col_h + delta_z, 4),
            "stress_ratio": round(stress_ratio, 3),
        })

    # Dados das 5 soluções alternativas para alternância no 3D
    variants_3d = []
    if latest_analysis and latest_analysis.variants:
        for v in latest_analysis.variants:
            variants_3d.append({
                "variant_number": v.variant_number,
                "title": v.title,
                "strategy": v.strategy_name,
                "metrics_delta": v.metrics_delta,
                "structural_modifications": v.visual_features,
            })

    return {
        "project_id": project.id,
        "title": project.title,
        "is_physically_viable": is_viable,
        "deflection_mm": deflection_mm,
        "elements": elements,
        "deflection_curve": deflection_curve,
        "bounding_box": {
            "width_x": span_m + cantilever_m + 2.0,
            "depth_y": 7.0,
            "height_z": col_h + 1.5,
        },
        "variants_3d": variants_3d,
    }


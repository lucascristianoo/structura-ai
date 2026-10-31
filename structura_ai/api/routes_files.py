"""
Rotas de Gestão de Arquivos Carregados, Versionamento (v1..vn) por Arquivo,
Mudança de Estilo (AutoCAD / Blender) e Tool de Código (Arquitetura Excalidraw).
"""

import json
import os
import uuid
from typing import List, Optional

from agno.run import RunContext
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from structura_ai.cad import CadIngestor
from structura_ai.config import settings
from structura_ai.database import get_db
from structura_ai.models import FileVersion, ProjectFile, UserMemoryDecision
from structura_ai.physics.structural_core import StructuralCoreEngine
from structura_ai.schemas import (
    ChangeStyleRequest,
    FileVersionOut,
    GenerateCodeRequest,
    ProjectFileOut,
    SelectFileRequest,
)
from structura_ai.tools.code_generator_tool import generate_cad_code_tool
from structura_ai.tools.file_version_tools import (
    _build_styled_svg_preview,
    change_file_style,
    switch_file_version,
)
from structura_ai.workflows.chatbot.runner import (
    serialize_file_version,
    serialize_project_file,
)

router = APIRouter(prefix="/api/v1/files", tags=["Files & Versioning (v1..vn)"])


@router.post("/upload", response_model=ProjectFileOut)
async def upload_project_file(
    file: UploadFile = File(...),
    user_id: str = Form("default_user"),
    render_style: str = Form("autocad"),
    landscape_context: Optional[str] = Form(None),
    span_length_m: float = Form(9.5),
    cantilever_length_m: float = Form(3.5),
    beam_height_cm: float = Form(35.0),
    beam_width_cm: float = Form(20.0),
    column_height_m: float = Form(3.2),
    column_section_cm: float = Form(25.0),
    concrete_fck_mpa: float = Form(30.0),
    db: AsyncSession = Depends(get_db),
):
    """
    Carrega um novo arquivo no workspace do usuário, extrai geometria CAD/BIM se aplicável,
    torna este arquivo o ativo (`is_selected=True`) e inicializa sua árvore de versões com a `v1`.
    """
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    raw_basename = os.path.basename(file.filename or "projeto.dxf")
    safe_name = "".join(c for c in raw_basename if c.isalnum() or c in "._-").strip() or "projeto.dxf"
    stem, ext_dot = os.path.splitext(safe_name)
    ext = ext_dot.lower().lstrip(".")[:12] or "dxf"
    safe_name = f"{(stem[:96] or 'projeto')}.{ext}"

    stored_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    save_path = os.path.join(settings.UPLOAD_DIR, stored_name)
    content_bytes = await file.read()
    with open(save_path, "wb") as f:
        f.write(content_bytes)

    if CadIngestor.is_cad_format(safe_name) and span_length_m == 9.5 and beam_height_cm == 35.0:
        try:
            ingested = CadIngestor.ingest(save_path, filename=safe_name, project_name=safe_name)
            if getattr(ingested, "total_entities", 0) > 0:
                if ingested.max_span_m > 0:
                    span_length_m = float(ingested.max_span_m)
                if ingested.max_cantilever_m >= 0:
                    cantilever_length_m = float(ingested.max_cantilever_m)
                if ingested.suggested_beam_height_cm > 0:
                    beam_height_cm = float(ingested.suggested_beam_height_cm)
                if ingested.suggested_beam_width_cm > 0:
                    beam_width_cm = float(ingested.suggested_beam_width_cm)
                if ingested.suggested_fck_mpa > 0:
                    concrete_fck_mpa = float(ingested.suggested_fck_mpa)
        except Exception:
            pass

    params = {
        "span_length_m": span_length_m,
        "cantilever_length_m": cantilever_length_m,
        "beam_height_cm": beam_height_cm,
        "beam_width_cm": beam_width_cm,
        "column_height_m": column_height_m,
        "column_section_cm": column_section_cm,
        "concrete_fck_mpa": concrete_fck_mpa,
    }

    eval_report = StructuralCoreEngine.evaluate_structure(
        span_length_m=span_length_m,
        cantilever_length_m=cantilever_length_m,
        beam_height_cm=beam_height_cm,
        beam_width_cm=beam_width_cm,
        column_height_m=column_height_m,
        column_section_cm=column_section_cm,
        concrete_fck_mpa=concrete_fck_mpa,
    )

    # Desmarca outros arquivos do usuário e seleciona este novo arquivo
    await db.execute(update(ProjectFile).where(ProjectFile.user_id == user_id).values(is_selected=False))

    pf = ProjectFile(
        user_id=user_id,
        filename=safe_name,
        file_format=ext,
        active_version_number=1,
        is_selected=True,
    )
    db.add(pf)
    await db.flush()

    image_url = _build_styled_svg_preview(
        filename=safe_name,
        version_label="v1",
        render_style=render_style,
        params=params,
        landscape_context=landscape_context,
    )

    v1 = FileVersion(
        file_id=pf.id,
        version_number=1,
        version_label="v1",
        render_style=render_style.lower(),
        landscape_context=landscape_context,
        file_path=f"/uploads/{stored_name}",
        image_url=image_url,
        structural_parameters=params,
        validation_report={
            "is_physically_viable": eval_report["is_physically_viable"],
            "structural_score": eval_report["structural_score"],
            "compliance_level": eval_report["compliance_level"],
            "max_deflection_mm": eval_report["max_deflection_mm"],
            "allowable_deflection_mm": eval_report["allowable_deflection_mm"],
        },
        change_summary="Upload inicial do arquivo (v1)",
        created_by="user_upload",
    )
    db.add(v1)

    db.add(
        UserMemoryDecision(
            user_id=user_id,
            file_id=pf.id,
            memory_type="decision",
            title=f"Upload do arquivo '{safe_name}' (v1)",
            content=f"Arquivo '{safe_name}' carregado com vão={span_length_m}m, balanço={cantilever_length_m}m e estilo={render_style}.",
            decisions_metadata={"parameters": params, "version": "v1"},
        )
    )

    await db.commit()

    stmt = select(ProjectFile).options(selectinload(ProjectFile.versions)).where(ProjectFile.id == pf.id)
    res = await db.execute(stmt)
    pf_loaded = res.scalar_one()
    return serialize_project_file(pf_loaded)


@router.get("", response_model=List[ProjectFileOut])
async def get_user_files(
    user_id: str = Query("default_user"),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os arquivos carregados do usuário e suas respectivas versões (v1..vn)."""
    stmt = (
        select(ProjectFile)
        .options(selectinload(ProjectFile.versions))
        .where(ProjectFile.user_id == user_id)
        .order_by(ProjectFile.created_at.desc())
    )
    res = await db.execute(stmt)
    files = list(res.scalars().all())
    return [serialize_project_file(pf) for pf in files]


@router.get("/{file_id}", response_model=ProjectFileOut)
async def get_file_details(file_id: str, db: AsyncSession = Depends(get_db)):
    """Retorna os detalhes de um arquivo específico e toda a sua árvore de versões v1..vn."""
    stmt = select(ProjectFile).options(selectinload(ProjectFile.versions)).where(ProjectFile.id == file_id)
    res = await db.execute(stmt)
    pf = res.scalar_one_or_none()
    if not pf:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return serialize_project_file(pf)


@router.post("/{file_id}/select", response_model=ProjectFileOut)
async def select_active_file_endpoint(
    file_id: str,
    payload: SelectFileRequest = SelectFileRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Alterna o arquivo selecionado na barra de arquivos carregados.
    Quando trocado, a barra superior de versões (v1..vn) passa a refletir as versões deste arquivo.
    """
    stmt = select(ProjectFile).options(selectinload(ProjectFile.versions)).where(ProjectFile.id == file_id)
    res = await db.execute(stmt)
    pf = res.scalar_one_or_none()
    if not pf:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    await db.execute(update(ProjectFile).where(ProjectFile.user_id == pf.user_id).values(is_selected=False))
    pf.is_selected = True
    await db.commit()

    stmt = select(ProjectFile).options(selectinload(ProjectFile.versions)).where(ProjectFile.id == file_id)
    res = await db.execute(stmt)
    return serialize_project_file(res.scalar_one())


@router.get("/{file_id}/versions", response_model=List[FileVersionOut])
async def list_versions_for_file(file_id: str, db: AsyncSession = Depends(get_db)):
    """Lista todas as versões (v1, v2, ..., vn) pertencentes exclusivamente a este arquivo."""
    stmt = select(ProjectFile).options(selectinload(ProjectFile.versions)).where(ProjectFile.id == file_id)
    res = await db.execute(stmt)
    pf = res.scalar_one_or_none()
    if not pf:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return [serialize_file_version(v) for v in pf.versions]


@router.post("/{file_id}/versions/{version_number}/activate", response_model=ProjectFileOut)
async def activate_version_endpoint(
    file_id: str,
    version_number: int,
    user_id: str = Query("default_user"),
    db: AsyncSession = Depends(get_db),
):
    """Alterna a versão ativa (v1..vn) de um arquivo específico."""
    ctx = RunContext(
        run_id=f"activate_v{version_number}",
        session_id="rest_api",
        dependencies={"user_id": user_id, "active_file_id": file_id},
    )
    res_json = await switch_file_version(ctx, version_number=version_number, file_id=file_id)
    data = json.loads(res_json)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])

    stmt = select(ProjectFile).options(selectinload(ProjectFile.versions)).where(ProjectFile.id == file_id)
    res = await db.execute(stmt)
    return serialize_project_file(res.scalar_one())


@router.post("/{file_id}/style", response_model=ProjectFileOut)
async def change_style_endpoint(
    file_id: str,
    payload: ChangeStyleRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Altera o estilo de visualização do arquivo ('autocad', 'blender', 'wireframe', 'landscape_insight')
    criando uma nova versão vN+1 (ou atualizando a versão atual).
    """
    ctx = RunContext(
        run_id="change_style",
        session_id="rest_api",
        dependencies={"user_id": payload.user_id, "active_file_id": file_id},
    )
    res_json = await change_file_style(
        ctx,
        render_style=payload.render_style,
        landscape_context=payload.landscape_context,
        create_new_version=payload.create_new_version,
    )
    data = json.loads(res_json)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])

    stmt = select(ProjectFile).options(selectinload(ProjectFile.versions)).where(ProjectFile.id == file_id)
    res = await db.execute(stmt)
    return serialize_project_file(res.scalar_one())


@router.post("/{file_id}/generate-code", response_model=ProjectFileOut)
async def generate_code_for_file_endpoint(
    file_id: str,
    payload: GenerateCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Executa a Tool de Código diretamente sobre o arquivo, gerando script/artefato
    no formato pedido ('autocad', 'blender', 'ifc') e criando a versão vN+1.
    """
    chk = await db.execute(select(ProjectFile).where(ProjectFile.id == file_id))
    if chk.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    ctx = RunContext(
        run_id="generate_code",
        session_id="rest_api",
        dependencies={"user_id": payload.user_id, "active_file_id": file_id},
    )
    overrides = payload.structural_overrides or {}
    res_json = await generate_cad_code_tool(
        ctx,
        target_format=payload.target_format,
        modification_instructions=payload.instructions,
        span_length_m=overrides.get("span_length_m"),
        cantilever_length_m=overrides.get("cantilever_length_m"),
        beam_height_cm=overrides.get("beam_height_cm"),
        beam_width_cm=overrides.get("beam_width_cm"),
        concrete_fck_mpa=overrides.get("concrete_fck_mpa"),
    )
    data = json.loads(res_json)
    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"])

    stmt = select(ProjectFile).options(selectinload(ProjectFile.versions)).where(ProjectFile.id == file_id)
    res = await db.execute(stmt)
    return serialize_project_file(res.scalar_one())


@router.post("/{file_id}/convert", response_model=ProjectFileOut)
async def convert_file_format_endpoint(
    file_id: str,
    target_format: str = Query("blender", description="Formato alvo: autocad, blender, ifc, grasshopper_rhino, openscad"),
    user_id: str = Query("default_user"),
    notes: str = Query("Conversão entre formatos de software via seletor superior"),
    db: AsyncSession = Depends(get_db),
):
    """
    Converte o arquivo ativo entre formatos de software ('autocad'/'dxf', 'blender'/'bpy',
    'ifc'/'bim', 'grasshopper_rhino', 'openscad'), gerando o código/artefato e criando a versão vN+1.
    """
    chk = await db.execute(select(ProjectFile).where(ProjectFile.id == file_id))
    if chk.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    ctx = RunContext(
        run_id="convert_format",
        session_id="rest_api",
        dependencies={"user_id": user_id, "active_file_id": file_id},
    )
    res_json = await generate_cad_code_tool(
        ctx,
        target_format=target_format,
        modification_instructions=f"[Conversão de Formato -> {target_format}] {notes}",
    )
    data = json.loads(res_json)
    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"])

    stmt = select(ProjectFile).options(selectinload(ProjectFile.versions)).where(ProjectFile.id == file_id)
    res = await db.execute(stmt)
    return serialize_project_file(res.scalar_one())


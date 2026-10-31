"""
Tools de Geração Visual Arquitetônica & Paisagens (Excalidraw: "Agente de Gen AI para gerar" e
"Agente de sugestao: fornecer visuais em paisagens diferentes para o user conseguir tambem ter insights").
"""

import json
from typing import Optional
from agno.run import RunContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from structura_ai.database import AsyncSessionLocal
from structura_ai.models import ProjectFile, FileVersion, UserMemoryDecision
from structura_ai.tools.file_version_tools import _build_styled_svg_preview, _register_ui_mutation


async def generate_architectural_visual(
    run_context: RunContext,
    visual_prompt: str,
    render_style: str = "landscape_insight",
    landscape_context: str = "encosta_montanhosa",
    suggested_beam_height_cm: Optional[float] = None,
    suggested_fck_mpa: Optional[float] = None,
) -> str:
    """
    Gera uma representação visual arquitetônica/estrutural da edificação inserida em uma
    paisagem ou estilo específico ('autocad', 'blender', 'landscape_insight') e cria
    uma nova versão vN+1 no arquivo ativo para o arquiteto visualizar no painel principal.

    Args:
        visual_prompt: Descrição detalhada da cena arquitetônica, solução estrutural e iluminação.
        render_style: Estilo de renderização ('autocad', 'blender', 'landscape_insight').
        landscape_context: Contexto geográfico/paisagem ('encosta_montanhosa', 'litoral_maresia', 'urbano_denso', 'alpino_neve').
        suggested_beam_height_cm: Opcional. Nova altura de viga sugerida para refletir no visual.
        suggested_fck_mpa: Opcional. Novo fck sugerido.
    """
    deps = (run_context.dependencies if run_context else None) or {}
    user_id = deps.get("user_id", "default_user")
    target_file_id = deps.get("active_file_id")

    async with AsyncSessionLocal() as db:
        pf = None
        if target_file_id:
            stmt = select(ProjectFile).options(selectinload(ProjectFile.versions)).where(ProjectFile.id == target_file_id)
            res = await db.execute(stmt)
            pf = res.scalar_one_or_none()
        if not pf:
            stmt = (
                select(ProjectFile)
                .options(selectinload(ProjectFile.versions))
                .where(ProjectFile.user_id == user_id, ProjectFile.is_selected.is_(True))
            )
            res = await db.execute(stmt)
            pf = res.scalar_one_or_none()

        if not pf:
            pf = ProjectFile(
                user_id=user_id,
                filename="conceito_arquitetonico.dxf",
                file_format="dxf",
                active_version_number=1,
                is_selected=True,
            )
            db.add(pf)
            await db.flush()
            pf_versions = []
        else:
            pf_versions = list(pf.versions)

        current_ver = next(
            (v for v in pf_versions if v.version_number == pf.active_version_number),
            pf_versions[-1] if pf_versions else None,
        )
        params = dict(current_ver.structural_parameters or {}) if current_ver else {
            "span_length_m": 9.5,
            "cantilever_length_m": 3.5,
            "beam_height_cm": 40.0,
            "beam_width_cm": 20.0,
            "concrete_fck_mpa": 35.0,
        }
        if suggested_beam_height_cm is not None:
            params["beam_height_cm"] = float(suggested_beam_height_cm)
        if suggested_fck_mpa is not None:
            params["concrete_fck_mpa"] = float(suggested_fck_mpa)

        next_num = (max((v.version_number for v in pf_versions), default=0)) + 1
        ver_label = f"v{next_num}"

        image_url = _build_styled_svg_preview(
            pf.filename, ver_label, render_style, params, landscape_context=landscape_context
        )

        new_ver = FileVersion(
            file_id=pf.id,
            version_number=next_num,
            version_label=ver_label,
            render_style=render_style,
            landscape_context=landscape_context,
            file_path=current_ver.file_path if current_ver else None,
            image_url=image_url,
            generated_code=current_ver.generated_code if current_ver else None,
            code_language=current_ver.code_language if current_ver else None,
            structural_parameters=params,
            validation_report=current_ver.validation_report if current_ver else {},
            change_summary=f"[GenAI Visual - {landscape_context}] {visual_prompt[:180]}",
            created_by="genai_agent",
        )
        db.add(new_ver)
        pf.active_version_number = next_num

        db.add(
            UserMemoryDecision(
                user_id=user_id,
                session_id=run_context.session_id if run_context else None,
                file_id=pf.id,
                memory_type="decision",
                title=f"Visual gerado em paisagem '{landscape_context}' ({ver_label})",
                content=visual_prompt,
                decisions_metadata={
                    "version": ver_label,
                    "render_style": render_style,
                    "landscape_context": landscape_context,
                    "image_url": image_url,
                },
            )
        )
        await db.commit()

        _register_ui_mutation(
            run_context,
            {
                "action": "version_created",
                "file_id": pf.id,
                "version_number": next_num,
                "version_label": ver_label,
                "render_style": render_style,
                "image_url": image_url,
                "details": {
                    "landscape_context": landscape_context,
                    "visual_prompt": visual_prompt,
                    "structural_parameters": params,
                },
            },
        )

        return json.dumps(
            {
                "status": "success",
                "file_id": pf.id,
                "new_version": ver_label,
                "render_style": render_style,
                "landscape_context": landscape_context,
                "image_url": image_url,
                "visual_prompt": visual_prompt,
                "structural_parameters": params,
            },
            ensure_ascii=False,
        )

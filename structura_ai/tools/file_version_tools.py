"""
Tools de controle de Arquivos Carregados, Versionamento (v1..vn) e Estilo (AutoCAD / Blender).
Podem ser acionadas tanto pelos endpoints REST do Frontend quanto diretamente pelo Chat ("chat pode alterar isso tbm se pedir").
"""

import json
import os
from typing import Any, Dict, Optional
from agno.run import RunContext
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from structura_ai.config import settings
from structura_ai.database import AsyncSessionLocal
from structura_ai.models import ProjectFile, FileVersion, UserMemoryDecision


def _build_styled_svg_preview(
    filename: str,
    version_label: str,
    render_style: str,
    params: Dict[str, Any],
    landscape_context: Optional[str] = None,
) -> str:
    """
    Gera um render vetorial SVG dinâmico para o viewport central ('Aqui fica a imagem')
    refletindo o estilo (autocad, blender, landscape_insight) e parâmetros da versão vN.
    """
    span_m = float(params.get("span_length_m", 9.5))
    cant_m = float(params.get("cantilever_length_m", 3.5))
    beam_h = float(params.get("beam_height_cm", 35.0))
    fck = float(params.get("concrete_fck_mpa", 30.0))

    style_key = render_style.lower()
    if "autocad" in style_key or "dxf" in style_key:
        bg = "#0a192f"
        grid_color = "#112240"
        stroke = "#00f5d4"
        accent = "#ffd166"
        label = "AUTOCAD / DXF TECHNICAL BLUEPRINT"
    elif "blender" in style_key or "3d" in style_key:
        bg = "#1e1e24"
        grid_color = "#2b2d42"
        stroke = "#ff9f1c"
        accent = "#e71d36"
        label = "BLENDER 3D CYCLES VIEWPORT"
    else:
        bg = "#0f172a"
        grid_color = "#1e293b"
        stroke = "#38bdf8"
        accent = "#4ade80"
        label = f"LANDSCAPE INSIGHT ({(landscape_context or 'urbano').upper()})"

    os.makedirs(settings.GENERATED_DIR, exist_ok=True)
    safe_name = "".join(c if c.isalnum() else "_" for c in filename)[:30]
    svg_filename = f"{safe_name}_{version_label}_{style_key}.svg"
    svg_path = os.path.join(settings.GENERATED_DIR, svg_filename)

    landscape_bg_el = ""
    if landscape_context:
        if "montanh" in landscape_context.lower() or "encosta" in landscape_context.lower():
            landscape_bg_el = '<polygon points="0,360 180,210 380,310 620,170 800,360" fill="#1e293b" opacity="0.65"/>'
        elif "litor" in landscape_context.lower() or "mar" in landscape_context.lower():
            landscape_bg_el = '<rect x="0" y="310" width="800" height="90" fill="#0284c7" opacity="0.35"/>'

    beam_px_h = max(14, min(48, int(beam_h * 0.6)))
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 420" width="100%" height="100%">
  <rect width="800" height="420" fill="{bg}"/>
  {landscape_bg_el}
  <g stroke="{grid_color}" stroke-width="1">
    <line x1="0" y1="100" x2="800" y2="100"/>
    <line x1="0" y1="200" x2="800" y2="200"/>
    <line x1="0" y1="300" x2="800" y2="300"/>
    <line x1="200" y1="0" x2="200" y2="420"/>
    <line x1="400" y1="0" x2="400" y2="420"/>
    <line x1="600" y1="0" x2="600" y2="420"/>
  </g>
  <!-- Pilares -->
  <rect x="130" y="{170 + beam_px_h}" width="24" height="150" fill="none" stroke="{stroke}" stroke-width="3"/>
  <rect x="490" y="{170 + beam_px_h}" width="24" height="150" fill="none" stroke="{stroke}" stroke-width="3"/>
  <!-- Viga Principal + Balanço -->
  <rect x="130" y="170" width="540" height="{beam_px_h}" fill="{stroke}" fill-opacity="0.18" stroke="{stroke}" stroke-width="3"/>
  <!-- Cotas Técnicas -->
  <line x1="142" y1="140" x2="502" y2="140" stroke="{accent}" stroke-width="1.5" stroke-dasharray="4,4"/>
  <text x="320" y="132" fill="{accent}" font-family="monospace" font-size="13" text-anchor="middle">Vão Livre: {span_m:.2f}m</text>
  <line x1="502" y1="140" x2="670" y2="140" stroke="{accent}" stroke-width="1.5" stroke-dasharray="4,4"/>
  <text x="586" y="132" fill="{accent}" font-family="monospace" font-size="13" text-anchor="middle">Balanço: {cant_m:.2f}m</text>
  <!-- Rodapé de Metadados -->
  <text x="24" y="34" fill="{stroke}" font-family="monospace" font-size="15" font-weight="bold">[{version_label.upper()}] {filename} — {label}</text>
  <text x="24" y="390" fill="#94a3b8" font-family="monospace" font-size="12">Seção Viga: h={beam_h:.0f}cm | Concreto fck={fck:.0f}MPa | Paisagem: {landscape_context or 'Padrão'}</text>
</svg>"""

    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    return f"/uploads/generated/{svg_filename}"


def _register_ui_mutation(run_context: RunContext, mutation: Dict[str, Any]) -> None:
    if run_context and run_context.dependencies is not None:
        mutations = run_context.dependencies.setdefault("ui_mutations", [])
        mutations.append(mutation)


async def list_project_files(run_context: RunContext) -> str:
    """
    Lista todos os arquivos carregados pelo usuário no workspace, indicando qual arquivo
    está selecionado no momento e quais são as versões (v1 .. vn) de cada um.
    """
    deps = (run_context.dependencies if run_context else None) or {}
    user_id = deps.get("user_id", "default_user")

    async with AsyncSessionLocal() as db:
        stmt = (
            select(ProjectFile)
            .options(selectinload(ProjectFile.versions))
            .where(ProjectFile.user_id == user_id)
            .order_by(ProjectFile.created_at.desc())
        )
        res = await db.execute(stmt)
        files = list(res.scalars().all())

        if not files:
            return json.dumps({"files": [], "message": "Nenhum arquivo carregado ainda para este usuário."}, ensure_ascii=False)

        payload = []
        for pf in files:
            payload.append(
                {
                    "file_id": pf.id,
                    "filename": pf.filename,
                    "file_format": pf.file_format,
                    "is_selected": pf.is_selected,
                    "active_version": f"v{pf.active_version_number}",
                    "available_versions": [v.version_label for v in pf.versions],
                }
            )
        return json.dumps({"files": payload}, ensure_ascii=False)


async def select_project_file(run_context: RunContext, file_id_or_name: str) -> str:
    """
    Muda o arquivo ativo no workspace (e consequentemente atualiza a árvore de versões v1..vn no topo).
    Use quando o usuário pedir no chat para alternar, abrir ou focar em outro arquivo carregado.

    Args:
        file_id_or_name: ID ou nome do arquivo (ex: 'planta_estrutural.dxf') a ser ativado.
    """
    deps = (run_context.dependencies if run_context else None) or {}
    user_id = deps.get("user_id", "default_user")

    async with AsyncSessionLocal() as db:
        stmt = (
            select(ProjectFile)
            .options(selectinload(ProjectFile.versions))
            .where(ProjectFile.user_id == user_id)
            .order_by(ProjectFile.created_at.desc())
        )
        res = await db.execute(stmt)
        files = list(res.scalars().all())

        target: Optional[ProjectFile] = None
        for pf in files:
            if pf.id == file_id_or_name or file_id_or_name.lower() in pf.filename.lower():
                target = pf
                break

        if not target:
            return json.dumps(
                {"error": f"Arquivo '{file_id_or_name}' não encontrado.", "available": [f.filename for f in files]},
                ensure_ascii=False,
            )

        await db.execute(
            update(ProjectFile).where(ProjectFile.user_id == user_id).values(is_selected=False)
        )
        target.is_selected = True
        await db.commit()

        reloaded_res = await db.execute(
            select(ProjectFile).options(selectinload(ProjectFile.versions)).where(ProjectFile.id == target.id)
        )
        target = reloaded_res.scalar_one()

        active_ver = next(
            (v for v in target.versions if v.version_number == target.active_version_number),
            target.versions[-1] if target.versions else None,
        )

        deps["active_file_id"] = target.id
        _register_ui_mutation(
            run_context,
            {
                "action": "file_selected",
                "file_id": target.id,
                "version_number": target.active_version_number,
                "version_label": f"v{target.active_version_number}",
                "render_style": active_ver.render_style if active_ver else "autocad",
                "image_url": active_ver.image_url if active_ver else None,
                "details": {
                    "filename": target.filename,
                    "versions": [v.version_label for v in target.versions],
                },
            },
        )

        return json.dumps(
            {
                "status": "success",
                "selected_file_id": target.id,
                "filename": target.filename,
                "active_version": f"v{target.active_version_number}",
                "versions_for_this_file": [v.version_label for v in target.versions],
                "render_style": active_ver.render_style if active_ver else "autocad",
            },
            ensure_ascii=False,
        )


async def switch_file_version(
    run_context: RunContext,
    version_number: int,
    file_id: Optional[str] = None,
) -> str:
    """
    Altera a versão ativa (v1, v2, ..., vn) do arquivo selecionado no topo da tela.
    Use quando o usuário pedir no chat para voltar ou avançar para uma versão específica (ex: 'voltar para a v1', 'ir para v3').

    Args:
        version_number: Número inteiro da versão desejada (1 para v1, 2 para v2, etc.).
        file_id: Opcional. Se omitido, usa o arquivo ativo do usuário.
    """
    deps = (run_context.dependencies if run_context else None) or {}
    user_id = deps.get("user_id", "default_user")
    target_file_id = file_id or deps.get("active_file_id")

    async with AsyncSessionLocal() as db:
        if target_file_id:
            stmt = (
                select(ProjectFile)
                .options(selectinload(ProjectFile.versions))
                .where(ProjectFile.id == target_file_id)
            )
        else:
            stmt = (
                select(ProjectFile)
                .options(selectinload(ProjectFile.versions))
                .where(ProjectFile.user_id == user_id, ProjectFile.is_selected.is_(True))
            )
        res = await db.execute(stmt)
        pf = res.scalar_one_or_none()
        if not pf:
            return json.dumps({"error": "Nenhum arquivo ativo encontrado para trocar versão."}, ensure_ascii=False)

        target_ver = next((v for v in pf.versions if v.version_number == version_number), None)
        if not target_ver:
            return json.dumps(
                {
                    "error": f"Versão v{version_number} não existe no arquivo '{pf.filename}'.",
                    "available_versions": [v.version_label for v in pf.versions],
                },
                ensure_ascii=False,
            )

        pf.active_version_number = version_number
        db.add(
            UserMemoryDecision(
                user_id=user_id,
                session_id=run_context.session_id if run_context else None,
                file_id=pf.id,
                memory_type="decision",
                title=f"Troca de versão para v{version_number}",
                content=f"Usuário alternou o arquivo '{pf.filename}' para a versão v{version_number} ({target_ver.render_style}).",
                decisions_metadata={"version_number": version_number, "render_style": target_ver.render_style},
            )
        )
        await db.commit()

        _register_ui_mutation(
            run_context,
            {
                "action": "version_switched",
                "file_id": pf.id,
                "version_number": target_ver.version_number,
                "version_label": target_ver.version_label,
                "render_style": target_ver.render_style,
                "image_url": target_ver.image_url,
                "details": {
                    "filename": pf.filename,
                    "change_summary": target_ver.change_summary,
                    "structural_parameters": target_ver.structural_parameters,
                },
            },
        )

        return json.dumps(
            {
                "status": "success",
                "file_id": pf.id,
                "filename": pf.filename,
                "active_version": target_ver.version_label,
                "render_style": target_ver.render_style,
                "image_url": target_ver.image_url,
                "structural_parameters": target_ver.structural_parameters,
                "change_summary": target_ver.change_summary,
            },
            ensure_ascii=False,
        )


async def change_file_style(
    run_context: RunContext,
    render_style: str,
    landscape_context: Optional[str] = None,
    create_new_version: bool = True,
) -> str:
    """
    Altera o estilo/formato de visualização do arquivo ativo ('autocad', 'blender', 'wireframe', 'landscape_insight').
    Conforme o Excalidraw ('Mudar estilo: formato autocad, formato blender' + 'Chat pode fazer isso tbm'),
    atualiza a imagem central e cria uma nova versão vN+1 (ou atualiza a atual).

    Args:
        render_style: Estilo alvo ('autocad', 'blender', 'wireframe', 'landscape_insight').
        landscape_context: Opcional. Paisagem/relevo para contextualização visual ('encosta_montanhosa', 'litoral_maresia', 'urbano_denso').
        create_new_version: Se True (default), cria uma nova versão vN+1 preservando o histórico anterior.
    """
    deps = (run_context.dependencies if run_context else None) or {}
    user_id = deps.get("user_id", "default_user")
    target_file_id = deps.get("active_file_id")

    async with AsyncSessionLocal() as db:
        if target_file_id:
            stmt = (
                select(ProjectFile)
                .options(selectinload(ProjectFile.versions))
                .where(ProjectFile.id == target_file_id)
            )
        else:
            stmt = (
                select(ProjectFile)
                .options(selectinload(ProjectFile.versions))
                .where(ProjectFile.user_id == user_id, ProjectFile.is_selected.is_(True))
            )
        res = await db.execute(stmt)
        pf = res.scalar_one_or_none()
        if not pf:
            return json.dumps({"error": "Nenhum arquivo ativo selecionado para mudar estilo."}, ensure_ascii=False)

        current_ver = next(
            (v for v in pf.versions if v.version_number == pf.active_version_number),
            pf.versions[-1] if pf.versions else None,
        )
        base_params = dict(current_ver.structural_parameters or {}) if current_ver else {}
        base_val = dict(current_ver.validation_report or {}) if current_ver else {}

        if create_new_version or not current_ver:
            next_num = (max((v.version_number for v in pf.versions), default=0)) + 1
            ver_label = f"v{next_num}"
            img_url = _build_styled_svg_preview(pf.filename, ver_label, render_style, base_params, landscape_context)
            new_ver = FileVersion(
                file_id=pf.id,
                version_number=next_num,
                version_label=ver_label,
                render_style=render_style.lower(),
                landscape_context=landscape_context or (current_ver.landscape_context if current_ver else None),
                file_path=current_ver.file_path if current_ver else None,
                image_url=img_url,
                generated_code=current_ver.generated_code if current_ver else None,
                code_language=current_ver.code_language if current_ver else None,
                structural_parameters=base_params,
                validation_report=base_val,
                change_summary=f"Mudança de estilo para '{render_style}'"
                + (f" na paisagem '{landscape_context}'" if landscape_context else ""),
                created_by="chat_command",
            )
            db.add(new_ver)
            pf.active_version_number = next_num
            target_ver = new_ver
        else:
            current_ver.render_style = render_style.lower()
            if landscape_context:
                current_ver.landscape_context = landscape_context
            current_ver.image_url = _build_styled_svg_preview(
                pf.filename, current_ver.version_label, render_style, base_params, current_ver.landscape_context
            )
            target_ver = current_ver

        db.add(
            UserMemoryDecision(
                user_id=user_id,
                session_id=run_context.session_id if run_context else None,
                file_id=pf.id,
                memory_type="decision",
                title=f"Mudança de estilo para {render_style}",
                content=f"Arquivo '{pf.filename}' atualizado para estilo '{render_style}' na versão {target_ver.version_label}.",
                decisions_metadata={
                    "render_style": render_style,
                    "landscape_context": landscape_context,
                    "version": target_ver.version_label,
                },
            )
        )
        await db.commit()

        _register_ui_mutation(
            run_context,
            {
                "action": "style_changed",
                "file_id": pf.id,
                "version_number": target_ver.version_number,
                "version_label": target_ver.version_label,
                "render_style": target_ver.render_style,
                "image_url": target_ver.image_url,
                "details": {
                    "landscape_context": target_ver.landscape_context,
                    "change_summary": target_ver.change_summary,
                },
            },
        )

        return json.dumps(
            {
                "status": "success",
                "file_id": pf.id,
                "filename": pf.filename,
                "active_version": target_ver.version_label,
                "render_style": target_ver.render_style,
                "landscape_context": target_ver.landscape_context,
                "image_url": target_ver.image_url,
            },
            ensure_ascii=False,
        )

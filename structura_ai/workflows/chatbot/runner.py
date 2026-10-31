"""
Runner de Orquestração do Chat Copiloto (Padrão Lembry `app/workflows/chatbot/chat/runner.py`).

Pré-resolve de forma assíncrona (`asyncio.gather`):
1. O arquivo atualmente selecionado (`ProjectFile`) e sua árvore de versões (`v1..vn`);
2. A lista de todos os arquivos carregados pelo usuário;
3. O histórico de memória e decisões do arquiteto (`UserMemoryDecision`).
Executa o agente conversacional Agno (com fallback determinístico local de tools caso GEMINI_API_KEY não esteja definida)
e devolve a resposta, sugestões e mutações de estado da UI (`ui_mutations`).
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from agno.run import RunContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from structura_ai.agents.chatbot.conversational.agent import build_conversational_agent
from structura_ai.config import settings
from structura_ai.database import AsyncSessionLocal
from structura_ai.models import ProjectFile, FileVersion, UserMemoryDecision
from structura_ai.schemas import FileVersionOut, ProjectFileOut, UIStateMutation
from structura_ai.tools.code_generator_tool import generate_cad_code_tool, convert_project_format_tool
from structura_ai.tools.file_version_tools import (
    change_file_style,
    select_project_file,
    switch_file_version,
)
from structura_ai.tools.genai_visual_tools import generate_architectural_visual
from structura_ai.tools.physics_validation_tools import validate_structural_calculations
from structura_ai.tools.rag_knowledge_tools import (
    save_project_knowledge_to_rag,
    search_engineering_rag,
)
from structura_ai.workflows.memory.runner import (
    build_evermemos_context_xml,
    run_memory_workflow,
)

logger = logging.getLogger(__name__)

_SUGGESTIONS_RE = re.compile(r"<suggestions>\s*(\[.*?\])\s*</suggestions>", re.DOTALL)


def serialize_file_version(v: FileVersion) -> FileVersionOut:
    return FileVersionOut(
        id=v.id,
        file_id=v.file_id,
        version_number=v.version_number,
        version_label=v.version_label,
        render_style=v.render_style,
        landscape_context=v.landscape_context,
        file_path=v.file_path,
        image_url=v.image_url,
        generated_code=v.generated_code,
        code_language=v.code_language,
        structural_parameters=v.structural_parameters or {},
        validation_report=v.validation_report or {},
        change_summary=v.change_summary,
        created_by=v.created_by,
        created_at=v.created_at.isoformat() if v.created_at else "",
    )


def serialize_project_file(pf: ProjectFile) -> ProjectFileOut:
    versions_out = [serialize_file_version(v) for v in (pf.versions or [])]
    active_v = next(
        (v for v in versions_out if v.version_number == pf.active_version_number),
        versions_out[-1] if versions_out else None,
    )
    return ProjectFileOut(
        id=pf.id,
        user_id=pf.user_id,
        project_id=pf.project_id,
        filename=pf.filename,
        file_format=pf.file_format,
        active_version_number=pf.active_version_number,
        is_selected=pf.is_selected,
        created_at=pf.created_at.isoformat() if pf.created_at else "",
        active_version=active_v,
        versions=versions_out,
    )


DEFAULT_ICP_SUGGESTIONS = [
    "Gostaria de ver essa solução em outro formato (Blender 3D / AutoCAD DXF)?",
    "Como adaptar a estética para o Brutalismo do Cerrado ou Art Déco Goianiense?",
    "Validar impacto no Latossolo Vermelho de Goiânia e NBR 6118",
]


def extract_suggestions(text: str) -> Tuple[str, List[str]]:
    """Extrai o bloco <suggestions>[...]</suggestions> da resposta do agente, garantindo sempre 3 sugestões do ICP."""
    match = _SUGGESTIONS_RE.search(text or "")
    if not match:
        return (text or "").strip(), list(DEFAULT_ICP_SUGGESTIONS)
    clean_text = _SUGGESTIONS_RE.sub("", text).strip()
    try:
        parsed = json.loads(match.group(1))
        if isinstance(parsed, list) and parsed:
            items = [str(x) for x in parsed[:3]]
            for fallback in DEFAULT_ICP_SUGGESTIONS:
                if len(items) >= 3:
                    break
                if fallback not in items:
                    items.append(fallback)
            return clean_text, items[:3]
    except Exception:
        pass
    return clean_text, list(DEFAULT_ICP_SUGGESTIONS)


async def _fetch_workspace_files_context(
    user_id: str, active_file_id: Optional[str] = None
) -> Tuple[Optional[str], str, str]:
    """Busca todos os arquivos do usuário e formata o resumo do arquivo ativo e suas versões v1..vn."""
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
            return (
                None,
                "Nenhum arquivo carregado ainda.",
                "Workspace sem arquivos carregados.",
            )

        active_pf: Optional[ProjectFile] = None
        if active_file_id:
            active_pf = next((f for f in files if f.id == active_file_id), None)
        if not active_pf:
            active_pf = next((f for f in files if f.is_selected), files[0])

        active_ver = next(
            (v for v in active_pf.versions if v.version_number == active_pf.active_version_number),
            active_pf.versions[-1] if active_pf.versions else None,
        )

        versions_labels = [v.version_label for v in active_pf.versions]
        active_summary = (
            f"Arquivo Ativo: '{active_pf.filename}' (id={active_pf.id}, formato={active_pf.file_format}) | "
            f"Versão Ativa no Topo: v{active_pf.active_version_number} de {versions_labels} | "
            f"Estilo Atual: {active_ver.render_style if active_ver else 'autocad'} | "
            f"Parâmetros Estruturais: {json.dumps(active_ver.structural_parameters if active_ver else {}, ensure_ascii=False)}"
        )

        all_files_lines = [
            f"- {f.filename} (id={f.id}, formato={f.file_format}, selecionado={f.is_selected}, "
            f"versão_ativa=v{f.active_version_number}, versões={[v.version_label for v in f.versions]})"
            for f in files
        ]
        return active_pf.id, active_summary, "\n".join(all_files_lines)


async def _fetch_user_memory_context(user_id: str, query: str = "") -> str:
    """
    Recupera o contexto de memória completo:
    1. Arquitetura EverMemOS da Lembry (<perfil_do_usuario> + <memorias_historicas>: MemScene & MemCell)
    2. Decisões recentes da Tabela 1 (`user_memory_decisions`).
    """
    evermemos_xml = await build_evermemos_context_xml(user_id=user_id, query=query or "projeto estrutura arquitetura goiás")
    async with AsyncSessionLocal() as db:
        stmt = (
            select(UserMemoryDecision)
            .where(UserMemoryDecision.user_id == user_id)
            .order_by(UserMemoryDecision.created_at.desc())
            .limit(8)
        )
        res = await db.execute(stmt)
        memories = list(res.scalars().all())

    decision_lines: List[str] = []
    if memories:
        decision_lines.append("## Decisões de Projeto Registradas")
        for m in reversed(memories):
            decision_lines.append(f"- [{m.memory_type}] {m.title or ''}: {m.content}")

    blocks = [b for b in [evermemos_xml, "\n".join(decision_lines)] if b.strip()]
    if not blocks:
        return "## Memória do Usuário\nNenhuma decisão ou perfil anterior registrado."
    return "\n\n".join(blocks)


async def _build_dependencies(
    user_id: str,
    session_id: str,
    active_file_id: Optional[str] = None,
    region_country: str = "BR",
    query: str = "",
    selected_format: str = "autocad",
) -> Dict[str, Any]:
    """Monta o dicionário de dependencies pré-resolvidas com `asyncio.gather` (Padrão Lembry)."""
    (resolved_file_id, active_summary, workspace_summary), memory_section = await asyncio.gather(
        _fetch_workspace_files_context(user_id, active_file_id),
        _fetch_user_memory_context(user_id, query=query),
    )

    return {
        "user_id": user_id,
        "session_id": session_id,
        "region_country": region_country.upper(),
        "selected_format": selected_format,
        "active_file_id": resolved_file_id,
        "active_file_summary": active_summary,
        "workspace_files_summary": workspace_summary,
        "memory_context_section": memory_section,
        "ui_mutations": [],
    }


def _detect_requested_format(msg_lower: str, default_format: str = "autocad") -> str:
    if any(k in msg_lower for k in ("blender", "bpy", ".blend", "3d script")):
        return "blender"
    if any(k in msg_lower for k in ("rhino", "grasshopper", "ghpython")):
        return "grasshopper_rhino"
    if any(k in msg_lower for k in ("openscad", "scad")):
        return "openscad"
    if any(k in msg_lower for k in ("ifc", "bim")):
        return "ifc"
    if any(k in msg_lower for k in ("autocad", "dxf", "ezdxf", "cad")):
        return "autocad"
    return default_format or "autocad"


async def _fallback_tool_orchestrator(
    message: str, dependencies: Dict[str, Any], session_id: str
) -> str:
    """
    Orquestrador determinístico das tools quando GEMINI_API_KEY não está configurada
    (garantindo execução 100% funcional em testes automatizados e POC offline).
    """
    ctx = RunContext(run_id=session_id, session_id=session_id, dependencies=dependencies)
    msg_lower = message.lower()
    selected_fmt = dependencies.get("selected_format", "autocad")

    # 1. Troca de versão v1..vn ("voltar para v1", "mudar para versao 2", "v3")
    ver_match = re.search(r"\b(?:vers[aã]o\s*|v)(\d+)\b", msg_lower)
    if ver_match and any(w in msg_lower for w in ("mudar", "trocar", "voltar", "ir", "ativar", "alterar", "selecionar", "mostrar")):
        v_num = int(ver_match.group(1))
        res_json = await switch_file_version(ctx, version_number=v_num)
        data = json.loads(res_json)
        if "error" in data:
            return (
                f"Não foi possível trocar para a versão v{v_num}: {data['error']}\n"
                '<suggestions>["Listar versões disponíveis do arquivo", "Gerar nova versão v2 com reforço", "Validar versão atual"]</suggestions>'
            )
        return (
            f"Versão alterada com sucesso para **{data['active_version']}** no arquivo `{data['filename']}` "
            f"(Estilo: `{data['render_style']}`). Gostaria de ver essa versão convertida em outro formato ou validar os cálculos?\n"
            '<suggestions>["Validar cálculos desta versão", "Converter esta versão para Blender 3D", "Gerar código AutoCAD DXF"]</suggestions>'
        )

    # 2. Troca de arquivo carregado ("trocar para o arquivo X", "abrir arquivo Y", "mudar arquivo")
    if any(k in msg_lower for k in ("trocar arquivo", "mudar arquivo", "selecionar arquivo", "abrir arquivo", "mudar para o arquivo")):
        tokens = re.findall(r"[\w\-\.]+\.(?:dxf|ifc|blend|obj|stl|png|jpg|scad|py)", msg_lower)
        target_name = tokens[0] if tokens else message.split()[-1].strip("'\"")
        res_json = await select_project_file(ctx, file_id_or_name=target_name)
        data = json.loads(res_json)
        if "error" in data:
            return (
                f"Não encontrei o arquivo solicitado: {data['error']}\n"
                '<suggestions>["Ver lista de arquivos carregados", "Fazer upload de novo arquivo DXF/IFC", "Validar arquivo atual"]</suggestions>'
            )
        return (
            f"Arquivo ativo alterado para **`{data['filename']}`**. "
            f"A barra de versionamento superior agora exibe as versões deste arquivo: `{data['versions_for_this_file']}` "
            f"(ativa: **{data['active_version']}**). Gostaria de validar a estrutura deste arquivo ou convertê-lo para outro formato?\n"
            '<suggestions>["Validar estrutura deste arquivo na NBR 6118", "Converter este arquivo para Blender 3D", "Sugerir estética do Cerrado para este projeto"]</suggestions>'
        )

    # 3. Conversão entre formatos ("converter para blender", "converter formato", "transformar em ifc")
    if any(k in msg_lower for k in ("converter", "conversão", "conversao", "transformar para", "exportar para formato")):
        fmt = _detect_requested_format(msg_lower, selected_fmt)
        res_json = await convert_project_format_tool(ctx, target_format=fmt, conversion_notes=message)
        data = json.loads(res_json)
        return (
            f"**Conversão Multi-Formato (Agente Gen AI)** concluída! O projeto `{data['filename']}` foi convertido para **`{data['code_language']}`**, "
            f"gerando a versão **{data['new_version']}**.\n"
            f"- **Arquivo convertido:** `{data['artifact_download_url']}`\n"
            f"- **Preview:** `{data['image_url']}`\n"
            f"- **Viabilidade Física:** `{data['validation_summary'].get('compliance_level')}` (Score: `{data['validation_summary'].get('structural_score')}`)\n"
            f"Gostaria de ver esse mesmo modelo convertido em mais algum formato (AutoCAD DXF, Blender, BIM IFC, Rhino/Grasshopper ou OpenSCAD)?\n"
            '<suggestions>["Converter também para BIM IFC 4 (.ifc)", "Converter para script Rhino / Grasshopper", "Voltar para a versão v1"]</suggestions>'
        )

    # 4. Mudança de estilo ("mudar estilo para blender", "formato autocad")
    if any(k in msg_lower for k in ("estilo", "formato autocad", "formato blender", "mudar para blender", "mudar para autocad")):
        style = "blender" if "blender" in msg_lower else ("autocad" if "autocad" in msg_lower else "landscape_insight")
        landscape = "encosta_montanhosa" if "montanh" in msg_lower or "encosta" in msg_lower or "piren" in msg_lower else None
        res_json = await change_file_style(ctx, render_style=style, landscape_context=landscape, create_new_version=True)
        data = json.loads(res_json)
        if "error" in data:
            return f"Erro ao mudar estilo: {data['error']}"
        return (
            f"Estilo atualizado para **`{data['render_style']}`** no arquivo `{data['filename']}`, "
            f"criando a versão **{data['active_version']}** (`{data['image_url']}`). Gostaria de gerar o código executável neste formato?\n"
            '<suggestions>["Gerar código Text-to-Code neste formato", "Voltar para v1", "Validar estrutura na NBR 6118"]</suggestions>'
        )

    # 5. Tool de código / Text-to-Code ("gerar codigo", "text to code", "script blender", "gerar dxf", "aplicar reforço", "nova versão v2")
    if any(
        k in msg_lower
        for k in (
            "gerar codigo",
            "gerar código",
            "gere o código",
            "gere o codigo",
            "text to code",
            "text-to-code",
            "script",
            "ezdxf",
            "bpy",
            "rhino",
            "openscad",
            "aplicar reforço",
            "aplicar reforco",
            "gerar v2",
            "gerar versão",
            "gerar dxf",
            "gerar ifc",
        )
    ):
        fmt = _detect_requested_format(msg_lower, selected_fmt)
        # Extrai eventual altura de viga ou fck pedidos na mensagem
        h_match = re.search(r"h\s*=\s*(\d+)|viga\s*(?:de\s*)?(\d+)\s*cm", msg_lower)
        fck_match = re.search(r"fck\s*=?\s*(\d+)|c(\d{2})\b", msg_lower)
        req_h = float(h_match.group(1) or h_match.group(2)) if h_match else None
        req_fck = float(fck_match.group(1) or fck_match.group(2)) if fck_match else None

        res_json = await generate_cad_code_tool(
            ctx,
            target_format=fmt,
            modification_instructions=message,
            beam_height_cm=req_h,
            concrete_fck_mpa=req_fck,
        )
        data = json.loads(res_json)
        return (
            f"**Agente Gen AI (Text-to-Code)** executado com sucesso! Criada a versão **{data['new_version']}** "
            f"no formato selecionado `{data['code_language']}`.\n"
            f"- **Código / Artefato gerado:** `{data['artifact_download_url']}`\n"
            f"- **Preview:** `{data['image_url']}`\n"
            f"- **Status Físico:** `{data['validation_summary'].get('compliance_level')}` "
            f"(Viável: `{data['validation_summary'].get('is_physically_viable')}`, Score: `{data['validation_summary'].get('structural_score')}`)\n"
            f"Gostaria de ver essa solução em outro formato de software ou testar uma variação arquitetônica na paisagem?\n"
            '<suggestions>["Gostaria de ver essa solução em Blender 3D (.py)?", "Converter projeto para BIM IFC (.ifc)", "Voltar para a versão v1 para comparar"]</suggestions>'
        )

    # 6. Consultas sobre Memória / Perfil do Arquiteto (EverMemOS) + Goiás
    if any(k in msg_lower for k in ("meu perfil", "minhas prefer", "decisões que tomamos", "decisoes que tomamos", "histórico", "historico", "padrão nos meus próximos")):
        mem_ctx = dependencies.get("memory_context_section", "")
        rag_json = await search_engineering_rag(ctx, query="Goiânia Pirenópolis Latossolo Brutalismo Art Déco", region_country="BR-GO")
        rag_items = json.loads(rag_json).get("results", [])
        goias_tip = rag_items[0]["title"] if rag_items else "Normas e Arquitetura de Goiás (BR-GO)"
        return (
            f"### Recomendações Personalizadas com Base no Seu Perfil (EverMemOS) & Contexto de Goiás\n"
            f"Com base no seu `<perfil_do_usuario>` e nas `<memorias_historicas>` consolidadas nas nossas cenas (`MemScene` / `MemCell`):\n\n"
            f"{mem_ctx}\n\n"
            f"**Especificação Padrão Recomendada para Seus Próximos Estudos em Goiás (`{goias_tip}`):**\n"
            f"1. **Estrutura & Balanços:** Concreto protendido aparente **fck = 40 a 45 MPa** combinado com perfis em **Aço Corten (ASTM A588)** ou Vigas Vierendel aparentes para vencer balanços de 6m a 10m com esbeltez.\n"
            f"2. **Fundações em Goiás:** **Estaca Hélice Contínua Monitorada** em Goiânia/Marista (atravessando a camada colapsível de Latossolo Vermelho de 4m–10m) e **Sapatas Ancoradas em Rocha (Quartzito)** para terrenos em aclive em Pirenópolis/Chapada.\n"
            f"3. **Linguagem Arquitetônica:** Que tal combinar brises escalonados inspirados no **Art Déco Goianiense** na fachada oeste com muros de arrimo em **Pedra de Pirenópolis** e espelho d'água sob pilotis (**Brutalismo do Cerrado**)?\n\n"
            f"Gostaria de ver essa especificação gerada como código base no seu formato favorito?\n"
            '<suggestions>["Gerar template Text-to-Code em Blender 3D com essa especificação", "Converter projeto atual para AutoCAD DXF com concreto C45", "Simular visual na paisagem do Cerrado em Pirenópolis"]</suggestions>'
        )

    # 7. Apresentação do Arquiteto / Declaração de Preferências (Turno Inicial)
    if any(k in msg_lower for k in ("sou arquiteto", "sou engenheiro", "trabalho em goi", "atuo em goi", "prefiro estruturas")):
        rag_json = await search_engineering_rag(ctx, query=message, region_country="BR-GO")
        rag_items = json.loads(rag_json).get("results", [])
        ref_titles = ", ".join(it["title"] for it in rag_items[:2]) if rag_items else "Geotecnia e Arquitetura de Goiás"
        return (
            f"Prazer! Registrei suas preferências e contexto regional no **EverMemOS** (`UserProfile`, `MemCell` e `MemScene`) "
            f"e já conectei a base regional de **Goiás (`BR-GO`)** ({ref_titles}).\n\n"
            f"Para seus projetos no **Setor Marista (Goiânia)** e em **Pirenópolis**, que tal explorarmos soluções que unam "
            f"grandes balanços protendidos (**Brutalismo do Cerrado**, ref. Paulo Mendes da Rocha), elementos em **Aço Corten + Pedra de Pirenópolis (Quartzito)** "
            f"e brises geométricos inspirados no **Art Déco Goianiense**, sempre verificando o **Latossolo Vermelho colapsível** e os ventos convectivos da **NBR 6123**?\n\n"
            f"Gostaria de validar os cálculos do seu arquivo atual ou ver uma sugestão visual e estrutural para Goiás?\n"
            '<suggestions>["Quais os riscos do Latossolo de Goiânia vs rocha em Pirenópolis para um balanço de 8m?", "Validar se está tudo certo com a estrutura atual na NBR 6118", "Gerar código Text-to-Code em Blender 3D para estrutura mista"]</suggestions>'
        )

    # 8. Agente de Sugestão / Paisagem / Goiás Artístico + Geotécnico ("sugerir", "sugestao", "paisagem", "goiás", "goiania", "pirenopolis", "art deco", "brutalista", "latossolo", "que tal")
    is_pure_validation = any(w in msg_lower for w in ("tudo certo", "valide", "validar")) and not any(
        w in msg_lower for w in ("sugerir", "sugest", "ideia", "paisagem", "art déco", "art deco", "latossolo")
    )
    if not is_pure_validation and any(
        k in msg_lower
        for k in (
            "sugerir",
            "sugest",
            "paisagem",
            "insight",
            "encosta",
            "litoral",
            "goiás",
            "goias",
            "goiânia",
            "goiania",
            "pirenópolis",
            "pirenopolis",
            "cerrado",
            "art déco",
            "art deco",
            "brutalista",
            "latossolo",
            "marista",
        )
    ):
        landscape = (
            "litoral_maresia"
            if "litoral" in msg_lower or "mar " in msg_lower
            else ("encosta_montanhosa" if any(w in msg_lower for w in ("encosta", "montanh", "piren", "chapada", "aclive")) else "urbano_denso")
        )
        rag_json = await search_engineering_rag(ctx, query=message, region_country="BR-GO")
        rag_items = json.loads(rag_json).get("results", [])
        rag_bullets = "\n".join(
            f"- **{it['title']}** (`{it['region_country']}`): {it['content'][:360]}..."
            for it in rag_items[:3]
        )
        val_json = await validate_structural_calculations(ctx)
        val_data = json.loads(val_json)
        opt_h = val_data.get("recommended_minimum_beam_height_cm") or 55.0
        vis_json = await generate_architectural_visual(
            ctx,
            visual_prompt=f"Sugestão estrutural e artística em Goiás ({landscape}) com viga h={opt_h}cm, fck=40MPa, Aço Corten, Pedra de Pirenópolis e inspiração Art Déco/Brutalista",
            render_style="landscape_insight",
            landscape_context=landscape,
            suggested_beam_height_cm=opt_h,
            suggested_fck_mpa=40.0,
        )
        vis_data = json.loads(vis_json)
        return (
            f"### Agente de Sugestão (Cálculos + Repertório Artístico & Geotécnico de Goiás + Visual na Paisagem)\n"
            f"1. **Diagnóstico Estrutural Atual:** Flecha de `{val_data['max_deflection_mm']} mm` (limite `{val_data['allowable_deflection_mm']} mm` - Status: `{val_data['compliance_level']}`).\n"
            f"2. **Modificação de Cálculo Sugerida:** Ajustar seção principal para **h = {opt_h:.0f} cm** com concreto **fck = 40 MPa** (ou seção mista Aço Corten ASTM A588 + concreto protendido).\n"
            f"3. **Referências Técnicas e Artísticas de Goiás (`tabela_vet` BR-GO):**\n{rag_bullets}\n"
            f"4. **Ideias Arquitetônicas ('Que tal fazer isso ou aquilo?'):**\n"
            f"   - *Que tal* usar um núcleo rígido revestido em **Pedra de Pirenópolis (Quartzito)** com tirantes chumbados na rocha (em Pirenópolis) ou **Estacas Hélice Contínua** atravessando o **Latossolo Vermelho colapsível** (no Setor Marista em Goiânia)?\n"
            f"   - *Que tal* desenhar a viga do balanço com frisos escalonados inspirados no **Art Déco Goianiense** ou em concreto aparente ripado do **Brutalismo do Cerrado** sobre um espelho d'água para amenizar a seca de agosto?\n"
            f"5. **Visual Gerado na Paisagem (`{landscape}`):** Criada a versão **{vis_data['new_version']}** (`{vis_data['image_url']}`).\n\n"
            f"Gostaria de ver essa sugestão transformada em código no formato `{selected_fmt}` ou testar outra variação?\n"
            '<suggestions>["Aplicar esse reforço e gerar código no formato Blender 3D (nova versão)", "Converter projeto para AutoCAD DXF (.dxf) com viga de 55cm", "Ver parâmetros do Plano Diretor de Goiânia (LC 349/2022)"]</suggestions>'
        )

    # 9. Agente de Busca & RAG ("norma", "eurocode", "aci", "japao", "japão", "relevo", "nbr", "salvar conhecimento", "plano diretor", "sinapi", "cub")
    if any(k in msg_lower for k in ("salvar conhecimento", "guardar aprendizado", "salvar no rag")):
        saved_json = await save_project_knowledge_to_rag(
            ctx,
            title="Aprendizado de Projeto Estrutural",
            knowledge_content=message,
            region_country=dependencies.get("region_country", "BR"),
        )
        saved = json.loads(saved_json)
        return (
            f"Conhecimento armazenado na `tabela_vet` (ID: `{saved['knowledge_id']}`) para reutilização nos seus futuros projetos!\n"
            '<suggestions>["Consultar aprendizados salvos na tabela_vet", "Validar estrutura atual na NBR 6118", "Gerar código CAD/BIM da versão ativa"]</suggestions>'
        )

    if any(k in msg_lower for k in ("norma", "eurocode", "aci", "japao", "japão", "nbr", "relevo", "exterior", "internacional", "rag", "busca", "plano diretor", "código de obras", "sinapi", "cub")):
        rag_json = await search_engineering_rag(
            ctx,
            query=message,
            region_country=dependencies.get("region_country"),
        )
        rag_data = json.loads(rag_json)
        items = rag_data.get("results", [])
        resumo = "\n".join(
            [f"- **{it['title']}** (`{it['region_country']}` / `{it['category']}`): {it['content']}" for it in items[:3]]
        )
        return (
            f"### Resultado do Agente de Busca & RAG (`tabela_vet`)\n{resumo}\n\n"
            f"Gostaria de aplicar esses parâmetros normativos diretamente na validação ou gerar uma nova versão do projeto?\n"
            '<suggestions>["Validar o projeto ativo com esses critérios normativos", "Gerar nova versão em AutoCAD DXF respeitando a norma", "Explorar sugestões estéticas de Goiás (Art Déco / Brutalismo)"]</suggestions>'
        )

    # 10. Default: Agente Validador ("validar", "ta tudo certo", "está tudo certo", "calculo", etc.)
    # Diferencia explicitamente entre Projeto APROVADO (Tudo Certo) e Projeto REPROVADO (Com Falha) com perguntas reais do ICP!
    val_json = await validate_structural_calculations(
        ctx, region_country=dependencies.get("region_country", "BR")
    )
    val_data = json.loads(val_json)
    is_ok = bool(val_data.get("is_physically_viable"))
    opt_h = val_data.get("recommended_minimum_beam_height_cm") or 55.0

    if is_ok:
        icp_question = (
            "✅ **Sim, está tudo certo! A estrutura está 100% aprovada** nos critérios de Estado Limite Último (ELU) "
            "e Estado Limite de Serviço (ELS - flecha dentro do limite normativo).\n\n"
            "**Pergunta de Projeto (ICP):** Como a concepção estrutural já tem folga de segurança, "
            "**gostaria de ver essa solução de outra forma** — por exemplo, convertendo para script **Blender 3D / BIM IFC**, "
            "esbeltecendo a borda da laje em balanço ou aplicando um acabamento inspirado no **Brutalismo do Cerrado / Art Déco Goianiense**?"
        )
        suggestions_tag = (
            '<suggestions>['
            '"Gostaria de ver essa solução de outra forma (converter para Blender 3D)?", '
            '"Que tal testar brises Art Déco Goianiense ou Pedra de Pirenópolis na fachada?", '
            '"Exportar código executável em AutoCAD DXF / BIM IFC"'
            ']</suggestions>'
        )
    else:
        icp_question = (
            "⚠️ **Atenção: A estrutura NÃO passou na verificação física atual** (há excedente de flecha e/ou solicitação resistente crítica).\n\n"
            f"**Pergunta de Projeto (ICP):** Para sanar essa patologia sem perder a intenção arquitetônica do vão/balanço, "
            f"**gostaria de ver isso de outra forma** — gerando automaticamente uma nova versão (`vN+1`) com viga redimensionada para "
            f"**h = {opt_h:.0f} cm e concreto fck = 40 MPa**, ou prefere simular uma **Viga Vierendel aparente / estrutura mista em Aço Corten** adequada ao solo de Goiás?"
        )
        suggestions_tag = (
            f'<suggestions>['
            f'"Gostaria de ver isso corrigido em uma nova versão com viga h={opt_h:.0f}cm e fck=40MPa?", '
            f'"Como resolver esse balanço com Viga Vierendel Brutalista ou Aço Corten?", '
            f'"Verificar impacto dessa carga no Latossolo Vermelho de Goiânia"'
            f']</suggestions>'
        )

    return (
        f"### Agente Validador ({val_data['norm_reference']})\n"
        f"- **Status:** `{val_data['compliance_level']}` (Viável: `{val_data['is_physically_viable']}`, Score: `{val_data['structural_score']}/100`)\n"
        f"- **Flecha Máxima:** `{val_data['max_deflection_mm']} mm` (Admissível: `{val_data['allowable_deflection_mm']} mm`)\n"
        f"- **Momento Fletor Máximo:** `{val_data['max_bending_moment_knm']} kNm` | **Altura Ótima Recomendada:** `{opt_h} cm`\n"
        f"- **Diagnóstico Técnico:** {val_data['diagnosis']}\n\n"
        f"{icp_question}\n"
        f"{suggestions_tag}"
    )


async def run_chat_workflow(
    message: str,
    user_id: str = "default_user",
    session_id: str = "default_session",
    active_file_id: Optional[str] = None,
    region_country: str = "BR",
    selected_format: str = "autocad",
    force_memory_flush: bool = False,
) -> Tuple[str, List[str], List[UIStateMutation], Optional[ProjectFileOut]]:
    """
    Executa o fluxo completo do Chat Copiloto no padrão Lembry + EverMemOS:
    1. Pré-resolve contexto de arquivos, versões e memória EverMemOS (<perfil_do_usuario> + <memorias_historicas>).
    2. Executa o agente conversacional (ou orquestrador determinístico de fallback).
    3. Extrai os 3 blocos de sugestões do ICP (<suggestions>[...]</suggestions>).
    4. Alimenta o pipeline EverMemOS (EpisodeBuffer -> MemCell -> MemScene -> UserProfile).
    """
    dependencies = await _build_dependencies(
        user_id=user_id,
        session_id=session_id,
        active_file_id=active_file_id,
        region_country=region_country,
        query=message,
        selected_format=selected_format,
    )

    raw_reply = ""
    if settings.effective_api_key:
        try:
            agent = build_conversational_agent(dependencies=dependencies)
            result = await agent.arun(
                message,
                session_id=session_id,
                user_id=user_id,
            )
            raw_reply = (result.content or "").strip()
        except Exception as exc:
            logger.warning("[ChatWorkflow] Fallback para orquestrador local após erro na API LLM: %s", exc)
            raw_reply = ""

    if not raw_reply:
        raw_reply = await _fallback_tool_orchestrator(message, dependencies, session_id)

    clean_reply, suggestions = extract_suggestions(raw_reply)
    raw_mutations = dependencies.get("ui_mutations", [])
    ui_mutations = [UIStateMutation(**m) for m in raw_mutations]

    # Atualiza o pipeline EverMemOS (EpisodeBuffer -> MemCell -> MemScene -> UserProfile)
    try:
        await run_memory_workflow(
            user_id=user_id,
            session_id=session_id,
            messages=[
                {"role": "user", "content": message},
                {"role": "assistant", "content": clean_reply},
            ],
            force_flush=force_memory_flush,
        )
    except Exception as mem_exc:
        logger.warning("[EverMemOS] Aviso ao processar memória episódica: %s", mem_exc)

    # Busca o estado atualizado do arquivo ativo após qualquer mutação feita pelas tools
    active_pf_out: Optional[ProjectFileOut] = None
    async with AsyncSessionLocal() as db:
        final_file_id = dependencies.get("active_file_id")
        if final_file_id:
            stmt = (
                select(ProjectFile)
                .options(selectinload(ProjectFile.versions))
                .where(ProjectFile.id == final_file_id)
            )
        else:
            stmt = (
                select(ProjectFile)
                .options(selectinload(ProjectFile.versions))
                .where(ProjectFile.user_id == user_id, ProjectFile.is_selected.is_(True))
            )
        res = await db.execute(stmt)
        pf = res.scalar_one_or_none()
        if pf:
            active_pf_out = serialize_project_file(pf)

    return clean_reply, suggestions, ui_mutations, active_pf_out

"""
Pipeline de Memória EverMemOS (Padrão Lembry.Chatbot) em 4 etapas:
Step 1: check_boundary (Boundary Detection)
Step 2: generate_memcell (MemCell Extraction + Embedding)
Step 3: consolidate_memscene (MemScene Centroid Clustering + Summary)
Step 4: profile_user (UserProfile Consolidation)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from structura_ai.config import settings
from structura_ai.integrations.embeddings import get_embedding
from structura_ai.integrations.memory import (
    MAX_EPISODE,
    SLIDING_WINDOW,
    episode_buffer_store,
    memcell_store,
    memscene_store,
    user_profile_store,
)
from structura_ai.schemas_memory import (
    BoundaryDecision,
    ConsolidatedProfile,
    ConsolidatedScene,
    ExtractedMemCell,
    FactItem,
    ForesightItem,
    MemCell,
    MemScene,
    ProfileExplicitFact,
    ProfileImplicitPattern,
    UserProfile,
)


def _heuristic_boundary(unconsumed: list[dict]) -> BoundaryDecision:
    """Heurística de fronteira de episódio determinística (e fallback para LLM)."""
    if len(unconsumed) >= MAX_EPISODE:
        return BoundaryDecision(
            should_close_episode=True,
            reason=f"Atingiu limite máximo de {MAX_EPISODE} mensagens no buffer.",
        )
    if len(unconsumed) < 2:
        return BoundaryDecision(
            should_close_episode=False,
            reason="Aguardando par completo de interação usuário-assistente.",
        )

    combined = " ".join(m.get("content", "").lower() for m in unconsumed[-2:])
    trigger_keywords = [
        "sou arquiteto", "sou engenheiro", "trabalho em", "goiânia", "goiania", "goiás", "goias",
        "pirenópolis", "pirenopolis", "prefiro", "meu estilo", "gerar código", "gere o código",
        "nova versão", "v2", "v3", "converter", "mudar para", "blender", "autocad", "ifc",
        "balanço", "fundação", "latossolo", "art déco", "art deco", "brutalista", "aprovar",
    ]
    if any(k in combined for k in trigger_keywords) or len(unconsumed) >= 4:
        return BoundaryDecision(
            should_close_episode=True,
            reason="Decisão técnica, preferência de perfil ou marco de projeto detectado no diálogo.",
        )
    return BoundaryDecision(
        should_close_episode=False,
        reason="Conversa ainda em desenvolvimento no mesmo subtópico.",
    )


def _heuristic_extract_memcell(messages: list[dict], user_id: str) -> ExtractedMemCell:
    """Extrator determinístico rico para MemCell quando LLM não está disponível ou como fallback."""
    user_msgs = [m.get("content", "") for m in messages if m.get("role") == "user"]
    asst_msgs = [m.get("content", "") for m in messages if m.get("role") == "assistant"]
    full_text = " | ".join(user_msgs)
    low = full_text.lower()

    facts: list[FactItem] = []
    foresights: list[ForesightItem] = []

    if any(w in low for w in ["goiânia", "goiania", "goiás", "goias", "marista", "bueno", "pirenópolis", "pirenopolis", "chapada"]):
        facts.append(
            FactItem(
                category="context",
                fact=f"Atuação ou projeto localizado em Goiás ({full_text[:140]}).",
            )
        )
    if any(w in low for w in ["prefiro", "gosto", "estilo", "brutalista", "art déco", "art deco", "concreto", "aço", "corten", "pedra"]):
        facts.append(
            FactItem(
                category="preference",
                fact=f"Preferência arquitetônica/estrutural declarada: {full_text[:150]}",
            )
        )
    if any(w in low for w in ["v2", "v3", "versão", "gerar", "reforçar", "converter", "blender", "autocad", "ifc"]):
        facts.append(
            FactItem(
                category="decision",
                fact=f"Decisão de modelagem/versionamento executada: {full_text[:150]}",
            )
        )
    if not facts:
        facts.append(
            FactItem(
                category="task_pattern",
                fact=f"Interação técnica sobre projeto estrutural: {full_text[:150]}",
            )
        )

    now = datetime.now(timezone.utc)
    foresights.append(
        ForesightItem(
            text=f"Manter diretrizes discutidas por {user_id} nas próximas iterações e revisões do projeto.",
            valid_from=now - timedelta(minutes=5),
            valid_until=now + timedelta(days=30),
        )
    )

    episode_summary = (
        f"O arquiteto/engenheiro ({user_id}) interagiu sobre: '{' ; '.join(user_msgs)[:220]}'. "
        f"Síntese técnica aplicada: '{(asst_msgs[-1] if asst_msgs else '')[:180]}'."
    )
    return ExtractedMemCell(episode=episode_summary, facts=facts, foresights=foresights)


def _heuristic_consolidate_scene(
    cell: MemCell,
    existing_scene: Optional[MemScene],
) -> ConsolidatedScene:
    low = cell.searchable_text.lower()
    if "goi" in low or "piren" in low or "marista" in low or "cerrado" in low:
        topic = "Projetos Arquitetônicos e Estruturais em Goiás (Cerrado / Goiânia / Pirenópolis)"
    elif "blender" in low or "autocad" in low or "ifc" in low or "código" in low:
        topic = "Modelagem Text-to-Code, Conversão CAD/BIM e Versionamento"
    else:
        topic = existing_scene.topic if existing_scene else "Análise e Concepção Estrutural NBR 6118"

    if existing_scene and existing_scene.summary:
        updated_summary = f"{existing_scene.summary} | Evolução recente: {cell.episode}"
    else:
        updated_summary = cell.episode

    return ConsolidatedScene(topic=topic, updated_summary=updated_summary[:1200])


def _heuristic_consolidate_profile(
    user_id: str,
    scene: MemScene,
    cell: MemCell,
    current_profile: Optional[UserProfile],
) -> ConsolidatedProfile:
    explicit_facts: list[ProfileExplicitFact] = list(current_profile.explicit_facts) if current_profile else []
    patterns: list[ProfileImplicitPattern] = list(current_profile.patterns) if current_profile else []

    existing_exp_vals = {f.value for f in explicit_facts}
    existing_pat_obs = {p.observation for p in patterns}

    low = cell.searchable_text.lower()
    if any(w in low for w in ["arquiteto", "engenheiro", "goiânia", "goiania", "goiás", "goias", "pirenópolis"]):
        val = "Profissional de Arquitetura/Engenharia atuando em projetos no Estado de Goiás (Goiânia / Pirenópolis / Cerrado)."
        if val not in existing_exp_vals:
            explicit_facts.append(ProfileExplicitFact(category="role", value=val))
            existing_exp_vals.add(val)

    for tool_kw, tool_label in [
        ("blender", "Blender 3D (.py / .obj)"),
        ("autocad", "AutoCAD (.dxf)"),
        ("ifc", "BIM IFC 4 (.ifc)"),
        ("rhino", "Rhino / Grasshopper (.py)"),
        ("openscad", "OpenSCAD (.scad)"),
    ]:
        if tool_kw in low and tool_label not in existing_exp_vals:
            explicit_facts.append(ProfileExplicitFact(category="tool", value=tool_label))
            existing_exp_vals.add(tool_label)

    for f in cell.facts:
        if f.category in ("preference", "decision", "context"):
            obs = f"[{f.category.upper()}] {f.fact}"
            if obs not in existing_pat_obs:
                patterns.append(
                    ProfileImplicitPattern(
                        category="preference" if f.category == "preference" else "style",
                        observation=obs,
                    )
                )
                existing_pat_obs.add(obs)

    summary = (
        f"Perfil consolidado de {user_id}: {len(explicit_facts)} fatos explícitos e {len(patterns)} padrões técnicos/estéticos mapeados. "
        f"Foco recente em '{scene.topic}'. Último resumo: {scene.summary[:260]}"
    )
    return ConsolidatedProfile(
        explicit_facts=explicit_facts[:12],
        patterns=patterns[:12],
        summary=summary,
    )


async def run_memory_workflow(
    user_id: str,
    session_id: str = "default_session",
    messages: Optional[list[dict]] = None,
    force_flush: bool = False,
) -> dict[str, Any]:
    """
    Executa o pipeline completo EverMemOS da Lembry:
    1. Enfileira novas mensagens no EpisodeBufferStore
    2. Step 1 (check_boundary): avalia se fecha episódio
    3. Step 2 (generate_memcell): consome buffer, gera MemCell + embedding e salva
    4. Step 3 (consolidate_memscene): encontra ou cria MemScene por centroide e atualiza resumo
    5. Step 4 (profile_user): consolida e versiona o UserProfile do arquiteto
    """
    if messages:
        await episode_buffer_store.enqueue_messages(user_id, session_id, messages)

    unconsumed = await episode_buffer_store.get_unconsumed(user_id, session_id)
    if not unconsumed:
        return {"episode_closed": False, "reason": "Buffer vazio."}

    # Step 1: Boundary Detection
    decision = _heuristic_boundary(unconsumed)
    if force_flush:
        decision = BoundaryDecision(should_close_episode=True, reason="Flush forçado solicitado.")

    if not decision.should_close_episode:
        return {
            "episode_closed": False,
            "reason": decision.reason,
            "buffered_messages": len(unconsumed),
        }

    # Step 2: Consume Buffer & Extract MemCell
    consumed = await episode_buffer_store.consume_all(user_id, session_id)
    extracted: Optional[ExtractedMemCell] = None

    if settings.effective_api_key:
        try:
            from structura_ai.agents.memory.extraction.agent import get_extraction_agent

            agent = get_extraction_agent()
            transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in consumed)
            resp = await agent.arun(f"Extraia a MemCell deste episódio de {user_id}:\n{transcript}")
            if resp and isinstance(getattr(resp, "content", None), ExtractedMemCell):
                extracted = resp.content
        except Exception:
            extracted = None

    if extracted is None:
        extracted = _heuristic_extract_memcell(consumed, user_id)

    facts_text = " ".join(f.fact for f in extracted.facts)
    foresights_text = " ".join(fs.text for fs in extracted.foresights)
    searchable_text = f"{extracted.episode} {facts_text} {foresights_text}".strip()
    emb = get_embedding(searchable_text)

    cell = MemCell(
        user_id=user_id,
        session_id=session_id,
        episode=extracted.episode,
        searchable_text=searchable_text,
        facts=extracted.facts,
        foresights=extracted.foresights,
        embedding=emb,
        message_count=len(consumed),
    )
    await memcell_store.save(cell)

    # Step 3: Consolidate MemScene (Centroid Clustering)
    nearest_scene = await memscene_store.find_nearest_scene(user_id, emb)
    consolidated_scene = _heuristic_consolidate_scene(cell, nearest_scene)

    if nearest_scene is None:
        scene = MemScene(
            user_id=user_id,
            topic=consolidated_scene.topic,
            summary=consolidated_scene.updated_summary,
            cell_ids=[cell.id],
            centroid_embedding=emb,
            cell_count=1,
        )
    else:
        scene = nearest_scene
        scene.topic = consolidated_scene.topic
        scene.summary = consolidated_scene.updated_summary

    scene = await memscene_store.save_or_update_scene(scene, new_cell_id=cell.id, new_embedding=emb)

    # Step 4: Consolidate UserProfile
    current_profile = await user_profile_store.get(user_id)
    consolidated_profile = _heuristic_consolidate_profile(user_id, scene, cell, current_profile)

    updated_profile = UserProfile(
        user_id=user_id,
        explicit_facts=consolidated_profile.explicit_facts,
        patterns=consolidated_profile.patterns,
        summary=consolidated_profile.summary,
    )
    await user_profile_store.save(updated_profile, trigger_scene_id=scene.id)

    return {
        "episode_closed": True,
        "reason": decision.reason,
        "memcell_id": cell.id,
        "memscene_id": scene.id,
        "memscene_topic": scene.topic,
        "profile_summary": updated_profile.summary,
    }


async def build_evermemos_context_xml(user_id: str, query: str) -> str:
    """
    Monta os blocos XML <perfil_do_usuario> e <memorias_historicas> (MemCell + MemScene expansion)
    idênticos ao padrão da Lembry.Chatbot para injeção no agente conversacional.
    """
    profile = await user_profile_store.get(user_id)
    cells = await memcell_store.search(user_id=user_id, query=query, top_k=4)

    parts: list[str] = []

    if profile:
        facts_str = "\n".join(f"  - [{f.category}] {f.value}" for f in profile.explicit_facts)
        pats_str = "\n".join(f"  - [{p.category}] {p.observation}" for p in profile.patterns)
        parts.append(
            "<perfil_do_usuario>\n"
            f"  Resumo: {profile.summary}\n"
            f"  Fatos Explícitos:\n{facts_str or '  - Nenhum registrado ainda'}\n"
            f"  Padrões e Preferências:\n{pats_str or '  - Nenhum registrado ainda'}\n"
            "</perfil_do_usuario>"
        )

    if cells:
        scene_summaries: list[str] = []
        seen_scenes: set[str] = set()
        cell_lines: list[str] = []

        for c in cells:
            f_list = "; ".join(f"{f.category}: {f.fact}" for f in c.facts)
            fs_list = "; ".join(fs.text for fs in c.foresights)
            cell_lines.append(
                f"  - [MemCell {c.id[:8]}] Episódio: {c.episode} | Fatos: {f_list} | Foresights Ativos: {fs_list}"
            )
            scene = await memscene_store.get_scene_for_cell(c.id)
            if scene and scene.id not in seen_scenes:
                seen_scenes.add(scene.id)
                scene_summaries.append(
                    f"  - [MemScene '{scene.topic}' ({scene.cell_count} episódios)]: {scene.summary}"
                )

        parts.append(
            "<memorias_historicas>\n"
            "  Cenas Temáticas Consolidadas (MemScenes):\n"
            + ("\n".join(scene_summaries) if scene_summaries else "  - Nenhuma cena consolidada")
            + "\n  Episódios Relevantes Recuperados (MemCells):\n"
            + "\n".join(cell_lines)
            + "\n</memorias_historicas>"
        )

    return "\n\n".join(parts)

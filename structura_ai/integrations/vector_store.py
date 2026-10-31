"""
Base Vetorial e Recuperação Híbrida RRF (Padrão Lembry aplicado à `tabela_vet` do Excalidraw).

Armazena e consulta:
- Normas Nacionais (NBR 6118, NBR 6120, NBR 6123, NBR 8800)
- Normas Internacionais (Eurocode 2 UE, ACI 318 / ASCE 7 EUA, BSLJ Sísmica Japão)
- Cálculos Estruturais e Tipologias de Edificações
- Informações sobre Relevo, Geotecnia e Clima Local
- Conhecimento gerado pelos próprios projetos avaliados do arquiteto (user_id)
"""

import re
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from structura_ai.models import KnowledgeVector
from structura_ai.integrations.embeddings import compute_embedding, cosine_similarity
from structura_ai.integrations.goias_scraper import GOIAS_CURATED_CORPUS

RRF_K = 60

DEFAULT_KNOWLEDGE_CORPUS: List[Dict[str, Any]] = [
    {
        "category": "norma_nacional",
        "region_country": "BR",
        "title": "ABNT NBR 6118:2023 — Projeto de Estruturas de Concreto (Limites de Flecha e Cobrimento)",
        "content": (
            "A NBR 6118:2023 define os requisitos para concreto armado e protendido no Brasil. "
            "Limites de deslocamento no Estado Limite de Serviço (ELS - Aceitabilidade Sensorial/Visual): "
            "flecha máxima admissível de L/250 para vãos biapoiados/contínuos e L/125 para balanços livres. "
            "Para evitar fissuração em alvenarias apoiadas na viga, o limite após construção da parede é L/500 (ou 10mm). "
            "Classes de Agressividade Ambiental (CAA): CAA I (Rural, fck >= 20 MPa, cobrimento viga/pilar 25mm), "
            "CAA II (Urbana, fck >= 25 MPa, cobrimento 30mm), CAA III (Marinha/Industrial, fck >= 30 MPa, cobrimento 40mm), "
            "CAA IV (Respingos de maré, fck >= 40 MPa, cobrimento 50mm)."
        ),
        "technical_metadata": {
            "norm_code": "NBR 6118:2023",
            "span_deflection_limit_ratio": 250,
            "cantilever_deflection_limit_ratio": 125,
            "min_fck_urban_mpa": 25,
            "min_fck_marine_mpa": 30,
        },
    },
    {
        "category": "norma_nacional",
        "region_country": "BR",
        "title": "ABNT NBR 6120:2019 & NBR 6123:2023 — Ações, Sobrecargas de Uso e Vento em Edificações",
        "content": (
            "A NBR 6120:2019 estabelece cargas verticais mínimas por tipologia: Residencial (dormitórios/sala 1,5 kN/m², "
            "varandas 2,5 kN/m²), Escritórios/Corporativo (2,5 a 3,0 kN/m²), Shoppings/Áreas Públicas (4,0 a 5,0 kN/m²). "
            "A NBR 6123:2023 define a velocidade básica do vento V0 no Brasil (30 m/s no Norte/Centro-Oeste até 50 m/s no Sul), "
            "com fatores topográficos S1 (relevo plano vs morros/escarpas), rugosidade S2 e fator estatístico S3."
        ),
        "technical_metadata": {
            "norm_code": "NBR 6120 / NBR 6123",
            "live_load_residential_kpa": 2.0,
            "live_load_commercial_kpa": 3.0,
            "live_load_public_kpa": 5.0,
        },
    },
    {
        "category": "norma_internacional",
        "region_country": "EU",
        "title": "Eurocode 2 (EN 1992-1-1) & Eurocode 8 (EN 1998) — União Europeia",
        "content": (
            "Para projetos arquitetônicos na União Europeia, o Eurocode 2 (EN 1992-1-1) especifica concreto por resistência "
            "cilíndrica/cúbica (ex: C30/37, C40/50). O limite de flecha sob combinação quase-permanente é L/250 para estética "
            "geral e L/500 após instalação de divisórias frágeis. Para regiões mediterrâneas (Itália, Grécia, Portugal), "
            "o Eurocode 8 exige dutibilidade sísmica (classes DCM/DCH), nós viga-pilar confinados e continuidade de diafragma rígido."
        ),
        "technical_metadata": {
            "norm_code": "EN 1992-1-1 / EN 1998",
            "span_deflection_limit_ratio": 250,
            "partition_deflection_limit_ratio": 500,
            "seismic_ductility_classes": ["DCL", "DCM", "DCH"],
        },
    },
    {
        "category": "norma_internacional",
        "region_country": "US",
        "title": "ACI 318-19 & ASCE 7-22 — Estados Unidos (Concreto Estrutural, Vento/Furacão e Sismo)",
        "content": (
            "Nos Estados Unidos, o ACI 318-19 utiliza o método LRFD com combinação governante 1.2D + 1.6L (e combinações de vento W "
            "e sismo E da ASCE 7-22). Limite de flecha imediata devido à sobrecarga L: L/360 em pisos e L/240 para deslocamento total "
            "de longo prazo (fluência + retração). Na Costa Oeste (Califórnia - SDC D/E/F), exige Special Moment Frames; na Flórida/Golfo, "
            "dimensionamento de fachada e estrutura principal para ventos de furacão até 180 mph (80 m/s)."
        ),
        "technical_metadata": {
            "norm_code": "ACI 318-19 / ASCE 7-22",
            "live_load_deflection_limit_ratio": 360,
            "total_deflection_limit_ratio": 240,
            "load_combination": "1.2D + 1.6L",
        },
    },
    {
        "category": "norma_internacional",
        "region_country": "JP",
        "title": "Building Standard Law of Japan (BSLJ / AIJ) — Engenharia Sísmica e Arquitetura no Japão",
        "content": (
            "No Japão, projetos arquitetônicos seguem o BSLJ com verificação em dois níveis sísmicos: Nível 1 (terremotos moderados "
            "frequentes, sem danos estruturais, drift inter-pavimento <= 1/200) e Nível 2 (terremotos severos raros, prevenção de colapso, "
            "drift <= 1/100). Vãos livres e balanços exigem controle rigoroso de massa suspensa, uso de isolamento de base (Menshin), "
            "amortecedores viscoelásticos/histeréticos (Seishin) ou perfis híbridos aço-concreto (SRC)."
        ),
        "technical_metadata": {
            "norm_code": "BSLJ / AIJ Japan",
            "max_story_drift_level1": 0.005,
            "max_story_drift_level2": 0.01,
            "recommended_systems": ["Menshin Base Isolation", "Seishin Dampers", "SRC Hybrid Frame"],
        },
    },
    {
        "category": "relevo_geotecnia",
        "region_country": "GLOBAL",
        "title": "Implantação em Relevo Acidentado, Encostas Montanhosas e Taludes",
        "content": (
            "Em terrenos de encosta ou topografia acidentada (declividade > 20%), o fator topográfico de vento S1 aumenta em até 1,3x "
            "no topo da escarpa. Recomendações de projeto: (1) Implantação escalonada acompanhando as curvas de nível para minimizar "
            "corte/aterro; (2) Contenção a montante com cortina atirantada ou muro em balanço com drenagem sub-horizontal; "
            "(3) Fundação profunda em estacas raiz ou microestacas engastadas em rocha sã; (4) Balanços frontais sobre o vale devem "
            "usar seção caixão protendida ou treliça metálica atirantada para reduzir peso próprio na borda do talude."
        ),
        "technical_metadata": {
            "terrain_type": "encosta_montanhosa",
            "wind_topography_factor_s1": 1.25,
            "recommended_foundation": "Estaca raiz / Microestaca em rocha + Cortina atirantada",
        },
    },
    {
        "category": "relevo_geotecnia",
        "region_country": "GLOBAL",
        "title": "Implantação em Zona Litorânea / Orla Marítima e Solos Compressíveis",
        "content": (
            "Em zonas costeiras e frentes marítimas: (1) Ambiente de alta salinidade exige concreto fck >= 40 MPa com adição de "
            "sílica ativa/metacaulim, cobrimento mínimo de 45-50mm ou estruturas em madeira engenheirada (Glulam/CLT) e aço inox/dupla "
            "galvanização; (2) Solos arenosos fofos ou argilas marinhas moles exigem fundação em estacas hélice contínua ou radier "
            "protendido para limitar recalques diferenciais a L/500; (3) Pressão dinâmica de vento costeiro requer contraventamento em núcleo rígido."
        ),
        "technical_metadata": {
            "terrain_type": "litoral_maresia",
            "min_fck_mpa": 40,
            "min_cover_mm": 45,
            "recommended_materials": ["Concreto fck 40+ MPa com sílica ativa", "Madeira Lamelada Colada (Glulam)", "Aço Duplex"],
        },
    },
    {
        "category": "calculo_estrutural",
        "region_country": "GLOBAL",
        "title": "Dimensionamento de Grandes Vãos Livres (> 8m) e Balanços Arrojados (> 3m)",
        "content": (
            "Regras práticas de pré-dimensionamento estrutural para arquitetos: "
            "1. Viga de concreto armado convencional: altura h ≈ L/10 a L/12 para vãos simples e h ≈ L_balanço/4 a L_balanço/5 para balanços. "
            "2. Viga protendida (cordoalhas engraxadas): permite reduzir altura para h ≈ L/18 a L/20 e vencer balanços de 4m a 6m com contra-flecha ativa. "
            "3. Viga Vierendeel ou Treliça de Pavimento (Story-deep truss): utiliza o pé-direito do pavimento superior (h = 2,8m a 3,5m) para vencer vãos de 12m a 25m sem pilares intermediários. "
            "4. Seção mista aço-concreto (Perfil W/I + Laje Steel Deck): reduz peso próprio em 40%, diminuindo momentos fletores de gravidade e sismo."
        ),
        "technical_metadata": {
            "rc_beam_span_depth_ratio": 10,
            "post_tensioned_span_depth_ratio": 18,
            "cantilever_depth_ratio": 4.5,
        },
    },
    {
        "category": "edificacao_tipologia",
        "region_country": "GLOBAL",
        "title": "Tipologias de Edificações: Residencial High-End, Pavilhão Cultural e Torre Mista",
        "content": (
            "1. Residência Contemporânea em Balanço: prioriza esbeltez visual de borda de laje (nervuras recuadas em seção T invertida ou laje protendida com borda chanfrada de 15cm na fachada e 45cm no núcleo). "
            "2. Pavilhão / Museu de Grande Vão: grelha bidirecional (laje nervurada/waffle) ou casca em concreto UHPC / Glulam, distribuindo esforços em duas direções ortogonais. "
            "3. Edifício Corporativo / Misto: núcleo central rígido de concreto (core de elevadores) combinado com pilares periféricos esbeltos e lajes planas protendidas sem vigas (flat slab)."
        ),
        "technical_metadata": {
            "typologies": ["Residencial", "Comercial", "Institucional", "Industrial"],
        },
    },
]


async def ensure_knowledge_seeded(db: AsyncSession) -> int:
    """Popula a `tabela_vet` (`knowledge_vectors`) com o corpus técnico inicial + Goiás (BR-GO) caso falte."""
    stmt = select(KnowledgeVector.title)
    res = await db.execute(stmt)
    existing_titles = set(res.scalars().all())

    count = 0
    for item in list(DEFAULT_KNOWLEDGE_CORPUS) + list(GOIAS_CURATED_CORPUS):
        if item["title"] in existing_titles:
            continue
        full_text = f"{item['title']} {item['content']} {item['region_country']} {item['category']}"
        emb = compute_embedding(full_text)
        kv = KnowledgeVector(
            user_id=None,
            category=item["category"],
            region_country=item["region_country"],
            title=item["title"],
            content=item["content"],
            technical_metadata=item.get("technical_metadata", {}),
            embedding=emb,
            lifecycle="active",
        )
        db.add(kv)
        existing_titles.add(item["title"])
        count += 1

    if count > 0:
        await db.commit()
    return count


async def ingest_knowledge_item(
    db: AsyncSession,
    title: str,
    content: str,
    category: str = "projeto_usuario",
    region_country: str = "BR",
    user_id: Optional[str] = None,
    technical_metadata: Optional[Dict[str, Any]] = None,
) -> KnowledgeVector:
    """
    Insere novo item de conhecimento na `tabela_vet` (incluindo aprendizados/decisões
    gerados nos projetos do próprio arquiteto para reutilização em novos projetos).
    """
    full_text = f"{title} {content} {region_country} {category}"
    emb = compute_embedding(full_text)
    kv = KnowledgeVector(
        user_id=user_id,
        category=category,
        region_country=region_country.upper(),
        title=title,
        content=content,
        technical_metadata=technical_metadata or {},
        embedding=emb,
        lifecycle="active",
    )
    db.add(kv)
    await db.commit()
    await db.refresh(kv)
    return kv


async def search_knowledge_hybrid(
    db: AsyncSession,
    query: str,
    user_id: Optional[str] = None,
    region_country: Optional[str] = None,
    category: Optional[str] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Busca Híbrida com Reciprocal Rank Fusion (RRF, k=60 — Padrão Lembry):
    Combina ranking semântico por cosseno (`embedding`) + ranking lexical BM25-like,
    filtrando itens globais (`user_id IS NULL`) + itens privados do próprio arquiteto (`user_id`).
    """
    await ensure_knowledge_seeded(db)

    stmt = select(KnowledgeVector).where(KnowledgeVector.lifecycle == "active")
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    # Filtra visibilidade: global (user_id None) ou do próprio usuário
    filtered: List[KnowledgeVector] = []
    for r in rows:
        if r.user_id is not None and user_id is not None and r.user_id != user_id:
            continue
        if category and r.category != category:
            continue
        if region_country and region_country.upper() not in ("ALL", "ANY"):
            rc_up = region_country.upper()
            allowed_regions = {rc_up, "GLOBAL"}
            if rc_up in ("BR", "GO", "BR-GO", "GOIAS", "GOIÁS", "GOIANIA", "GOIÂNIA"):
                allowed_regions.update({"BR", "BR-GO", "GO"})
            if r.region_country not in allowed_regions:
                continue
        filtered.append(r)

    if not filtered:
        filtered = [r for r in rows if r.user_id is None or r.user_id == user_id]

    query_vec = compute_embedding(query)
    query_tokens = set(re.findall(r"[a-z0-9à-ú_]+", query.lower()))

    semantic_scores: List[tuple[str, float]] = []
    lexical_scores: List[tuple[str, float]] = []
    by_id: Dict[str, KnowledgeVector] = {}

    for item in filtered:
        by_id[item.id] = item
        sim = cosine_similarity(query_vec, item.embedding or [])
        semantic_scores.append((item.id, sim))

        doc_text = f"{item.title} {item.content} {item.category} {item.region_country}".lower()
        doc_tokens = set(re.findall(r"[a-z0-9à-ú_]+", doc_text))
        overlap = len(query_tokens & doc_tokens) / max(1, len(query_tokens))
        lexical_scores.append((item.id, overlap))

    semantic_ranked = sorted(semantic_scores, key=lambda x: x[1], reverse=True)
    lexical_ranked = sorted(lexical_scores, key=lambda x: x[1], reverse=True)

    sem_rank_map = {doc_id: rank + 1 for rank, (doc_id, _) in enumerate(semantic_ranked)}
    lex_rank_map = {doc_id: rank + 1 for rank, (doc_id, _) in enumerate(lexical_ranked)}
    sem_score_map = dict(semantic_scores)

    rrf_results: List[Dict[str, Any]] = []
    for doc_id, item in by_id.items():
        r_sem = sem_rank_map.get(doc_id, len(by_id) + 1)
        r_lex = lex_rank_map.get(doc_id, len(by_id) + 1)
        rrf_score = (1.0 / (RRF_K + r_sem)) + (1.0 / (RRF_K + r_lex))
        rrf_results.append(
            {
                "id": item.id,
                "user_id": item.user_id,
                "category": item.category,
                "region_country": item.region_country,
                "title": item.title,
                "content": item.content,
                "technical_metadata": item.technical_metadata or {},
                "score": round(rrf_score + 0.01 * sem_score_map.get(doc_id, 0.0), 5),
                "created_at": item.created_at.isoformat() if item.created_at else "",
            }
        )

    rrf_results.sort(key=lambda x: x["score"], reverse=True)
    return rrf_results[:top_k]

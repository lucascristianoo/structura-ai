"""
Scraper e Base de Conhecimento Regional do Estado de Goiás (BR-GO) para a tabela_vet.
Coleta dados públicos via HTTP (quando online) e indexa o corpus técnico + artístico/arquitetônico
de Goiás (Goiânia, Pirenópolis, Cidade de Goiás, Chapada dos Veadeiros, Caldas Novas, Anápolis, Rio Verde).
"""

from __future__ import annotations

from typing import Any
import re
import httpx
from sqlalchemy import select

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore

from structura_ai.database import AsyncSessionLocal
from structura_ai.models import KnowledgeVector
from structura_ai.integrations.embeddings import get_embedding

GOIAS_PUBLIC_SOURCES = [
    {
        "url": "https://www.goiania.go.gov.br/planejamento/plano-diretor/",
        "source_name": "Prefeitura de Goiânia - SEPLANH (Plano Diretor LC 349/2022 & Código de Obras LC 363/2023)",
        "category": "norma_nacional",
    },
    {
        "url": "https://sinduscongoias.com.br/cub/",
        "source_name": "SINDUSCON-GO - CUB Goiás e Custos Regionais da Construção Civil",
        "category": "calculo_estrutural",
    },
    {
        "url": "http://portal.iphan.gov.br/pagina/detalhes/1501/",
        "source_name": "IPHAN Goiás - Patrimônio Art Déco de Goiânia e Arquitetura Colonial de Pirenópolis/Goiás",
        "category": "arquitetura_estetica_goias",
    },
]

GOIAS_CURATED_CORPUS: list[dict[str, Any]] = [
    {
        "category": "arquitetura_estetica_goias",
        "region_country": "BR-GO",
        "title": "Arquitetura Art Déco Goianiense (IPHAN) — Geometria Escalonada, Marquises e Fachadas Sombreantes",
        "content": (
            "Goiânia possui o maior e mais homogêneo acervo Art Déco do Brasil, projetado originalmente por Attilio Corrêa Lima "
            "(Teatro Goiânia, Estação Ferroviária, Torre do Relógio da Av. Goiás, Palácio das Esmeraldas). "
            "Para auxiliar o arquiteto com sugestões criativas ('Que tal fazer isso ou aquilo?'): "
            "1) Que tal reinterpretar os frisos verticais escalonados e platibandas geométricas do Art Déco Goianiense usando brises de concreto aparente ou UHPC para proteger a fachada oeste do sol da tarde? "
            "2) Que tal criar uma marquise curva em balanço aerodinâmico (estilo streamline goianiense) com borda esbelta protendida de 18cm e óculos zenitais circulares que projetam feixes de luz dramáticos no espelho d'água? "
            "3) Uso do pórtico estrutural simétrico escalonado como elemento escultural que absorve os momentos fletores do balanço sem precisar de pilares de canto."
        ),
        "technical_metadata": {
            "style": "Art Déco Goianiense",
            "architects_reference": ["Attilio Corrêa Lima", "Armando Augusto de Godoy"],
            "structural_synergy": "Pórticos escalonados de inércia variável e marquises curvas protendidas",
            "state": "GO",
        },
    },
    {
        "category": "arquitetura_estetica_goias",
        "region_country": "BR-GO",
        "title": "Modernismo e Brutalismo do Cerrado (Paulo Mendes da Rocha em Goiânia) — Grandes Balanços, Praças de Sombra e Água",
        "content": (
            "A arquitetura brutalista em Goiás tem como ícones o Estádio Serra Dourada e a Sede do Jóquei Clube de Goiás "
            "(Paulo Mendes da Rocha), além das obras de Eurico Calixto de Godoi e Elder Rocha Lima. "
            "Diretrizes estéticas e estruturais para sugerir ao arquiteto: "
            "1) 'Que tal suspender o volume principal em concreto aparente ripado sobre apenas 2 apoios centrais recuados, criando uma grande varanda-sombra livre sob pilotis com balanços de 8m a 12m?' "
            "2) 'Que tal transformar a viga de transição em uma Viga Vierendel aparente na fachada ou viga-parede vazada, onde a própria estrutura resolve a estética brutalista?' "
            "3) 'Que tal posicionar um espelho d'água linear sob o balanço na direção dos ventos dominantes Leste-Nordeste de Goiânia para promover resfriamento evaporativo nos meses de seca (agosto-setembro, umidade < 15%)?' "
            "4) Uso de gárgulas esculturais em concreto armado aparente para lançar as águas das chuvas torrenciais de verão do Cerrado em bacias de pedra."
        ),
        "technical_metadata": {
            "style": "Brutalismo do Cerrado / Escola Paulista-Goiana",
            "architects_reference": ["Paulo Mendes da Rocha", "Eurico Calixto de Godoi", "Elder Rocha Lima"],
            "structural_synergy": "Concreto protendido aparente C40-C50, Vigas Vierendel e consolos de inércia variável",
            "state": "GO",
        },
    },
    {
        "category": "arquitetura_estetica_goias",
        "region_country": "BR-GO",
        "title": "Arquitetura Vernacular e Contemporânea do Cerrado (Pirenópolis, Cidade de Goiás, Chapada e Condomínios de Goiânia)",
        "content": (
            "A arquitetura contemporânea goiana (referências como Leo Romano, pavilhões na Chapada dos Veadeiros, Pirenópolis e residências "
            "em condomínios como Aldeia do Vale, Alphaville Flamboyant e Portal do Sol em Goiânia) funde materiais vernaculares do Cerrado com engenharia arrojada: "
            "1) Pedra de Pirenópolis (Quartzito foliado): 'Que tal revestir os muros de arrimo e o núcleo rígido da caixa de escada/elevador em pedra de Pirenópolis em junta seca (filete serrado ou lascas rústicas), contrastando com uma laje fina metálica em balanço?' "
            "2) Aço Corten + Latossolo: 'Que tal usar perfis metálicos em Aço Corten (ASTM A588 patinável) ou brises oxidados que dialogam cromaticamente com o vermelho-terracota do Latossolo e a casca tortuosa dos pequizeiros e ipês do Cerrado?' "
            "3) Taipa de Pilão Contemporânea (Rammed Earth): Paredes autoportantes ou de vedação térmica com terra local do Cerrado estabilizada com 8% de cimento, garantindo alta inércia térmica para a amplitude térmica goiana. "
            "4) Beirais largos (1,8m a 3,0m) com forro ripado em madeira Cumaru ou Freijó e muxarabis contemporâneos para ventilação cruzada permanente."
        ),
        "technical_metadata": {
            "style": "Contemporâneo do Cerrado & Vernacular Pirenopolino",
            "materials": ["Pedra de Pirenópolis (Quartzito)", "Aço Corten ASTM A588", "Taipa de Pilão / Solo-Cimento", "Madeira Cumaru"],
            "locations": ["Goiânia", "Pirenópolis", "Cidade de Goiás", "Chapada dos Veadeiros (Alto Paraíso)"],
            "state": "GO",
        },
    },
    {
        "category": "relevo_geotecnia",
        "region_country": "BR-GO",
        "title": "Geotecnia de Goiânia e Aparecida (Latossolo Vermelho Colapsível, Argilas do Marista/Bueno/Oeste e Rocha em Pirenópolis)",
        "content": (
            "Mapeamento geotécnico e de fundações no Estado de Goiás para projetos estruturais: "
            "1) Latossolo Vermelho Poroso e Colapsível (Goiânia e Aparecida de Goiânia): camada superficial de 4m a 10m de espessura com baixo índice de resistência à penetração (N_SPT entre 2 e 6) e estrutura macroporosa instável. Quando saturado por chuvas intensas ou vazamentos, sofre colapso brusco de volume (recalques diferenciais severos). Recomenda-se evitar sapatas rasas isoladas em obras de médio/grande porte; adotar Estacas Hélice Contínua Monitorada, estacas escavadas apoiadas no saprolito de micaxisto/gnaisse (N_SPT > 25 a partir de 12m-18m) ou radier protendido sobre colchão de solo-cimento compactado. "
            "2) Bairros Verticais de Goiânia (Setor Marista, Setor Bueno, Setor Oeste, Jardim Goiás / Parque Flamboyant): presença de lentes de argila hidromórfica mole e lençol freático elevado nas bacias dos córregos Cascavel, Vaca Brava, Botafogo e Macambira. Subsolos exigem cortinas de estacas secantes ou parede diafragma atirantada e verificação de subpressão hidrostática. "
            "3) Pirenópolis e Chapada dos Veadeiros (Alto Paraíso/Cavalcante): terrenos em encosta íngreme com afloramentos de quartzito e rocha sã rasa (N_SPT impenetrável < 3m). Ideal para sapatas ancoradas em rocha com chumbadores químicos/tirantes protendidos para equilibrar grandes balanços panorâmicos sobre o vale. "
            "4) Caldas Novas e Rio Quente: lençol hidrotermal com águas sulfurosas/termais (40°C a 57°C), exigindo Classe de Agressividade Ambiental CAA III ou IV (NBR 6118), concreto com adição de sílica ativa/pozolana e cobrimento nominal de 45mm a 50mm."
        ),
        "technical_metadata": {
            "soil_types": ["Latossolo Vermelho Colapsível", "Saprolito de Micaxisto/Gnaisse", "Quartzito Pirenópolis"],
            "recommended_foundations": ["Estaca Hélice Contínua Monitorada", "Ancoragem em Rocha com Tirantes", "Cortina Atirantada"],
            "state": "GO",
        },
    },
    {
        "category": "norma_nacional",
        "region_country": "BR-GO",
        "title": "Legislação Urbana de Goiânia — Plano Diretor (LC 349/2022), Código de Obras (LC 363/2023) e CBMGO",
        "content": (
            "Parâmetros normativos municipais e estaduais obrigatórios em Goiânia e Goiás: "
            "1) Plano Diretor de Goiânia (Lei Complementar nº 349/2022): disciplina a Macrozona Construída, eixos de desenvolvimento (BRT Norte-Sul e Anhanguera), Outorga Onerosa do Direito de Construir (OODC) e exigência estrita de Taxa de Permeabilidade mínima (15% a 25% do lote) combinada com Caixa de Recarga do Lençol Freático / Reservatório de Retenção Pluvial para combater alagamentos na bacia do Meia Ponte. "
            "2) Código de Obras e Edificações de Goiânia (Lei Complementar nº 363/2023): define recuos frontais mínimos (5,0m em vias arteriais/coletoras), afastamentos laterais e de fundos escalonados pela altura H da edificação, pé-direito mínimo de 2,70m (residencial) e 3,00m a 3,50m (comercial/térreo ativo), além de ventilação e iluminação zenital/prismas. "
            "3) Corpo de Bombeiros Militar do Estado de Goiás (CBMGO — NT 01, NT 08 e NT 11): resistência ao fogo das estruturas (TRRF de 60 a 120 min conforme altura conforme NBR 15200 / NBR 14323), escadas enclausuradas à prova de fumaça e distância máxima a percorrer até saídas de emergência."
        ),
        "technical_metadata": {
            "laws": ["LC 349/2022 (Plano Diretor Goiânia)", "LC 363/2023 (Código de Obras Goiânia)", "CBMGO NT-01/NT-08/NT-11"],
            "municipality": "Goiânia - GO",
            "state": "GO",
        },
    },
    {
        "category": "calculo_estrutural",
        "region_country": "BR-GO",
        "title": "Clima, Ventos do Cerrado (NBR 6123), Zona Bioclimática 6/7 (NBR 15220) e Custos SINAPI-GO / SINDUSCON-GO",
        "content": (
            "Parâmetros ambientais, de vento, reologia do concreto e custos em Goiás: "
            "1) Ventos em Goiás (NBR 6123): Velocidade básica V0 = 30 m/s a 35 m/s (isopletas de Goiás). Em platôs elevados e morros (Morro do Além, Serrinha, Setor Bueno/Marista alto e encostas de Pirenópolis/Chapada), o Fator Topográfico S1 sobe para 1,10 a 1,25. Atenção crítica às tempestades convectivas de transição seca-chuva no Cerrado (setembro a novembro), que produzem rajadas descendentes (downbursts) e sucção severa (Cp = -1,2 a -1,8) em grandes coberturas metálicas e beirais em balanço. "
            "2) Retração e Dilatação Térmica no Cerrado (NBR 6118 & NBR 15220 - Zona Bioclimática 6 em Goiânia/Anápolis e Zona 7 no Araguaia): durante a estiagem (maio a setembro), a umidade relativa cai abaixo de 15% com insolação intensa, duplicando a deformação específica por retração hidráulica (epsilon_cs) e exigindo cura úmida rigorosa / aditivos redutores de retração, além de dimensionamento para variação térmica uniforme Delta_T = 25°C a 30°C em estruturas aparentes. "
            "3) Custos Regionais SINAPI-GO / CUB SINDUSCON-GO: Concreto usinado C35/C40 bombeado em Goiânia (~R$ 540 a R$ 650/m³), Aço CA-50 cortado/dobrado (~R$ 8,20 a R$ 9,50/kg), Estrutura Metálica ASTM A572 montada (~R$ 16,50 a R$ 21,00/kg), Pedra de Pirenópolis aplicada (~R$ 180 a R$ 340/m²)."
        ),
        "technical_metadata": {
            "wind_v0_ms": 35.0,
            "bioclimatic_zone": "ZB6 (Goiânia/Anápolis) e ZB7 (Vale do Araguaia)",
            "sinapi_cub_region": "GO (SINDUSCON-GO / SINAPI-GO)",
            "state": "GO",
        },
    },
]


async def scrape_and_seed_goias_knowledge(force_network: bool = False) -> dict[str, Any]:
    """
    Executa o scraping de páginas públicas de Goiás (quando force_network=True)
    e garante que todo o corpus técnico, normativo, geotécnico e artístico-arquitetônico
    de Goiás (BR-GO) esteja indexado na tabela_vet (`knowledge_vectors`).
    """
    scraped_snippets: list[dict[str, str]] = []

    if force_network:
        async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
            for src in GOIAS_PUBLIC_SOURCES:
                try:
                    resp = await client.get(src["url"])
                    if resp.status_code == 200 and resp.text:
                        if BeautifulSoup is not None:
                            soup = BeautifulSoup(resp.text, "html.parser")
                            for tag in soup(["script", "style", "nav", "footer"]):
                                tag.decompose()
                            title = (soup.title.string.strip() if soup.title and soup.title.string else src["source_name"])
                            paragraphs = [
                                p.get_text(" ", strip=True)
                                for p in soup.find_all(["p", "h1", "h2", "h3", "li"])
                                if len(p.get_text(" ", strip=True)) > 40
                            ]
                            snippet = " ".join(paragraphs[:8])[:1200]
                        else:
                            clean_txt = re.sub(r"<[^>]+>", " ", resp.text)
                            snippet = re.sub(r"\s+", " ", clean_txt).strip()[:1200]
                            title = src["source_name"]
                        if snippet:
                            scraped_snippets.append(
                                {
                                    "url": src["url"],
                                    "source_name": src["source_name"],
                                    "category": src["category"],
                                    "title": f"[Web Scrape GO] {title[:180]}",
                                    "content": f"Fonte Oficial ({src['url']}): {snippet}",
                                }
                            )
                except Exception:
                    continue

    inserted_count = 0
    async with AsyncSessionLocal() as db:
        existing_res = await db.execute(
            select(KnowledgeVector.title).where(KnowledgeVector.region_country == "BR-GO")
        )
        existing_titles = set(existing_res.scalars().all())

        all_items = list(GOIAS_CURATED_CORPUS)
        for s in scraped_snippets:
            all_items.append(
                {
                    "category": s["category"],
                    "region_country": "BR-GO",
                    "title": s["title"],
                    "content": s["content"],
                    "technical_metadata": {"source_url": s["url"], "scraped": True, "state": "GO"},
                }
            )

        for item in all_items:
            if item["title"] in existing_titles:
                continue
            emb = get_embedding(f"{item['title']} {item['content']}")
            row = KnowledgeVector(
                user_id=None,
                category=item["category"],
                region_country=item["region_country"],
                title=item["title"],
                content=item["content"],
                technical_metadata=item.get("technical_metadata", {}),
                embedding=emb,
                lifecycle="active",
            )
            db.add(row)
            existing_titles.add(item["title"])
            inserted_count += 1

        if inserted_count > 0:
            await db.commit()

    return {
        "status": "ok",
        "region": "BR-GO",
        "inserted_count": inserted_count,
        "total_goias_entries": len(existing_titles),
        "scraped_live_pages": len(scraped_snippets),
    }

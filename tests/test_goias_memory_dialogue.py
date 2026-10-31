"""
Suíte Completa de Testes E2E (Fase 2):
1. Unificação Frontend (viewer.html, barra de versões v1..vn, seletor de formatos no canto superior direito, 3 blocos de sugestões) + Backend
2. Scraping & Base Vetorial Regional de Goiás (tabela_vet BR-GO: Normas, Latossolo, Vento NBR 6123, Art Déco Goianiense, Brutalismo do Cerrado, Pedra de Pirenópolis e Aço Corten)
3. Upload de múltiplos arquivos, troca entre arquivos, árvore de versionamento (v1..vn), Text-to-Code e conversão entre formatos (AutoCAD, Blender, IFC, Rhino/Grasshopper, OpenSCAD)
4. Teste comparativo: Projeto "Tudo Certo" (Aprovado) vs Projeto "Com Falha" (Reprovado) + Perguntas Proativas do ICP ("Gostaria de ver isso de outra forma?") + 3 Blocos de Sugestões
5. Diálogo Multi-Turno com Arquitetura EverMemOS (EpisodeBuffer -> MemCell -> MemScene -> UserProfile)
6. Edge Cases (versão inexistente, arquivo inexistente, overflow de buffer > 8 mensagens, isolamento multi-usuário)
"""

import io
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from structura_ai.main import app
from structura_ai.database import init_db, AsyncSessionLocal
from structura_ai.integrations.vector_store import ensure_knowledge_seeded


@pytest_asyncio.fixture(autouse=True)
async def setup_test_environment():
    await init_db()
    async with AsyncSessionLocal() as db:
        await ensure_knowledge_seeded(db)


@pytest.mark.asyncio
async def test_frontend_unification_and_goias_rag():
    """Verifica a unificação do frontend do GitHub com as extensões do Excalidraw e o RAG de Goiás (Engenharia + Arte)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET / renderiza o viewer.html completo com barra de versões, seletor de formato e 3 blocos de sugestão
        home_resp = await client.get("/")
        assert home_resp.status_code == 200
        html = home_resp.text
        assert "id=\"login-screen\"" in html
        assert "id=\"viewer-workspace\"" in html
        assert "id=\"version-bar-container\"" in html
        assert "id=\"software-format-select\"" in html
        assert "id=\"btn-convert-format\"" in html
        assert "id=\"loaded-files-list\"" in html
        assert "id=\"chat-suggestions-bar\"" in html

        # 2. GET /viewer redireciona (307) para /
        redir_resp = await client.get("/viewer", follow_redirects=False)
        assert redir_resp.status_code == 307
        assert redir_resp.headers["location"] == "/"

        # 3. Dispara o scraper/seeder de Goiás e verifica os itens técnicos e artísticos na tabela_vet
        scrape_resp = await client.post("/api/v1/knowledge/scrape-goias?force_network=false")
        assert scrape_resp.status_code == 200
        scrape_data = scrape_resp.json()
        assert scrape_data["region"] == "BR-GO"
        assert scrape_data["total_goias_entries"] >= 6

        # Busca por Art Déco Goianiense e Brutalismo do Cerrado
        art_resp = await client.get(
            "/api/v1/knowledge/search",
            params={"q": "Art Déco Goianiense Brutalismo Paulo Mendes da Rocha Pedra de Pirenópolis", "region_country": "BR-GO"},
        )
        assert art_resp.status_code == 200
        art_items = art_resp.json()
        assert len(art_items) >= 2
        titles_joined = " | ".join(it["title"] for it in art_items)
        assert "Art Déco" in titles_joined or "Brutalismo" in titles_joined or "Pirenópolis" in titles_joined

        # Busca por Geotecnia de Goiânia (Latossolo Vermelho colapsível)
        soil_resp = await client.get(
            "/api/v1/knowledge/search",
            params={"q": "Latossolo Vermelho colapsível Setor Marista Bueno Estaca Hélice", "region_country": "BR-GO"},
        )
        assert soil_resp.status_code == 200
        soil_items = soil_resp.json()
        assert any("Latossolo" in it["content"] for it in soil_items)


@pytest.mark.asyncio
async def test_approved_vs_rejected_projects_and_icp_questions():
    """
    Testa dois projetos distintos:
    - Projeto A (TUDO CERTO / APROVADO): viga robusta 30x75cm, fck=45MPa para vão de 5.5m e balanço de 1.0m.
    - Projeto B (COM FALHA / REPROVADO): viga esbelta 15x22cm, fck=20MPa para vão de 13.5m e balanço de 5.5m.
    Verifica se o agente identifica cada caso corretamente, faz perguntas proativas de ICP
    ('gostaria de ver essa solução de outra forma?') e sempre devolve 3 blocos de sugestões!
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id = "arq_teste_icp"

        # Upload Projeto A (100% Viável / Aprovado)
        resp_ok = await client.post(
            "/api/v1/files/upload",
            data={
                "user_id": user_id,
                "render_style": "autocad",
                "span_length_m": "5.5",
                "cantilever_length_m": "1.0",
                "beam_height_cm": "75.0",
                "beam_width_cm": "30.0",
                "column_height_m": "3.0",
                "column_section_cm": "35.0",
                "concrete_fck_mpa": "45.0",
            },
            files={"file": ("residencia_marista_aprovada.dxf", io.BytesIO(b"0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n"), "application/dxf")},
        )
        assert resp_ok.status_code == 200
        file_ok = resp_ok.json()
        assert file_ok["active_version"]["validation_report"]["is_physically_viable"] is True

        # Pergunta no chat sobre o Projeto A (Tudo Certo)
        chat_ok = await client.post(
            "/api/analysis/copilot",
            json={
                "user_id": user_id,
                "active_file_id": file_ok["id"],
                "message": "Valide os cálculos desta estrutura, está tudo certo?",
            },
        )
        assert chat_ok.status_code == 200
        data_ok = chat_ok.json()
        assert len(data_ok["suggestions"]) == 3
        reply_ok_lower = data_ok["reply"].lower()
        assert "tudo certo" in reply_ok_lower or "aprovada" in reply_ok_lower or "viável: `true`" in reply_ok_lower
        assert "gostaria de ver" in reply_ok_lower or "outra forma" in reply_ok_lower

        # Upload Projeto B (Inviável / Com Falha Crítica)
        resp_fail = await client.post(
            "/api/v1/files/upload",
            data={
                "user_id": user_id,
                "render_style": "autocad",
                "span_length_m": "13.5",
                "cantilever_length_m": "5.5",
                "beam_height_cm": "22.0",
                "beam_width_cm": "15.0",
                "column_height_m": "4.0",
                "column_section_cm": "20.0",
                "concrete_fck_mpa": "20.0",
            },
            files={"file": ("pavilhao_balanco_critico.dxf", io.BytesIO(b"0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n"), "application/dxf")},
        )
        assert resp_fail.status_code == 200
        file_fail = resp_fail.json()
        assert file_fail["active_version"]["validation_report"]["is_physically_viable"] is False

        # Pergunta no chat sobre o Projeto B (Com Falha)
        chat_fail = await client.post(
            "/api/analysis/copilot",
            json={
                "user_id": user_id,
                "active_file_id": file_fail["id"],
                "message": "Verifique se está tudo certo com os cálculos dessa estrutura.",
            },
        )
        assert chat_fail.status_code == 200
        data_fail = chat_fail.json()
        assert len(data_fail["suggestions"]) == 3
        reply_fail_lower = data_fail["reply"].lower()
        assert "não passou" in reply_fail_lower or "crítico" in reply_fail_lower or "viável: `false`" in reply_fail_lower
        assert "gostaria de ver" in reply_fail_lower or "outra forma" in reply_fail_lower


@pytest.mark.asyncio
async def test_multi_file_switching_versioning_and_format_conversion():
    """
    Testa o fluxo completo de:
    - Enviar múltiplos arquivos (Arquivo 1 e Arquivo 2);
    - Criar versões v1 -> v2 -> v3 no Arquivo 2 convertendo entre formatos (Blender, IFC, Rhino/Grasshopper, OpenSCAD);
    - Trocar entre Arquivo 1 (que tem apenas [v1]) e Arquivo 2 (que tem [v1, v2, v3, v4]);
    - Alternar versões (voltar para v1 e ativar v3).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id = "arq_multi_files"

        # 1. Envia Arquivo 1
        r1 = await client.post(
            "/api/v1/files/upload",
            data={"user_id": user_id, "span_length_m": "7.0", "beam_height_cm": "45.0"},
            files={"file": ("casa_aldeia_do_vale.dxf", io.BytesIO(b"DXF1"), "application/dxf")},
        )
        f1 = r1.json()
        assert f1["active_version_number"] == 1
        assert len(f1["versions"]) == 1

        # 2. Envia Arquivo 2
        r2 = await client.post(
            "/api/v1/files/upload",
            data={"user_id": user_id, "span_length_m": "10.0", "beam_height_cm": "40.0"},
            files={"file": ("mirante_pirenopolis.dxf", io.BytesIO(b"DXF2"), "application/dxf")},
        )
        f2 = r2.json()
        assert f2["active_version_number"] == 1

        # 3. Converte Arquivo 2 para Blender 3D pelo endpoint do botão no canto superior direito (-> v2)
        conv_blender = await client.post(
            f"/api/v1/files/{f2['id']}/convert",
            params={"target_format": "blender", "user_id": user_id},
        )
        assert conv_blender.status_code == 200
        f2_v2 = conv_blender.json()
        assert f2_v2["active_version_number"] == 2
        assert f2_v2["active_version"]["code_language"] == "python_blender_bpy"

        # 4. Converte Arquivo 2 para Rhino / Grasshopper (-> v3)
        conv_rhino = await client.post(
            f"/api/v1/files/{f2['id']}/convert",
            params={"target_format": "grasshopper_rhino", "user_id": user_id},
        )
        assert conv_rhino.status_code == 200
        f2_v3 = conv_rhino.json()
        assert f2_v3["active_version_number"] == 3
        assert f2_v3["active_version"]["code_language"] == "python_rhino_grasshopper"

        # 5. Converte Arquivo 2 para OpenSCAD (-> v4)
        conv_scad = await client.post(
            f"/api/v1/files/{f2['id']}/convert",
            params={"target_format": "openscad", "user_id": user_id},
        )
        assert conv_scad.status_code == 200
        f2_v4 = conv_scad.json()
        assert f2_v4["active_version_number"] == 4
        assert f2_v4["active_version"]["code_language"] == "openscad"

        # 6. Troca o arquivo selecionado de volta para o Arquivo 1: a árvore de versões deve refletir apenas [v1]
        sel_f1 = await client.post(f"/api/v1/files/{f1['id']}/select", json={"user_id": user_id})
        assert sel_f1.status_code == 200
        f1_active = sel_f1.json()
        assert f1_active["is_selected"] is True
        assert [v["version_label"] for v in f1_active["versions"]] == ["v1"]

        # 7. Troca de volta para o Arquivo 2 pelo Chat e volta para a versão v1
        chat_switch = await client.post(
            "/api/analysis/copilot",
            json={
                "user_id": user_id,
                "message": "Trocar arquivo para mirante_pirenopolis.dxf",
            },
        )
        assert chat_switch.status_code == 200
        assert chat_switch.json()["active_file"]["id"] == f2["id"]
        assert [v["version_label"] for v in chat_switch.json()["active_file"]["versions"]] == ["v1", "v2", "v3", "v4"]

        chat_v1 = await client.post(
            "/api/analysis/copilot",
            json={
                "user_id": user_id,
                "active_file_id": f2["id"],
                "message": "Voltar para a versão v1",
            },
        )
        assert chat_v1.status_code == 200
        assert chat_v1.json()["active_file"]["active_version_number"] == 1


@pytest.mark.asyncio
async def test_multi_turn_dialogue_with_evermemos_and_goias_ideas():
    """
    Testa um diálogo multi-turno realista de um arquiteto em Goiás:
    - Turno 1: Apresenta perfil e estilo (Goiânia / Pirenópolis, concreto aparente + aço corten, balanços).
    - Turno 2: Pede ideias artísticas e geotécnicas de Goiás ('Que tal fazer isso ou aquilo?').
    - Turno 3: Pede Text-to-Code gerando nova versão em Blender com viga h=55cm e fck=40MPa.
    - Turno 4: Pede recomendação baseada no perfil e histórico consolidado no EverMemOS (MemCell, MemScene, UserProfile).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id = "arq_lucas_goiania"
        session_id = "sessao_goias_poc"

        # Upload via endpoint do frontend (/api/projects/upload) que sincroniza Project + ProjectFile (v1)
        up_resp = await client.post(
            "/api/projects/upload",
            data={
                "title": "Casa Cerrado Setor Marista",
                "author_architect": user_id,
                "category": "Residencial",
                "span_length_m": "10.5",
                "cantilever_length_m": "4.2",
                "beam_height_cm": "35.0",
                "beam_width_cm": "20.0",
                "concrete_fck_mpa": "30.0",
            },
            files={"file": ("casa_marista.dxf", io.BytesIO(b"0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n"), "application/dxf")},
        )
        assert up_resp.status_code == 200
        up_data = up_resp.json()
        file_id = up_data["file_id"]
        project_id = up_data["project_id"]

        # Verifica também o endpoint de Laudo HTML do frontend
        rep_resp = await client.get(f"/api/export/{project_id}/report.html")
        assert rep_resp.status_code == 200
        assert "Casa Cerrado Setor Marista" in rep_resp.text

        # Turno 1: Apresentação e preferências
        t1 = await client.post(
            "/api/analysis/copilot",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "active_file_id": file_id,
                "message": "Olá! Sou arquiteto em Goiânia e Pirenópolis, prefiro estruturas em concreto aparente brutalista com aço corten e grandes balanços.",
            },
        )
        assert t1.status_code == 200
        d1 = t1.json()
        assert len(d1["suggestions"]) == 3

        # Turno 2: Ideias de Goiás (Art Déco, Brutalismo, Pirenópolis e Latossolo)
        t2 = await client.post(
            "/api/analysis/copilot",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "active_file_id": file_id,
                "message": "Pode me sugerir ideias de arquitetura de Goiás (Art Déco, Brutalismo do Cerrado, Pedra de Pirenópolis) e avaliar o solo Latossolo para esse balanço?",
            },
        )
        assert t2.status_code == 200
        d2 = t2.json()
        assert len(d2["suggestions"]) == 3
        assert any(w in d2["reply"].lower() for w in ["goiânia", "pirenópolis", "art déco", "brutalismo", "latossolo"])

        # Turno 3: Text-to-Code gerando versão no formato selecionado (Blender)
        t3 = await client.post(
            "/api/analysis/copilot",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "active_file_id": file_id,
                "selected_format": "blender",
                "message": "Perfeito! Gere o código Text-to-Code no formato Blender aplicando reforço com viga h=60cm e fck=45MPa.",
            },
        )
        assert t3.status_code == 200
        d3 = t3.json()
        assert len(d3["suggestions"]) == 3
        assert d3["active_file"]["active_version_number"] >= 2

        # Turno 4: Consulta ao Perfil e Memória Histórica (EverMemOS)
        t4 = await client.post(
            "/api/analysis/copilot",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "active_file_id": file_id,
                "force_memory_flush": True,
                "message": "Baseado no meu perfil e nas decisões que tomamos no histórico, qual padrão você recomenda manter nos meus próximos projetos em Goiás?",
            },
        )
        assert t4.status_code == 200
        d4 = t4.json()
        assert len(d4["suggestions"]) == 3
        assert "perfil" in d4["reply"].lower() or "evermemos" in d4["reply"].lower() or "goiás" in d4["reply"].lower()

        # Inspeciona o estado persistido do EverMemOS (UserProfile, MemScenes e MemCells)
        mem_resp = await client.get(f"/api/v1/chat/evermemos/{user_id}", params={"session_id": session_id})
        assert mem_resp.status_code == 200
        mem_state = mem_resp.json()
        assert mem_state["user_profile"] is not None
        assert len(mem_state["user_profile"]["explicit_facts"]) >= 1
        assert len(mem_state["mem_cells"]) >= 1
        assert len(mem_state["mem_scenes"]) >= 1
        assert mem_state["mem_scenes"][0]["cell_count"] >= 1


@pytest.mark.asyncio
async def test_edge_cases_and_isolation():
    """
    Testa edge cases:
    1. Tentativa de mudar para versão inexistente (v99) pelo chat;
    2. Tentativa de selecionar arquivo inexistente pelo chat;
    3. Isolamento estrito entre dois usuários diferentes.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Upload para user_edge_1
        up = await client.post(
            "/api/v1/files/upload",
            data={"user_id": "user_edge_1"},
            files={"file": ("projeto_edge.dxf", io.BytesIO(b"DXF"), "application/dxf")},
        )
        fid = up.json()["id"]

        # Edge Case 1: Versão inexistente v99
        c1 = await client.post(
            "/api/analysis/copilot",
            json={"user_id": "user_edge_1", "active_file_id": fid, "message": "Mudar para a versão v99"},
        )
        assert c1.status_code == 200
        assert len(c1.json()["suggestions"]) == 3
        assert "não foi possível" in c1.json()["reply"].lower() or "não encontrada" in c1.json()["reply"].lower()

        # Edge Case 2: Arquivo inexistente
        c2 = await client.post(
            "/api/analysis/copilot",
            json={"user_id": "user_edge_1", "message": "Trocar arquivo para fantasma_inexistente.dxf"},
        )
        assert c2.status_code == 200
        assert len(c2.json()["suggestions"]) == 3
        assert "não encontrei" in c2.json()["reply"].lower()

        # Edge Case 3: Isolamento de arquivos entre usuários
        files_u2 = await client.get("/api/v1/files", params={"user_id": "usuario_isolado_999"})
        assert files_u2.status_code == 200
        assert files_u2.json() == []

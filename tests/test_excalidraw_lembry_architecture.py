"""
Suite Completa de Testes da Arquitetura Excalidraw + Stack Lembry (Agno Agents, Versionamento v1..vn,
Troca de Arquivos, Mudança de Estilo AutoCAD/Blender, Tool de Código e 3 Tabelas de Banco + RAG).
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from structura_ai.agents.chatbot.conversational.agent import build_conversational_agent
from structura_ai.agents.chatbot.genai.agent import build_genai_agent
from structura_ai.agents.chatbot.search_rag.agent import build_search_rag_agent
from structura_ai.agents.chatbot.suggester.agent import build_suggester_agent
from structura_ai.agents.chatbot.validator.agent import build_validator_agent
from structura_ai.database import AsyncSessionLocal, init_db
from structura_ai.integrations.vector_store import ensure_knowledge_seeded
from structura_ai.main import app


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    await init_db()
    async with AsyncSessionLocal() as db:
        await ensure_knowledge_seeded(db)


def test_lembry_agent_loader_and_5_agents_instantiation():
    """
    Garante que todos os 5 agentes (Conversacional, Validador, Busca/RAG, Sugestão e GenAI)
    seguem o padrão Lembry (`config.yaml` + `agent.py` via `build_agent`) com Gemini default.
    """
    deps = {
        "user_id": "test_arch_1",
        "region_country": "BR",
        "active_file_summary": "planta.dxf (v1)",
        "workspace_files_summary": "- planta.dxf (v1)",
        "memory_context_section": "",
    }
    conv = build_conversational_agent(dependencies=deps)
    val = build_validator_agent(dependencies=deps)
    rag = build_search_rag_agent(dependencies=deps)
    sug = build_suggester_agent(dependencies=deps)
    gen = build_genai_agent(dependencies=deps)

    assert conv.name == "Structura.AI Copiloto Conversacional"
    assert val.name == "Agente Validador Estrutural"
    assert rag.name == "Agente de Busca de Cálculos, Edificações e RAG"
    assert sug.name == "Agente de Sugestão Estrutural & Paisagens (Diferencial)"
    assert gen.name == "Agente de Gen AI & Código CAD/BIM"
    assert len(conv.tools) >= 9


@pytest.mark.asyncio
async def test_multi_file_upload_versioning_and_style_switching():
    """
    Testa o fluxo central do Excalidraw:
    - Carregar múltiplos arquivos (`residencia_a.dxf` e `torre_b.ifc`);
    - Cada arquivo possui sua própria árvore de versões (`v1..vn`);
    - Mudar estilo (`autocad` -> `blender`) cria `v2` no arquivo ativo;
    - Alternar entre arquivos carregados muda a árvore de versões ativa no topo.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload do Arquivo A
        resp_a = await client.post(
            "/api/v1/files/upload",
            data={
                "user_id": "user_excali",
                "render_style": "autocad",
                "span_length_m": "10.0",
                "cantilever_length_m": "3.5",
            },
            files={"file": ("residencia_a.dxf", b"0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF", "application/dxf")},
        )
        assert resp_a.status_code == 200
        file_a = resp_a.json()
        assert file_a["filename"] == "residencia_a.dxf"
        assert file_a["active_version_number"] == 1
        assert len(file_a["versions"]) == 1
        assert file_a["versions"][0]["version_label"] == "v1"

        # 2. Muda estilo do Arquivo A para Blender (gera v2 no Arquivo A)
        style_resp = await client.post(
            f"/api/v1/files/{file_a['id']}/style",
            json={
                "render_style": "blender",
                "landscape_context": "encosta_montanhosa",
                "create_new_version": True,
                "user_id": "user_excali",
            },
        )
        assert style_resp.status_code == 200
        file_a_v2 = style_resp.json()
        assert file_a_v2["active_version_number"] == 2
        assert [v["version_label"] for v in file_a_v2["versions"]] == ["v1", "v2"]
        assert file_a_v2["active_version"]["render_style"] == "blender"

        # 3. Upload do Arquivo B (possui apenas v1 inicialmente)
        resp_b = await client.post(
            "/api/v1/files/upload",
            data={
                "user_id": "user_excali",
                "render_style": "autocad",
                "span_length_m": "7.5",
                "cantilever_length_m": "1.5",
            },
            files={"file": ("pavilhao_b.dxf", b"0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF", "application/dxf")},
        )
        assert resp_b.status_code == 200
        file_b = resp_b.json()
        assert file_b["is_selected"] is True
        assert [v["version_label"] for v in file_b["versions"]] == ["v1"]

        # 4. Seleciona de volta o Arquivo A -> árvore no topo volta a mostrar [v1, v2]
        sel_resp = await client.post(
            f"/api/v1/files/{file_a['id']}/select",
            json={"user_id": "user_excali"},
        )
        assert sel_resp.status_code == 200
        selected_a = sel_resp.json()
        assert selected_a["id"] == file_a["id"]
        assert selected_a["is_selected"] is True
        assert [v["version_label"] for v in selected_a["versions"]] == ["v1", "v2"]


@pytest.mark.asyncio
async def test_chat_controls_version_style_code_validator_suggester_and_rag():
    """
    Testa todas as interações do Chat Copiloto desenhadas no Excalidraw:
    1. 'chat pode alterar versão se pedir' (voltar para v1);
    2. 'chat pode mudar estilo (formato autocad, formato blender)';
    3. 'Tool de código para gerar o que precisar na linguagem/formato do arquivo';
    4. 'Agente Validador (valida se os cálculos fazem sentido)';
    5. 'Agente de Sugestão (sugere modificações de cálculo/estrutura + visuais em paisagens)';
    6. 'Agente de Busca & RAG (`tabela_vet`: normas nacionais/internacionais e relevo)';
    7. Persistência nas 3 tabelas (`user_memory_decisions`, `knowledge_vectors`, `project_files`/`file_versions`).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Cria arquivo inicial v1
        up = await client.post(
            "/api/v1/files/upload",
            data={"user_id": "arch_copilot", "render_style": "autocad", "span_length_m": "11.0", "cantilever_length_m": "4.0"},
            files={"file": ("mirante_alpino.dxf", b"0\nSECTION\n0\nEOF", "application/dxf")},
        )
        file_id = up.json()["id"]

        # A) Chat muda estilo para Blender -> cria v2
        chat_style = await client.post(
            "/api/v1/chat/message",
            json={
                "message": "Por favor, mudar estilo para formato blender",
                "user_id": "arch_copilot",
                "session_id": "sess_01",
                "active_file_id": file_id,
            },
        )
        assert chat_style.status_code == 200
        cs_data = chat_style.json()
        assert cs_data["active_file"]["active_version_number"] == 2
        assert any(m["action"] == "style_changed" for m in cs_data["ui_mutations"])

        # B) Chat pede para voltar para a v1
        chat_ver = await client.post(
            "/api/v1/chat/message",
            json={
                "message": "Voltar para a versão v1",
                "user_id": "arch_copilot",
                "session_id": "sess_01",
                "active_file_id": file_id,
            },
        )
        assert chat_ver.status_code == 200
        cv_data = chat_ver.json()
        assert cv_data["active_file"]["active_version_number"] == 1
        assert any(m["action"] == "version_switched" for m in cv_data["ui_mutations"])

        # C) Chat aciona Tool de Código para gerar script/arquivo AutoCAD DXF -> cria v3
        chat_code = await client.post(
            "/api/v1/chat/message",
            json={
                "message": "Gerar código dxf aumentando a altura da viga principal para 60cm",
                "user_id": "arch_copilot",
                "session_id": "sess_01",
                "active_file_id": file_id,
            },
        )
        assert chat_code.status_code == 200
        cc_data = chat_code.json()
        assert cc_data["active_file"]["active_version_number"] == 3
        assert cc_data["active_file"]["active_version"]["code_language"] == "python_ezdxf_autocad"

        # D) Chat aciona Agente de Sugestão (Diferencial: cálculo + visual em paisagem de encosta) -> cria v4
        chat_sug = await client.post(
            "/api/v1/chat/message",
            json={
                "message": "Pode sugerir modificações estruturais e gerar visual em paisagem de encosta montanhosa?",
                "user_id": "arch_copilot",
                "session_id": "sess_01",
                "active_file_id": file_id,
            },
        )
        assert chat_sug.status_code == 200
        csug_data = chat_sug.json()
        assert csug_data["active_file"]["active_version_number"] == 4
        assert csug_data["active_file"]["active_version"]["landscape_context"] == "encosta_montanhosa"

        # E) Chat consulta Agente de Busca & RAG para normas internacionais (Eurocode / Europa)
        chat_rag = await client.post(
            "/api/v1/chat/message",
            json={
                "message": "Buscar na norma Eurocode limites de flecha e sismo para projetar no exterior",
                "user_id": "arch_copilot",
                "session_id": "sess_01",
                "active_file_id": file_id,
                "region_country": "EU",
            },
        )
        assert chat_rag.status_code == 200
        assert "Eurocode" in chat_rag.json()["reply"]

        # F) Verifica Tabela 1 (`user_memory_decisions`) e Tabela 2 (`knowledge_vectors` / `tabela_vet`)
        mem_resp = await client.get("/api/v1/chat/memory", params={"user_id": "arch_copilot"})
        assert mem_resp.status_code == 200
        assert len(mem_resp.json()) >= 4

        rag_resp = await client.get("/api/v1/knowledge/search", params={"q": "encosta montanhosa talude fundação"})
        assert rag_resp.status_code == 200
        assert len(rag_resp.json()) >= 1

        # G) Testa Streaming SSE (`/api/v1/chat/stream`)
        sse_resp = await client.post(
            "/api/v1/chat/stream",
            json={
                "message": "Validar se os cálculos estruturais fazem sentido",
                "user_id": "arch_copilot",
                "session_id": "sess_01",
                "active_file_id": file_id,
            },
        )
        assert sse_resp.status_code == 200
        assert "data:" in sse_resp.text
        assert '"type": "done"' in sse_resp.text

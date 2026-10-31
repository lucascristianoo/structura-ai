# Structura.AI — Backend API & Orquestrador de Agentes (Padrão Lembry + Arquitetura Excalidraw)

Backend enxuto em **FastAPI + Agno Agents + PostgreSQL (`pgvector`)** com motor físico-estrutural determinístico (`Euler-Bernoulli`, `DSM 2D`, `OptiSection`) e ingestão/exportação nativa de arquivos CAD/BIM (`AutoCAD DXF`, `Blender Python bpy`, `IFC4`, `OBJ/STL`).

---

## 🏛️ Arquitetura do Projeto

### 1. Stack de Agentes (Padrão `Lembry.Chatbot`)
Cada agente reside em `structura_ai/agents/chatbot/<nome>/` com o par estrito `config.yaml` (modelo Gemini gratuito por padrão) + `agent.py` (`build_<nome>_agent()` via `agent_loader.py`):
- **`conversational/`**: Copiloto principal com memória de sessão Agno e controle de fan-out (`sub_agente_slot()`).
- **`validator/` (Agente Validador)**: Valida se os cálculos estruturais fazem sentido físico e normativo (`NBR 6118`, `Eurocode 2`, `ACI 318`, `BSLJ Japão`).
- **`search_rag/` (Agente de Busca & RAG)**: Busca híbrida RRF (`tabela_vet`) sobre normas nacionais/internacionais, tipos de edificações, relevo/geotecnia e histórico de projetos do próprio arquiteto.
- **`suggester/` (Agente de Sugestão — Diferencial)**: Sugere modificações de cálculo/estrutura para sanar a "Dor" do projeto e gera visuais em paisagens diferentes (`encosta_montanhosa`, `litoral_maresia`, `urbano_denso`, `alpino_neve`) para dar insights ao arquiteto.
- **`genai/` (Agente de Gen AI + Tool de Código)**: Gera renders visuais e código executável na linguagem/formato do arquivo editado (`AutoCAD DXF/ezdxf`, `Blender bpy`, `IFC4`), criando automaticamente uma nova versão `vN+1`.

### 2. As 3 Camadas do Banco de Dados (`structura_ai/models.py`)
1. **`user_memory_decisions` (Tabela 1 — Memória & Decisões)**: `user_id`, histórico de decisões arquitetônicas/estruturais e aprendizados por sessão/arquivo.
2. **`knowledge_vectors` (Tabela 2 — `tabela_vet` / RAG)**: Base vetorial com busca híbrida **RRF ($k=60$)** contendo normas nacionais e internacionais, relevo/geotecnia, tipologias e aprendizados gerados nos projetos do próprio arquiteto.
3. **`project_files` & `file_versions` (Tabela 3 — Arquivos & Versionamento `v1..vn`)**: Suporta múltiplos arquivos carregados por usuário. Cada arquivo possui sua própria árvore de versões (`v1, v2, ..., vn`). Trocar o arquivo ativo alterna imediatamente as versões exibidas no topo.

---

## 🚀 Como Rodar

### Opção 1: Local rápido (Zero-Config)
```bash
uv sync
.venv/bin/uvicorn structura_ai.main:app --reload --port 8000
```

### Opção 2: Com PostgreSQL 16 + `pgvector` (Docker)
```bash
docker compose up -d db
export DATABASE_URL="postgresql+asyncpg://structura_user:structura_secure_pass_2026@localhost:5432/structura_db"
export POSTGRES_URL="postgresql://structura_user:structura_secure_pass_2026@localhost:5432/structura_db"
.venv/bin/uvicorn structura_ai.main:app --reload --port 8000
```

---

## 🧪 Testes e Samples

```bash
./test.sh            # gera samples (se necessário) + roda toda a suíte
./test.sh --samples  # só os testes de samples (rápido)
./test.sh --regen    # força regerar os samples
./test.sh --check    # valida o manifest versionado (CI)
```

- `tests/samples/` contém ~50 arquivos (DXF, IFC, OBJ/STL/GLB/glTF, SVG, PDF, PNG e `invalid/` corrompidos), gerados por `tests/samples/generate_samples.py`; `manifest.json` guarda os valores esperados.
- `tests/test_samples_rigorous.py` valida vãos, contagens, invariantes, consistência entre formatos/escalas, rejeição de inválidos e desempenho.
- Bugs conhecidos do parser aparecem como `xfail` estrito (`known_issue` no manifest) e avisam quando forem corrigidos.

## 🔌 Contrato da API para o Frontend (`/docs`)

### 1. Arquivos Carregados, Versionamento (`v1..vn`) e Estilo (`AutoCAD` / `Blender`)
- `POST /api/v1/files/upload` (`multipart/form-data`): Carrega arquivo (`dxf`, `ifc`, `obj`, `blend`, `png`), seleciona como ativo e cria a `v1`.
- `GET /api/v1/files?user_id=default_user`: Lista todos os arquivos carregados pelo usuário, indicando qual está ativo (`is_selected=true`) e sua lista `versions` (`v1..vn`).
- `POST /api/v1/files/{file_id}/select`: Seleciona outro arquivo carregado (atualiza as versões `v1..vn` do topo para este arquivo).
- `GET /api/v1/files/{file_id}/versions`: Lista todas as versões `v1..vn` do arquivo.
- `POST /api/v1/files/{file_id}/versions/{version_number}/activate`: Alterna a versão ativa no topo (`1` para `v1`, `2` para `v2`, etc.).
- `POST /api/v1/files/{file_id}/style`: Muda o estilo (`autocad`, `blender`, `wireframe`, `landscape_insight`) e cria `vN+1`.
- `POST /api/v1/files/{file_id}/generate-code`: Executa a **Tool de Código** (`autocad`, `blender`, `ifc`) e cria `vN+1`.

### 2. Chat Copiloto (REST & SSE Streaming)
- `POST /api/v1/chat/message`:
  ```json
  {
    "message": "Mudar estilo para formato blender e validar estrutura",
    "user_id": "arquiteto_01",
    "session_id": "sessao_01",
    "active_file_id": "opcional-uuid",
    "region_country": "BR"
  }
  ```
  Retorna `reply`, `suggestions`, `active_file` (já atualizado com a nova versão/estilo) e `ui_mutations` (lista de eventos `version_switched`, `version_created`, `file_selected`, `style_changed`, `validation_completed`).
- `POST /api/v1/chat/stream`: Streaming **SSE (`text/event-stream`)** emitindo eventos `ui_mutation`, `content` e `done`.
- `GET /api/v1/chat/memory?user_id=arquiteto_01`: Lista a memória e decisões registradas para o arquiteto.

### 3. Base de Conhecimento & RAG (`tabela_vet`)
- `GET /api/v1/knowledge/search?q=balanco+eurocode&region_country=EU`
- `POST /api/v1/knowledge/ingest`

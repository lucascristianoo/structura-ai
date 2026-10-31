# Structura.AI: Backend API e Orquestrador de Agentes

Backend em FastAPI, Agno Agents e PostgreSQL com extensao pgvector, integrando motor fisico-estrutural deterministico (Euler-Bernoulli, DSM 2D e OptiSection) e ingestao/exportacao nativa de arquivos tecnicos CAD/BIM (AutoCAD DXF, Blender Python bpy, IFC4, OBJ e STL).

---

## Arquitetura do Sistema

O sistema adota uma arquitetura em camadas orientada a servicos e copilotos tecnicos baseada no padrao Lembry.Chatbot:

1. **Camada de Orquestracao Agentica**: Cada agente reside no diretorio `structura_ai/agents/chatbot/<nome>/` contendo sua definicao declarativa em `config.yaml` e seu instanciador funcional em `agent.py` atraves do `agent_loader.py`.
2. **Camada de Fisica e Engenharia**: Nucleo deterministico de calculo estrutural que opera independentemente de modelos de linguagem para garantir conformidade normativa (NBR 6118, Eurocode 2, ACI 318 e BSLJ Japao).
3. **Camada de Memoria Episodica e Semantica (EverMemOS)**: Gestao de memoria em tres estagios (celulas de memoria atomicas, agregacao de cenas e perfil consolidado do usuario).
4. **Camada de Persistencia Relacional e Vetorial**: Armazenamento em PostgreSQL 16 com pgvector para historico de versoes de arquivos, decisoes do arquiteto e busca hibrida em normas tecnicas.

---

## Fluxo do Agente: Inputs, Logica e Outputs

A operacao do copiloto Structura.AI segue um pipeline deterministico e rastreavel, estruturado em tres etapas fundamentais:

```
[ Entradas / Inputs ]
  ├── Payload HTTP (mensagem, usuario, sessao, arquivo ativo, formato alvo)
  ├── Geometria e Fisica da Versao Ativa (vao, balanco, secoes, fck, cargas)
  ├── Contexto Regional e Normas (NBR 6118, Eurocode 2, LC 349/2022 Goiania)
  ├── Memoria Recuperada EverMemOS (perfil do arquiteto, cenas anteriores)
  └── Vetores RAG da tabela_vet (chunks tecnicos via busca hibrida RRF k=60)
         │
         ▼
[ Logica de Processamento e Orquestracao ]
  ├── Montagem do RunContext via asyncio.gather
  ├── Avaliacao Normativa e Fisica (Agente Validador + OptiSectionEngine)
  ├── Recuperacao e Ingestao de Normas (Agente Search RAG)
  ├── Geracao de Variantes Estruturais e Regionais (Agente Suggester)
  ├── Sintese Text-to-Code Parametrico (Agente GenAI: DXF, Blender, IFC, OpenSCAD)
  └── Consolidacao de Memoria Episodica no EverMemOS
         │
         ▼
[ Saidas / Outputs ]
  ├── Resposta Conversacional Fundamentada
  ├── 3 Blocos de Sugestao Proativa (<suggestions>)
  ├── Eventos de Mutacao de Interface (ui_mutations: version_created, style_changed)
  ├── Nova Versao Persistida no Banco (FileVersion vN+1 com codigo executavel)
  └── Eventos de Transmissao em Tempo Real (SSE)
```

### 1. Inputs (Entradas)

O agente recebe dados de multiplas fontes sincronizadas no momento da chamada:

- **Payload da Requisicao HTTP**:
  - `message` (str): Comando ou duvida do usuario em linguagem natural.
  - `user_id` (str): Identificador unico do profissional.
  - `session_id` (str): Identificador da sessao de trabalho.
  - `active_file_id` (UUID, opcional): Referencia ao arquivo tecnico atualmente carregado no canvas.
  - `target_format` (str): Formato de software selecionado no cabecalho ou chat (`autocad`, `blender`, `ifc`, `grasshopper_rhino`, `openscad`).
  - `region_country` (str): Codigo de regiao para aplicacao de normas (padrao: `BR`).
- **Contexto Geometria e Fisica da Versao Ativa**:
  - Parametros dimensionais extraidos do arquivo: vao livre (`span`), comprimento de balanco (`cantilever`), largura (`b`) e altura (`h`) de vigas e pilares.
  - Parametros de materiais: resistencia caracteristica do concreto (`fck`), modulo de elasticidade (`E`) e tensao de escoamento do aco (`fyk`).
  - Carregamentos: cargas permanentes (`dead_load`) e acidentais (`live_load`).
- **Contexto Regional e Parametros de Zoneamento**:
  - Normas estruturais aplicaveis: ABNT NBR 6118 (estruturas de concreto), NBR 6123 (forcas devidas ao vento), Eurocode 2, ACI 318 e BSLJ Japao.
  - Legislacao municipal regional: Codigo de Obras e Plano Diretor de Goiania (Lei Complementar 349/2022 e LC 368/2023), incluindo recuos frontais obrigatorios, taxa de ocupacao, permeabilidade e coeficiente de aproveitamento.
- **Memoria Episodica e Perfil do Arquiteto (EverMemOS)**:
  - Perfil consolidado em formato estruturado XML (`<perfil_do_usuario>`) com preferencias esteticas, materiais recorrentes e nivel de aversao a risco estrutural.
  - Historico de celulas de memoria ativas (`MemCell`) e cenas tematicas agrupadas (`MemScene`).
- **Base Vetorial RAG (`tabela_vet`)**:
  - Chunks de conhecimento recuperados via busca hibrida com fusao por posto reciproco (RRF com k=60), combinando busca textual densa e esparsa (BM25 e similaridade por cosseno).

### 2. Logica de Processamento e Orquestracao

O orquestrador processa a requisicao atraves de um pipeline estruturado:

- **Montagem Assincrona do Contexto (`RunContext`)**:
  - O sistema dispara consultas paralelas via `asyncio.gather` para carregar a versao ativa do arquivo, recuperar memorias no EverMemOS e buscar normas tecnicas pertinentes na `tabela_vet`.
- **Roteamento de Subagentes com Controle de Acesso**:
  - O orquestrador distribui subtarefas controlando a concorrencia atraves de semaforos de execucao (`sub_agente_slot`):
    - **Agente Validador**: Submete a geometria ao motor deterministico `Euler-Bernoulli` e `DSM 2D`. Calcula flecha maxima imediata e diferida no tempo, tensao de flexao, forca cortante e carga critica de flambagem de Euler. Em caso de desconformidade, invoca o `OptiSectionEngine` para sugerir secoes comerciais viaveis.
    - **Agente de Busca RAG**: Recupera diretrizes tecnicas especificas para a tipologia do projeto, caracteristicas do solo regional (como o Latossolo Vermelho do Planalto Central) e requisitos de durabilidade ambiental.
    - **Agente de Sugestao (Diferencial)**: Analisa a dor do projeto e formula alternativas de refinamento estrutural e composicao plastica (por exemplo, uso de concreto aparente brutalista, tensores em aco corten ou fechamentos com pedra de Pirenopolis).
    - **Agente GenAI e Tool de Codigo**: Converte a intencao parametrica em codigo fonte executavel no formato selecionado (`ezdxf` para AutoCAD, script Python `bpy` para Blender 4.x, ou criacao de entidades geometricas em IFC4).
- **Consolidacao de Aprendizados e Memoria**:
  - O sistema extrai fatos atomicos da interacao, verifica fronteiras episodicas e atualiza os centroides de cena no EverMemOS, garantindo que as preferencias do arquiteto sejam lembradas nas proximas sessoes.
- **Mecanismo de Fallback Deterministico**:
  - Quando a chave de API de LLM externa nao esta configurada no ambiente, o sistema ativa imediatamente os geradores deterministicos locais, assegurando que calculos, geracao de codigo e criacao de versoes continuem operando perfeitamente.

### 3. Outputs (Saidas)

A resposta entregue pelo backend contem todas as informacoes necessarias para a interface e para o fluxo de projeto:

- **Resposta Conversacional Fundamentada (`reply`)**:
  - Texto tecnico explicando o diagnostico da estrutura, os calculos efetuados e as justificativas das alteracoes recomendadas.
- **Tres Blocos de Sugestao Proativa (`suggestions`)**:
  - Tres mensagens prontas e contextuais que aparecem na interface do usuario para guiar o proximo passo da tomada de decisao sem bloqueio criativo (padrao Lembry).
- **Mutacoes de Estado da Interface (`ui_mutations`)**:
  - Lista de eventos para atualizacao reativa do frontend:
    - `version_created`: Notifica a criacao de uma nova versao com numero `vN+1`.
    - `version_switched`: Alterna o visualizador 3D para a versao recem-ativada.
    - `file_selected`: Atualiza o contexto do projeto caso um novo arquivo tenha sido ativado.
    - `style_changed`: Atualiza o renderizador de estilo visual (AutoCAD, Blender, Wireframe ou Landscape Insight).
    - `validation_completed`: Fornece os indicadores visuais de conformidade (passou/falhou, taxa de utilizacao e flecha relativa L/d).
- **Nova Versao Persistida no Banco (`FileVersion`)**:
  - Registro imutavel no banco de dados contendo o snapshot dos parametros fisicos, o codigo fonte gerado e o arquivo binario compilado.
- **Transmissao em Fluxo Continuo (SSE)**:
  - No endpoint de streaming (`/api/v1/chat/stream`), os outputs sao emitidos incrementalmente em eventos do tipo `ui_mutation`, `content` e `done`.

---

## Estrutura do Banco de Dados

O banco de dados relacional e vetorial esta estruturado em tres dominios principais:

1. **`project_files` e `file_versions`**:
   - `project_files`: Cadastro do arquivo raiz do projeto, formato original e metadados.
   - `file_versions`: Versoes incrementais (`v1, v2, ..., vn`) com historico de modificacoes, parametros fisicos e script executavel gerado.
2. **`knowledge_vectors` (`tabela_vet`)**:
   - Base vetorial com embeddings de 1536 dimensoes indexados com pgvector (indice HNSW/IVFFlat), armazenando normas ABNT, Eurocodes, dados geotécnicos e legislacao urbanistica municipal.
3. **Memoria EverMemOS (`memory_cells`, `memory_scenes`, `user_profiles`)**:
   - `memory_cells`: Fatos atomicos extraidos das interacoes com data de expiracao e nivel de confianca.
   - `memory_scenes`: Agrupamentos de contexto tematico com centroides vetoriais para recuperacao de memoria episódica.
   - `user_profiles`: Perfil compilado do profissional contendo suas preferencias de design e engenharia.

---

## Como Executar

### Ambiente Local com uv

```bash
uv sync
.venv/bin/uvicorn structura_ai.main:app --reload --port 8000
```

### Ambiente Conteinerizado com Docker Compose

```bash
docker compose up -d db
export DATABASE_URL="postgresql+asyncpg://structura_user:structura_secure_pass_2026@localhost:5432/structura_db"
export POSTGRES_URL="postgresql://structura_user:structura_secure_pass_2026@localhost:5432/structura_db"
.venv/bin/uvicorn structura_ai.main:app --reload --port 8000
```

---

## Suite de Testes Automatizados

A base conta com cobertura integral de testes unitarios, de integracao e de casos de borda:

```bash
# Executa toda a suite de testes (139 testes)
.venv/bin/pytest -v

# Executa testes rapidos de validacao de amostras CAD/BIM
./test.sh --samples

# Valida o manifesto de integridade de arquivos em pipeline de CI
./test.sh --check
```

Escopo dos testes implementados:
- **Testes Fisicos e Parametricos**: Validacao de flechas em vigas, flambagem e conformidade de secoes.
- **Testes de Parsers e Formatos**: Ingestao e extracao de geometrias em DXF, IFC4, OBJ, STL e Blender bpy.
- **Testes de Fluxo do Agente**: Cenarios completos de conversa, geracao de versoes v1 a vn, alternancia de arquivos e memoria EverMemOS.
- **Testes de Casos de Borda**: Arquivos corrompidos, parametros de entrada invalidos e garantia de degradacao graciosa sem falhas criticas.

---

## Endpoints Principais da API

Documentacao interativa disponivel via Swagger UI em `/docs`.

### Arquivos e Versionamento
- `POST /api/v1/files/upload`: Carregamento de arquivo (`multipart/form-data`) e criacao da versao inicial `v1`.
- `GET /api/v1/files?user_id=default_user`: Listagem de arquivos do usuario com indicacao do arquivo ativo e versoes disponiveis.
- `POST /api/v1/files/{file_id}/select`: Definicao do arquivo ativo para a sessao.
- `GET /api/v1/files/{file_id}/versions`: Historico completo de versoes do arquivo.
- `POST /api/v1/files/{file_id}/versions/{version_number}/activate`: Ativacao de uma versao especifica.
- `POST /api/v1/files/{file_id}/style`: Alteracao do estilo visual e registro de versao `vN+1`.
- `POST /api/v1/files/{file_id}/generate-code`: Geracao de codigo executavel no formato alvo e criacao de nova versao.

### Chat Copiloto e Sugestoes
- `POST /api/v1/chat/message`: Envio de mensagem sincrona com retorno do diagnostico, mutacoes de UI e tres sugestoes proativas.
- `POST /api/v1/chat/stream`: Conexao SSE para recepcao em fluxo continuo de eventos de interface e tokens de texto.
- `GET /api/v1/chat/memory?user_id=arquiteto_01`: Consulta a memoria e perfil acumulado do profissional.

### Base de Conhecimento e RAG
- `GET /api/v1/knowledge/search?q=balanco+eurocode&region_country=BR`: Busca hibrida por normas e parametros tecnicos.
- `POST /api/v1/knowledge/ingest`: Ingestao de novos documentos tecnicos na base vetorial.

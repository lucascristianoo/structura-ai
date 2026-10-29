# 🏛️ Structura.AI — HackTown 2026 Edition
### *O Intermediário Inteligente entre o Traço do Arquiteto e o Cálculo do Engenheiro Civil*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=flat&logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg?style=flat&logo=postgresql)](https://postgresql.org)
[![Google Gemini](https://img.shields.io/badge/Google%20AI-Gemini%202.5%20Flash-4285F4.svg?style=flat&logo=google)](https://aistudio.google.com)
[![Norma](https://img.shields.io/badge/Norma-ABNT%20NBR%206118%3A2023-emerald.svg?style=flat)]()
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🎯 A Dor Real da Construção Civil & Arquitetura
No desenvolvimento de qualquer projeto imobiliário ou residencial de alto padrão, existe um **abismo clássico de comunicação** entre duas mentes brilhantes:

1. **O Arquiteto** busca fluidez espacial, grandes vãos livres envidraçados, tetos delgados e balanços esculturais para maximizar a experiência humana e a estética.
2. **O Engenheiro Calculista** precisa garantir que o edifício obedeça às leis imutáveis da física e aos limites de serviço das normas técnicas (**ABNT NBR 6118**, **NBR 6120**, **ACI 318** e **Eurocode 2**), impedindo fissurações severas, flechas inaceitáveis e risco de flambagem.

Quando o calculista reprova o desenho original, a resposta comum é um atrito demorado: *"engrosse uma viga enorme no meio da sala"* ou *"adicione 3 pilares feios no meio do living"*. Isso destrói a intenção plástica do arquiteto.

### 💡 A Solução: Structura.AI
O **Structura.AI** atua como o **árbitro computacional em tempo real**. O arquiteto sobe sua planta baixa, croqui ou CAD:
- Se o projeto for **fisicamente aceitável**, recebe o **Selo Verde de Viabilidade Estrutural** e avança direto para o projeto executivo.
- Se o projeto **violar as leis da física**, o Structura.AI **não descarta o conceito**: ele gera imediatamente **5 propostas visuais alternativas de redesign estrutural** com renderização vetorial dinâmica (SVG interativo), memória de cálculo comparativa e narrativa de vendas para apresentar ao cliente final!

---

## 🚀 As 5 Propostas Visuais de Redesign Geradas

Quando uma flecha excessiva, vão crítico ou balanço desbalanceado é identificado, o motor sintetiza 5 caminhos de engenharia que viram assinaturas estéticas:

| # | Proposta Visual | Estratégia de Engenharia | Impacto Físico | Linguagem Arquitetônica |
|---|---|---|---|---|
| **01** | **Grelha Otimizada com Protensão Ativa** | Cordalhas engraxadas parabólicas embutidas (CP-190 RB) | Redução de até **72% na flecha ativa** via empuxo ascendente ($q_{bal}$) | Preserva o **teto plano contínuo**, espessura delgada sem nenhuma viga aparente. |
| **02** | **Exoesqueleto de Fachada & Viga Vierendeel** | Parede do andar superior como viga-parede rígida | Inércia multiplicada em **8x** ($I = \frac{b \cdot H^3}{12}$) | **Térreo 100% livre de pilares**. Efeito de levitação brutalista contemporânea. |
| **03** | **Balanço Atirantado com Pilares em V** | Tirantes de alta tração (ASTM A572) e pilares angulados a 65° | Converte flexão destrutiva em **tração axial pura** nos tirantes | Dinamismo de **ponte estaiada**. Balanço amplo transformado em escultura. |
| **04** | **Lajes Nervuradas Waffle com Capitéis** | Alívio por cubetas plásticas 80x80cm + capitéis maciços | **-38% de carga permanente** de concreto | **Teto rítmico aparente** com spots de iluminação zenital de LED embutidos. |
| **05** | **Geometria Catenária Funicular** | Curvatura funicular em arco suave (Gaudí / Eladio Dieste) | **Momento fletor $\approx 0$** (compressão axial pura) | Cobertura orgânica fluida, casca esbelta de 10cm cobrindo vão recorde. |

---

## 🛠️ Stack Tecnológica (Python Monolítico & Leve)

A aplicação foi desenhada sob uma **arquitetura monolítica moderna em Python**, ultra-otimizada para resposta instantânea (< 50ms) e sem dependência de build steps complexos de Node.js:

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) assíncrono de alto desempenho com Pydantic v2.
- **Banco de Dados:** [PostgreSQL 16](https://www.postgresql.org/) via SQLAlchemy 2.0 (asyncpg) com fallback automático para SQLite local (zero-setup em desenvolvimento).
- **Inteligência Artificial:** [Google Gemini 2.5 Flash](https://aistudio.google.com/) (Free Tier) Multimodal Vision para inspeção de plantas e desenhos conceituais.
- **Motor Físico Determinístico:** Algoritmos próprios baseados na **ABNT NBR 6118:2023** e **NBR 6120:2019** (momentos fletores, flechas diferidas por fluência do concreto $\alpha_f$, inércia fissurada de Branson e flambagem Euleriana $\lambda \le 140$).
- **Frontend Monolítico Craft UI:** HTML5 semântico, [Tailwind CSS](https://tailwindcss.com/) CDN, ícones [Lucide](https://lucide.dev/), Canvas 2D interativo e renderizadores SVG responsivos em tempo real.

---

## ⚡ Como Rodar o Projeto

Você pode rodar de duas formas simples:

### Opção A: 1-Click com Docker Compose (PostgreSQL 16 + FastAPI)
A forma recomendada para ambiente completo com PostgreSQL:

```bash
# Clone o repositório
git clone https://github.com/lucascristianoo/structura-ai.git
cd structura-ai

# Suba os containers
docker compose up --build
```
Acesse a aplicação em: **`http://localhost:8000`** ou no Studio: **`http://localhost:8000/analyzer`**.

---

### Opção B: Execução Local Rápida com Python (`uv` ou `pip`)
Graças ao fallback automático para SQLite integrado, você pode rodar em segundos sem precisar subir o Postgres:

```bash
# Clone o repositório
git clone https://github.com/lucascristianoo/structura-ai.git
cd structura-ai

# Crie o ambiente virtual e instale dependências
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Ou se preferir uv:
# uv sync

# Inicie o servidor
./run.sh
# ou:
# uvicorn structura_ai.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🔑 Configuração da API do Google Gemini (Opcional & Gratuita)

O sistema possui um **motor físico autônomo offline** que funciona 100% mesmo sem internet ou sem chave de API. Para habilitar a leitura visual multimodal com o Google Gemini 2.5 Flash:

1. Obtenha sua chave gratuita no [Google AI Studio](https://aistudio.google.com/).
2. Copie o arquivo `.env.example` para `.env`:
   ```bash
   cp .env.example .env
   ```
3. Insira sua chave:
   ```ini
   GEMINI_API_KEY=AIzaSy...
   ```

---

## 🧪 Testes Automatizados (Suite Pytest)

O projeto conta com testes unitários e de integração cobrindo o motor de cálculo físico, fórmulas da NBR 6118, gerador de variantes e endpoints REST da API:

```bash
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -v
```

Exemplo de resultado dos testes:
```text
tests/test_api_routes.py::test_health_endpoint PASSED                    [  7%]
tests/test_api_routes.py::test_quick_calc_endpoint PASSED                [ 15%]
tests/test_api_routes.py::test_preset_load_and_export PASSED             [ 23%]
tests/test_edge_cases.py::test_clamped_boundary_values PASSED            [ 30%]
tests/test_edge_cases.py::test_extreme_cantilever_failure PASSED         [ 38%]
tests/test_edge_cases.py::test_canvas_analysis_endpoint PASSED           [ 46%]
tests/test_edge_cases.py::test_multipart_upload_endpoint PASSED          [ 53%]
tests/test_physics_core.py::test_concrete_properties_calculation PASSED  [ 61%]
tests/test_physics_core.py::test_deflection_limits_nbr6118 PASSED        [ 69%]
tests/test_physics_core.py::test_excessive_span_failure PASSED           [ 76%]
tests/test_physics_core.py::test_compliant_structure_passes PASSED       [ 84%]
tests/test_physics_core.py::test_slender_column_buckling_detection PASSED [ 92%]
tests/test_redesign_generator.py::test_generates_exactly_5_variants PASSED [100%]

============================== 13 passed in 0.95s ==============================
```

---

## 📁 Estrutura do Repositório

```
structura-ai/
├── structura_ai/
│   ├── main.py                  # Ponto de entrada FastAPI Monolítico e rotas HTML
│   ├── config.py                # Configurações de ambiente e chaves Google AI
│   ├── database.py              # Sessão assíncrona SQLAlchemy (PostgreSQL / SQLite)
│   ├── models.py                # Modelos relacionais (Project, AnalysisResult, RedesignVariant)
│   ├── schemas.py               # Schemas Pydantic de validação e API
│   ├── physics/                 # Motor Físico Determinístico de Engenharia Civil
│   │   ├── structural_core.py   # Análise de flexão, cortante, flecha e flambagem
│   │   ├── nbr_standards.py     # Coeficientes e limites normativos NBR 6118:2023
│   │   ├── load_calculator.py   # Combinações de cargas permanentes e variáveis NBR 6120
│   │   └── generator.py         # Gerador matemático das 5 propostas de redesign e SVGs
│   ├── ai/                      # Integração com Google Gemini
│   │   ├── gemini_client.py     # Cliente multimodal Gemini 2.5 Flash Free Tier
│   │   ├── prompt_templates.py  # Prompts de síntese entre arquiteto e engenheiro
│   │   └── mock_engine.py       # Fallback local com análise detalhada em markdown
│   ├── services/
│   │   ├── analyzer_service.py  # Orquestrador do pipeline de análise e persistência
│   │   ├── report_generator.py  # Gerador de laudos executivos imprimíveis em HTML/PDF
│   │   └── sample_projects.py   # Presets pré-configurados para o HackTown
│   ├── api/                     # Rotas REST da aplicação
│   │   ├── routes_projects.py   # CRUD de projetos e upload de arquivos
│   │   ├── routes_analysis.py   # Cálculos em tempo real e extração de croqui
│   │   └── routes_export.py     # Exportação de relatórios e SVGs
│   ├── templates/               # Templates Jinja2 (Craft UI)
│   │   ├── base.html            # Layout mestre responsivo
│   │   ├── index.html           # Landing page e dashboard de projetos
│   │   ├── analyzer.html        # Studio Interativo (Sliders + Canvas + 5 Propostas)
│   │   └── project_view.html    # Laudo técnico completo e galeria executiva
│   └── static/                  # Arquivos estáticos (CSS e JS vanilla)
│       ├── css/custom.css       # Estilização blueprint e temas de alto contraste
│       └── js/
│           ├── app.js           # Gerenciador de estado e sincronização dos sliders
│           └── canvas_draw.js   # Canvas interativo para croquis arquitetônicos
├── tests/                       # Suite de testes automatizados com Pytest
│   ├── test_physics_core.py
│   ├── test_redesign_generator.py
│   ├── test_api_routes.py
│   └── test_edge_cases.py
├── docker-compose.yml           # Orquestração do PostgreSQL 16 + App FastAPI
├── Dockerfile                   # Imagem Docker leve Python 3.12-slim
├── requirements.txt             # Dependências Python travadas
├── pyproject.toml               # Metadados e configuração do pytest
├── run.sh                       # Script de inicialização facilitada
└── README.md                    # Este documento
```

---

## 🏆 Demonstração para Jurados do HackTown

Para demonstrar a solução em uma apresentação de 3 minutos:
1. Abra a aplicação no navegador em `http://localhost:8000/analyzer`.
2. Mostre o preset **"Residência Horizon — Vão Livre Panorâmico de 10m"**.
3. Aponte como a flecha calculada (**54.2mm**) estoura o limite normativo da NBR 6118 (**40.0mm**) devido à viga delgada de apenas 28cm.
4. Demonstre como a ferramenta não diz apenas "não é viável", mas imediatamente apresenta as **5 Alternativas Visuais de Redesign**:
   - Navegue pela aba **01 (Protensão Ativa)** com o teto plano intacto.
   - Mostre a aba **02 (Exoesqueleto Vierendeel)** com o térreo completamente sem pilares.
   - Mostre a aba **03 (Balanço Atirantado com Pilares em V)** resolvendo a estabilidade.
   - Mostre a aba **04 (Laje Waffle)** e aba **05 (Arco Funicular de Gaudí)**.
5. Clique em **"Laudo Imprimível (HTML/PDF)"** para exibir o dossiê formal pronto para assinatura entre o arquiteto e o engenheiro civil calculista!

---

## 👨‍💻 Autor & Licença
Desenvolvido por **Lucas Cristiano Soares Lino** ([@lucascristianoo](https://github.com/lucascristianoo)) para o **HackTown 2026**.  
Distribuído sob a licença MIT. Aberto para colaborações de arquitetos, calculistas e desenvolvedores.

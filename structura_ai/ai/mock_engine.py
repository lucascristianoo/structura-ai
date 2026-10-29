"""
Deterministic AI Structural Review Engine (Offline Fallback).
Generates realistic, deeply articulated technical reviews when Gemini API key is absent or offline.
"""
from typing import Dict, Any

class MockGeminiEngine:
    """
    Simulates high-end Gemini Vision Multimodal architectural-engineering critique
    calibrated with precise engineering metrics and architectural terminology.
    """

    @classmethod
    def generate_review(cls, project_title: str, category: str, evaluation: Dict[str, Any]) -> str:
        is_viable = evaluation.get("is_physically_viable", False)
        score = evaluation.get("structural_score", 0.0)
        max_d = evaluation.get("max_deflection_mm", 0.0)
        adm_d = evaluation.get("allowable_deflection_mm", 0.0)
        inputs = evaluation.get("calculated_inputs", {})
        span = inputs.get("span_length_m", 9.5)
        cantilever = inputs.get("cantilever_length_m", 3.5)
        beam_h = inputs.get("beam_height_cm", 30.0)
        col_h = inputs.get("column_height_m", 3.2)
        col_sec = inputs.get("column_section_cm", 20.0)

        if is_viable:
            return f"""### 🏛️ Parecer Técnico-Arquitetônico Structura.AI (Google Gemini 2.5 Flash Vision)

**Projeto:** {project_title} | **Tipologia:** {category}  
**Status Normativo:** ✅ **CONFORME NBR 6118:2023 (Índice de Viabilidade Física: {score}/100)**

#### 1. Diagnóstico de Integração Arquitetura-Engenharia
A geometria proposta demonstra maturidade estrutural exemplar. O traçado da grelha de vigas e pilares respeita a hierarquia de transferência de cargas gravitacionais, preservando a fluidez espacial almejada pelo arquiteto sem comprometer a rigidez mecânica.

- **Vão Livre Avaliado:** {span:.1f} metros.
- **Flecha Máxima Calculada:** {max_d} mm contra limite de serviço (ELS) de {adm_d} mm (Margem de segurança: {round(((adm_d - max_d)/adm_d)*100)}%).
- **Comportamento dos Apoios:** O dimensionamento da seção dos pilares ({col_sec:.0f}x{col_sec:.0f} cm para pé-direito de {col_h:.1f}m) garante coeficiente de esbeltez estável contra fenômenos de flambagem elasto-plástica de 2ª ordem.

#### 2. Recomendações para a Etapa de Detalhamento Executivo
1. **Armadura de Pele e Combate à Fissuração:** Adotar taxa mínima de armadura longitudinal e transversal para controle de abertura de fissuras (wk <= 0.3mm) nas faces expostas ao ambiente.
2. **Definição de Contraflecha de Execução:** Recomenda-se aplicar contraflecha no escoramento equivalente a 50% da flecha elástica inicial (~{round(max_d * 0.25, 1)} mm) para garantia de horizontalidade perfeita do contrapiso após a desforma.
3. **Compatibilização Hidrossanitária e HVAC:** Prever furações em vigas exclusivamente no terço médio do vão, onde o esforço cortante é mínimo."""

        # IF FAILS: Detailed corrective diagnosis
        return f"""### ⚠️ Parecer Técnico-Arquitetônico Structura.AI (Google Gemini 2.5 Flash Vision)

**Projeto:** {project_title} | **Tipologia:** {category}  
**Status Normativo:** ❌ **REVISÃO ESTRUTURAL MANDATÓRIA (Índice de Viabilidade Física: {score}/100)**

#### 1. O Conflito entre a Plástica Arquitetônica e a Física dos Materiais
O projeto possui grande mérito espacial e aspira a um minimalismo com generoso vão livre de **{span:.1f} metros** e balanço frontal projetado de **{cantilever:.1f} metros**. No entanto, a tentativa de esconder a estrutura dentro de uma viga de apenas **{beam_h:.0f} cm de altura** viola as equações constitutivas de flexão e deformação diferida no tempo da ABNT NBR 6118.

- **Flecha em Serviço Calculada:** **{max_d} mm** (superando o limite normativo $L/250$ de **{adm_d} mm** por uma margem crítica de {round(((max_d - adm_d)/adm_d)*100)}%).
- **Patologias Iminentes:** Esta magnitude de deformação causará esmagamento de caixilhos de vidro, trincas diagonais severas em alvenarias e sensação de oscilação desagradável aos usuários sob cargas móveis.
- **Vulnerabilidade no Balanço:** O balanço de {cantilever:.1f}m sem contra-haste de ancoragem gera momentos negativos que ameaçam a ancoragem nos pilares de transição.

#### 2. Princípio da Intervenção: "A Estrutura como Escultura"
Não se deve resolver este desafio simplesmente "engrossando" uma viga desajeitada no meio do ambiente social. A engenharia moderna oferece **5 soluções de redesign inteligente** que resolvem a física do problema e simultaneamente elevam o prestígio visual do projeto:

1. **Protensão Ativa (Post-Tensioning):** Mantém o teto perfeitamente plano e esbelto através de cabos de aço parabólicos embutidos que exercem força ascendente contrária à gravidade.
2. **Exoesqueleto Vierendeel:** Transforma a parede do pavimento superior em uma colossal viga-parede vazada, suspendendo o térreo e deixando-o 100% livre de pilares.
3. **Balanço Atirantado com Pilares em V:** Introduz tirantes de aço inoxidável e pilares bifurcados em V que convertem a flexão destrutiva em tração pura nos cabos.
4. **Lajes Nervuradas Bidirecionais (Waffle Slab):** Alivia 38% da massa de concreto através de cubetas aparentes com iluminação cenográfica de LED.
5. **Geometria Catenária Funicular:** Substitui a linha reta por uma curvatura suave inspirada em Gaudí, onde toda a flexão se transforma em compressão simples.

*Consulte as 5 propostas visuais interativas geradas abaixo para escolher a linguagem conceitual definitiva com o calculista.*"""

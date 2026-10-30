"""
Pre-configured Architectural Sample Projects for Benchmark Testing & Live Demos.
Explicitly separated into two canonical benchmark scenarios:
  - Scenario 1: Requer Ajustes Matemáticos (Overstressed / Failing NBR 6118 limits)
  - Scenario 2: NÃO Requer Ajustes (100% Compliant NBR 6118 / Physical Benchmark)
"""
from typing import Dict, Any, List

SAMPLE_PRESETS: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # CENÁRIO 1: PROJETOS QUE PRECISAM DE AJUSTES MATEMÁTICOS (REPROVADOS NBR 6118)
    # =========================================================================
    "residencia_vao_livre_critico": {
        "title": "Residência Horizon — Vão Livre Panorâmico de 10m",
        "author_architect": "Studio Horizon Arq & Design",
        "category": "Residencial",
        "scenario": 1,
        "scenario_label": "Cenário 1: Requer Ajustes Matemáticos",
        "description": "Conceito minimalista com living integrado sem pilares internos e balanço frontal de 3.8m. A viga de apenas 28cm de altura sofre flecha excessiva de 48mm (limite NBR 6118: 40mm).",
        "span_length_m": 10.0,
        "cantilever_length_m": 3.8,
        "beam_height_cm": 28.0,
        "beam_width_cm": 20.0,
        "column_height_m": 3.2,
        "column_section_cm": 20.0,
        "dead_load_kpa": 4.5,
        "live_load_kpa": 2.5,
        "concrete_fck_mpa": 30.0,
        "expected_result": "FAIL (Flecha crítica e balanço excessivo)",
        "needs_adjustment": True,
        "primary_issue": "Deformação elástica e fluência em serviço (ELS)"
    },
    "balanco_corporativo_extremo": {
        "title": "Sede Corporativa Nexus — Varanda em Balanço de 4.8m",
        "author_architect": "Nexus Corporate Atelier",
        "category": "Comercial",
        "scenario": 1,
        "scenario_label": "Cenário 1: Requer Ajustes Matemáticos",
        "description": "Edifício corporativo com salas suspensas em balanço de quase 5 metros sem apoio visível. O momento de engaste e a rotação causam risco de fissuração plástica.",
        "span_length_m": 8.0,
        "cantilever_length_m": 4.8,
        "beam_height_cm": 35.0,
        "beam_width_cm": 25.0,
        "column_height_m": 3.5,
        "column_section_cm": 25.0,
        "dead_load_kpa": 5.0,
        "live_load_kpa": 3.0,
        "concrete_fck_mpa": 35.0,
        "expected_result": "FAIL (Instabilidade de balanço e momento de engaste)",
        "needs_adjustment": True,
        "primary_issue": "Instabilidade de balanço e vibração excessiva"
    },
    "pe_direito_duplo_flambagem": {
        "title": "Galeria de Arte Lumina — Pé-Direito Duplo com Pilar Esbelto",
        "author_architect": "Lumina Spazio",
        "category": "Institucional",
        "scenario": 1,
        "scenario_label": "Cenário 1: Requer Ajustes Matemáticos",
        "description": "Salão de exposições com pé-direito duplo de 5.2m. O arquiteto optou por pilares super delgados de 18x18cm para transparência total da fachada, gerando esbeltez lambda de 100.",
        "span_length_m": 8.5,
        "cantilever_length_m": 1.2,
        "beam_height_cm": 45.0,
        "beam_width_cm": 20.0,
        "column_height_m": 5.2,
        "column_section_cm": 18.0,
        "dead_load_kpa": 4.0,
        "live_load_kpa": 4.0,
        "concrete_fck_mpa": 30.0,
        "expected_result": "FAIL (Flambagem Euleriana crítica no pilar)",
        "needs_adjustment": True,
        "primary_issue": "Flambagem por flexo-compressão em pilar esbelto"
    },

    # =========================================================================
    # CENÁRIO 2: PROJETOS QUE NÃO PRECISAM DE AJUSTES (BENCHMARKS CONFORMES NBR 6118)
    # =========================================================================
    "sobrado_grid_racional": {
        "title": "Residência Racional NBR — Grelha Modular 5.0m",
        "author_architect": "Studio Modular Arquitetura",
        "category": "Residencial",
        "scenario": 2,
        "scenario_label": "Cenário 2: Totalmente Conforme (Não Requer Redesign)",
        "description": "Residência contemporânea com malha estrutural racional de 5.0m x 5.0m, vigas de 20x45cm (L/11) e pilares 20x30cm. Flecha total de 8.2mm contra limite normativo de 20.0mm (folga de 59%).",
        "span_length_m": 5.0,
        "cantilever_length_m": 0.0,
        "beam_height_cm": 45.0,
        "beam_width_cm": 20.0,
        "column_height_m": 3.0,
        "column_section_cm": 25.0,
        "dead_load_kpa": 4.0,
        "live_load_kpa": 2.0,
        "concrete_fck_mpa": 30.0,
        "expected_result": "PASS (Conforme NBR 6118 com 59% de folga)",
        "needs_adjustment": False,
        "primary_issue": "Nenhum — Estrutura 100% aprovada para detalhamento executivo"
    },
    "pavilhao_otimizado_aprovado": {
        "title": "Pavilhão Fênix — Estrutura Racional Aprovada",
        "author_architect": "Atelier Racional",
        "category": "Cultural",
        "scenario": 2,
        "scenario_label": "Cenário 2: Totalmente Conforme (Não Requer Redesign)",
        "description": "Projeto cultural com modulação calculada de 6.5m, viga com inércia compatível de 50cm e pilares robustos. Cumpre rigorosamente todas as prescrições de serviço ELS e ELU.",
        "span_length_m": 6.5,
        "cantilever_length_m": 1.2,
        "beam_height_cm": 50.0,
        "beam_width_cm": 25.0,
        "column_height_m": 3.0,
        "column_section_cm": 25.0,
        "dead_load_kpa": 4.0,
        "live_load_kpa": 2.0,
        "concrete_fck_mpa": 35.0,
        "expected_result": "PASS (Total conformidade NBR 6118)",
        "needs_adjustment": False,
        "primary_issue": "Nenhum — Estrutura em equilíbrio ideal"
    },
    "edificio_modulado_comercial": {
        "title": "Edifício Comercial Alpha — Pórticos 6.0m",
        "author_architect": "Alpha Corporate Design",
        "category": "Comercial",
        "scenario": 2,
        "scenario_label": "Cenário 2: Totalmente Conforme (Não Requer Redesign)",
        "description": "Laje corporativa modulada em vãos de 6.0m com vigas de 25x50cm e pilares 25x30cm. Flecha calculada de 11.2mm confortavelmente abaixo dos 24.0mm admissíveis pela NBR 6118.",
        "span_length_m": 6.0,
        "cantilever_length_m": 0.0,
        "beam_height_cm": 50.0,
        "beam_width_cm": 25.0,
        "column_height_m": 3.2,
        "column_section_cm": 25.0,
        "dead_load_kpa": 4.5,
        "live_load_kpa": 3.0,
        "concrete_fck_mpa": 35.0,
        "expected_result": "PASS (Conforme NBR 6118/NBR 6120)",
        "needs_adjustment": False,
        "primary_issue": "Nenhum — Relação rigidez/esforço ótima"
    }
}

def get_preset_list() -> List[Dict[str, Any]]:
    return [
        {"key": k, **v} for k, v in SAMPLE_PRESETS.items()
    ]

def get_presets_by_scenario(scenario_number: int) -> List[Dict[str, Any]]:
    return [
        {"key": k, **v} for k, v in SAMPLE_PRESETS.items() if v.get("scenario") == scenario_number
    ]

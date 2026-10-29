"""
Pre-configured Architectural Sample Projects for HackTown Live Demonstrations.
Includes both structurally failing concepts (triggering 5 visual redesigns)
and structurally compliant benchmarks.
"""
from typing import Dict, Any, List

SAMPLE_PRESETS: Dict[str, Dict[str, Any]] = {
    "residencia_vao_livre_critico": {
        "title": "Residência Horizon — Vão Livre Panorâmico de 10m",
        "author_architect": "Studio Horizon Arq & Design",
        "category": "Residencial",
        "description": "Conceito minimalista com living integrado sem pilares internos e balanço frontal projetado para a serra. O arquiteto previu uma viga plana rebaixada de apenas 28cm.",
        "span_length_m": 10.0,
        "cantilever_length_m": 3.8,
        "beam_height_cm": 28.0,
        "beam_width_cm": 20.0,
        "column_height_m": 3.2,
        "column_section_cm": 20.0,
        "dead_load_kpa": 4.5,
        "live_load_kpa": 2.5,
        "concrete_fck_mpa": 30.0,
        "expected_result": "FAIL (Flecha crítica e balanço excessivo)"
    },
    "balanco_corporativo_extremo": {
        "title": "Sede Corporativa Nexus — Varanda em Balanço de 4.8m",
        "author_architect": "Nexus Corporate Atelier",
        "category": "Comercial",
        "description": "Edifício corporativo com marquise e salas de reunião suspensas em balanço de quase 5 metros sem apoio visível, gerando preocupação de vibração.",
        "span_length_m": 8.0,
        "cantilever_length_m": 4.8,
        "beam_height_cm": 35.0,
        "beam_width_cm": 25.0,
        "column_height_m": 3.5,
        "column_section_cm": 25.0,
        "dead_load_kpa": 5.0,
        "live_load_kpa": 3.0,
        "concrete_fck_mpa": 35.0,
        "expected_result": "FAIL (Instabilidade de balanço e momento de engaste)"
    },
    "pe_direito_duplo_flambagem": {
        "title": "Galeria de Arte Lumina — Pé-Direito Duplo com Pilar Esbelto",
        "author_architect": "Lumina Spazio",
        "category": "Institucional",
        "description": "Salão de exposições com pé-direito duplo de 5.2m. O arquiteto optou por pilares super delgados de 18x18cm para maximizar a transparência da fachada de vidro.",
        "span_length_m": 8.5,
        "cantilever_length_m": 1.2,
        "beam_height_cm": 45.0,
        "beam_width_cm": 20.0,
        "column_height_m": 5.2,
        "column_section_cm": 18.0,
        "dead_load_kpa": 4.0,
        "live_load_kpa": 4.0,
        "concrete_fck_mpa": 30.0,
        "expected_result": "FAIL (Flambagem Euleriana crítica no pilar)"
    },
    "pavilhao_otimizado_aprovado": {
        "title": "Pavilhão Fênix — Estrutura Racional Aprovada",
        "author_architect": "Atelier Racional",
        "category": "Cultural",
        "description": "Projeto com modulação calculada de 6.5m, viga com inércia compatível de 50cm e pilares robustos. Cumpre rigorosamente todas as prescrições de serviço.",
        "span_length_m": 6.5,
        "cantilever_length_m": 1.2,
        "beam_height_cm": 50.0,
        "beam_width_cm": 25.0,
        "column_height_m": 3.0,
        "column_section_cm": 25.0,
        "dead_load_kpa": 4.0,
        "live_load_kpa": 2.0,
        "concrete_fck_mpa": 35.0,
        "expected_result": "PASS (Total conformidade NBR 6118)"
    }
}

def get_preset_list() -> List[Dict[str, Any]]:
    return [
        {"key": k, **v} for k, v in SAMPLE_PRESETS.items()
    ]

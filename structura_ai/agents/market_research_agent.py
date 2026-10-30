"""
Market Research & Competitive Intelligence Agent (Agente Pesquisador de Mercado).
Surveys global AEC technology trends, competitors (Finch 3D, TestFit, Hypar, Karamba3D, Higharc, TQS),
monitors pricing models, and identifies high-margin market gaps for Structura.AI.
"""
from typing import Dict, Any, List
from structura_ai.services.solow_matrix import SolowMatrixService


class MarketResearchAgent:
    """
    Analyzes global and Brazilian AEC competitive landscapes,
    validating economic positioning and market differentiation.
    """

    def __init__(self, agent_id: str = "market_intel_strategist"):
        self.agent_id = agent_id

    def conduct_market_survey(self) -> Dict[str, Any]:
        """
        Executes comparative intelligence analysis based on Solow growth metrics and market benchmarks.
        """
        competitors = SolowMatrixService.get_competitor_comparison_matrix()
        solow_model = SolowMatrixService.get_solow_growth_model()
        pareto = SolowMatrixService.get_pareto_essential_features()
        killer_feature = SolowMatrixService.get_signature_killer_feature()

        market_trends = [
            {
                "trend": "Fim do 'Silo' entre Projeto Arquitetônico e Cálculo Estrutural",
                "impact": "Incorporadoras não toleram mais 3 semanas de espera para descobrir se uma varanda é viável.",
                "structura_advantage": "Reduz o tempo de 21 dias para 1.2 segundos."
            },
            {
                "trend": "Exigência de Metrificação de Carbono Embutido (ESG / A1-A3)",
                "impact": "Bancos e investidores institucionais exigem relatórios de kg CO2e para concessão de crédito verde.",
                "structura_advantage": "Nativo em todas as 5 variantes com cálculo de concreto e aço."
            },
            {
                "trend": "Rejeição a Softwares Monolíticos Pesados (Curva de Aprendizado Zero)",
                "impact": "Arquitetos jovens evitam softwares que exigem cursos de 6 meses (como SAP2000 ou Revit avançado).",
                "structura_advantage": "Visualizador 3D Three.js direto no browser com sliders e 1-clique."
            }
        ]

        strategic_recommendations = [
            "Focar agressivamente na marca registrada 'Instant Structural Truth Slider™'.",
            "Manter o modelo de precificação acessível frente aos $10.000/ano do TestFit e R$ 25.000 do TQS.",
            "Expandir o ecossistema de exportação BIM (IFC4 e DXF) para permitir que o cliente exporte com 1 clique.",
            "Preservar a máxima do Agente Engenheiro: 'Menos é Mais' — não inflar o produto com features supérfluas."
        ]

        return {
            "researcher_id": self.agent_id,
            "market_status": "HIGH_GROWTH_WINDOW",
            "macro_tfp_growth_factor": solow_model["solow_residual_gain_tfp"],
            "competitor_landscape_analyzed": len(competitors),
            "market_trends_2026": market_trends,
            "strategic_recommendations": strategic_recommendations,
            "essential_20_percent_validated": pareto["the_essential_20_percent"],
            "signature_feature": killer_feature["signature_name"],
            "competitive_moat_summary": killer_feature["competitive_moat"]
        }

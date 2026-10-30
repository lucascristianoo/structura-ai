"""
Engineer Curator Agent (Agente Engenheiro).
Motto: "Menos é Mais" (Less is More).
Persona: Senior structural engineering curator and minimalist architect.
Evaluates complaints and feature requests from the User Agent, prunes bloated fluff,
calibrates safety margins and structural formulas, and decides what to keep, discard, or refine.
"""
from typing import Dict, Any, List


class EngineerCuratorAgent:
    """
    Curates the feature set and calibrates the physical engine.
    Filters out noise, prevents software bloat, and optimizes the essential 20%.
    """

    def __init__(self, agent_id: str = "minimalist_engineer_lead"):
        self.agent_id = agent_id
        self.motto = "Menos é mais — simplicidade estrutural e foco no valor essencial (20/60)"
        self.decisions_log: List[Dict[str, Any]] = []

    def review_user_agent_feedback(self, user_agent_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes complaints and requests from the User Agent,
        issuing verdicts: KEEP (Manter), PRUNE (Descartar/Podar), or REFINE (Calibrar).
        """
        complaints = user_agent_report.get("complaints", [])
        benchmarks = user_agent_report.get("benchmarks", [])

        kept_count = 0
        pruned_count = 0
        refined_count = 0

        for comp in complaints:
            target = comp.get("target_feature", "")
            req = comp.get("feature_requested", "")
            text = comp.get("complaint", "")
            cat = comp.get("category", "")

            # Decision Logic per "Menos é Mais" philosophy:
            if "UF" in req or "BDI regional" in req:
                # User asked for 27 state selectors. PRUNE: adds dropdown bloat without changing physical truth.
                decision = "PRUNE (Descartar)"
                rationale = (
                    "Rejeitado: Adicionar 27 seletores de estados (UFs) e matrizes de frete polui a interface "
                    "e desvia o software de seu propósito (física estrutural e compatibilização rápida). "
                    "Mantemos o multiplicador de BDI nacional unificado de 1.35x."
                )
                pruned_count += 1

            elif "treliça metálica" in req or "vãos > 16m" in req:
                # User asked for proactive alert for extreme spans. KEEP & REFINE: improves safety.
                decision = "KEEP & REFINE (Aprovar com Calibração)"
                rationale = (
                    "Aprovado: Para vãos extremos (>16m), o sistema deve sugerir imediatamente a Variante 5 "
                    "(Casca Funicular ou Treliça Metálica), evitando que o arquiteto tente resolver com viga de concreto plano."
                )
                refined_count += 1

            elif "protensão ativa diretamente" in req:
                # User wants to apply post-tensioning without CAD rework. KEEP: Core 20% killer feature!
                decision = "KEEP (Pilar Estratégico)"
                rationale = (
                    "Aprovado: É exatamente o cerne da Variante 1. Os cabos parabólicos engraxados anulam a flecha "
                    "mantendo a viga esbelta. Essa é a essência da nossa proposta de valor."
                )
                kept_count += 1

            elif "diagrama de momento fletor (DMF)" in req:
                # User wants visual DMF. KEEP: Educational and builds trust with engineers.
                decision = "KEEP (Melhoria Visual Didática)"
                rationale = (
                    "Aprovado: O solver DSM já calcula os momentos fletores nodais e no meio do vão. "
                    "Exibir a curva de flexão graficamente no modal técnico reforça a autoridade da física."
                )
                kept_count += 1

            elif "taxa de estribos por metro linear" in req:
                # User asked for detailed stirrups on compliant projects. REFINE: Provide summary without complex tables.
                decision = "REFINE (Resumo Sintético)"
                rationale = (
                    "Calibrado: Não devemos poluir com detalhamento executivo de prancha de armação (que pertence ao TQS/Eberick), "
                    "mas sim incluir uma linha sintética: 'Taxa média de armadura: 85 kg/m³ | Estribos estimados: 1 estribo a cada 15cm'."
                )
                refined_count += 1

            else:
                decision = "KEEP (Manter Monitorado)"
                rationale = f"Aprovado sob monitoramento: {req}"
                kept_count += 1

            self.decisions_log.append({
                "target_feature": target,
                "complaint": text,
                "feature_requested": req,
                "verdict": decision,
                "engineering_rationale": rationale
            })

        # Evaluate benchmark consistency
        s1_passed_unexpectedly = [b for b in benchmarks if b.get("scenario") == 1 and b.get("is_viable")]
        s2_failed_unexpectedly = [b for b in benchmarks if b.get("scenario") == 2 and not b.get("is_viable")]

        calibration_status = "STABLE & ACCURATE"
        if s1_passed_unexpectedly or s2_failed_unexpectedly:
            calibration_status = "REQUIRES_FORMULA_TUNING"

        return {
            "engineer_id": self.agent_id,
            "motto": self.motto,
            "calibration_status": calibration_status,
            "statistics": {
                "total_complaints_reviewed": len(complaints),
                "features_kept": kept_count,
                "features_pruned": pruned_count,
                "features_refined": refined_count,
                "minimalism_pruning_ratio_pct": round((pruned_count / max(len(complaints), 1)) * 100, 1)
            },
            "curator_decisions": self.decisions_log,
            "engineering_verdict": (
                "A plataforma opera com fidelidade à ABNT NBR 6118:2023. As tentativas do User Agent de introduzir "
                "complexidade desnecessária (como dezenas de tabelas de frete ou de armação individual) foram podadas "
                "para preservar a latência sub-segundo e a curva de aprendizado zero que definem o produto."
            )
        }

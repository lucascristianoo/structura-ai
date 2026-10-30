#!/usr/bin/env python3
"""
CLI Runner for Structura.AI Autonomous Agent Council.
Orchestrates User Adversarial Agent, Engineer Curator Agent, and Market Research Agent.
Saves audit findings to docs/AGENT_COUNCIL_AUDIT.md.
"""
import sys
from pathlib import Path

# Add project root to path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from structura_ai.agents.agent_council import AgentCouncilOrchestrator


def main():
    print("=" * 75)
    print("  🏛️ STRUCTURA.AI — CONSELHO DE AGENTES AUTÔNOMOS")
    print("  Adversarial Testing, 'Menos é Mais' Curation & Solow Productivity")
    print("=" * 75)

    print("\n[1/3] 🕵️  Executando Agente User (Arquiteto Adversarial & IP Cloner)...")
    council_result = AgentCouncilOrchestrator.run_council_session()

    user_rep = council_result["user_adversarial_report"]
    print(f"       ✅ Concluído em {user_rep['execution_time_ms']} ms")
    print(f"       📊 Benchmarks testados: {user_rep['total_benchmarks_evaluated']}")
    print(f"       ⚠️  Queixas registradas: {user_rep['total_complaints_filed']}")

    print("\n[2/3] 📐 Executando Agente Engenheiro (Lema: 'Menos é Mais')...")
    eng_rep = council_result["engineer_curator_report"]
    stats = eng_rep["statistics"]
    print(f"       ✅ Status de Calibração: {eng_rep['calibration_status']}")
    print(f"       ✂️  Funcionalidades mantidas: {stats['features_kept']}")
    print(f"       🗑️  Complexidade podada (bloat descartado): {stats['features_pruned']}")
    print(f"       🎯 Calibrações refinadas: {stats['features_refined']}")

    print("\n[3/3] 📈 Executando Agente de Mercado & Análise Solow...")
    mkt_rep = council_result["market_research_report"]
    print(f"       ⭐ Feature Matadora: {mkt_rep['signature_feature']}")

    # Save Markdown Dossier
    output_path = root_dir / "AGENT_COUNCIL_AUDIT.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(council_result["markdown_dossier"])

    print("\n" + "=" * 75)
    print(f"  🎉 Sessão do Conselho concluída com sucesso!")
    print(f"  📄 Relatório completo salvo em: {output_path}")
    print("=" * 75)


if __name__ == "__main__":
    main()

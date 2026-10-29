"""
Structural Audit Report Generator for Structura.AI.
Exports professional civil engineering & architectural compliance dossier.
"""
from typing import Dict, Any

class ReportGenerator:
    """Generates standalone printable HTML compliance dossier."""

    @classmethod
    def generate_html_dossier(
        cls,
        project_title: str,
        author: str,
        category: str,
        analysis_data: Dict[str, Any],
        variants: list,
        project_image_url: str = None
    ) -> str:
        score = analysis_data.get("structural_score", 0.0)
        is_viable = analysis_data.get("is_physically_viable", False)
        status_color = "#10b981" if is_viable else "#ef4444"
        status_text = "APROVADO PARA ENGENHARIA DE DETALHAMENTO" if is_viable else "REVISÃO ESTRUTURAL MANDATÓRIA (PROPOSTAS GERADAS)"
        ai_model = analysis_data.get("ai_model_used", "Google Gemini")
        
        failures_html = ""
        for f in analysis_data.get("failure_reasons", []):
            failures_html += f"<li style='color:#ef4444; margin-bottom:8px;'>⚠️ {f}</li>"
        if not failures_html:
            failures_html = "<li style='color:#10b981;'>Nenhuma não-conformidade identificada segundo NBR 6118:2023.</li>"

        original_drawing_html = ""
        if project_image_url:
            original_drawing_html = f"""
            <div style="background:#0f172a; border:1px solid #1e293b; border-radius:8px; padding:16px; margin-bottom:30px; text-align:center;">
                <h4 style="color:#94a3b8; font-size:12px; text-transform:uppercase; margin-top:0; margin-bottom:10px;">Desenho Original Submetido pelo Arquiteto</h4>
                <img src="{project_image_url}" alt="Desenho Original" style="max-height:360px; max-width:100%; border-radius:6px; border:1px solid #334155;" />
            </div>
            """

        variants_html = ""
        for v in variants:
            metrics = v.get("metrics_delta", {})
            svg_block = f"<div style='margin:14px 0; border:1px solid #1e293b; border-radius:6px; overflow:hidden;'>{v.get('svg_render')}</div>" if v.get("svg_render") else ""
            variants_html += f"""
            <div style="border:1px solid #334155; border-radius:8px; padding:16px; margin-bottom:24px; background:#0f172a; color:#f8fafc;">
                <h3 style="color:#38bdf8; margin-top:0;">Proposta {v.get('variant_number')}: {v.get('title')}</h3>
                <p><strong>Estratégia:</strong> {v.get('strategy_name')}</p>
                <p><strong>Conceito Arquitetônico:</strong> {v.get('architectural_concept')}</p>
                <p><strong>Solução de Engenharia:</strong> {v.get('engineering_solution')}</p>
                {svg_block}
                <div style="background:#1e293b; padding:10px; border-radius:6px; font-family:monospace; font-size:13px;">
                    Redução de Flecha: {metrics.get('deflection_reduction_pct')}% | Flecha Final: {metrics.get('deflection_final_mm')}mm | Fator de Segurança: {metrics.get('safety_factor')}
                </div>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Laudo de Viabilidade Estrutural — {project_title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #020617; color: #e2e8f0; margin: 40px; }}
        .header {{ border-bottom: 2px solid #334155; padding-bottom: 20px; margin-bottom: 30px; }}
        .badge {{ display: inline-block; padding: 6px 14px; border-radius: 9999px; font-weight: bold; background: {status_color}; color: white; }}
        .metric-box {{ display: inline-block; width: 22%; background: #0f172a; border: 1px solid #1e293b; padding: 14px; border-radius: 8px; margin-right: 2%; box-sizing: border-box; }}
        .metric-val {{ font-size: 24px; font-weight: bold; color: #38bdf8; }}
        .metric-lbl {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; }}
    </style>
</head>
<body>
    <div class="header">
        <span class="badge">{status_text}</span>
        <h1 style="margin: 15px 0 5px 0;">STRUCTURA.AI — Laudo de Compatibilização Físico-Arquitetônica</h1>
        <p style="color: #94a3b8; margin: 0;">Projeto: <strong>{project_title}</strong> | Autor: <strong>{author}</strong> | Tipologia: <strong>{category}</strong> | Norma: <strong>ABNT NBR 6118 / NBR 6120</strong></p>
    </div>

    <div style="margin-bottom: 30px;">
        <div class="metric-box">
            <div class="metric-val">{score}/100</div>
            <div class="metric-lbl">Índice de Viabilidade</div>
        </div>
        <div class="metric-box">
            <div class="metric-val">{analysis_data.get('max_deflection_mm')} mm</div>
            <div class="metric-lbl">Flecha Calculada (ELS)</div>
        </div>
        <div class="metric-box">
            <div class="metric-val">{analysis_data.get('allowable_deflection_mm')} mm</div>
            <div class="metric-lbl">Limite Normativo L/250</div>
        </div>
        <div class="metric-box">
            <div class="metric-val">{analysis_data.get('max_bending_moment_knm')} kN.m</div>
            <div class="metric-lbl">Momento Máximo Fletor</div>
        </div>
    </div>

    {original_drawing_html}

    <h2>1. Diagnóstico Estrutural & Patologias Físicas</h2>
    <div style="background:#0f172a; border:1px solid #1e293b; border-radius:8px; padding:20px; margin-bottom:30px;">
        <p>{analysis_data.get('structural_diagnosis_text')}</p>
        <h4>Pontos Críticos Registrados:</h4>
        <ul>{failures_html}</ul>
    </div>

    <h2>2. Parecer da Inteligência Artificial ({ai_model})</h2>
    <div style="background:#0f172a; border:1px solid #1e293b; border-radius:8px; padding:20px; margin-bottom:30px; white-space: pre-wrap;">
{analysis_data.get('ai_gemini_review', 'Não disponível')}
    </div>

    <h2>3. As 5 Propostas de Redesign Visual & Matemático</h2>
    <div>
        {variants_html}
    </div>

    <div style="border-top:1px solid #334155; padding-top:20px; margin-top:40px; color:#64748b; font-size:12px; text-align:center;">
        Structura.AI Monolith • Engenharia Estrutural e Arquitetura Computacional • HackTown 2026
    </div>
</body>
</html>"""

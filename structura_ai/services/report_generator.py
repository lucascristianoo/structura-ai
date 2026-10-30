"""
Structural Audit Report Generator for Structura.AI.
Exports professional civil engineering & architectural compliance dossier.
"""
import html
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
        safe_title = html.escape(str(project_title or ""))
        safe_author = html.escape(str(author or ""))
        safe_category = html.escape(str(category or ""))

        score = analysis_data.get("structural_score", 0.0)
        is_viable = analysis_data.get("is_physically_viable", False)
        status_color = "#10b981" if is_viable else "#ef4444"
        status_text = (
            "APROVADO PARA ENGENHARIA DE DETALHAMENTO"
            if is_viable
            else "REVISÃO ESTRUTURAL MANDATÓRIA (PROPOSTAS GERADAS)"
        )
        safe_ai_model = html.escape(str(analysis_data.get("ai_model_used") or "Google Gemini"))
        safe_diagnosis = html.escape(str(analysis_data.get("structural_diagnosis_text") or ""))
        safe_ai_review = html.escape(str(analysis_data.get("ai_gemini_review") or "Não disponível"))

        failures_html = ""
        for f in analysis_data.get("failure_reasons", []):
            failures_html += f"<li style='color:#ef4444; margin-bottom:8px;'>⚠️ {html.escape(str(f))}</li>"
        if not failures_html:
            failures_html = "<li style='color:#10b981;'>Nenhuma não-conformidade identificada segundo NBR 6118:2023.</li>"

        original_drawing_html = ""
        if project_image_url:
            safe_img_url = html.escape(str(project_image_url), quote=True)
            original_drawing_html = f"""
            <div style="background:#0f172a; border:1px solid #1e293b; border-radius:8px; padding:16px; margin-bottom:30px; text-align:center;">
                <h4 style="color:#94a3b8; font-size:12px; text-transform:uppercase; margin-top:0; margin-bottom:10px;">Desenho Original Submetido pelo Arquiteto</h4>
                <img src="{safe_img_url}" alt="Desenho Original" style="max-height:360px; max-width:100%; border-radius:6px; border:1px solid #334155;" />
            </div>
            """

        variants_html = ""
        for v in variants:
            metrics = v.get("metrics_delta", {})
            svg_block = (
                f"<div style='margin:14px 0; border:1px solid #1e293b; border-radius:6px; overflow:hidden;'>{v.get('svg_render')}</div>"
                if v.get("svg_render")
                else ""
            )
            variants_html += f"""
            <div style="border:1px solid #334155; border-radius:8px; padding:16px; margin-bottom:24px; background:#0f172a; color:#f8fafc;">
                <h3 style="color:#38bdf8; margin-top:0;">Proposta {html.escape(str(v.get('variant_number', '')))}: {html.escape(str(v.get('title', '')))}</h3>
                <p><strong>Estratégia:</strong> {html.escape(str(v.get('strategy_name', '')))}</p>
                <p><strong>Conceito Arquitetônico:</strong> {html.escape(str(v.get('architectural_concept', '')))}</p>
                <p><strong>Solução de Engenharia:</strong> {html.escape(str(v.get('engineering_solution', '')))}</p>
                {svg_block}
                <div class="mono-bar">
                    Redução de Flecha: {html.escape(str(metrics.get('deflection_reduction_pct', '')))}% | Flecha Final: {html.escape(str(metrics.get('deflection_final_mm', '')))}mm | Fator de Segurança: {html.escape(str(metrics.get('safety_factor', '')))}
                </div>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Laudo de Viabilidade Estrutural — {safe_title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #020617; color: #e2e8f0; margin: 40px; line-height: 1.6; }}
        .header {{ border-bottom: 2px solid #334155; padding-bottom: 20px; margin-bottom: 30px; }}
        .badge {{ display: inline-block; padding: 6px 14px; border-radius: 9999px; font-weight: bold; background: {status_color}; color: white; font-size: 13px; }}
        .metric-box {{ display: inline-block; width: 22%; background: #0f172a; border: 1px solid #1e293b; padding: 14px; border-radius: 8px; margin-right: 2%; box-sizing: border-box; vertical-align: top; }}
        .metric-val {{ font-size: 24px; font-weight: bold; color: #38bdf8; font-family: "JetBrains Mono", "JetBrainsMono Nerd Font", "Noto Sans Mono", ui-monospace, monospace; }}
        .metric-lbl {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; }}
        .mono-bar {{ background: #1e293b; padding: 10px 12px; border-radius: 6px; font-family: "JetBrains Mono", "JetBrainsMono Nerd Font", "Noto Sans Mono", ui-monospace, monospace; font-weight: 500; font-size: 13px; }}
        .markdown-body {{ color: #e2e8f0; font-size: 15px; line-height: 1.7; }}
        .markdown-body.raw-fallback {{ white-space: pre-wrap; }}
        .markdown-body h1, .markdown-body h2, .markdown-body h3 {{ color: #ffffff; margin-top: 18px; margin-bottom: 10px; line-height: 1.3; }}
        .markdown-body h1:first-child, .markdown-body h2:first-child, .markdown-body h3:first-child {{ margin-top: 0; }}
        .markdown-body h4, .markdown-body h5, .markdown-body h6 {{ color: #38bdf8; font-family: "JetBrains Mono", "JetBrainsMono Nerd Font", ui-monospace, monospace; font-size: 14px; margin-top: 18px; margin-bottom: 8px; }}
        .markdown-body p {{ margin: 10px 0; }}
        .markdown-body ul, .markdown-body ol {{ margin: 10px 0; padding-left: 24px; }}
        .markdown-body li {{ margin-bottom: 6px; }}
        .markdown-body strong {{ color: #ffffff; font-weight: 600; }}
        .markdown-body code {{ font-family: "JetBrains Mono", "JetBrainsMono Nerd Font", ui-monospace, monospace; font-size: 13px; background: #1e293b; color: #38bdf8; padding: 2px 6px; border-radius: 4px; }}
        .markdown-body pre {{ background: #020617; border: 1px solid #1e293b; border-radius: 6px; padding: 12px; overflow-x: auto; }}
        .markdown-body pre code {{ background: transparent; padding: 0; color: #e2e8f0; }}
        .markdown-body blockquote {{ border-left: 3px solid #38bdf8; margin: 12px 0; padding: 4px 16px; color: #cbd5e1; background: rgba(30, 41, 59, 0.35); border-radius: 0 6px 6px 0; }}
        .markdown-body table {{ width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 14px; }}
        .markdown-body th, .markdown-body td {{ border: 1px solid #334155; padding: 8px 12px; text-align: left; }}
        .markdown-body th {{ background: #1e293b; color: #ffffff; }}
        .markdown-body hr {{ border: none; border-top: 1px solid #334155; margin: 18px 0; }}
        svg.font-mono, svg .font-mono {{ font-family: "JetBrains Mono", "JetBrainsMono Nerd Font", "Noto Sans Mono", ui-monospace, monospace; font-weight: 500; }}
        @media print {{
            body {{ margin: 20px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <span class="badge">{status_text}</span>
        <h1 style="margin: 15px 0 5px 0;">STRUCTURA.AI — Laudo de Compatibilização Físico-Arquitetônica</h1>
        <p style="color: #94a3b8; margin: 0;">Projeto: <strong>{safe_title}</strong> | Autor: <strong>{safe_author}</strong> | Tipologia: <strong>{safe_category}</strong> | Norma: <strong>ABNT NBR 6118 / NBR 6120</strong></p>
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

    <h2>1. Diagnóstico Estrutural &amp; Patologias Físicas</h2>
    <div style="background:#0f172a; border:1px solid #1e293b; border-radius:8px; padding:20px; margin-bottom:30px;">
        <p style="margin-top:0;">{safe_diagnosis}</p>
        <h4>Pontos Críticos Registrados:</h4>
        <ul style="margin-bottom:0;">{failures_html}</ul>
    </div>

    <h2>2. Parecer da Inteligência Artificial ({safe_ai_model})</h2>
    <div style="background:#0f172a; border:1px solid #1e293b; border-radius:8px; padding:24px; margin-bottom:30px;">
        <div id="ai-review-content" class="markdown-body raw-fallback">{safe_ai_review}</div>
    </div>

    <h2>3. As 5 Propostas de Redesign Visual &amp; Matemático</h2>
    <div>
        {variants_html}
    </div>

    <div style="border-top:1px solid #334155; padding-top:20px; margin-top:40px; color:#64748b; font-size:12px; text-align:center;">
        Structura.AI Monolith • Engenharia Estrutural e Arquitetura Computacional • HackTown 2026
    </div>

    <script src="https://cdn.jsdelivr.net/npm/marked@15.0.7/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/dompurify@3.2.4/dist/purify.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            const container = document.getElementById('ai-review-content');
            if (!container || !window.marked || !window.DOMPurify) return;

            const rawMarkdown = container.textContent.trim();
            if (!rawMarkdown) return;

            const rawHtml = window.marked.parse(rawMarkdown, {{ gfm: true, breaks: true }});
            container.innerHTML = window.DOMPurify.sanitize(rawHtml);
            container.classList.remove('raw-fallback');
        }});
    </script>
</body>
</html>"""

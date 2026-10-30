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
        badge_class = "badge-ok" if is_viable else "badge-fail"
        status_text = (
            "Aprovado para detalhamento executivo"
            if is_viable
            else "Revisão estrutural necessária"
        )
        safe_ai_model = html.escape(str(analysis_data.get("ai_model_used") or "Google Gemini"))
        safe_diagnosis = html.escape(str(analysis_data.get("structural_diagnosis_text") or ""))
        safe_ai_review = html.escape(str(analysis_data.get("ai_gemini_review") or "Não disponível"))

        failures_html = ""
        for f in analysis_data.get("failure_reasons", []):
            failures_html += f"<li class='failure-item'>— {html.escape(str(f))}</li>"
        if not failures_html:
            failures_html = "<li class='ok-item'>Nenhuma não conformidade identificada segundo a ABNT NBR 6118:2023.</li>"

        original_drawing_html = ""
        if project_image_url:
            safe_img_url = html.escape(str(project_image_url), quote=True)
            original_drawing_html = f"""
            <div class="report-card drawing-card">
                <h4 class="drawing-caption">Desenho submetido</h4>
                <img src="{safe_img_url}" alt="Desenho original" class="drawing-img" />
            </div>
            """

        variants_html = ""
        for v in variants:
            metrics = v.get("metrics_delta", {})
            svg_block = (
                f"<div class='blueprint-frame svg-wrap'>{v.get('svg_render')}</div>"
                if v.get("svg_render")
                else ""
            )
            variants_html += f"""
            <div class="report-card variant-card">
                <h3 class="variant-title">Proposta {html.escape(str(v.get('variant_number', '')))} · {html.escape(str(v.get('title', '')))}</h3>
                <p><strong>Estratégia:</strong> {html.escape(str(v.get('strategy_name', '')))}</p>
                <p><strong>Partido arquitetônico:</strong> {html.escape(str(v.get('architectural_concept', '')))}</p>
                <p><strong>Solução estrutural:</strong> {html.escape(str(v.get('engineering_solution', '')))}</p>
                {svg_block}
                <div class="mono-bar">
                    Redução de flecha: {html.escape(str(metrics.get('deflection_reduction_pct', '')))}% · Flecha final: {html.escape(str(metrics.get('deflection_final_mm', '')))} mm · Fator de segurança: {html.escape(str(metrics.get('safety_factor', '')))}
                </div>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Laudo de Viabilidade Estrutural — {safe_title}</title>
    <script>
        (function () {{
            try {{
                var saved = localStorage.getItem('structura-theme');
                var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
                var theme = (saved === 'light' || saved === 'dark') ? saved : (prefersDark ? 'dark' : 'light');
                document.documentElement.classList.toggle('dark', theme === 'dark');
                document.documentElement.dataset.theme = theme;
            }} catch (e) {{}}
        }})();
    </script>
    <link rel="stylesheet" href="/static/css/theme.css">
    <link rel="stylesheet" href="/static/css/components.css">
    <link rel="stylesheet" href="/static/css/custom.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --rpt-bg: rgb(var(--surface-base));
            --rpt-card: rgb(var(--surface-card));
            --rpt-well: rgb(var(--surface-inset));
            --rpt-border: rgb(var(--edge-default));
            --rpt-border-strong: rgb(var(--edge-strong));
            --rpt-heading: rgb(var(--ink-strong));
            --rpt-text: rgb(var(--ink-primary));
            --rpt-secondary: rgb(var(--ink-secondary));
            --rpt-muted: rgb(var(--ink-muted));
            --rpt-danger: rgb(var(--accent-rose));
            --rpt-ok: rgb(var(--accent-emerald));
        }}
        body {{
            font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: var(--rpt-bg);
            color: var(--rpt-text);
            max-width: 960px;
            margin: 36px auto;
            padding: 0 24px;
            font-size: 13px;
            line-height: 1.6;
        }}
        h1, h2, h3, strong {{ color: var(--rpt-heading); letter-spacing: -0.015em; }}
        h1 {{ font-size: 20px; font-weight: 600; margin: 12px 0 6px 0; }}
        h2 {{ font-size: 15px; font-weight: 600; margin: 28px 0 10px 0; }}
        h3 {{ font-size: 14px; font-weight: 600; }}
        .header {{ border-bottom: 1px solid var(--rpt-border); padding-bottom: 18px; margin-bottom: 24px; }}
        .header-meta {{ color: var(--rpt-muted); margin: 0; font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 11px; }}
        .badge {{
            display: inline-block;
            padding: 3px 9px;
            border-radius: 4px;
            font-family: "JetBrains Mono", ui-monospace, monospace;
            font-weight: 500;
            font-size: 11px;
        }}
        .badge-ok {{ background: rgba(21, 109, 77, 0.08); color: var(--rpt-ok); border: 1px solid rgba(21, 109, 77, 0.3); }}
        .badge-fail {{ background: rgba(185, 28, 28, 0.08); color: var(--rpt-danger); border: 1px solid rgba(185, 28, 28, 0.3); }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }}
        @media (max-width: 640px) {{ .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
        .metric-box {{ background: var(--rpt-card); border: 1px solid var(--rpt-border); padding: 12px; border-radius: 6px; }}
        .metric-val {{ font-size: 17px; font-weight: 600; color: var(--rpt-heading); font-family: "JetBrains Mono", ui-monospace, monospace; margin-top: 4px; }}
        .metric-lbl {{ font-size: 11px; color: var(--rpt-muted); font-family: "JetBrains Mono", ui-monospace, monospace; }}
        .report-card {{ background: var(--rpt-card); border: 1px solid var(--rpt-border); border-radius: 8px; padding: 18px; margin-bottom: 20px; }}
        .drawing-card {{ text-align: center; padding: 16px; }}
        .drawing-caption {{ color: var(--rpt-muted); font-size: 11px; font-family: "JetBrains Mono", ui-monospace, monospace; text-transform: uppercase; margin: 0 0 10px 0; }}
        .drawing-img {{ max-height: 340px; max-width: 100%; border-radius: 4px; border: 1px solid var(--rpt-border); }}
        .variant-card {{ padding: 18px; margin-bottom: 18px; }}
        .variant-title {{ color: var(--rpt-heading); margin-top: 0; margin-bottom: 8px; }}
        .variant-card p {{ color: var(--rpt-secondary); margin: 6px 0; }}
        .svg-wrap {{ margin: 12px 0; border: 1px solid var(--rpt-border); border-radius: 6px; overflow: hidden; }}
        .mono-bar {{ background: var(--rpt-well); border: 1px solid var(--rpt-border); padding: 8px 12px; border-radius: 4px; font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 11px; color: var(--rpt-text); }}
        .failure-item {{ color: var(--rpt-danger); margin-bottom: 6px; list-style: none; }}
        .ok-item {{ color: var(--rpt-ok); list-style: none; }}
        .markdown-body {{ color: var(--rpt-secondary); font-size: 13px; line-height: 1.65; }}
        .markdown-body.raw-fallback {{ white-space: pre-wrap; }}
        .markdown-body h1, .markdown-body h2, .markdown-body h3 {{ color: var(--rpt-heading); margin-top: 16px; margin-bottom: 8px; line-height: 1.3; }}
        .markdown-body h1:first-child, .markdown-body h2:first-child, .markdown-body h3:first-child {{ margin-top: 0; }}
        .markdown-body h4, .markdown-body h5, .markdown-body h6 {{ color: var(--rpt-heading); font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 12px; margin-top: 14px; margin-bottom: 6px; }}
        .markdown-body p {{ margin: 8px 0; }}
        .markdown-body ul, .markdown-body ol {{ margin: 8px 0; padding-left: 20px; }}
        .markdown-body li {{ margin-bottom: 4px; }}
        .markdown-body code {{ font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 12px; background: var(--rpt-well); color: var(--rpt-heading); padding: 1px 5px; border-radius: 3px; }}
        .markdown-body pre {{ background: var(--rpt-well); border: 1px solid var(--rpt-border); border-radius: 6px; padding: 12px; overflow-x: auto; }}
        .markdown-body pre code {{ background: transparent; padding: 0; }}
        .markdown-body blockquote {{ border-left: 2px solid var(--rpt-heading); margin: 10px 0; padding: 4px 14px; color: var(--rpt-secondary); background: var(--rpt-well); }}
        .markdown-body table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 12px; }}
        .markdown-body th, .markdown-body td {{ border: 1px solid var(--rpt-border); padding: 7px 10px; text-align: left; }}
        .markdown-body th {{ background: var(--rpt-well); color: var(--rpt-heading); }}
        .report-footer {{ border-top: 1px solid var(--rpt-border); padding-top: 16px; margin-top: 32px; color: var(--rpt-muted); font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 11px; display: flex; flex-wrap: wrap; gap: 8px; justify-content: space-between; }}
        svg.font-mono, svg .font-mono {{ font-family: "JetBrains Mono", ui-monospace, monospace; font-weight: 500; }}
        @media print {{
            body {{ margin: 16px auto; background: #ffffff !important; color: #111113 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <span class="badge {badge_class}">{status_text}</span>
        <h1>STRUCTURA.AI — Laudo de Compatibilização Físico-Arquitetônica</h1>
        <p class="header-meta">Projeto: <strong>{safe_title}</strong> · Autoria: <strong>{safe_author}</strong> · Tipologia: <strong>{safe_category}</strong> · Normas: <strong>ABNT NBR 6118 / NBR 6120</strong></p>
    </div>

    <div class="metrics-grid">
        <div class="metric-box">
            <div class="metric-lbl">Índice estrutural</div>
            <div class="metric-val">{score}/100</div>
        </div>
        <div class="metric-box">
            <div class="metric-lbl">Flecha calculada (ELS)</div>
            <div class="metric-val">{analysis_data.get('max_deflection_mm')} mm</div>
        </div>
        <div class="metric-box">
            <div class="metric-lbl">Limite normativo (L/250)</div>
            <div class="metric-val">{analysis_data.get('allowable_deflection_mm')} mm</div>
        </div>
        <div class="metric-box">
            <div class="metric-lbl">Momento fletor máximo</div>
            <div class="metric-val">{analysis_data.get('max_bending_moment_knm')} kN·m</div>
        </div>
    </div>

    {original_drawing_html}

    <h2>1. Diagnóstico estrutural</h2>
    <div class="report-card">
        <p style="margin-top:0; color: var(--rpt-secondary);">{safe_diagnosis}</p>
        <h4 style="font-size: 11px; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; margin-bottom: 6px;">Apontamentos normativos</h4>
        <ul style="margin:0; padding-left:0;">{failures_html}</ul>
    </div>

    <h2>2. Parecer técnico complementar ({safe_ai_model})</h2>
    <div class="report-card">
        <div id="ai-review-content" class="markdown-body raw-fallback">{safe_ai_review}</div>
    </div>

    <h2>3. Propostas de compatibilização estrutural</h2>
    <div>
        {variants_html}
    </div>

    <div class="report-footer">
        <span>Structura.ai — Compatibilização físico-arquitetônica</span>
        <span>ABNT NBR 6118:2023 · NBR 6120</span>
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

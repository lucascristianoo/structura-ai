"""
Google Gemini Free Tier Integration Client.
Supports Gemini 2.5 Flash / 1.5 Flash Vision Multimodal Analysis with fallback.
"""
import os
import base64
import logging
import httpx
from typing import Dict, Any, Optional
from structura_ai.config import settings
from structura_ai.ai.prompt_templates import ARCHITECT_ENGINEER_SYNTHESIS_PROMPT
from structura_ai.ai.mock_engine import MockGeminiEngine

logger = logging.getLogger(__name__)

class GeminiVisionClient:
    """
    Client for Google Gemini Multimodal APIs.
    Communicates with Gemini 2.5 Flash (free tier) for architectural blueprint inspections.
    """

    @classmethod
    async def analyze_project(
        cls,
        project_title: str,
        category: str,
        evaluation: Dict[str, Any],
        image_bytes: Optional[bytes] = None,
        image_mime: str = "image/png"
    ) -> Dict[str, Any]:
        """
        Analyzes the project image/blueprint and structural metrics using Google Gemini.
        Falls back to MockGeminiEngine if API key is not configured or network error occurs.
        """
        api_key = settings.effective_api_key
        
        if not api_key:
            logger.info("No Gemini API key provided. Using built-in architectural-engineering synthesis engine.")
            review_text = MockGeminiEngine.generate_review(project_title, category, evaluation)
            return {
                "review": review_text,
                "model": "offline-deterministic-physics",
                "source": "Local Structural Physics & AI Synthesis Engine"
            }

        try:
            # We use direct Google Generative Language v1beta REST API for maximum speed and zero dependency fragility
            model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

            # Prepare prompt with dynamic evaluation details
            inputs = evaluation.get("calculated_inputs", {})
            prompt_context = (
                f"{ARCHITECT_ENGINEER_SYNTHESIS_PROMPT}\n\n"
                f"### DADOS TÉCNICOS PREVIAMENTE APURADOS PELA FÍSICA ESTRUTURAL:\n"
                f"- Título do Projeto: {project_title}\n"
                f"- Categoria: {category}\n"
                f"- Vão livre principal: {inputs.get('span_length_m', 9.5)}m\n"
                f"- Balanço estrutural: {inputs.get('cantilever_length_m', 3.5)}m\n"
                f"- Altura da viga original: {inputs.get('beam_height_cm', 30.0)}cm (Largura: {inputs.get('beam_width_cm', 20.0)}cm)\n"
                f"- Flecha calculada: {evaluation.get('max_deflection_mm', 0.0)}mm (Limite NBR 6118: {evaluation.get('allowable_deflection_mm', 0.0)}mm)\n"
                f"- Viabilidade física segundo cálculos: {'VIÁVEL' if evaluation.get('is_physically_viable') else 'INVIÁVEL / REQUER REDESIGN'}\n"
                f"- Falhas identificadas: {', '.join(evaluation.get('failure_reasons', [])) or 'Nenhuma'}\n\n"
                f"Por favor, elabore sua síntese arquitetônica-estrutural com diagnóstico e orientações executivas."
            )

            parts = [{"text": prompt_context}]

            # If image bytes exist, attach as inline_data
            if image_bytes and len(image_bytes) > 0:
                b64_image = base64.b64encode(image_bytes).decode("utf-8")
                parts.append({
                    "inline_data": {
                        "mime_type": image_mime,
                        "data": b64_image
                    }
                })

            payload = {
                "contents": [
                    {
                        "parts": parts
                    }
                ],
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 2048,
                }
            }

            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        content_parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join([p.get("text", "") for p in content_parts])
                        return {
                            "review": text,
                            "model": model_name,
                            "source": "Google Gemini 2.5 Flash Free Tier"
                        }
                else:
                    logger.warning(f"Gemini API returned status {response.status_code}: {response.text}")

        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}. Falling back to local engine.")

        # Graceful fallback on error or 429
        fallback_review = MockGeminiEngine.generate_review(project_title, category, evaluation)
        return {
            "review": fallback_review,
            "model": "gemini-fallback-local",
            "source": "Local Fallback Engine"
        }

    @classmethod
    async def chat_copilot(
        cls,
        message: str,
        project_context: Optional[Dict[str, Any]] = None,
        chat_history: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Multi-turn copilot dialogue for architectural and structural co-design.
        """
        api_key = settings.effective_api_key
        ctx = project_context or {}
        has_project = bool(ctx)
        span = float(ctx.get("span_length_m", 10.0))
        cantilever = float(ctx.get("cantilever_length_m", 0.0))
        bw = float(ctx.get("beam_width_cm", 20.0))
        bh = float(ctx.get("beam_height_cm", 30.0))
        fck = float(ctx.get("concrete_fck_mpa", 30.0))
        max_defl = float(ctx.get("max_deflection_mm", 0.0))
        adm_defl = float(ctx.get("allowable_deflection_mm", round((span * 1000.0) / 250.0, 1)))
        moment_knm = float(ctx.get("max_bending_moment_knm", 0.0))
        score = float(ctx.get("structural_score", 0.0))
        is_viable = bool(ctx.get("is_physically_viable", False))
        proj_title = str(ctx.get("title", "Modelo atual"))
        failures = ctx.get("failure_reasons") or []

        ctx_str = ""
        if has_project:
            failures_txt = "; ".join(str(f) for f in failures) if failures else "Nenhuma"
            ctx_str = (
                f"\nContexto Atual do Projeto ({proj_title}):\n"
                f"- Vão principal: {span:.1f} m | Balanço: {cantilever:.1f} m\n"
                f"- Seção da viga: {bw:.0f}×{bh:.0f} cm | Concreto: C{fck:.0f}\n"
                f"- Flecha calculada (ELS): {max_defl:.1f} mm (Limite NBR 6118: {adm_defl:.1f} mm)\n"
                f"- Momento fletor máximo: {moment_knm:.1f} kN·m | Índice estrutural: {score:.1f}/100\n"
                f"- Status Físico: {'CONFORME NBR 6118' if is_viable else 'REPROVADO / REQUER REDESIGN'}\n"
                f"- Não conformidades: {failures_txt}\n"
            )

        history_str = ""
        if chat_history and isinstance(chat_history, list):
            recent_turns = chat_history[-10:]
            formatted_turns = []
            for turn in recent_turns:
                if isinstance(turn, dict) and turn.get("content"):
                    role_label = "Usuário" if turn.get("role") == "user" else "Assistente"
                    formatted_turns.append(f"{role_label}: {turn['content']}")
            if formatted_turns:
                history_str = "\nHistórico recente do debate:\n" + "\n".join(formatted_turns) + "\n"

        system_instruction = (
            "Você é o assistente técnico do Structura.AI, especializado em compatibilização arquitetônica e física estrutural "
            "segundo as normas ABNT NBR 6118:2023, NBR 6120 e NBR 8800. Ajude o usuário a compreender o diagnóstico do modelo "
            "carregado e debater alternativas técnicas de forma objetiva, precisa e colaborativa."
        )

        if not api_key:
            msg_lower = message.lower()
            rec_rc_h = max(30, round((span * 100.0) / 11.0 / 5.0) * 5)
            rec_pt_h = max(22, round((span * 100.0) / 36.0))

            if not has_project:
                reply = (
                    "Ainda não há um arquivo carregado na sessão. Importe um arquivo (DXF, IFC, OBJ, glTF, imagem ou PDF) "
                    "no painel de arquivos para que eu possa calcular os esforços pela NBR 6118, gerar o diagnóstico e debater "
                    "os resultados específicos do seu projeto."
                )
            elif any(k in msg_lower for k in ("protens", "cabo", "cordoalha", "plana")):
                reply = (
                    f"Para o vão de {span:.1f} m de '{proj_title}', a **protensão ativa** com cordoalhas engraxadas CP-190 RB "
                    f"introduz carga equivalente ascendente que compensa cerca de 70% a 80% da flecha permanente. "
                    f"Isso permite trabalhar com altura da ordem de **{rec_pt_h} a {rec_pt_h + 4} cm** mantendo conformidade "
                    f"com o limite ELS de {adm_defl:.1f} mm."
                )
            elif any(k in msg_lower for k in ("altura", "seção", "secao", "redimension", "engross", "viga")):
                reply = (
                    f"Na seção atual ({bw:.0f}×{bh:.0f} cm em C{fck:.0f}), a flecha é de **{max_defl:.1f} mm** "
                    f"(limite ≤ {adm_defl:.1f} mm). Como a inércia cresce com o cubo da altura ($I = b \\cdot h^3 / 12$), "
                    f"em concreto armado convencional recomenda-se elevar a altura para cerca de **{bw:.0f}×{rec_rc_h} cm** "
                    f"(relação ~L/11). Se não puder reduzir o pé-direito livre, considere viga protendida ou perfil metálico híbrido."
                )
            elif any(k in msg_lower for k in ("flecha", "deforma", "els", "reprov", "por que", "porque", "falha", "motivo")):
                if is_viable:
                    reply = (
                        f"O modelo '{proj_title}' está **conforme a NBR 6118** (índice {score:.1f}/100): a flecha total diferida "
                        f"de **{max_defl:.1f} mm** respeita o limite de serviço $L/250$ (**{adm_defl:.1f} mm**), mantendo integridade "
                        f"de vedações e conforto visual."
                    )
                else:
                    reasons_detail = " ".join(str(f) for f in failures) if failures else (
                        f"A flecha calculada de {max_defl:.1f} mm supera o limite admissível de {adm_defl:.1f} mm."
                    )
                    reply = (
                        f"O diagnóstico apontou necessidade de revisão em '{proj_title}' (índice {score:.1f}/100). "
                        f"{reasons_detail} Pela NBR 6118, a fissuração no Estádio II e a fluência do concreto ampliam a deformação "
                        f"imediata ao longo do tempo, exigindo maior inércia ou sistema ativo."
                    )
            elif any(k in msg_lower for k in ("balanço", "balanco", "tirante", "consol")):
                if cantilever > 0:
                    rec_cant_h = max(30, round((cantilever * 100.0) / 4.5 / 5.0) * 5)
                    reply = (
                        f"O balanço de **{cantilever:.1f} m** funciona como consola engastada, cuja flecha na ponta é muito sensível "
                        f"à rotação do apoio. Sem tirantes superiores, recomenda-se seção com altura próxima de **{rec_cant_h} cm** "
                        f"na raiz (seção variável/mísula) ou atirantamento metálico ancorado no pilar."
                    )
                else:
                    reply = (
                        f"O modelo atual ('{proj_title}') foi avaliado sem balanço livre relevante (Lc = 0,0 m), concentrando os "
                        f"esforços no vão principal de {span:.1f} m (Mk = {moment_knm:.1f} kN·m)."
                    )
            elif any(k in msg_lower for k in ("custo", "sinapi", "preço", "preco", "orçamento", "orcamento", "barat", "econom")):
                reply = (
                    f"Comparando custos referenciais (SINAPI) para o vão de {span:.1f} m:\n"
                    f"- **Concreto armado ({bw:.0f}×{rec_rc_h} cm):** menor custo unitário de execução, porém maior volume de concreto e fôrmas.\n"
                    f"- **Laje nervurada (Waffle):** reduz cerca de 30% a 35% do consumo de concreto, vantajosa em plantas ortogonais.\n"
                    f"- **Protensão ou sistema misto aço-concreto:** maior insumo especializado, compensado pela redução de peso nas fundações e ganho de pé-direito."
                )
            elif any(k in msg_lower for k in ("carbon", "co2", "sustentab", "ambiental")):
                reply = (
                    "Na avaliação de carbono incorporado (A1–A3), o concreto C30 emite ~320 kg CO₂e/m³ e o aço CA-50 ~1,82 kg CO₂e/kg. "
                    "Soluções que aliviam peso próprio — como lajes nervuradas, treliças Vierendeel ou seções mistas — podem reduzir "
                    "a pegada de carbono estrutural entre 25% e 40%."
                )
            elif any(k in msg_lower for k in ("alternativa", "opç", "opc", "soluç", "soluc", "variante", "sugest")):
                reply = (
                    f"Para vencer os **{span:.1f} m** de '{proj_title}' com segurança normativa, as principais estratégias são:\n"
                    f"1. **Redimensionamento em C.A.:** ajustar viga para ~{bw:.0f}×{rec_rc_h} cm.\n"
                    f"2. **Protensão ativa:** manter estética esbelta (~{rec_pt_h}–{rec_pt_h + 4} cm) anulando flechas.\n"
                    f"3. **Grelha nervurada (Waffle):** aliviar peso próprio em vãos bidirecionais.\n"
                    f"4. **Viga Vierendeel ou perfil metálico:** integrar a altura estrutural à fachada ou caixilharia."
                )
            else:
                status_summary = "conforme os limites da NBR 6118" if is_viable else "acima do limite de deformação em serviço (ELS)"
                reply = (
                    f"Sobre '{proj_title}' (vão de {span:.1f} m, viga {bw:.0f}×{bh:.0f} cm, flecha de {max_defl:.1f} mm vs limite de {adm_defl:.1f} mm — {status_summary}): "
                    f"o momento solicitante atinge **{moment_knm:.1f} kN·m**. Podemos avaliar juntos o aumento de inércia da seção "
                    f"(~{bw:.0f}×{rec_rc_h} cm), uso de fck superior (C35/C40), protensão ou mudança de sistema estrutural. Qual restrição arquitetônica é prioritária aqui?"
                )
            return {
                "reply": reply,
                "model": "structura-copilot-deterministic",
                "source": "Local Synthesis Engine"
            }

        try:
            model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            prompt = f"{system_instruction}\n{ctx_str}{history_str}\nMensagem atual do usuário: {message}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024}
            }
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join([p.get("text", "") for p in parts])
                        return {"reply": text, "model": model_name, "source": "Google Gemini"}
        except Exception as e:
            logger.error(f"Copilot error: {e}")

        return {
            "reply": f"Para o vão de {span:.1f} m (flecha {max_defl:.1f} mm / limite {adm_defl:.1f} mm), recomendamos avaliar ajuste de altura da seção ou protensão ativa.",
            "model": "structura-copilot-fallback",
            "source": "Local Engine"
        }


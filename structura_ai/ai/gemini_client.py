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
        ctx_str = ""
        if project_context:
            ctx_str = (
                f"\nContexto Atual do Projeto:\n"
                f"- Vão: {project_context.get('span_length_m', 10.0)}m\n"
                f"- Viga: {project_context.get('beam_width_cm', 20.0)}x{project_context.get('beam_height_cm', 30.0)}cm\n"
                f"- Flecha calculada: {project_context.get('max_deflection_mm', 0.0)}mm (Limite NBR: {project_context.get('allowable_deflection_mm', 0.0)}mm)\n"
                f"- Status Físico: {'CONFORME' if project_context.get('is_physically_viable') else 'REPROVADO / REQUER REDESIGN'}\n"
            )

        system_instruction = (
            "Você é o Structura Copilot, um co-piloto especializado em compatibilização arquitetônica e física estrutural "
            "segundo as normas ABNT NBR 6118:2023, NBR 6120 e NBR 8800. Seu objetivo é ajudar arquitetos a preservar seu conceito "
            "estético sem comprometer a estabilidade e a segurança das estruturas. Responda de forma clara, técnica, elegante e propositiva."
        )

        if not api_key:
            # Deterministic architectural copilot response
            msg_lower = message.lower()
            if "protens" in msg_lower or "cabo" in msg_lower:
                reply = (
                    "A protensão ativa é a solução ideal quando você precisa manter a viga plana ou embutida na laje. "
                    "Com cordoalhas engraxadas de aço CP-190 RB, introduzimos uma contra-flecha ativa que anula até 75% da flecha em serviço, "
                    "permitindo vãos de 10m a 14m com espessuras da ordem de 24 a 28cm sem rebaixar vigas."
                )
            elif "custo" in msg_lower or "sinapi" in msg_lower or "preço" in msg_lower:
                reply = (
                    "Com base no SINAPI 2026 e nos índices CUB, a grelha nervurada (Waffle Slab) economiza até 35% no consumo de concreto, "
                    "embora exija formas plásticas recuperáveis. Já a protensão tem custo inicial de cordoalhas compensado pela eliminação "
                    "de vigas invertidas e alívio de fundações."
                )
            elif "carbon" in msg_lower or "co2" in msg_lower or "sustentab" in msg_lower:
                reply = (
                    "Na análise de ciclo de vida A1-A3, o concreto armado convencional emite ~320 kg CO2e/m³ e o aço CA-50 ~1.82 kg CO2e/kg. "
                    "A utilização de seções híbridas ou cascas funiculares de compressão reduz a pegada de carbono em até 45% pelo alívio de massa."
                )
            else:
                reply = (
                    f"Analisando sua solicitação sobre '{message}': {ctx_str}"
                    f"Recomendo verificar a relação vão/altura (L/12 a L/15 para vigas biapoiadas). Caso deseje manter a estética esbelta, "
                    f"uma das 5 variantes geradas (Protensão, Fachada Vierendeel, Tirantes em V, Waffle Slab ou Arco Funicular) garantirá total conformidade com a NBR 6118."
                )
            return {
                "reply": reply,
                "model": "structura-copilot-deterministic",
                "source": "Local Synthesis Engine"
            }

        try:
            model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            prompt = f"{system_instruction}\n{ctx_str}\nMensagem do Arquiteto: {message}"
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
            "reply": f"Structura Copilot: Para este vão, recomendamos avaliar a contra-flecha ou as variantes com protensão e treliças integradas. ({ctx_str})",
            "model": "structura-copilot-fallback",
            "source": "Local Engine"
        }


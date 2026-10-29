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

"""
Provedor de Embeddings Semânticos (Padrão Lembry + POC Gratuita Gemini / Hash Determinístico).

Suporta:
1. GeminiEmbeddingProvider (gratuito via Google GenAI SDK `text-embedding-004` quando há API key e rede).
2. HashEmbeddingProvider (100% gratuito/offline baseado em projeção léxico-semântica SHA-256 normalizada,
   garantindo similaridade por cosseno real entre termos arquitetônicos/estruturais sem custo de API).
"""

import hashlib
import logging
import math
import re
from typing import Dict, List, Optional, Protocol, runtime_checkable

from structura_ai.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSION = 256


@runtime_checkable
class EmbeddingProvider(Protocol):
    @property
    def dimension(self) -> int:
        ...

    @property
    def model_id(self) -> str:
        ...

    def get_embedding(self, text: str) -> List[float]:
        ...


class HashEmbeddingProvider:
    """
    Provedor determinístico de embeddings semânticos via feature hashing de tokens e bi-gramas.
    Garante que documentos com vocabulário técnico próximo tenham alta similaridade de cosseno.
    """

    def __init__(self, dimensions: int = EMBEDDING_DIMENSION) -> None:
        self._dim = dimensions
        self._model_id = f"deterministic-hash-{dimensions}d"
        self._cache: Dict[str, List[float]] = {}

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_id(self) -> str:
        return self._model_id

    def get_embedding(self, text: str) -> List[float]:
        clean = (text or "").strip().lower()
        if not clean:
            return [0.0] * self._dim

        if clean in self._cache:
            return self._cache[clean]

        tokens = re.findall(r"[a-z0-9à-ú_]+", clean)
        if not tokens:
            return [0.0] * self._dim

        features = list(tokens)
        # Adiciona prefixos de radicais (4 chars) e bigramas para capturar variações morfológicas
        for t in tokens:
            if len(t) >= 4:
                features.append(f"stem:{t[:4]}")
            if len(t) >= 6:
                features.append(f"stem6:{t[:6]}")
        for i in range(len(tokens) - 1):
            features.append(f"bi:{tokens[i]}_{tokens[i + 1]}")

        vec = [0.0] * self._dim
        for feat in features:
            digest = hashlib.sha256(feat.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self._dim
            sign = 1.0 if (digest[4] % 2 == 0) else -1.0
            weight = 1.5 if not feat.startswith(("stem", "bi:")) else 0.8
            vec[idx] += sign * weight

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [round(v / norm, 6) for v in vec]

        self._cache[clean] = vec
        return vec


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


_global_provider: Optional[EmbeddingProvider] = None


def get_embedding_provider() -> EmbeddingProvider:
    global _global_provider
    if _global_provider is None:
        _global_provider = HashEmbeddingProvider(dimensions=EMBEDDING_DIMENSION)
    return _global_provider


def compute_embedding(text: str) -> List[float]:
    return get_embedding_provider().get_embedding(text)


get_embedding = compute_embedding


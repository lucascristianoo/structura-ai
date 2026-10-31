"""
Arquitetura de Memória EverMemOS (Padrão Lembry.Chatbot) para Structura-AI.
Implementa:
1. EpisodeBufferStore (memory_buffers): fila de mensagens com janela deslizante (SLIDING_WINDOW=3, MAX_EPISODE=8)
2. MemCellStore (memory_cells): memória episódica com busca híbrida BM25 + Cosine via RRF (k=60) e filtro temporal de foresights
3. MemSceneStore (memory_scenes + memory_scene_cells + memory_scene_versions): agrupamento temático por centroide móvel (threshold=0.28)
4. UserProfileStore (user_profiles + user_profile_versions): perfil evolutivo do arquiteto/engenheiro com fatos explícitos e padrões implícitos
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, delete

from structura_ai.database import AsyncSessionLocal
from structura_ai.models import (
    MemoryBufferRow,
    MemoryCellRow,
    MemorySceneRow,
    MemorySceneCellRow,
    MemorySceneVersionRow,
    UserProfileRow,
    UserProfileVersionRow,
)
from structura_ai.schemas_memory import (
    FactItem,
    ForesightItem,
    MemCell,
    MemScene,
    MemSceneVersion,
    ProfileExplicitFact,
    ProfileImplicitPattern,
    UserProfile,
    UserProfileVersion,
)
from structura_ai.integrations.embeddings import get_embedding, cosine_similarity

SLIDING_WINDOW = 3
MAX_EPISODE = 8
SCENE_DISTANCE_THRESHOLD = 0.28


def _merge_centroid(
    old_centroid: list[float],
    new_embedding: list[float],
    old_count: int,
) -> list[float]:
    """Recalcula o centroide da MemScene via média ponderada móvel normalizada L2."""
    if not old_centroid:
        return list(new_embedding)
    if not new_embedding or len(old_centroid) != len(new_embedding):
        return list(old_centroid)

    total = old_count + 1
    merged = [
        (old_val * old_count + new_val) / total
        for old_val, new_val in zip(old_centroid, new_embedding)
    ]
    norm = math.sqrt(sum(v * v for v in merged))
    if norm > 0:
        merged = [v / norm for v in merged]
    return merged


class EpisodeBufferStore:
    """Gerencia o buffer de mensagens brutas não consumidas por (user_id, session_id)."""

    async def enqueue_messages(
        self,
        user_id: str,
        session_id: str,
        messages: list[dict],
    ) -> None:
        async with AsyncSessionLocal() as db:
            for msg in messages:
                row = MemoryBufferRow(
                    user_id=user_id,
                    session_id=session_id or "default_session",
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    processed=False,
                )
                db.add(row)
            await db.commit()

    async def get_unconsumed(self, user_id: str, session_id: str) -> list[dict]:
        async with AsyncSessionLocal() as db:
            stmt = (
                select(MemoryBufferRow)
                .where(
                    MemoryBufferRow.user_id == user_id,
                    MemoryBufferRow.session_id == (session_id or "default_session"),
                    MemoryBufferRow.processed == False,  # noqa: E712
                )
                .order_by(MemoryBufferRow.id.asc())
            )
            res = await db.execute(stmt)
            rows = res.scalars().all()
            return [
                {
                    "id": r.id,
                    "role": r.role,
                    "content": r.content,
                    "timestamp": r.message_timestamp.isoformat() if r.message_timestamp else "",
                }
                for r in rows
            ]

    async def get_sliding_window(self, user_id: str, session_id: str) -> tuple[list[dict], list[dict]]:
        """Retorna (historical_messages, recent_window_of_3)."""
        unconsumed = await self.get_unconsumed(user_id, session_id)
        if len(unconsumed) <= SLIDING_WINDOW:
            return [], unconsumed
        return unconsumed[:-SLIDING_WINDOW], unconsumed[-SLIDING_WINDOW:]

    async def consume_all(self, user_id: str, session_id: str) -> list[dict]:
        async with AsyncSessionLocal() as db:
            stmt = (
                select(MemoryBufferRow)
                .where(
                    MemoryBufferRow.user_id == user_id,
                    MemoryBufferRow.session_id == (session_id or "default_session"),
                    MemoryBufferRow.processed == False,  # noqa: E712
                )
                .order_by(MemoryBufferRow.id.asc())
            )
            res = await db.execute(stmt)
            rows = res.scalars().all()
            messages = [
                {
                    "id": r.id,
                    "role": r.role,
                    "content": r.content,
                    "timestamp": r.message_timestamp.isoformat() if r.message_timestamp else "",
                }
                for r in rows
            ]
            for r in rows:
                r.processed = True
            await db.commit()
            return messages


class MemSceneStore:
    """Agrupa MemCells por centroide temático (MemScene) e salva versões auditáveis."""

    async def find_nearest_scene(
        self,
        user_id: str,
        embedding: list[float],
        threshold: float = SCENE_DISTANCE_THRESHOLD,
    ) -> Optional[MemScene]:
        if not embedding:
            return None
        scenes = await self.list_by_user(user_id)
        best_scene: Optional[MemScene] = None
        best_distance = 1.0

        for scene in scenes:
            if not scene.centroid_embedding:
                continue
            sim = cosine_similarity(embedding, scene.centroid_embedding)
            cosine_distance = 1.0 - sim
            if cosine_distance <= threshold and cosine_distance < best_distance:
                best_distance = cosine_distance
                best_scene = scene
        return best_scene

    async def save_or_update_scene(
        self,
        scene: MemScene,
        new_cell_id: str,
        new_embedding: Optional[list[float]] = None,
    ) -> MemScene:
        async with AsyncSessionLocal() as db:
            stmt = select(MemorySceneRow).where(MemorySceneRow.id == scene.id)
            res = await db.execute(stmt)
            row = res.scalar_one_or_none()

            if row is None:
                centroid = list(new_embedding) if new_embedding else (scene.centroid_embedding or [])
                row = MemorySceneRow(
                    id=scene.id,
                    user_id=scene.user_id,
                    topic=scene.topic,
                    summary=scene.summary,
                    centroid_embedding=centroid,
                    cell_count=1,
                )
                db.add(row)
                scene.centroid_embedding = centroid
                scene.cell_count = 1
            else:
                old_count = row.cell_count or 1
                if new_embedding:
                    row.centroid_embedding = _merge_centroid(
                        row.centroid_embedding or [],
                        new_embedding,
                        old_count,
                    )
                row.topic = scene.topic
                row.summary = scene.summary
                row.cell_count = old_count + 1
                row.updated_at = datetime.now(timezone.utc)
                scene.centroid_embedding = row.centroid_embedding
                scene.cell_count = row.cell_count

            # Registra vínculo N:N (scene <-> cell)
            link_stmt = select(MemorySceneCellRow).where(
                MemorySceneCellRow.scene_id == scene.id,
                MemorySceneCellRow.cell_id == new_cell_id,
            )
            existing_link = (await db.execute(link_stmt)).scalar_one_or_none()
            if existing_link is None:
                db.add(MemorySceneCellRow(scene_id=scene.id, cell_id=new_cell_id))

            # Registra versão imutável para auditoria
            version_row = MemorySceneVersionRow(
                scene_id=scene.id,
                user_id=scene.user_id,
                topic=scene.topic,
                summary=scene.summary,
                trigger_cell_id=new_cell_id,
                cell_count_at_version=scene.cell_count,
            )
            db.add(version_row)
            await db.commit()

            # Atualiza lista de cell_ids
            cells_res = await db.execute(
                select(MemorySceneCellRow.cell_id).where(MemorySceneCellRow.scene_id == scene.id)
            )
            scene.cell_ids = list(cells_res.scalars().all())
            return scene

    async def get_scene_for_cell(self, cell_id: str) -> Optional[MemScene]:
        async with AsyncSessionLocal() as db:
            link_res = await db.execute(
                select(MemorySceneCellRow).where(MemorySceneCellRow.cell_id == cell_id)
            )
            link = link_res.scalar_one_or_none()
            if not link:
                return None

            row_res = await db.execute(
                select(MemorySceneRow).where(MemorySceneRow.id == link.scene_id)
            )
            row = row_res.scalar_one_or_none()
            if not row:
                return None

            cells_res = await db.execute(
                select(MemorySceneCellRow.cell_id).where(MemorySceneCellRow.scene_id == row.id)
            )
            cell_ids = list(cells_res.scalars().all())
            return MemScene(
                id=row.id,
                user_id=row.user_id,
                topic=row.topic,
                summary=row.summary,
                cell_ids=cell_ids,
                centroid_embedding=row.centroid_embedding,
                cell_count=row.cell_count,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    async def list_by_user(self, user_id: str) -> list[MemScene]:
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(MemorySceneRow)
                .where(MemorySceneRow.user_id == user_id)
                .order_by(MemorySceneRow.updated_at.desc())
            )
            rows = res.scalars().all()
            scenes: list[MemScene] = []
            for row in rows:
                cells_res = await db.execute(
                    select(MemorySceneCellRow.cell_id).where(MemorySceneCellRow.scene_id == row.id)
                )
                c_ids = list(cells_res.scalars().all())
                scenes.append(
                    MemScene(
                        id=row.id,
                        user_id=row.user_id,
                        topic=row.topic,
                        summary=row.summary,
                        cell_ids=c_ids,
                        centroid_embedding=row.centroid_embedding,
                        cell_count=row.cell_count,
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                    )
                )
            return scenes


class MemCellStore:
    """Armazena MemCells e executa busca híbrida BM25 + Semântica via Reciprocal Rank Fusion (RRF)."""

    async def save(self, cell: MemCell) -> MemCell:
        if not cell.embedding:
            cell.embedding = get_embedding(cell.searchable_text)
        async with AsyncSessionLocal() as db:
            row = MemoryCellRow(
                id=cell.id,
                user_id=cell.user_id,
                session_id=cell.session_id,
                episode=cell.episode,
                searchable_text=cell.searchable_text,
                facts=[f.model_dump(mode="json") for f in cell.facts],
                foresights=[fs.model_dump(mode="json") for fs in cell.foresights],
                embedding=cell.embedding,
                message_count=cell.message_count,
            )
            db.add(row)
            await db.commit()
        return cell

    def _row_to_cell(self, row: MemoryCellRow) -> MemCell:
        now = datetime.now(timezone.utc)
        valid_foresights: list[ForesightItem] = []
        for fs_raw in (row.foresights or []):
            fs = ForesightItem(**fs_raw)
            v_from = fs.valid_from
            v_until = fs.valid_until
            if v_from and v_from.tzinfo is None:
                v_from = v_from.replace(tzinfo=timezone.utc)
            if v_until and v_until.tzinfo is None:
                v_until = v_until.replace(tzinfo=timezone.utc)
            if v_from and now < v_from:
                continue
            if v_until and now > v_until:
                continue
            valid_foresights.append(fs)

        return MemCell(
            id=row.id,
            user_id=row.user_id,
            session_id=row.session_id,
            episode=row.episode,
            searchable_text=row.searchable_text,
            facts=[FactItem(**f) for f in (row.facts or [])],
            foresights=valid_foresights,
            embedding=row.embedding,
            message_count=row.message_count,
            created_at=row.created_at,
        )

    async def list_by_user(self, user_id: str, limit: int = 20) -> list[MemCell]:
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(MemoryCellRow)
                .where(MemoryCellRow.user_id == user_id)
                .order_by(MemoryCellRow.created_at.desc())
                .limit(limit)
            )
            rows = res.scalars().all()
            return [self._row_to_cell(r) for r in rows]

    async def search(self, user_id: str, query: str, top_k: int = 4) -> list[MemCell]:
        """Busca híbrida BM25/Lexical + Cosine Similarity via Reciprocal Rank Fusion (RRF, k=60)."""
        cells = await self.list_by_user(user_id, limit=50)
        if not cells:
            return []

        q_vec = get_embedding(query)
        q_tokens = {t.lower() for t in query.split() if len(t) > 2}

        # Ranking Vetorial
        vec_ranked = sorted(
            cells,
            key=lambda c: cosine_similarity(q_vec, c.embedding or []),
            reverse=True,
        )
        # Ranking Lexical / BM25 simplificado
        def _lex_score(c: MemCell) -> float:
            text_low = c.searchable_text.lower()
            return sum(1.0 for tok in q_tokens if tok in text_low)

        lex_ranked = sorted(cells, key=_lex_score, reverse=True)

        k_rrf = 60
        rrf_scores: dict[str, float] = {}
        cell_map: dict[str, MemCell] = {c.id: c for c in cells}

        for rank_idx, c in enumerate(vec_ranked):
            rrf_scores[c.id] = rrf_scores.get(c.id, 0.0) + 1.0 / (k_rrf + rank_idx + 1)
        for rank_idx, c in enumerate(lex_ranked):
            rrf_scores[c.id] = rrf_scores.get(c.id, 0.0) + 1.0 / (k_rrf + rank_idx + 1)

        top_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)[:top_k]
        return [cell_map[cid] for cid in top_ids]


class UserProfileStore:
    """Mantém o UserProfile vivo e versionado do Arquiteto/Engenheiro."""

    async def get(self, user_id: str) -> Optional[UserProfile]:
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(UserProfileRow).where(UserProfileRow.user_id == user_id)
            )
            row = res.scalar_one_or_none()
            if not row:
                return None
            return UserProfile(
                user_id=row.user_id,
                explicit_facts=[ProfileExplicitFact(**f) for f in (row.explicit_facts or [])],
                patterns=[ProfileImplicitPattern(**p) for p in (row.patterns or [])],
                summary=row.summary or "",
                updated_at=row.updated_at,
            )

    async def save(
        self,
        profile: UserProfile,
        trigger_scene_id: Optional[str] = None,
    ) -> UserProfile:
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(UserProfileRow).where(UserProfileRow.user_id == profile.user_id)
            )
            row = res.scalar_one_or_none()
            exp_json = [f.model_dump(mode="json") for f in profile.explicit_facts]
            pat_json = [p.model_dump(mode="json") for p in profile.patterns]

            if row is None:
                row = UserProfileRow(
                    user_id=profile.user_id,
                    explicit_facts=exp_json,
                    patterns=pat_json,
                    summary=profile.summary,
                )
                db.add(row)
            else:
                row.explicit_facts = exp_json
                row.patterns = pat_json
                row.summary = profile.summary
                row.updated_at = datetime.now(timezone.utc)

            version_row = UserProfileVersionRow(
                user_id=profile.user_id,
                explicit_facts=exp_json,
                patterns=pat_json,
                summary=profile.summary,
                trigger_scene_id=trigger_scene_id,
            )
            db.add(version_row)
            await db.commit()
            return profile


episode_buffer_store = EpisodeBufferStore()
memcell_store = MemCellStore()
memscene_store = MemSceneStore()
user_profile_store = UserProfileStore()

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, model_validator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class FactItem(BaseModel):
    category: Literal["decision", "preference", "alias", "task_pattern", "impediment", "context"] = "decision"
    fact: str

    @model_validator(mode="before")
    @classmethod
    def _normalize_fact(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)
            cat_map = {
                "preferencia": "preference",
                "preferência": "preference",
                "decisao": "decision",
                "decisão": "decision",
                "padrao": "task_pattern",
                "padrão": "task_pattern",
                "impedimento": "impediment",
                "contexto": "context",
            }
            raw_cat = str(d.get("category", "decision")).lower().strip()
            allowed = {"decision", "preference", "alias", "task_pattern", "impediment", "context"}
            d["category"] = cat_map.get(raw_cat, raw_cat if raw_cat in allowed else "decision")
            return d
        return data


class ForesightItem(BaseModel):
    text: str
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_foresight(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)
            if "text" not in d:
                d["text"] = str(d.get("description") or d.get("content") or "Previsão arquitetônica")
            return d
        return data


class MemCell(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    session_id: str = "default_session"
    episode: str
    searchable_text: str = ""
    facts: list[FactItem] = Field(default_factory=list)
    foresights: list[ForesightItem] = Field(default_factory=list)
    embedding: Optional[list[float]] = None
    created_at: datetime = Field(default_factory=_utc_now)
    message_count: int = 0

    @model_validator(mode="after")
    def _populate_searchable_text(self) -> "MemCell":
        if not self.searchable_text:
            parts = [self.episode] + [f.fact for f in self.facts] + [fs.text for fs in self.foresights]
            self.searchable_text = " | ".join(p for p in parts if p)
        return self


class MemScene(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    topic: str
    summary: str
    cell_ids: list[str] = Field(default_factory=list)
    centroid_embedding: Optional[list[float]] = None
    cell_count: int = 1
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class MemSceneVersion(BaseModel):
    id: str = Field(default_factory=_uuid)
    scene_id: str
    user_id: str
    topic: str
    summary: str
    trigger_cell_id: Optional[str] = None
    cell_count_at_version: int = 1
    created_at: datetime = Field(default_factory=_utc_now)


class ProfileExplicitFact(BaseModel):
    category: Literal["role", "team", "rule", "tool"] = "role"
    value: str

    @model_validator(mode="before")
    @classmethod
    def _normalize_explicit(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)
            raw_cat = str(d.get("category", "rule")).lower().strip()
            allowed = {"role", "team", "rule", "tool"}
            d["category"] = raw_cat if raw_cat in allowed else "rule"
            return d
        return data


class ProfileImplicitPattern(BaseModel):
    category: Literal["preference", "style", "habit"] = "preference"
    observation: str

    @model_validator(mode="before")
    @classmethod
    def _normalize_implicit(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)
            if "observation" not in d:
                d["observation"] = str(d.get("pattern") or d.get("evidence") or "Padrão observado")
            raw_cat = str(d.get("category", "preference")).lower().strip()
            allowed = {"preference", "style", "habit"}
            d["category"] = raw_cat if raw_cat in allowed else "preference"
            return d
        return data


class UserProfile(BaseModel):
    user_id: str
    explicit_facts: list[ProfileExplicitFact] = Field(default_factory=list)
    patterns: list[ProfileImplicitPattern] = Field(default_factory=list)
    summary: str = ""
    updated_at: datetime = Field(default_factory=_utc_now)


class UserProfileVersion(BaseModel):
    id: str = Field(default_factory=_uuid)
    user_id: str
    explicit_facts: list[ProfileExplicitFact] = Field(default_factory=list)
    patterns: list[ProfileImplicitPattern] = Field(default_factory=list)
    summary: str = ""
    trigger_scene_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)


class BoundaryDecision(BaseModel):
    should_close_episode: bool
    reason: str


class ExtractedMemCell(BaseModel):
    episode: str
    facts: list[FactItem] = Field(default_factory=list)
    foresights: list[ForesightItem] = Field(default_factory=list)


class ConsolidatedScene(BaseModel):
    topic: str
    updated_summary: str


class ConsolidatedProfile(BaseModel):
    explicit_facts: list[ProfileExplicitFact] = Field(default_factory=list)
    patterns: list[ProfileImplicitPattern] = Field(default_factory=list)
    summary: str

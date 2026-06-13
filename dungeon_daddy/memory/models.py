from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    memory_id: str
    campaign_id: str
    type: str
    title: str
    summary: str = ""
    status: Literal["draft", "approved", "rejected", "archived"] = "draft"
    importance: int = 5
    markdown_path: str | None = None
    checksum: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class MemoryTag(BaseModel):
    memory_id: str
    tag: str


class MemoryLink(BaseModel):
    from_id: str
    to_id: str
    link_type: str


class DomainEvent(BaseModel):
    event_id: str
    campaign_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ContextBundle(BaseModel):
    bundle_id: str
    campaign_id: str
    scene_id: str | None = None
    mode: Literal["run_scene", "recap", "room_revisit", "fallout_resolution"]
    scene_brief: dict[str, Any] = Field(default_factory=dict)
    mechanical_state: dict[str, Any] = Field(default_factory=dict)
    active_fallout: list[dict[str, Any]] = Field(default_factory=list)
    open_clocks: list[dict[str, Any]] = Field(default_factory=list)
    must_remember: list[str] = Field(default_factory=list)
    memory_cards: list[dict[str, Any]] = Field(default_factory=list)
    faction_reputations: list[dict[str, Any]] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)

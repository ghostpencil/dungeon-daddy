from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


class EntityRow(TypedDict):
    """One normalized ``MemoryRepository.search_entities`` result row (spec
    §7/§7.1) — the single definition of the shape its readers consume."""

    entity_type: str
    id: str
    slug: str | None
    display_name: str | None
    room_id: str | None
    status: str | None
    tags: list[str]
    snippet: str


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
        default_factory=lambda: datetime.now(UTC)
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
    related_lore: list[dict[str, Any]] = Field(default_factory=list)
    faction_reputations: list[dict[str, Any]] = Field(default_factory=list)
    inventory: dict[str, Any] = Field(default_factory=dict)
    current_room: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

_REPUTATION_TIERS = ["hostile", "cold", "neutral", "warm", "allied"]


class FactionManifest(BaseModel):
    slug: str
    display_name: str
    concept: str | None = None
    goal: str | None = None
    status: Literal["active", "inactive", "dissolved"] = "active"
    reputation: Literal["hostile", "cold", "neutral", "warm", "allied"] = "neutral"
    tier: int = 0
    tags: list[str] = Field(default_factory=list)

    @field_validator("tier")
    @classmethod
    def tier_in_range(cls, v: int) -> int:
        if not 0 <= v <= 4:
            raise ValueError("tier must be 0–4")
        return v


class ActorManifest(BaseModel):
    slug: str
    display_name: str
    actor_type: Literal["pc", "npc", "monster", "dungeon", "dungeon_presence"]
    concept: str | None = None
    status: Literal["active", "inactive", "dead", "absorbed", "lost"] = "active"
    action_ratings: dict[str, int] = Field(default_factory=dict)
    stress_tracks: list[dict] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ClockManifest(BaseModel):
    slug: str
    label: str
    segments: int
    filled: int = 0
    status: Literal["active", "completed", "abandoned"] = "active"
    clock_level: Literal["room", "level", "dungeon", "quest", "character", "faction"] = "dungeon"
    category: str | None = None
    scope_room_id: str | None = None
    level_id: str | None = None
    action_tags: list[str] = Field(default_factory=list)
    visible_to_player: bool = True
    stakes: str | None = None
    completion_effect: str | None = None

    @model_validator(mode="after")
    def filled_within_segments(self) -> "ClockManifest":
        if self.filled > self.segments:
            raise ValueError("filled cannot exceed segments")
        return self


class CampaignManifest(BaseModel):
    slug: str
    title: str
    premise: str | None = None
    dungeon_slug: str
    starting_level: str | None = None
    player_side: list[str] = Field(default_factory=list)
    world_actors: list[ActorManifest] = Field(default_factory=list)
    factions: list[FactionManifest] = Field(default_factory=list)
    clocks: list[ClockManifest] = Field(default_factory=list)
    memory_seeds: list[str] = Field(default_factory=list)
    room_threats: list[dict] = Field(default_factory=list)

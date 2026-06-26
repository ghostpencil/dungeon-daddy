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
    playbook_slug: str | None = None


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


class ItemFeatureManifest(BaseModel):
    feature_type: Literal["new_action", "rating_modifier"]
    action_key: str
    modifier: int | None = None


class ItemManifest(BaseModel):
    slug: str
    display_name: str
    item_type: Literal["class_kit", "dungeon_item", "equipped_gear"]
    description: str
    owner_slug: str | None = None
    room_id: str | None = None
    level_id: str | None = None
    charges_max: int | None = None
    is_equipped: bool = False
    features: list[ItemFeatureManifest] = Field(default_factory=list)


class ObjectTransitionManifest(BaseModel):
    from_state: str
    to_state: str
    trigger: str
    requires_item_slug: str | None = None
    spawns_item_slug: str | None = None
    advances_clock_slug: str | None = None


class RoomObjectManifest(BaseModel):
    slug: str
    display_name: str
    room_id: str
    level_id: str
    archetype: Literal["container", "door", "mechanism", "structure", "trap", "lore_fixture", "resource"]
    description: str
    initial_state: str
    transitions: list[ObjectTransitionManifest] = Field(default_factory=list)


class RoomExitSeed(BaseModel):
    from_room_id: str
    to_room_id: str
    label: str
    exit_type: str = "door"
    connector_type: str | None = None
    to_level_id: str | None = None
    status: str = "open"
    requires_item_slug: str | None = None
    requires_object_id: str | None = None
    requires_object_state: str | None = None
    requires_clock_slug: str | None = None
    requires_clock_min_filled: int | None = None
    requires_memory_slug: str | None = None


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
    items: list[ItemManifest] = Field(default_factory=list)
    room_objects: list[RoomObjectManifest] = Field(default_factory=list)
    room_exits: list[RoomExitSeed] = Field(default_factory=list)
    dungeon_voice: str | None = None
    dungeon_knowledge: list[str] = Field(default_factory=list)
    dungeon_corruption_clock: bool = False

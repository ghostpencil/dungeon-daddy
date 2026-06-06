from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class StressTrack(BaseModel):
    track_key: str
    capacity: int = 4
    filled: int = 0

    @field_validator("filled")
    @classmethod
    def filled_not_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("filled cannot be negative")
        return v

    @model_validator(mode="after")
    def filled_within_capacity(self) -> "StressTrack":
        if self.filled > self.capacity:
            raise ValueError("filled cannot exceed capacity")
        return self


class ClockState(BaseModel):
    clock_id: str
    campaign_id: str
    label: str
    segments: int
    filled: int = 0
    status: Literal["active", "completed", "abandoned"] = "active"
    scope_room_id: str | None = None
    action_tags: list[str] = Field(default_factory=list)
    clock_level: Literal["room", "level", "dungeon", "quest", "character", "faction"] = "dungeon"
    category: str | None = None
    level_id: str | None = None
    owner_actor_id: str | None = None
    stakes: str | None = None
    completion_effect: str | None = None
    visible_to_player: bool = True

    @model_validator(mode="after")
    def filled_within_segments(self) -> "ClockState":
        if self.filled > self.segments:
            raise ValueError("filled cannot exceed segments")
        return self


class ActionRating(BaseModel):
    actor_id: str
    action_key: str
    rating: int = 0

    @field_validator("rating")
    @classmethod
    def rating_in_range(cls, v: int) -> int:
        if not (0 <= v <= 3):
            raise ValueError("rating must be 0–3")
        return v


class ActorState(BaseModel):
    actor_id: str
    campaign_id: str
    actor_type: Literal["pc", "npc", "monster", "dungeon", "faction", "dungeon_presence"]
    slug: str
    display_name: str
    concept: str | None = None
    status: Literal["active", "inactive", "dead", "absorbed", "lost"] = "active"
    markdown_path: str | None = None
    actions: dict[str, int] = Field(default_factory=dict)
    stress: dict[str, StressTrack] = Field(default_factory=dict)
    abilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class Ability(BaseModel):
    actor_id: str
    ability_key: str
    value: str | None = None


class ActionRequest(BaseModel):
    campaign_id: str
    scene_id: str | None = None
    actor_id: str
    action_key: str
    dice_pool: int = 1
    momentum_spend: int = 0
    push_yourself: bool = False


class ActionResolution(BaseModel):
    resolution_id: str
    campaign_id: str
    actor_id: str
    action_key: str
    dice_rolled: list[int]
    outcome: Literal["critical", "full", "partial", "miss"]
    stress_cost: int = 0
    notes: str | None = None


class ReactionClockLine(BaseModel):
    clock_id: str
    label: str
    ticks: int
    new_filled: int
    new_status: str
    reason: str


class ReactionStressLine(BaseModel):
    actor_id: str
    display_name: str
    track_key: str
    amount: int
    new_filled: int
    triggered_fallout: bool = False
    reason: str


class WorldReaction(BaseModel):
    reaction_id: str
    campaign_id: str
    source_resolution_id: str
    outcome: Literal["critical", "full", "partial", "miss"]
    clock_lines: list["ReactionClockLine"] = Field(default_factory=list)
    stress_lines: list["ReactionStressLine"] = Field(default_factory=list)
    summary_lines: list[str] = Field(default_factory=list)


class FalloutRecord(BaseModel):
    fallout_id: str
    campaign_id: str
    actor_id: str
    source_action_id: str | None = None
    track_key: Literal["body", "composure", "bonds", "weird"]
    severity: Literal["minor", "moderate", "severe"]
    title: str
    summary: str
    status: Literal["active", "resolved", "escalated"] = "active"
    mechanical_hooks: dict[str, Any] = Field(default_factory=dict)
    markdown_path: str | None = None

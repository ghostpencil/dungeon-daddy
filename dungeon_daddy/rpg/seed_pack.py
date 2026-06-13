from __future__ import annotations

import dataclasses
import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from dungeon_daddy.memory.repository import MemoryRepository

_ACTOR_NS = uuid.UUID("7a3f1c2e-4b5d-5e6f-8a9b-0c1d2e3f4a5b")
_CLOCK_NS = uuid.UUID("1b2c3d4e-5f6a-5b7c-8d9e-0f1a2b3c4d5e")
_FACTION_NS = uuid.UUID("9f8e7d6c-5b4a-5392-8172-06152d3c4b5a")


def derive_actor_id(campaign_slug: str, actor_slug: str) -> str:
    return str(uuid.uuid5(_ACTOR_NS, f"{campaign_slug}:{actor_slug}"))


def derive_clock_id(campaign_slug: str, clock_slug: str) -> str:
    return str(uuid.uuid5(_CLOCK_NS, f"{campaign_slug}:{clock_slug}"))


def derive_faction_id(campaign_slug: str, faction_slug: str) -> str:
    return str(uuid.uuid5(_FACTION_NS, f"{campaign_slug}:{faction_slug}"))


class SeedFaction(BaseModel):
    slug: str
    display_name: str
    concept: str | None = None
    goal: str | None = None
    status: Literal["active", "inactive", "dissolved"] = "active"
    reputation: Literal["hostile", "cold", "neutral", "warm", "allied"] = "neutral"
    tier: int = 0
    tags: list[str] = Field(default_factory=list)


class SeedActor(BaseModel):
    slug: str
    display_name: str
    actor_type: Literal["pc", "npc", "monster", "faction", "dungeon_presence"]
    concept: str | None = None
    instinct: str | None = None
    actions: dict[str, int] = Field(default_factory=dict)
    stress_tracks: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    threat_tags: list[str] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)


class SeedClock(BaseModel):
    slug: str
    label: str
    segments: int
    category: str
    notes: str | None = None
    scope_room_id: str | None = None
    action_tags: list[str] = Field(default_factory=list)
    clock_level: Literal["room", "level", "dungeon", "quest", "character", "faction"] = "dungeon"
    level_id: str | None = None
    owner_actor_slug: str | None = None
    stakes: str | None = None
    completion_effect: str | None = None
    visible_to_player: bool = True


class SeedRoomThreat(BaseModel):
    location_slug: str
    trigger_tags: list[str] = Field(default_factory=list)
    related_actor_slugs: list[str] = Field(default_factory=list)
    related_clock_slugs: list[str] = Field(default_factory=list)
    possible_reactions: list[str] = Field(default_factory=list)
    notes: str | None = None


class SeedMemory(BaseModel):
    title: str
    summary: str
    type: str
    importance: int = 5
    tags: list[str] = Field(default_factory=list)


class SeedPlayerSide(BaseModel):
    label: str
    actors: list[SeedActor] = Field(default_factory=list)


class SeedDungeonSide(BaseModel):
    actors: list[SeedActor] = Field(default_factory=list)


class SeedPack(BaseModel):
    campaign_slug: str
    player_side: SeedPlayerSide
    dungeon_side: SeedDungeonSide
    clocks: list[SeedClock] = Field(default_factory=list)
    memories: list[SeedMemory] = Field(default_factory=list)
    room_threats: list[SeedRoomThreat] = Field(default_factory=list)
    factions: list[SeedFaction] = Field(default_factory=list)


def load_seed_pack(path: Path) -> SeedPack:
    data = json.loads(path.read_text(encoding="utf-8"))
    return SeedPack.model_validate(data)


_MEMORY_NS = uuid.UUID("3c4d5e6f-7a8b-5c9d-0e1f-2a3b4c5d6e7f")


def derive_memory_id(campaign_slug: str, memory_title: str) -> str:
    return str(uuid.uuid5(_MEMORY_NS, f"{campaign_slug}:{memory_title}"))


@dataclasses.dataclass
class ApplyResult:
    actors_applied: int
    clocks_applied: int
    memories_applied: int
    factions_applied: int = 0


def apply_seed_pack(
    pack: SeedPack,
    campaign_id: str,
    repo: "MemoryRepository",
    migrations_dir: Path,
) -> ApplyResult:
    from dungeon_daddy.memory.repository import MemoryRepository as _Repo  # noqa: F401

    repo.initialize_schema(migrations_dir)

    all_actors = pack.player_side.actors + pack.dungeon_side.actors
    for actor in all_actors:
        actor_id = derive_actor_id(pack.campaign_slug, actor.slug)
        repo.save_actor(actor_id, campaign_id, actor.actor_type, actor.slug, actor.display_name)
        for action_key, rating in actor.actions.items():
            repo.save_actor_action_rating(actor_id, action_key, rating)
        for track_key in actor.stress_tracks:
            repo.save_actor_stress_track(actor_id, track_key, capacity=6, filled=0)

    for clock in pack.clocks:
        clock_id = derive_clock_id(pack.campaign_slug, clock.slug)
        owner_actor_id = (
            derive_actor_id(pack.campaign_slug, clock.owner_actor_slug)
            if clock.owner_actor_slug
            else None
        )
        repo.save_clock(
            clock_id, campaign_id, clock.label, clock.segments,
            scope_room_id=clock.scope_room_id,
            action_tags=clock.action_tags,
            clock_level=clock.clock_level,
            category=clock.category,
            level_id=clock.level_id,
            owner_actor_id=owner_actor_id,
            stakes=clock.stakes,
            completion_effect=clock.completion_effect,
            visible_to_player=clock.visible_to_player,
        )

    for memory in pack.memories:
        memory_id = derive_memory_id(pack.campaign_slug, memory.title)
        repo.save_memory_entry(
            memory_id, campaign_id, memory.type, memory.title, memory.summary,
            importance=memory.importance, status="approved",
        )
        for tag in memory.tags:
            repo.add_memory_tag(memory_id, tag)

    for threat in pack.room_threats:
        for clock_slug in threat.related_clock_slugs:
            clock_id = derive_clock_id(pack.campaign_slug, clock_slug)
            repo.update_clock_scope(
                clock_id,
                scope_room_id=threat.location_slug,
                action_tags=threat.trigger_tags,
            )

    existing_faction_ids = {f["faction_id"] for f in repo.get_factions(campaign_id)}
    factions_applied = 0
    for faction in pack.factions:
        faction_id = derive_faction_id(pack.campaign_slug, faction.slug)
        if faction_id not in existing_faction_ids:
            from dungeon_daddy.rpg.models import FactionState
            repo.save_faction(FactionState(
                faction_id=faction_id,
                campaign_id=campaign_id,
                slug=faction.slug,
                display_name=faction.display_name,
                concept=faction.concept,
                goal=faction.goal,
                status=faction.status,
                reputation=faction.reputation,
                tier=faction.tier,
                tags=faction.tags,
            ))
            factions_applied += 1

    return ApplyResult(
        actors_applied=len(all_actors),
        clocks_applied=len(pack.clocks),
        memories_applied=len(pack.memories),
        factions_applied=factions_applied,
    )

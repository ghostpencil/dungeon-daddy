from __future__ import annotations

import dataclasses
import json
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, model_validator

from dungeon_daddy.memory.tags import validate_tag

if TYPE_CHECKING:
    from dungeon_daddy.data.models import Level, Room
    from dungeon_daddy.memory.repository import MemoryRepository
    from dungeon_daddy.rpg.models import RoomState


def _append_trait_tags(existing: list[str], raws: Iterable[str]) -> list[str]:
    """Fold descriptive raw tokens into ``existing`` as validated ``trait:<slug>``
    tags, de-duplicated (T5, A3 findings F2/F3). Shared by the ``SeedActor``
    ``threat_tags`` fold and the room-threat ``trigger_tags`` routing so both
    validate (rejects a malformed / empty token) and dedup identically.
    """
    tags = list(existing)
    for raw in raws:
        trait = validate_tag(f"trait:{raw}")
        if trait not in tags:
            tags.append(trait)
    return tags

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
    relationships: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _fold_threat_tags(cls, data: object) -> object:
        # T5 (Phase 51.8): the legacy `threat_tags` vocabulary held descriptive
        # actor traits (boss/construct/undead). Absorb them into `tags` as
        # `trait:<slug>` and drop the field. Applies to any legacy seed pack.
        if isinstance(data, dict) and data.get("threat_tags"):
            tags = _append_trait_tags(list(data.get("tags") or []), data["threat_tags"])
            data = {k: v for k, v in data.items() if k != "threat_tags"}
            data["tags"] = tags
        return data


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


def validate_seed_room_ids(pack: SeedPack, valid_room_ids: set[str]) -> None:
    """Fail loudly (§4.3) if any room reference in the pack does not exactly match
    a room id in the dungeon model. Catches `r1`-vs-`R1` / zero-padding mismatches
    that would otherwise silently never scope. Checks `SeedClock.scope_room_id` and
    `SeedRoomThreat.location_slug`; `None` scopes are skipped.
    """
    bad: list[str] = []
    for clock in pack.clocks:
        if clock.scope_room_id is not None and clock.scope_room_id not in valid_room_ids:
            bad.append(f"clock {clock.slug!r} scope_room_id={clock.scope_room_id!r}")
    for threat in pack.room_threats:
        if threat.location_slug not in valid_room_ids:
            bad.append(f"room_threat location_slug={threat.location_slug!r}")
    if bad:
        raise ValueError(
            "Seed references room ids absent from the dungeon model: "
            + "; ".join(bad)
            + f" (known room ids: {sorted(valid_room_ids)})"
        )


_MEMORY_NS = uuid.UUID("3c4d5e6f-7a8b-5c9d-0e1f-2a3b4c5d6e7f")


def derive_memory_id(campaign_slug: str, memory_title: str) -> str:
    return str(uuid.uuid5(_MEMORY_NS, f"{campaign_slug}:{memory_title}"))


def _room_slug(room: Room) -> str:
    """Slugify a room's name for its ``slug`` field, falling back to the grid
    id when the room has no name."""
    slug = room.name.lower().replace(" ", "-").replace("'", "").replace(",", "")
    return slug or room.id


def build_room_states(
    levels: list[Level],
    campaign_id: str,
    *,
    quest_roles: dict[str, str] | None = None,
    room_tags: dict[str, list[str]] | None = None,
) -> list[RoomState]:
    """Project a dungeon's rooms into first-class :class:`RoomState` records
    (Phase 51.8 Slice B0, spec §7.1).

    Geometry stays in the dungeon JSON; this builds only the campaign-facing
    searchable fields. ``level_id`` uses the ``level:<n>`` form (matching
    ``room_objects``/``items``); ``summary`` is sourced from ``Room.note``.

    ``quest_role`` defaults to the dungeon room's ``main_loop_role`` (the room's
    role in the quest layout — ``entry``/``goal``/``obstacle``/…), and an entry
    in ``quest_roles`` (``room_id`` → role) overrides it (owner ruling
    2026-07-11: hybrid — derive from ``main_loop_role``, authored override wins).
    ``tags`` are authored: ``room_tags`` maps ``room_id`` → its namespaced tags
    (each validated via :func:`validate_tag`); rooms carry no tags in the
    dungeon JSON.
    """
    from dungeon_daddy.rpg.models import RoomState

    quest_roles = quest_roles or {}
    room_tags = room_tags or {}

    # Guard (spec §7.1): an override keyed to a room-id absent from the dungeon
    # model is a silent typo that would never apply — fail loudly instead.
    known_room_ids = {room.id for level in levels for room in level.rooms}
    unknown = (set(quest_roles) | set(room_tags)) - known_room_ids
    if unknown:
        raise ValueError(
            "Room override references room ids absent from the dungeon model: "
            f"{sorted(unknown)} (known room ids: {sorted(known_room_ids)})"
        )

    rooms: list[RoomState] = []
    for level in levels:
        level_id = f"level:{level.id}"
        for room in level.rooms:
            tags = [validate_tag(t) for t in room_tags.get(room.id, [])]
            rooms.append(RoomState(
                room_id=room.id,
                campaign_id=campaign_id,
                level_id=level_id,
                slug=_room_slug(room),
                display_name=room.name,
                room_type=room.type,
                summary=room.note,
                quest_role=quest_roles.get(room.id, room.main_loop_role),
                tags=tags,
            ))
    return rooms


def enrich_room_tags(
    repo: MemoryRepository,
    campaign_id: str,
    room_tags: dict[str, list[str]],
) -> int:
    """Merge authored lore tags into already-seeded room records (idempotent;
    Slice B0 §7.1).

    Reads each existing room, adds the validated ``room_tags`` (de-duplicated,
    order-preserving), and re-saves — preserving the base seed's ``summary`` and
    ``quest_role``. A room the seed path has not planted yet is skipped with a
    warning (the seed is the source of the base record). Returns the number of
    rooms enriched. Shared by the Crucible populate scripts so the merge/skip
    semantics live in one place.
    """
    from dungeon_daddy.rpg.models import RoomState

    enriched = 0
    for room_id, tags in room_tags.items():
        row = repo.get_room(campaign_id, room_id)
        if row is None:
            print(f"  ⚠ room {room_id} not seeded — run the seed first; skipping tags")
            continue
        validated = [validate_tag(t) for t in tags]
        merged = list(dict.fromkeys([*row["tags"], *validated]))
        repo.save_room(RoomState(**row).model_copy(update={"tags": merged}))
        enriched += 1
    return enriched


@dataclasses.dataclass
class ApplyResult:
    actors_applied: int
    clocks_applied: int
    memories_applied: int
    factions_applied: int = 0
    rooms_applied: int = 0


def apply_seed_pack(
    pack: SeedPack,
    campaign_id: str,
    repo: MemoryRepository,
    migrations_dir: Path,
    valid_room_ids: set[str] | None = None,
    levels: list[Level] | None = None,
) -> ApplyResult:
    from dungeon_daddy.memory.repository import MemoryRepository as _Repo  # noqa: F401

    if valid_room_ids is not None:
        validate_seed_room_ids(pack, valid_room_ids)

    repo.initialize_schema(migrations_dir)

    rooms_applied = 0
    if levels is not None:
        for room_state in build_room_states(levels, campaign_id):
            repo.save_room(room_state)
            rooms_applied += 1

    all_actors = pack.player_side.actors + pack.dungeon_side.actors
    for actor in all_actors:
        actor_id = derive_actor_id(pack.campaign_slug, actor.slug)
        repo.save_actor(
            actor_id, campaign_id, actor.actor_type, actor.slug, actor.display_name,
            tags=actor.tags,
        )
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
        # T5 (Phase 51.8): trigger_tags are descriptive trigger conditions, not a
        # verb gate. Route them to the clock's `tags` as validated, de-duplicated
        # trait:<slug> tags (F2/F3). Leave the clock's own action_tags untouched
        # (F5) — this loop only scopes + tags the co-referenced clock.
        trait_tags = _append_trait_tags([], threat.trigger_tags)
        for clock_slug in threat.related_clock_slugs:
            clock_id = derive_clock_id(pack.campaign_slug, clock_slug)
            repo.update_clock_scope(
                clock_id,
                scope_room_id=threat.location_slug,
                # Only set tags when this threat actually carries trigger_tags —
                # an empty trigger list must not blank a co-referenced clock's
                # existing tags (mirrors the action_tags leave-untouched rule).
                tags=trait_tags or None,
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
        rooms_applied=rooms_applied,
    )

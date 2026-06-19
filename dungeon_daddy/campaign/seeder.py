"""Campaign manifest seeder — applies a CampaignManifest to a MemoryRepository."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, FactionManifest, ItemManifest, RoomObjectManifest, RoomExitSeed
from dungeon_daddy.memory.repository import MemoryRepository

if TYPE_CHECKING:
    from dungeon_daddy.data.models import Dungeon


@dataclass
class SeedResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)

    def print_summary(self) -> None:
        print(f"Created:  {self.created}")
        print(f"Updated:  {self.updated}")
        print(f"Skipped:  {self.skipped}")
        for w in self.warnings:
            print(f"  WARNING: {w}")


def seed_from_manifest(
    manifest: CampaignManifest,
    repo: MemoryRepository,
    campaign_id: str,
    dry_run: bool = False,
    force: bool = False,
    dungeon: "Dungeon | None" = None,
) -> SeedResult:
    """Apply a CampaignManifest to a campaign DB.

    Idempotent — existing records are skipped unless force=True.
    dry_run=True returns counts without writing.
    If dungeon is provided, exits are derived from its connections and overlaid
    with manifest.room_exits overrides. Without dungeon, manifest.room_exits
    are seeded directly.
    """
    result = SeedResult()
    slug = manifest.slug

    for actor in manifest.world_actors:
        _seed_actor(actor, repo, campaign_id, slug, result, dry_run=dry_run, force=force)

    for clock in manifest.clocks:
        _seed_clock(clock, repo, campaign_id, slug, result, dry_run=dry_run, force=force)

    for i, memory_text in enumerate(manifest.memory_seeds):
        _seed_memory(memory_text, i, repo, campaign_id, slug, result, dry_run=dry_run, force=force)

    for faction in manifest.factions:
        _seed_faction(faction, repo, campaign_id, slug, result, dry_run=dry_run)

    for item in manifest.items:
        _seed_item(item, repo, campaign_id, slug, result, dry_run=dry_run, force=force)

    for room_object in manifest.room_objects:
        _seed_room_object(room_object, repo, campaign_id, slug, result, dry_run=dry_run, force=force)

    _seed_exits(manifest, repo, campaign_id, slug, result, dry_run=dry_run, force=force, dungeon=dungeon)

    return result


def _actor_id(campaign_slug: str, actor_slug: str) -> str:
    return f"actor:{campaign_slug}:{actor_slug}"


def _clock_id(campaign_slug: str, clock_slug: str) -> str:
    return f"clock:{campaign_slug}:{clock_slug}"


def _memory_id(campaign_slug: str, index: int) -> str:
    return f"memory:{campaign_slug}:seed-{index}"


def _faction_id(campaign_slug: str, faction_slug: str) -> str:
    return f"faction:{campaign_slug}:{faction_slug}"


def _seed_actor(
    actor: ActorManifest,
    repo: MemoryRepository,
    campaign_id: str,
    campaign_slug: str,
    result: SeedResult,
    dry_run: bool,
    force: bool,
) -> None:
    actor_id = _actor_id(campaign_slug, actor.slug)
    existing = repo.get_actor(actor_id)

    if dry_run:
        result.created += 1 if existing is None else 0
        result.skipped += 0 if existing is None else 1
        return

    if existing is None:
        repo.save_actor(actor_id, campaign_id, actor.actor_type, actor.slug, actor.display_name, actor.status)
        for action_key, rating in actor.action_ratings.items():
            repo.save_actor_action_rating(actor_id, action_key, rating)
        for track in actor.stress_tracks:
            if isinstance(track, dict):
                repo.save_actor_stress_track(
                    actor_id,
                    track.get("track_key", "body"),
                    capacity=track.get("capacity", 6),
                    filled=track.get("filled", 0),
                )
        result.created += 1
    elif force:
        repo.save_actor(actor_id, campaign_id, actor.actor_type, actor.slug, actor.display_name, actor.status)
        for action_key, rating in actor.action_ratings.items():
            repo.save_actor_action_rating(actor_id, action_key, rating)
        result.updated += 1
    else:
        result.skipped += 1


def _seed_clock(
    clock,
    repo: MemoryRepository,
    campaign_id: str,
    campaign_slug: str,
    result: SeedResult,
    dry_run: bool,
    force: bool,
) -> None:
    from dungeon_daddy.campaign.manifest import ClockManifest
    assert isinstance(clock, ClockManifest)
    clock_id = _clock_id(campaign_slug, clock.slug)
    existing_ids = {c["clock_id"] for c in repo.get_clocks(campaign_id)}

    if dry_run:
        result.created += 1 if clock_id not in existing_ids else 0
        result.skipped += 0 if clock_id not in existing_ids else 1
        return

    is_new = clock_id not in existing_ids
    if is_new or force:
        repo.save_clock(
            clock_id,
            campaign_id,
            clock.label,
            clock.segments,
            scope_room_id=clock.scope_room_id,
            action_tags=clock.action_tags,
            clock_level=clock.clock_level,
            category=clock.category,
            level_id=clock.level_id,
            stakes=clock.stakes,
            completion_effect=clock.completion_effect,
            visible_to_player=clock.visible_to_player,
        )
        result.created += 1 if is_new else 0
        result.updated += 0 if is_new else 1
    else:
        result.skipped += 1


def _seed_faction(
    faction: FactionManifest,
    repo: MemoryRepository,
    campaign_id: str,
    campaign_slug: str,
    result: SeedResult,
    dry_run: bool,
) -> None:
    from dungeon_daddy.rpg.models import FactionState
    fac_id = _faction_id(campaign_slug, faction.slug)
    existing_ids = {f["faction_id"] for f in repo.get_factions(campaign_id)}

    if dry_run:
        result.created += 1 if fac_id not in existing_ids else 0
        result.skipped += 0 if fac_id not in existing_ids else 1
        return

    if fac_id not in existing_ids:
        repo.save_faction(FactionState(
            faction_id=fac_id,
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
        result.created += 1
    else:
        result.skipped += 1


def _item_id(campaign_slug: str, item_slug: str) -> str:
    return f"item:{campaign_slug}:{item_slug}"


def _seed_item(
    item: ItemManifest,
    repo: MemoryRepository,
    campaign_id: str,
    campaign_slug: str,
    result: SeedResult,
    dry_run: bool,
    force: bool,
) -> None:
    from dungeon_daddy.rpg.models import Item, ItemFeature

    item_id = _item_id(campaign_slug, item.slug)
    existing_ids = {i["item_id"] for i in repo.get_items(campaign_id)}

    if dry_run:
        result.created += 1 if item_id not in existing_ids else 0
        result.skipped += 0 if item_id not in existing_ids else 1
        return

    owner_actor_id = (
        _actor_id(campaign_slug, item.owner_slug) if item.owner_slug else None
    )
    charges_current = item.charges_max if item.charges_max is not None else None
    features = [
        ItemFeature(
            feature_id=f"feat:{item_id}:{f.action_key}:{f.feature_type}",
            item_id=item_id,
            feature_type=f.feature_type,
            action_key=f.action_key,
            modifier=f.modifier,
        )
        for f in item.features
    ]
    room_id = None if owner_actor_id else item.room_id
    domain_item = Item(
        item_id=item_id,
        campaign_id=campaign_id,
        slug=item.slug,
        display_name=item.display_name,
        item_type=item.item_type,
        description=item.description,
        owner_actor_id=owner_actor_id,
        room_id=room_id,
        level_id=item.level_id,
        charges_max=item.charges_max,
        charges_current=charges_current,
        is_equipped=item.is_equipped,
        features=features,
    )

    if item_id not in existing_ids:
        repo.save_item(domain_item)
        result.created += 1
    elif force:
        repo.save_item(domain_item)
        result.updated += 1
    else:
        result.skipped += 1


def _object_id(campaign_slug: str, object_slug: str) -> str:
    return f"obj:{campaign_slug}:{object_slug}"


def _transition_id(campaign_slug: str, object_slug: str, index: int) -> str:
    return f"tr:{campaign_slug}:{object_slug}:{index}"


def _seed_room_object(
    room_object: RoomObjectManifest,
    repo: MemoryRepository,
    campaign_id: str,
    campaign_slug: str,
    result: SeedResult,
    dry_run: bool,
    force: bool,
) -> None:
    from dungeon_daddy.rpg.models import ObjectTransition, RoomObject

    obj_id = _object_id(campaign_slug, room_object.slug)
    existing = repo.get_room_object(obj_id)

    if dry_run:
        result.created += 1 if existing is None else 0
        result.skipped += 0 if existing is None else 1
        return

    if existing is not None and not force:
        result.skipped += 1
        return

    transitions = [
        ObjectTransition(
            transition_id=_transition_id(campaign_slug, room_object.slug, i),
            object_id=obj_id,
            from_state=t.from_state,
            to_state=t.to_state,
            trigger=t.trigger,
            requires_item_slug=t.requires_item_slug,
            spawns_item_slug=t.spawns_item_slug,
            advances_clock_slug=t.advances_clock_slug,
        )
        for i, t in enumerate(room_object.transitions)
    ]
    domain_obj = RoomObject(
        object_id=obj_id,
        campaign_id=campaign_id,
        room_id=room_object.room_id,
        level_id=room_object.level_id,
        slug=room_object.slug,
        display_name=room_object.display_name,
        archetype=room_object.archetype,
        description=room_object.description,
        current_state=room_object.initial_state,
        transitions=transitions,
    )
    repo.save_room_object(domain_obj)
    if existing is None:
        result.created += 1
    else:
        result.updated += 1


def _seed_memory(
    memory_text: str,
    index: int,
    repo: MemoryRepository,
    campaign_id: str,
    campaign_slug: str,
    result: SeedResult,
    dry_run: bool,
    force: bool,
) -> None:
    memory_id = _memory_id(campaign_slug, index)
    existing = repo.get_memory_entry(memory_id)

    if dry_run:
        result.created += 1 if existing is None else 0
        result.skipped += 0 if existing is None else 1
        return

    if existing is None:
        repo.save_memory_entry(
            memory_id,
            campaign_id,
            "event",
            memory_text[:80],
            memory_text,
            status="approved",
            importance=5,
        )
        result.created += 1
    elif force:
        repo.save_memory_entry(
            memory_id,
            campaign_id,
            "event",
            memory_text[:80],
            memory_text,
            status="approved",
            importance=5,
        )
        result.updated += 1
    else:
        result.skipped += 1


# ---------------------------------------------------------------------------
# Room Exits
# ---------------------------------------------------------------------------

_CONN_TYPE_TO_EXIT_TYPE: dict[str, str] = {
    "door": "door",
    "arch": "arch",
    "archway": "arch",
    "corridor": "passage",
    "passage": "passage",
    "tunnel": "tunnel",
    "stair": "stair",
    "stairs": "stair",
    "staircase": "stair",
    "stair_down": "stair",
    "stair_up": "stair",
    "shaft": "shaft",
    "gate": "gate",
}

_EXIT_TYPE_LABELS: dict[str, str] = {
    "door": "Door",
    "arch": "Archway",
    "passage": "Passage",
    "tunnel": "Tunnel",
    "stair": "Stairs",
    "shaft": "Shaft",
    "gate": "Gate",
    "hall": "Hall",
}

# Map a dungeon connection's layout_connection_role to a navigation exit status.
# Roles not listed here (e.g. critical_path, optional_branch) are ordinary open exits.
_CONN_ROLE_TO_STATUS: dict[str, str] = {
    "locked": "locked",
    "secret": "hidden",
}


def _status_for_role(layout_connection_role: str | None) -> str:
    if not layout_connection_role:
        return "open"
    return _CONN_ROLE_TO_STATUS.get(layout_connection_role.lower(), "open")


def _exit_id(campaign_slug: str, from_room: str, to_room: str) -> str:
    return f"exit:{campaign_slug}:{from_room}:{to_room}"


def _exit_type_for(conn_type: str) -> str:
    # Normalize known synonyms to canonical types; otherwise keep the source
    # type verbatim rather than collapsing everything unknown to "door"
    # (which mislabeled hall/hole connections as doors).
    key = conn_type.lower()
    return _CONN_TYPE_TO_EXIT_TYPE.get(key, key)


def _default_label(exit_type: str) -> str:
    return _EXIT_TYPE_LABELS.get(exit_type, exit_type.replace("_", " ").title())


def _seed_exits(
    manifest: CampaignManifest,
    repo: MemoryRepository,
    campaign_id: str,
    campaign_slug: str,
    result: SeedResult,
    dry_run: bool,
    force: bool,
    dungeon: "Dungeon | None",
) -> None:
    from dungeon_daddy.rpg.models import RoomExit

    # Build override lookup keyed by (from_room_id, to_room_id)
    overrides: dict[tuple[str, str], RoomExitSeed] = {
        (s.from_room_id, s.to_room_id): s for s in manifest.room_exits
    }

    exits_to_seed: list[RoomExit] = []

    if dungeon is not None:
        for level in dungeon.levels:
            level_id = f"level:{level.id}"
            for conn in level.connections:
                for from_room, to_room in [
                    (conn.from_room, conn.to_room),
                    (conn.to_room, conn.from_room),
                ]:
                    override = overrides.pop((from_room, to_room), None)
                    exit_type = _exit_type_for(
                        override.exit_type if override else conn.type
                    )
                    exits_to_seed.append(
                        RoomExit(
                            exit_id=_exit_id(campaign_slug, from_room, to_room),
                            campaign_id=campaign_id,
                            from_room_id=from_room,
                            to_room_id=to_room,
                            level_id=level_id,
                            label=override.label if override else _default_label(exit_type),
                            exit_type=exit_type,
                            connector_type=override.connector_type if override else None,
                            to_level_id=override.to_level_id if override else None,
                            status=override.status if override else _status_for_role(conn.layout_connection_role),
                            requires_item_slug=override.requires_item_slug if override else None,
                            requires_object_id=override.requires_object_id if override else None,
                            requires_object_state=override.requires_object_state if override else None,
                            requires_clock_slug=override.requires_clock_slug if override else None,
                            requires_clock_min_filled=override.requires_clock_min_filled if override else None,
                            requires_memory_slug=override.requires_memory_slug if override else None,
                        )
                    )

    # Any remaining overrides not matched to a connection are added directly
    for seed in overrides.values():
        exit_type = _exit_type_for(seed.exit_type)
        exits_to_seed.append(
            RoomExit(
                exit_id=_exit_id(campaign_slug, seed.from_room_id, seed.to_room_id),
                campaign_id=campaign_id,
                from_room_id=seed.from_room_id,
                to_room_id=seed.to_room_id,
                level_id="",
                label=seed.label,
                exit_type=exit_type,
                connector_type=seed.connector_type,
                to_level_id=seed.to_level_id,
                status=seed.status,
                requires_item_slug=seed.requires_item_slug,
                requires_object_id=seed.requires_object_id,
                requires_object_state=seed.requires_object_state,
                requires_clock_slug=seed.requires_clock_slug,
                requires_clock_min_filled=seed.requires_clock_min_filled,
                requires_memory_slug=seed.requires_memory_slug,
            )
        )

    for room_exit in exits_to_seed:
        existing = repo.get_exits_by_room(campaign_id, room_exit.from_room_id)
        existing_ids = {e["exit_id"] for e in existing}
        is_new = room_exit.exit_id not in existing_ids

        if dry_run:
            result.created += 1 if is_new else 0
            result.skipped += 0 if is_new else 1
            continue

        if is_new or force:
            repo.save_room_exit(room_exit)
            if is_new:
                result.created += 1
            else:
                result.updated += 1
        else:
            result.skipped += 1

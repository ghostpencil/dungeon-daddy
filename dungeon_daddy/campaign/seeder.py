"""Campaign manifest seeder — applies a CampaignManifest to a MemoryRepository."""
from __future__ import annotations

from dataclasses import dataclass, field

from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, FactionManifest, ItemManifest, RoomObjectManifest
from dungeon_daddy.memory.repository import MemoryRepository


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
) -> SeedResult:
    """Apply a CampaignManifest to a campaign DB.

    Idempotent — existing records are skipped unless force=True.
    dry_run=True returns counts without writing.
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

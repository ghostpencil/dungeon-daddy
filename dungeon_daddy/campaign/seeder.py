"""Campaign manifest seeder — applies a CampaignManifest to a MemoryRepository."""
from __future__ import annotations

from dataclasses import dataclass, field

from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest
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

    all_actors = manifest.world_actors + manifest.factions
    for actor in all_actors:
        _seed_actor(actor, repo, campaign_id, slug, result, dry_run=dry_run, force=force)

    for clock in manifest.clocks:
        _seed_clock(clock, repo, campaign_id, slug, result, dry_run=dry_run, force=force)

    for i, memory_text in enumerate(manifest.memory_seeds):
        _seed_memory(memory_text, i, repo, campaign_id, slug, result, dry_run=dry_run, force=force)

    return result


def _actor_id(campaign_slug: str, actor_slug: str) -> str:
    return f"actor:{campaign_slug}:{actor_slug}"


def _clock_id(campaign_slug: str, clock_slug: str) -> str:
    return f"clock:{campaign_slug}:{clock_slug}"


def _memory_id(campaign_slug: str, index: int) -> str:
    return f"memory:{campaign_slug}:seed-{index}"


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

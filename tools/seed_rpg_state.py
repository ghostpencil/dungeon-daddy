"""Seed RPG-ready data into existing campaign folders for Phase 33/34 testing.

Usage:
    python tools/seed_rpg_state.py --campaign "The Crucible" [--dry-run]
    python tools/seed_rpg_state.py --all-existing-campaigns [--dry-run]
    python tools/seed_rpg_state.py --campaign "The Crucible" --seed-pack seed_data/campaigns/the-crucible/rpg_seed.json
    python tools/seed_rpg_state.py --campaign "The Crucible" --seed-pack ... --force
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Allow running directly as `python tools/seed_rpg_state.py`
sys.path.insert(0, str(Path(__file__).parent.parent))


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
        if self.warnings:
            print("Warnings:")
            for w in self.warnings:
                print(f"  - {w}")


def seed_campaign(campaign_dir: Path, dry_run: bool = False) -> SeedResult:
    """Seed RPG data into a single campaign folder.

    Idempotent — safe to run multiple times. Dry-run mode prints intended
    changes without writing any files or database rows.
    """
    result = SeedResult()

    if not campaign_dir.exists():
        result.warnings.append(f"Campaign folder not found: {campaign_dir}")
        return result

    if dry_run:
        _dry_run_report(campaign_dir, result)
        return result

    _apply_seed(campaign_dir, result)
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MIGRATIONS_DIR = Path(__file__).parent.parent / "dungeon_daddy" / "data" / "migrations"

_ACTIONS = ["fight", "move", "tinker", "study", "focus", "sway", "sense", "channel", "endure"]
_STRESS_TRACKS = ["body", "composure", "bonds", "weird"]


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "").replace(",", "")


def _campaign_id(campaign_dir: Path) -> str:
    return f"campaign:{_slugify(campaign_dir.name)}"


def _actor_id(campaign_slug: str, actor_slug: str) -> str:
    return f"actor:{campaign_slug}:{actor_slug}"


def _clock_id(campaign_slug: str, clock_slug: str) -> str:
    return f"clock:{campaign_slug}:{clock_slug}"


def _memory_id(campaign_slug: str, memory_slug: str) -> str:
    return f"memory:{campaign_slug}:{memory_slug}"


def _scene_id(campaign_slug: str, location_slug: str) -> str:
    return f"scene:{campaign_slug}:{location_slug}"


def _session_id(campaign_slug: str) -> str:
    return f"session:{campaign_slug}:1"


def _load_seed_spec(campaign_dir: Path) -> _CampaignSeedSpec:
    """Build a seed spec from campaign folder content and generic defaults."""
    slug = _slugify(campaign_dir.name)
    title = campaign_dir.name
    return _CampaignSeedSpec(slug=slug, title=title)


class _CampaignSeedSpec:
    """Holds the seed entities for one campaign."""

    def __init__(self, slug: str, title: str) -> None:
        self.slug = slug
        self.title = title
        self.campaign_id = f"campaign:{slug}"

        self.pc_actors: list[dict] = []
        self.npc_actors = [
            {"slug": "dungeon-presence", "display_name": "Dungeon Presence", "actor_type": "dungeon",
             "concept": "[seed] dungeon-controlled presence"},
            {"slug": "wandering-threat", "display_name": "Wandering Threat", "actor_type": "monster",
             "concept": "[seed] wandering monster"},
        ]
        self.clocks = [
            {"slug": "heat", "label": "Heat Rising", "segments": 6},
            {"slug": "ruin", "label": "Dungeon Ruin", "segments": 8},
            {"slug": "escape", "label": "Escape Route Open", "segments": 4},
        ]
        self.memories = [
            {"slug": "arrival", "type": "event", "title": "[seed] Party arrived at the dungeon",
             "summary": "The party entered the dungeon for the first time.", "importance": 6,
             "tags": ["actor:protagonist", "location:entrance", "theme:arrival"]},
            {"slug": "first-threat", "type": "threat", "title": "[seed] First danger encountered",
             "summary": "The party encountered the first sign of danger.", "importance": 5,
             "tags": ["actor:dungeon-presence", "theme:danger"]},
            {"slug": "party-goal", "type": "faction", "title": "[seed] Party objective established",
             "summary": "The party's goal for this dungeon run is clear.", "importance": 7,
             "tags": ["actor:protagonist", "theme:goal"]},
        ]


def _dry_run_report(campaign_dir: Path, result: SeedResult) -> None:
    spec = _load_seed_spec(campaign_dir)
    slug = spec.slug
    print(f"[dry-run] Campaign: {campaign_dir.name} ({slug})")
    print(f"[dry-run] Would seed {len(spec.pc_actors)} PC actor(s), "
          f"{len(spec.npc_actors)} NPC/dungeon actor(s), "
          f"{len(spec.clocks)} clock(s), "
          f"{len(spec.memories)} memory entry(ies)")


def _apply_seed(campaign_dir: Path, result: SeedResult) -> None:
    from dungeon_daddy.memory.repository import MemoryRepository

    db_path = campaign_dir / "campaign.duckdb"
    repo = MemoryRepository(db_path)
    repo.initialize_schema(_MIGRATIONS_DIR)

    spec = _load_seed_spec(campaign_dir)
    slug = spec.slug
    campaign_id = spec.campaign_id

    # Campaign row
    _upsert_campaign(repo, campaign_id, slug, spec.title, campaign_dir, result)

    # Session row
    _upsert_session(repo, campaign_id, slug, result)

    # Scene row
    _upsert_scene(repo, campaign_id, slug, result)

    # PC actors
    for actor_spec in spec.pc_actors:
        _upsert_actor(repo, campaign_id, slug, actor_spec["slug"],
                      actor_spec["display_name"], "pc", actor_spec.get("concept"), result)

    if not spec.pc_actors:
        result.warnings.append(
            "No player-controlled actors seeded — use --seed-pack to add real actors"
        )

    # NPC/dungeon actors
    for actor_spec in spec.npc_actors:
        _upsert_actor(repo, campaign_id, slug, actor_spec["slug"],
                      actor_spec["display_name"], actor_spec["actor_type"],
                      actor_spec.get("concept"), result)

    # Action ratings for PC actors only
    for actor_spec in spec.pc_actors:
        actor_id = _actor_id(slug, actor_spec["slug"])
        for action_key in _ACTIONS:
            _upsert_action_rating(repo, actor_id, action_key, result)

    # Stress tracks for PC actors only
    for actor_spec in spec.pc_actors:
        actor_id = _actor_id(slug, actor_spec["slug"])
        for track_key in _STRESS_TRACKS:
            _upsert_stress_track(repo, actor_id, track_key, result)

    # Clocks
    for clock_spec in spec.clocks:
        _upsert_clock(repo, campaign_id, slug, clock_spec, result)

    # Memories
    for mem_spec in spec.memories:
        _upsert_memory(repo, campaign_id, slug, mem_spec, result)

    repo.close()

    if result.warnings:
        pass  # already accumulated


# ---------------------------------------------------------------------------
# Upsert helpers — each returns True if created, False if already existed
# ---------------------------------------------------------------------------


def _upsert_campaign(
    repo: object, campaign_id: str, slug: str, title: str,
    campaign_dir: Path, result: SeedResult
) -> None:
    from dungeon_daddy.memory.repository import MemoryRepository
    assert isinstance(repo, MemoryRepository)
    existing = repo.get_campaign(campaign_id)
    if existing is None:
        repo.save_campaign(campaign_id, slug, title)
        result.created += 1
    else:
        result.skipped += 1


def _upsert_session(
    repo: object, campaign_id: str, slug: str, result: SeedResult
) -> None:
    from dungeon_daddy.memory.repository import MemoryRepository
    assert isinstance(repo, MemoryRepository)
    session_id = _session_id(slug)
    existing = repo.get_session(session_id)
    if existing is None:
        repo.save_session(session_id, campaign_id, session_number=1)
        result.created += 1
    else:
        result.skipped += 1


def _upsert_scene(
    repo: object, campaign_id: str, slug: str, result: SeedResult
) -> None:
    from dungeon_daddy.memory.repository import MemoryRepository
    assert isinstance(repo, MemoryRepository)
    scene_id_val = _scene_id(slug, "entrance")
    existing = repo.get_scene(scene_id_val)
    if existing is None:
        repo.save_scene(scene_id_val, campaign_id, location_slug="entrance")
        result.created += 1
    else:
        result.skipped += 1


def _upsert_actor(
    repo: object, campaign_id: str, campaign_slug: str,
    actor_slug: str, display_name: str, actor_type: str,
    concept: str | None, result: SeedResult
) -> None:
    from dungeon_daddy.memory.repository import MemoryRepository
    assert isinstance(repo, MemoryRepository)
    actor_id = _actor_id(campaign_slug, actor_slug)
    existing = repo.get_actor(actor_id)
    if existing is None:
        repo.save_actor(actor_id, campaign_id, actor_type, actor_slug, display_name)
        result.created += 1
    else:
        result.skipped += 1


def _upsert_action_rating(
    repo: object, actor_id: str, action_key: str, result: SeedResult
) -> None:
    from dungeon_daddy.memory.repository import MemoryRepository
    assert isinstance(repo, MemoryRepository)
    existing = repo.get_actor_action_ratings(actor_id)
    existing_keys = {r["action_key"] for r in existing}
    if action_key not in existing_keys:
        repo.save_actor_action_rating(actor_id, action_key, rating=0)
        result.created += 1
    else:
        result.skipped += 1


def _upsert_stress_track(
    repo: object, actor_id: str, track_key: str, result: SeedResult
) -> None:
    from dungeon_daddy.memory.repository import MemoryRepository
    assert isinstance(repo, MemoryRepository)
    existing = repo.get_actor_stress_tracks(actor_id)
    existing_keys = {r["track_key"] for r in existing}
    if track_key not in existing_keys:
        repo.save_actor_stress_track(actor_id, track_key, capacity=6, filled=0)
        result.created += 1
    else:
        result.skipped += 1


def _upsert_clock(
    repo: object, campaign_id: str, campaign_slug: str,
    clock_spec: dict, result: SeedResult
) -> None:
    from dungeon_daddy.memory.repository import MemoryRepository
    assert isinstance(repo, MemoryRepository)
    clock_id = _clock_id(campaign_slug, clock_spec["slug"])
    existing = repo.get_clocks(campaign_id)
    existing_ids = {c["clock_id"] for c in existing}
    if clock_id not in existing_ids:
        repo.save_clock(clock_id, campaign_id, clock_spec["label"], clock_spec["segments"])
        result.created += 1
    else:
        result.skipped += 1


def _upsert_memory(
    repo: object, campaign_id: str, campaign_slug: str,
    mem_spec: dict, result: SeedResult
) -> None:
    from dungeon_daddy.memory.repository import MemoryRepository
    assert isinstance(repo, MemoryRepository)
    memory_id = _memory_id(campaign_slug, mem_spec["slug"])
    existing = repo.get_memory_entry(memory_id)
    if existing is None:
        repo.save_memory_entry(
            memory_id, campaign_id, mem_spec["type"],
            mem_spec["title"], mem_spec["summary"],
            importance=mem_spec.get("importance", 5),
            status="approved",
        )
        for tag in mem_spec.get("tags", []):
            repo.add_memory_tag(memory_id, tag)
        result.created += 1
    else:
        result.skipped += 1


# ---------------------------------------------------------------------------
# Seed-pack applier (34-4)
# ---------------------------------------------------------------------------


def seed_campaign_with_pack(
    campaign_dir: Path,
    seed_pack_path: Path,
    dry_run: bool = False,
    force: bool = False,
) -> SeedResult:
    """Apply a JSON seed pack to a campaign folder.

    Without --force, existing records are skipped.  With --force, they are
    overwritten.  Dry-run prints intended changes without writing.
    """
    result = SeedResult()

    if not campaign_dir.exists():
        result.warnings.append(f"Campaign folder not found: {campaign_dir}")
        return result

    from dungeon_daddy.rpg.seed_pack import load_seed_pack

    pack = load_seed_pack(seed_pack_path)
    campaign_slug = _slugify(campaign_dir.name)
    campaign_id = f"campaign:{campaign_slug}"

    if dry_run:
        all_actors = pack.player_side.actors + pack.dungeon_side.actors
        print(f"[dry-run] Campaign: {campaign_dir.name} ({campaign_slug})")
        print(
            f"[dry-run] Seed pack: {seed_pack_path.name} — "
            f"{len(all_actors)} actor(s), {len(pack.clocks)} clock(s), "
            f"{len(pack.memories)} memory entry(ies)"
        )
        return result

    from dungeon_daddy.memory.repository import MemoryRepository

    db_path = campaign_dir / "campaign.duckdb"
    repo = MemoryRepository(db_path)
    repo.initialize_schema(_MIGRATIONS_DIR)

    _upsert_campaign(repo, campaign_id, campaign_slug, campaign_dir.name, campaign_dir, result)
    _upsert_session(repo, campaign_id, campaign_slug, result)
    _upsert_scene(repo, campaign_id, campaign_slug, result)

    from dungeon_daddy.rpg.models import FactionState
    from dungeon_daddy.rpg.seed_pack import derive_actor_id, derive_faction_id

    all_actors = pack.player_side.actors + pack.dungeon_side.actors
    faction_slugs = {a.slug for a in all_actors if a.actor_type == "faction"}

    for actor in all_actors:
        if actor.actor_type == "faction":
            faction_id = derive_faction_id(pack.campaign_slug, actor.slug)
            existing_factions = {f["faction_id"] for f in repo.get_factions(campaign_id)}
            is_new = faction_id not in existing_factions
            if is_new or force:
                repo.save_faction(FactionState(
                    faction_id=faction_id,
                    campaign_id=campaign_id,
                    slug=actor.slug,
                    display_name=actor.display_name,
                    concept=actor.concept,
                    goal=actor.instinct,
                    status="active",
                    reputation="neutral",
                    tier=0,
                    tags=actor.tags,
                ))
                result.created += 1 if is_new else 0
                result.updated += 1 if not is_new else 0
            else:
                result.skipped += 1
            continue

        actor_id = derive_actor_id(pack.campaign_slug, actor.slug)
        existing = repo.get_actor(actor_id)
        if existing is None:
            repo.save_actor(actor_id, campaign_id, actor.actor_type, actor.slug, actor.display_name)
            for action_key, rating in actor.actions.items():
                repo.save_actor_action_rating(actor_id, action_key, rating)
            for track_key in actor.stress_tracks:
                repo.save_actor_stress_track(actor_id, track_key, capacity=6, filled=0)
            result.created += 1
        elif force:
            # The pack does not own playbook_slug / room_id / status (set by the
            # publish pipeline and movement). Preserve them across a force reseed
            # so re-applying the pack doesn't blank a PC's playbook (which the
            # action UI needs) or relocate actors.
            repo.save_actor(
                actor_id, campaign_id, actor.actor_type, actor.slug, actor.display_name,
                status=existing.get("status", "active"),
                playbook_slug=existing.get("playbook_slug"),
                room_id=existing.get("room_id"),
            )
            for action_key, rating in actor.actions.items():
                repo.save_actor_action_rating(actor_id, action_key, rating)
            for track_key in actor.stress_tracks:
                repo.save_actor_stress_track(actor_id, track_key, capacity=6, filled=0)
            result.updated += 1
        else:
            result.skipped += 1

    from dungeon_daddy.rpg.seed_pack import derive_actor_id as _derive_actor_id
    from dungeon_daddy.rpg.seed_pack import derive_clock_id

    existing_clock_ids = {c["clock_id"] for c in repo.get_clocks(campaign_id)}
    seed_clock_ids: set[str] = set()

    for clock in pack.clocks:
        clock_id = derive_clock_id(pack.campaign_slug, clock.slug)
        seed_clock_ids.add(clock_id)
        owner_actor_id = (
            _derive_actor_id(pack.campaign_slug, clock.owner_actor_slug)
            if clock.owner_actor_slug and clock.owner_actor_slug not in faction_slugs
            else None
        )
        is_new = clock_id not in existing_clock_ids
        if is_new or force:
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
            if is_new:
                result.created += 1
            else:
                result.updated += 1
        else:
            result.skipped += 1

    if force:
        for stale_id in existing_clock_ids - seed_clock_ids:
            repo.delete_clock(stale_id)

    for memory in pack.memories:
        from dungeon_daddy.rpg.seed_pack import derive_memory_id

        memory_id = derive_memory_id(pack.campaign_slug, memory.title)
        existing = repo.get_memory_entry(memory_id)
        if existing is None:
            repo.save_memory_entry(
                memory_id, campaign_id, memory.type, memory.title, memory.summary,
                importance=memory.importance,
                status="approved",
            )
            for tag in memory.tags:
                repo.add_memory_tag(memory_id, tag)
            result.created += 1
        elif force:
            repo.save_memory_entry(
                memory_id, campaign_id, memory.type, memory.title, memory.summary,
                importance=memory.importance,
                status="approved",
            )
            for tag in memory.tags:
                repo.add_memory_tag(memory_id, tag)
            result.updated += 1
        else:
            result.skipped += 1

    repo.close()
    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _find_campaigns_dir() -> Path:
    from platformdirs import user_data_path
    return user_data_path("DungeonDaddy", appauthor=False) / "campaigns"


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed RPG data into campaign folders.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--campaign", metavar="FOLDER_NAME",
                       help="Name of the campaign folder to seed")
    group.add_argument("--all-existing-campaigns", action="store_true",
                       help="Seed all existing campaign folders")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print intended changes without writing")
    parser.add_argument("--seed-pack", metavar="PATH",
                        help="Path to a JSON seed pack file to apply")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing records (requires --seed-pack)")
    parser.add_argument("--campaigns-dir", metavar="PATH",
                        help="Override the campaigns directory path")
    args = parser.parse_args()

    campaigns_dir = Path(args.campaigns_dir) if args.campaigns_dir else _find_campaigns_dir()

    if args.campaign:
        folders = [campaigns_dir / args.campaign]
    else:
        folders = [p for p in campaigns_dir.iterdir() if p.is_dir()]

    seed_pack_path = Path(args.seed_pack) if args.seed_pack else None

    for folder in folders:
        print(f"\n{'[dry-run] ' if args.dry_run else ''}Seeding: {folder.name}")
        if seed_pack_path is not None:
            result = seed_campaign_with_pack(
                folder, seed_pack_path, dry_run=args.dry_run, force=args.force
            )
        else:
            result = seed_campaign(folder, dry_run=args.dry_run)
        result.print_summary()


if __name__ == "__main__":
    main()

"""Integration tests for Phase 40.3 — Campaign Authoring CLI."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dungeon_daddy.campaign.creator import CreateResult, create_campaign_folder
from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, ClockManifest
from dungeon_daddy.campaign.seeder import SeedResult, seed_from_manifest
from dungeon_daddy.memory.repository import MemoryRepository

_MIGRATIONS = Path(__file__).parent.parent.parent / "dungeon_daddy" / "data" / "migrations"
_EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples" / "campaign_manifests"


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    db = tmp_path / "test.duckdb"
    r = MemoryRepository(db)
    r.initialize_schema(_MIGRATIONS)
    r.save_campaign("campaign:test", "test", "Test Campaign")
    yield r
    r.close()


def _minimal_manifest(**kwargs) -> CampaignManifest:
    defaults = dict(
        slug="test",
        title="Test Campaign",
        dungeon_slug="test-dungeon",
        player_side=["hero"],
        world_actors=[
            ActorManifest(slug="hero", display_name="Hero", actor_type="pc"),
        ],
    )
    defaults.update(kwargs)
    return CampaignManifest(**defaults)


# ---------------------------------------------------------------------------
# Bullet 1 — seeder applies actors to DB
# ---------------------------------------------------------------------------


def test_seed_from_manifest_creates_actors(repo: MemoryRepository) -> None:
    manifest = _minimal_manifest(
        world_actors=[
            ActorManifest(slug="hero", display_name="Hero", actor_type="pc"),
            ActorManifest(slug="guard", display_name="Guard", actor_type="npc"),
        ],
        factions=[
            ActorManifest(slug="cult", display_name="The Cult", actor_type="faction"),
        ],
    )

    result = seed_from_manifest(manifest, repo, "campaign:test")

    actors = repo.get_actors_by_campaign("campaign:test")
    slugs = {a["slug"] for a in actors}
    assert "hero" in slugs
    assert "guard" in slugs
    assert "cult" in slugs
    assert result.created >= 3


# ---------------------------------------------------------------------------
# Bullet 2 — seeder applies clocks to DB
# ---------------------------------------------------------------------------


def test_seed_from_manifest_creates_clocks(repo: MemoryRepository) -> None:
    manifest = _minimal_manifest(
        clocks=[
            ClockManifest(slug="doom", label="Doom Clock", segments=6),
            ClockManifest(slug="escape", label="Escape Route", segments=4, filled=1),
        ],
    )

    result = seed_from_manifest(manifest, repo, "campaign:test")

    clocks = repo.get_clocks("campaign:test")
    labels = {c["label"] for c in clocks}
    assert "Doom Clock" in labels
    assert "Escape Route" in labels
    assert result.created >= 2


# ---------------------------------------------------------------------------
# Bullet 3 — seeder applies memory seeds
# ---------------------------------------------------------------------------


def test_seed_from_manifest_creates_memory_seeds(repo: MemoryRepository) -> None:
    manifest = _minimal_manifest(
        memory_seeds=[
            "The party arrived through a collapsed archway.",
            "Mara sensed something watching from the ceiling.",
        ],
    )

    result = seed_from_manifest(manifest, repo, "campaign:test")

    entries = repo.get_memory_entries_by_campaign("campaign:test")
    summaries = {e["summary"] for e in entries}
    assert "The party arrived through a collapsed archway." in summaries
    assert result.created >= 2


# ---------------------------------------------------------------------------
# Bullet 4 — seeder is idempotent
# ---------------------------------------------------------------------------


def test_seed_from_manifest_is_idempotent(repo: MemoryRepository) -> None:
    manifest = _minimal_manifest(
        world_actors=[ActorManifest(slug="hero", display_name="Hero", actor_type="pc")],
        clocks=[ClockManifest(slug="doom", label="Doom", segments=6)],
        memory_seeds=["The party arrived."],
    )

    seed_from_manifest(manifest, repo, "campaign:test")
    result2 = seed_from_manifest(manifest, repo, "campaign:test")

    assert result2.created == 0
    assert result2.skipped >= 3  # 1 actor + 1 clock + 1 memory

    actors = repo.get_actors_by_campaign("campaign:test")
    assert sum(1 for a in actors if a["slug"] == "hero") == 1


# ---------------------------------------------------------------------------
# Bullet 5 — dry-run writes nothing
# ---------------------------------------------------------------------------


def test_seed_from_manifest_dry_run_writes_nothing(repo: MemoryRepository) -> None:
    manifest = _minimal_manifest(
        world_actors=[ActorManifest(slug="hero", display_name="Hero", actor_type="pc")],
        clocks=[ClockManifest(slug="doom", label="Doom", segments=6)],
        memory_seeds=["The party arrived."],
    )

    result = seed_from_manifest(manifest, repo, "campaign:test", dry_run=True)

    assert result.created >= 3
    # nothing actually written
    assert repo.get_actors_by_campaign("campaign:test") == []
    assert repo.get_clocks("campaign:test") == []
    assert repo.get_memory_entries_by_campaign("campaign:test") == []


# ---------------------------------------------------------------------------
# Bullet 6 — creator makes folder structure
# ---------------------------------------------------------------------------


def test_create_campaign_folder_creates_structure(tmp_path: Path) -> None:
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()

    result = create_campaign_folder("bone-cathedral", "The Bone Cathedral", campaigns_dir)

    folder = campaigns_dir / "bone-cathedral"
    assert folder.is_dir()
    assert (folder / "campaign.duckdb").exists()
    assert (folder / "rpg-memory").is_dir()
    assert (folder / "memory").is_dir()
    assert len(result.created) > 0


def test_create_campaign_folder_dry_run_writes_nothing(tmp_path: Path) -> None:
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()

    result = create_campaign_folder("bone-cathedral", "The Bone Cathedral", campaigns_dir, dry_run=True)

    assert not (campaigns_dir / "bone-cathedral").exists()
    assert len(result.created) > 0  # would-be creations reported
    assert result.dry_run is True


def test_create_campaign_folder_is_idempotent(tmp_path: Path) -> None:
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()

    create_campaign_folder("bone-cathedral", "The Bone Cathedral", campaigns_dir)
    result2 = create_campaign_folder("bone-cathedral", "The Bone Cathedral", campaigns_dir)

    assert result2.created == []  # nothing new to create
    assert len(result2.skipped) > 0


# ---------------------------------------------------------------------------
# CLI tool round-trip: create -> seed -> validate manifest
# ---------------------------------------------------------------------------


def test_validate_manifest_tool_accepts_valid_manifest(tmp_path: Path) -> None:
    from dungeon_daddy.campaign.manifest import CampaignManifest
    from dungeon_daddy.campaign.validator import validate_manifest

    manifest = CampaignManifest(
        slug="bone-cathedral",
        title="The Bone Cathedral",
        dungeon_slug="bone-cathedral",
        player_side=["valeria"],
        world_actors=[
            ActorManifest(slug="valeria", display_name="Valeria Crane", actor_type="pc"),
        ],
        clocks=[
            ClockManifest(slug="collapse", label="Cathedral Collapse", segments=8),
        ],
    )

    errors = validate_manifest(manifest)
    assert errors == []


def test_validate_manifest_tool_catches_empty_player_side(tmp_path: Path) -> None:
    from dungeon_daddy.campaign.manifest import CampaignManifest
    from dungeon_daddy.campaign.validator import validate_manifest

    manifest = CampaignManifest(
        slug="bone-cathedral",
        title="The Bone Cathedral",
        dungeon_slug="bone-cathedral",
        player_side=[],  # empty — should fail
        world_actors=[
            ActorManifest(slug="valeria", display_name="Valeria Crane", actor_type="pc"),
        ],
    )

    errors = validate_manifest(manifest)
    assert any(e.field == "player_side" for e in errors)


def test_seed_campaign_rpg_tool_creates_db_records(tmp_path: Path) -> None:
    """End-to-end: create folder, write manifest, seed via seeder, verify DB."""
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()

    # Create folder
    from dungeon_daddy.campaign.creator import create_campaign_folder
    create_campaign_folder("bone-cathedral", "The Bone Cathedral", campaigns_dir)

    # Write manifest
    manifest_data = {
        "slug": "bone-cathedral",
        "title": "The Bone Cathedral",
        "dungeon_slug": "bone-cathedral",
        "player_side": ["valeria"],
        "world_actors": [
            {"slug": "valeria", "display_name": "Valeria Crane", "actor_type": "pc",
             "action_ratings": {"fight": 2, "study": 1}},
        ],
        "clocks": [
            {"slug": "collapse", "label": "Cathedral Collapse", "segments": 8},
        ],
        "memory_seeds": ["The cathedral's bones still breathe."],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    # Seed
    from dungeon_daddy.campaign.manifest import CampaignManifest
    from dungeon_daddy.campaign.seeder import seed_from_manifest

    manifest = CampaignManifest(**manifest_data)
    db_path = campaigns_dir / "bone-cathedral" / "campaign.duckdb"
    repo = MemoryRepository(db_path)
    repo.initialize_schema(_MIGRATIONS)
    campaign_id = "campaign:bone-cathedral"
    if repo.get_campaign(campaign_id) is None:
        repo.save_campaign(campaign_id, "bone-cathedral", "The Bone Cathedral")

    result = seed_from_manifest(manifest, repo, campaign_id)

    actors = repo.get_actors_by_campaign(campaign_id)
    clocks = repo.get_clocks(campaign_id)
    memories = repo.get_memory_entries_by_campaign(campaign_id)
    repo.close()

    assert any(a["slug"] == "valeria" for a in actors)
    assert any(c["label"] == "Cathedral Collapse" for c in clocks)
    assert any("breathe" in m["summary"] for m in memories)
    assert result.created >= 3


# ---------------------------------------------------------------------------
# Round-trip: seed → export → validate (Phase 40.4)
# ---------------------------------------------------------------------------


def test_export_campaign_manifest_round_trip(repo: MemoryRepository) -> None:
    """Seed a manifest, export it back, and confirm the exported manifest validates."""
    from dungeon_daddy.campaign.exporter import export_campaign_manifest
    from dungeon_daddy.campaign.validator import validate_manifest

    manifest = _minimal_manifest(
        world_actors=[
            ActorManifest(slug="valeria", display_name="Valeria Crane", actor_type="pc",
                          action_ratings={"fight": 2, "study": 1}),
            ActorManifest(slug="bone-warden", display_name="The Bone Warden", actor_type="dungeon"),
        ],
        clocks=[
            ClockManifest(slug="collapse", label="Cathedral Collapse", segments=8,
                          clock_level="dungeon", category="danger"),
        ],
        memory_seeds=["The party arrived through the collapsed archway."],
    )

    seed_from_manifest(manifest, repo, "campaign:test")

    exported = export_campaign_manifest("campaign:test", repo)

    assert exported.slug == manifest.slug
    assert exported.title == manifest.title
    assert {a.slug for a in exported.world_actors} == {"valeria", "bone-warden"}
    assert "valeria" in exported.player_side
    assert "bone-warden" not in exported.player_side
    valeria = next(a for a in exported.world_actors if a.slug == "valeria")
    assert valeria.action_ratings == {"fight": 2, "study": 1}
    assert len(exported.clocks) == 1
    assert exported.clocks[0].label == "Cathedral Collapse"
    assert len(exported.memory_seeds) == 1

    errors = validate_manifest(exported)
    assert errors == []


# ---------------------------------------------------------------------------
# 40.5 — Example manifest validates and seeds cleanly
# ---------------------------------------------------------------------------


def test_example_bone_cathedral_manifest_validates(tmp_path: Path) -> None:
    """The example manifest in examples/campaign_manifests/ must have zero validation errors."""
    from dungeon_daddy.campaign.validator import validate_manifest

    manifest_file = _EXAMPLES_DIR / "bone-cathedral.json"
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest = CampaignManifest(**data)

    errors = validate_manifest(manifest)
    assert errors == [], [f"{e.field}: {e.message}" for e in errors]


def test_example_bone_cathedral_manifest_seeds_cleanly(tmp_path: Path) -> None:
    """The example manifest seeds all actors, clocks, and memories without error."""
    manifest_file = _EXAMPLES_DIR / "bone-cathedral.json"
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest = CampaignManifest(**data)

    db = tmp_path / "bone-cathedral.duckdb"
    repo = MemoryRepository(db)
    repo.initialize_schema(_MIGRATIONS)
    campaign_id = f"campaign:{manifest.slug}"
    repo.save_campaign(campaign_id, manifest.slug, manifest.title)

    result = seed_from_manifest(manifest, repo, campaign_id)

    actors = repo.get_actors_by_campaign(campaign_id)
    clocks = repo.get_clocks(campaign_id)
    memories = repo.get_memory_entries_by_campaign(campaign_id)
    repo.close()

    assert result.created >= 5  # 4 world_actors + 1 faction + 3 clocks + 3 memory_seeds
    assert result.warnings == []
    pc_slugs = {a["slug"] for a in actors if a["actor_type"] == "pc"}
    assert pc_slugs == {"valeria", "osric"}
    assert len(clocks) == 3
    assert len(memories) == 3


def test_example_bone_cathedral_manifest_seeds_idempotently(tmp_path: Path) -> None:
    """Seeding the example manifest twice produces no new records on the second pass."""
    manifest_file = _EXAMPLES_DIR / "bone-cathedral.json"
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest = CampaignManifest(**data)

    db = tmp_path / "bone-cathedral.duckdb"
    repo = MemoryRepository(db)
    repo.initialize_schema(_MIGRATIONS)
    campaign_id = f"campaign:{manifest.slug}"
    repo.save_campaign(campaign_id, manifest.slug, manifest.title)

    seed_from_manifest(manifest, repo, campaign_id)
    result2 = seed_from_manifest(manifest, repo, campaign_id)
    repo.close()

    assert result2.created == 0
    assert result2.skipped > 0

"""Tests for playbook seed-publish wiring in seed_from_manifest / _seed_actor."""
from pathlib import Path

import pytest

from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest
from dungeon_daddy.campaign.seeder import seed_from_manifest
from dungeon_daddy.memory.repository import MemoryRepository

_MIGRATIONS_DIR = Path("dungeon_daddy/data/migrations")
_CAMPAIGN_ID = "campaign:bone-cathedral"
_CAMPAIGN_SLUG = "bone-cathedral"


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "campaign.duckdb")
    r.initialize_schema(_MIGRATIONS_DIR)
    return r


def _fighter_manifest(actor_slug: str = "roland") -> CampaignManifest:
    return CampaignManifest(
        slug=_CAMPAIGN_SLUG,
        title="The Bone Cathedral",
        dungeon_slug=_CAMPAIGN_SLUG,
        world_actors=[
            ActorManifest(
                slug=actor_slug,
                display_name="Roland",
                actor_type="pc",
                playbook_slug="fighter",
            )
        ],
    )


# ---------------------------------------------------------------------------
# Cycle 22 — playbook_slug persisted on actors row
# ---------------------------------------------------------------------------

def test_seed_actor_with_playbook_slug_persists_slug(repo: MemoryRepository) -> None:
    seed_from_manifest(_fighter_manifest(), repo, campaign_id=_CAMPAIGN_ID)
    actor = repo.get_actor("actor:bone-cathedral:roland")
    assert actor is not None
    assert actor["playbook_slug"] == "fighter"


# ---------------------------------------------------------------------------
# Cycle 23 — action ratings seeded from playbook when manifest has none
# ---------------------------------------------------------------------------

def test_seed_actor_with_playbook_seeds_action_ratings(repo: MemoryRepository) -> None:
    seed_from_manifest(_fighter_manifest(), repo, campaign_id=_CAMPAIGN_ID)
    ratings = {
        r["action_key"]: r["rating"]
        for r in repo.get_actor_action_ratings("actor:bone-cathedral:roland")
    }
    assert ratings["fight"] == 2
    assert ratings["endure"] == 2
    assert ratings["move"] == 1
    assert ratings["tinker"] == 0


# ---------------------------------------------------------------------------
# Cycle 24 — stress tracks seeded from playbook when manifest has none
# ---------------------------------------------------------------------------

def test_seed_actor_with_playbook_seeds_stress_tracks(repo: MemoryRepository) -> None:
    seed_from_manifest(_fighter_manifest(), repo, campaign_id=_CAMPAIGN_ID)
    tracks = {
        t["track_key"]: t
        for t in repo.get_actor_stress_tracks("actor:bone-cathedral:roland")
    }
    for track_key in ("body", "composure", "bonds", "weird"):
        assert track_key in tracks
        assert tracks[track_key]["capacity"] == 4


# ---------------------------------------------------------------------------
# Cycle 25 — class tags seeded from playbook
# ---------------------------------------------------------------------------

def test_seed_actor_with_playbook_seeds_tags(repo: MemoryRepository) -> None:
    seed_from_manifest(_fighter_manifest(), repo, campaign_id=_CAMPAIGN_ID)
    actor = repo.get_actor("actor:bone-cathedral:roland")
    assert actor is not None
    tags = actor["tags"]
    assert "warrior" in tags
    assert "frontline" in tags


# ---------------------------------------------------------------------------
# Cycle 26 — kit seeded as class_kit Item owned by actor
# ---------------------------------------------------------------------------

def test_seed_actor_with_playbook_seeds_kit_item(repo: MemoryRepository) -> None:
    seed_from_manifest(_fighter_manifest(), repo, campaign_id=_CAMPAIGN_ID)
    items = repo.get_items(_CAMPAIGN_ID)
    kit_items = [i for i in items if i["item_type"] == "class_kit"]
    assert len(kit_items) == 1
    kit = kit_items[0]
    assert kit["slug"] == "combat-gear"
    assert kit["owner_actor_id"] == "actor:bone-cathedral:roland"
    assert kit["charges_max"] == 3
    assert kit["charges_current"] == 3


# ---------------------------------------------------------------------------
# Cycle 27 — actor_abilities rows seeded for kit abilities (source="kit")
# ---------------------------------------------------------------------------

def test_seed_actor_with_playbook_seeds_kit_abilities(repo: MemoryRepository) -> None:
    seed_from_manifest(_fighter_manifest(), repo, campaign_id=_CAMPAIGN_ID)
    abilities = repo.get_actor_abilities("actor:bone-cathedral:roland")
    slugs = {a.ability_slug for a in abilities}
    assert "shield-bash" in slugs
    shield_bash = next(a for a in abilities if a.ability_slug == "shield-bash")
    assert shield_bash.source == "kit"
    assert shield_bash.display_name == "Shield Bash"
    assert shield_bash.target_types == ["monster"]


# ---------------------------------------------------------------------------
# Cycle 28 — idempotent: re-seed without force skips abilities and item
# ---------------------------------------------------------------------------

def test_seed_actor_with_playbook_is_idempotent(repo: MemoryRepository) -> None:
    manifest = _fighter_manifest()
    seed_from_manifest(manifest, repo, campaign_id=_CAMPAIGN_ID)
    result2 = seed_from_manifest(manifest, repo, campaign_id=_CAMPAIGN_ID)

    assert result2.skipped == 1
    assert result2.created == 0
    # abilities unchanged — kit + first pool ability
    assert len(repo.get_actor_abilities("actor:bone-cathedral:roland")) == 2
    # kit item not duplicated
    assert len(repo.get_items(_CAMPAIGN_ID)) == 1


# ---------------------------------------------------------------------------
# Cycle 29 — force=True re-seeds actor row and actor_abilities
# ---------------------------------------------------------------------------

def test_seed_actor_with_force_reseeds_playbook_data(repo: MemoryRepository) -> None:
    manifest = _fighter_manifest()
    seed_from_manifest(manifest, repo, campaign_id=_CAMPAIGN_ID)
    # Simulate abilities being removed between publishes
    repo.delete_actor_ability("actor:bone-cathedral:roland", "shield-bash")
    repo.delete_actor_ability("actor:bone-cathedral:roland", "iron-will")
    assert repo.get_actor_abilities("actor:bone-cathedral:roland") == []

    result2 = seed_from_manifest(manifest, repo, campaign_id=_CAMPAIGN_ID, force=True)

    assert result2.updated >= 1
    # force re-seeded both kit and pool abilities
    abilities = repo.get_actor_abilities("actor:bone-cathedral:roland")
    slugs = {a.ability_slug for a in abilities}
    assert len(abilities) == 2
    assert "shield-bash" in slugs
    assert "iron-will" in slugs


# ---------------------------------------------------------------------------
# Cycle 30 — dry_run=True reports counts without writing anything
# ---------------------------------------------------------------------------

def test_seed_actor_with_playbook_dry_run_writes_nothing(repo: MemoryRepository) -> None:
    result = seed_from_manifest(_fighter_manifest(), repo, campaign_id=_CAMPAIGN_ID, dry_run=True)

    assert result.created >= 1
    assert repo.get_actor("actor:bone-cathedral:roland") is None
    assert repo.get_items(_CAMPAIGN_ID) == []
    assert repo.get_actor_abilities("actor:bone-cathedral:roland") == []

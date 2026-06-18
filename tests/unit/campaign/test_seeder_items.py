"""Tests for _seed_item behaviour in seed_from_manifest."""
from pathlib import Path

import pytest

from dungeon_daddy.campaign.manifest import CampaignManifest, ItemManifest
from dungeon_daddy.campaign.seeder import seed_from_manifest
from dungeon_daddy.memory.repository import MemoryRepository

_MIGRATIONS_DIR = Path("dungeon_daddy/data/migrations")


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "campaign.duckdb")
    r.initialize_schema(_MIGRATIONS_DIR)
    return r


def _manifest_with_kit(owner_slug: str | None = None) -> CampaignManifest:
    return CampaignManifest(
        slug="bone-cathedral",
        title="The Bone Cathedral",
        dungeon_slug="bone-cathedral",
        items=[
            ItemManifest(
                slug="lockpick-kit",
                display_name="Lockpick Kit",
                item_type="class_kit",
                description="A well-used set of picks.",
                charges_max=3,
                owner_slug=owner_slug,
            )
        ],
    )


def test_seed_item_creates_new_class_kit(repo: MemoryRepository) -> None:
    manifest = _manifest_with_kit()
    result = seed_from_manifest(manifest, repo, campaign_id="campaign:bone-cathedral")

    assert result.created == 1
    items = repo.get_items("campaign:bone-cathedral")
    assert len(items) == 1
    item = items[0]
    assert item["slug"] == "lockpick-kit"
    assert item["item_type"] == "class_kit"
    assert item["charges_max"] == 3
    assert item["charges_current"] == 3


def test_seed_item_skips_existing_without_force(repo: MemoryRepository) -> None:
    manifest = _manifest_with_kit()
    seed_from_manifest(manifest, repo, campaign_id="campaign:bone-cathedral")
    result2 = seed_from_manifest(manifest, repo, campaign_id="campaign:bone-cathedral")

    assert result2.skipped == 1
    assert result2.created == 0
    assert len(repo.get_items("campaign:bone-cathedral")) == 1


def test_seed_item_force_updates_existing(repo: MemoryRepository) -> None:
    manifest = _manifest_with_kit()
    seed_from_manifest(manifest, repo, campaign_id="campaign:bone-cathedral")
    result2 = seed_from_manifest(manifest, repo, campaign_id="campaign:bone-cathedral", force=True)

    assert result2.updated == 1
    assert result2.skipped == 0
    assert len(repo.get_items("campaign:bone-cathedral")) == 1


def test_seed_item_dry_run_counts_without_writing(repo: MemoryRepository) -> None:
    manifest = _manifest_with_kit()
    result = seed_from_manifest(manifest, repo, campaign_id="campaign:bone-cathedral", dry_run=True)

    assert result.created == 1
    assert repo.get_items("campaign:bone-cathedral") == []


def test_seed_item_owner_slug_resolves_to_actor_id(repo: MemoryRepository) -> None:
    manifest = _manifest_with_kit(owner_slug="valeria")
    seed_from_manifest(manifest, repo, campaign_id="campaign:bone-cathedral")

    items = repo.get_items("campaign:bone-cathedral")
    assert items[0]["owner_actor_id"] == "actor:bone-cathedral:valeria"


def _manifest_with_loose_item() -> CampaignManifest:
    return CampaignManifest(
        slug="bone-cathedral",
        title="The Bone Cathedral",
        dungeon_slug="bone-cathedral",
        items=[
            ItemManifest(
                slug="gold-coin",
                display_name="Gold Coin",
                item_type="dungeon_item",
                description="A shiny coin.",
                room_id="room:cathedral:nave",
            )
        ],
    )


def test_seed_item_room_id_seeds_loose_in_room(repo: MemoryRepository) -> None:
    manifest = _manifest_with_loose_item()
    result = seed_from_manifest(manifest, repo, campaign_id="campaign:bone-cathedral")

    assert result.created == 1
    items = repo.get_items("campaign:bone-cathedral")
    assert items[0]["room_id"] == "room:cathedral:nave"
    assert items[0]["owner_actor_id"] is None


def test_seed_item_with_both_owner_and_room_id_prefers_owner(repo: MemoryRepository) -> None:
    manifest = CampaignManifest(
        slug="bone-cathedral",
        title="The Bone Cathedral",
        dungeon_slug="bone-cathedral",
        items=[
            ItemManifest(
                slug="gold-coin",
                display_name="Gold Coin",
                item_type="dungeon_item",
                description="A coin.",
                owner_slug="valeria",
                room_id="room:cathedral:nave",
            )
        ],
    )
    seed_from_manifest(manifest, repo, campaign_id="campaign:bone-cathedral")

    items = repo.get_items("campaign:bone-cathedral")
    assert items[0]["owner_actor_id"] == "actor:bone-cathedral:valeria"

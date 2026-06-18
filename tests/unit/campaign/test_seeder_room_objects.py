"""Tests for _seed_room_object behaviour in seed_from_manifest."""
from pathlib import Path

import pytest

from dungeon_daddy.campaign.manifest import (
    CampaignManifest,
    ObjectTransitionManifest,
    RoomObjectManifest,
)
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


def _manifest_with_chest(transitions: list[ObjectTransitionManifest] | None = None) -> CampaignManifest:
    return CampaignManifest(
        slug=_CAMPAIGN_SLUG,
        title="The Bone Cathedral",
        dungeon_slug=_CAMPAIGN_SLUG,
        room_objects=[
            RoomObjectManifest(
                slug="iron-chest",
                display_name="Iron Chest",
                room_id="room:cathedral:nave",
                level_id="level:cathedral:ground",
                archetype="container",
                description="A heavy iron chest.",
                initial_state="sealed",
                transitions=transitions or [],
            )
        ],
    )


def test_seed_room_object_creates_new_object(repo: MemoryRepository) -> None:
    result = seed_from_manifest(_manifest_with_chest(), repo, campaign_id=_CAMPAIGN_ID)

    assert result.created == 1
    obj = repo.get_room_object("obj:bone-cathedral:iron-chest")
    assert obj is not None
    assert obj["current_state"] == "sealed"
    assert obj["display_name"] == "Iron Chest"
    assert obj["archetype"] == "container"
    assert obj["room_id"] == "room:cathedral:nave"


def test_seed_room_object_skips_existing_without_force(repo: MemoryRepository) -> None:
    seed_from_manifest(_manifest_with_chest(), repo, campaign_id=_CAMPAIGN_ID)
    result2 = seed_from_manifest(_manifest_with_chest(), repo, campaign_id=_CAMPAIGN_ID)

    assert result2.skipped == 1
    assert result2.created == 0


def test_seed_room_object_force_updates_existing(repo: MemoryRepository) -> None:
    seed_from_manifest(_manifest_with_chest(), repo, campaign_id=_CAMPAIGN_ID)
    result2 = seed_from_manifest(_manifest_with_chest(), repo, campaign_id=_CAMPAIGN_ID, force=True)

    assert result2.updated == 1
    assert result2.skipped == 0


def test_seed_room_object_dry_run_counts_without_writing(repo: MemoryRepository) -> None:
    result = seed_from_manifest(_manifest_with_chest(), repo, campaign_id=_CAMPAIGN_ID, dry_run=True)

    assert result.created == 1
    assert repo.get_room_object("obj:bone-cathedral:iron-chest") is None


def test_seed_room_object_seeds_transitions(repo: MemoryRepository) -> None:
    transitions = [
        ObjectTransitionManifest(
            from_state="sealed", to_state="opened", trigger="open",
            spawns_item_slug="gold-coin",
        ),
        ObjectTransitionManifest(
            from_state="sealed", to_state="broken", trigger="force",
        ),
    ]
    seed_from_manifest(_manifest_with_chest(transitions), repo, campaign_id=_CAMPAIGN_ID)

    obj = repo.get_room_object("obj:bone-cathedral:iron-chest")
    assert obj is not None
    assert len(obj["transitions"]) == 2
    t0 = obj["transitions"][0]
    assert t0["transition_id"] == "tr:bone-cathedral:iron-chest:0"
    assert t0["from_state"] == "sealed"
    assert t0["to_state"] == "opened"
    assert t0["trigger"] == "open"
    assert t0["spawns_item_slug"] == "gold-coin"
    t1 = obj["transitions"][1]
    assert t1["transition_id"] == "tr:bone-cathedral:iron-chest:1"
    assert t1["trigger"] == "force"
    assert t1["spawns_item_slug"] is None

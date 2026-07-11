"""Tests for room seeding in seed_from_manifest (Phase 51.8 Slice B0, spec §7.1).

The app's new-game seed path projects each dungeon room into a first-class
``rooms`` record — the base the populate scripts later enrich with lore tags.
"""
from pathlib import Path

import pytest

from dungeon_daddy.campaign.manifest import CampaignManifest
from dungeon_daddy.campaign.seeder import seed_from_manifest
from dungeon_daddy.data.models import Dungeon, DungeonMeta, Level, Room
from dungeon_daddy.memory.repository import MemoryRepository

_MIGRATIONS_DIR = Path("dungeon_daddy/data/migrations")
_CAMPAIGN_ID = "campaign:test"
_CAMPAIGN_SLUG = "test-campaign"


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "campaign.duckdb")
    r.initialize_schema(_MIGRATIONS_DIR)
    yield r
    r.close()


def _manifest() -> CampaignManifest:
    return CampaignManifest(
        slug=_CAMPAIGN_SLUG,
        title="Test Campaign",
        dungeon_slug=_CAMPAIGN_SLUG,
    )


def _room(room_id: str, name: str, *, note: str = "", main_loop_role: str | None = None) -> Room:
    return Room(
        id=room_id, num=1, name=name, x=0, y=0, w=1, h=1,
        type="room", note=note, main_loop_role=main_loop_role,
    )


def _dungeon(*rooms: Room) -> Dungeon:
    level = Level(
        id=1, name="Level One", summary="", ecology="", loop="",
        width=10, height=10, entries=[], rooms=list(rooms), connections=[],
    )
    meta = DungeonMeta(
        title="Test Dungeon", theme="dark", setting="cave",
        party="heroes", quest="escape",
    )
    return Dungeon(meta=meta, levels=[level])


def test_rooms_are_projected_from_the_dungeon(repo: MemoryRepository) -> None:
    dungeon = _dungeon(
        _room("R1", "Receiving Hall", note="A dusty entry.", main_loop_role="entry"),
        _room("R2", "Marketplace"),
    )
    seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon)
    rooms = {r["room_id"]: r for r in repo.get_rooms(_CAMPAIGN_ID)}
    assert set(rooms) == {"R1", "R2"}
    assert rooms["R1"]["summary"] == "A dusty entry."
    assert rooms["R1"]["level_id"] == "level:1"
    assert rooms["R1"]["quest_role"] == "entry"  # derived from main_loop_role


def test_no_rooms_seeded_without_a_dungeon(repo: MemoryRepository) -> None:
    seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID)
    assert repo.get_rooms(_CAMPAIGN_ID) == []


def test_dry_run_writes_no_rooms(repo: MemoryRepository) -> None:
    dungeon = _dungeon(_room("R1", "Hall"))
    seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon, dry_run=True)
    assert repo.get_rooms(_CAMPAIGN_ID) == []


def test_reseed_without_force_preserves_room_enrichment(repo: MemoryRepository) -> None:
    from dungeon_daddy.rpg.models import RoomState

    dungeon = _dungeon(_room("R1", "Hall", main_loop_role="entry"))
    seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon)
    # Simulate populate enrichment.
    row = repo.get_room(_CAMPAIGN_ID, "R1")
    repo.save_room(RoomState(**row).model_copy(update={"tags": ["theme:history"]}))

    seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon)  # plain reseed

    assert "theme:history" in repo.get_room(_CAMPAIGN_ID, "R1")["tags"]


def test_reseed_with_force_preserves_room_enrichment(repo: MemoryRepository) -> None:
    from dungeon_daddy.rpg.models import RoomState

    dungeon = _dungeon(_room("R1", "Hall", main_loop_role="entry"))
    seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon)
    row = repo.get_room(_CAMPAIGN_ID, "R1")
    repo.save_room(RoomState(**row).model_copy(update={"tags": ["theme:history"]}))

    seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon, force=True)

    assert "theme:history" in repo.get_room(_CAMPAIGN_ID, "R1")["tags"]

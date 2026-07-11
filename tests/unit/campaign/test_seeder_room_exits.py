"""Tests for room-exit seeding in seed_from_manifest."""
from pathlib import Path

import pytest

from dungeon_daddy.campaign.manifest import CampaignManifest, RoomExitSeed
from dungeon_daddy.campaign.seeder import seed_from_manifest
from dungeon_daddy.data.models import Connection, Dungeon, DungeonMeta, Level, Room
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


def _manifest(room_exits: list[RoomExitSeed] | None = None) -> CampaignManifest:
    return CampaignManifest(
        slug=_CAMPAIGN_SLUG,
        title="Test Campaign",
        dungeon_slug=_CAMPAIGN_SLUG,
        room_exits=room_exits or [],
    )


def _room(room_id: str, num: int = 1) -> Room:
    return Room(id=room_id, num=num, name=room_id, x=0, y=0, w=1, h=1, type="room", note="")


def _dungeon_with_connection(
    from_room: str = "room-a",
    to_room: str = "room-b",
    conn_type: str = "door",
    layout_connection_role: str | None = None,
) -> Dungeon:
    payload: dict = {"from": from_room, "to": to_room, "type": conn_type}
    if layout_connection_role is not None:
        payload["layout_connection_role"] = layout_connection_role
    connection = Connection.model_validate(payload)
    level = Level(
        id=1,
        name="Level One",
        summary="",
        ecology="",
        loop="",
        width=10,
        height=10,
        entries=[],
        rooms=[_room(from_room, 1), _room(to_room, 2)],
        connections=[connection],
    )
    meta = DungeonMeta(title="Test Dungeon", theme="dark", setting="cave", party="heroes", quest="escape")
    return Dungeon(meta=meta, levels=[level])


def test_connection_derives_two_bidirectional_exits(repo: MemoryRepository) -> None:
    dungeon = _dungeon_with_connection()
    seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon)

    exits_from_a = repo.get_exits_by_room(_CAMPAIGN_ID, "room-a")
    exits_from_b = repo.get_exits_by_room(_CAMPAIGN_ID, "room-b")

    assert len(exits_from_a) == 1
    assert exits_from_a[0]["to_room_id"] == "room-b"
    assert exits_from_a[0]["status"] == "open"

    assert len(exits_from_b) == 1
    assert exits_from_b[0]["to_room_id"] == "room-a"
    assert exits_from_b[0]["status"] == "open"


def test_hall_connection_labeled_hall_not_door(repo: MemoryRepository) -> None:
    """A 'hall' connection must not silently collapse to a 'Door' exit."""
    dungeon = _dungeon_with_connection(conn_type="hall")
    seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon)

    exits = repo.get_exits_by_room(_CAMPAIGN_ID, "room-a")
    assert exits[0]["exit_type"] == "hall"
    assert exits[0]["label"] == "Hall"


def test_stair_down_connection_labeled_stairs(repo: MemoryRepository) -> None:
    dungeon = _dungeon_with_connection(conn_type="stair_down")
    seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon)

    exits = repo.get_exits_by_room(_CAMPAIGN_ID, "room-a")
    assert exits[0]["exit_type"] == "stair"
    assert exits[0]["label"] == "Stairs"


def test_locked_connection_role_derives_locked_status(repo: MemoryRepository) -> None:
    """A connection flagged layout_connection_role='locked' must seed locked exits."""
    dungeon = _dungeon_with_connection(layout_connection_role="locked")
    seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon)

    exits_from_a = repo.get_exits_by_room(_CAMPAIGN_ID, "room-a")
    exits_from_b = repo.get_exits_by_room(_CAMPAIGN_ID, "room-b")
    assert exits_from_a[0]["status"] == "locked"
    assert exits_from_b[0]["status"] == "locked"


def test_secret_connection_role_derives_hidden_status(repo: MemoryRepository) -> None:
    dungeon = _dungeon_with_connection(layout_connection_role="secret")
    seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon)

    exits = repo.get_exits_by_room(_CAMPAIGN_ID, "room-a")
    assert exits[0]["status"] == "hidden"


def test_ordinary_connection_role_stays_open(repo: MemoryRepository) -> None:
    dungeon = _dungeon_with_connection(layout_connection_role="critical_path")
    seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon)

    exits = repo.get_exits_by_room(_CAMPAIGN_ID, "room-a")
    assert exits[0]["status"] == "open"


def test_manifest_override_applied_to_connection_exit(repo: MemoryRepository) -> None:
    override = RoomExitSeed(
        from_room_id="room-a",
        to_room_id="room-b",
        label="Iron Gate",
        status="locked",
        requires_item_slug="iron-key",
    )
    dungeon = _dungeon_with_connection()
    seed_from_manifest(_manifest(room_exits=[override]), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon)

    exits = repo.get_exits_by_room(_CAMPAIGN_ID, "room-a")
    assert len(exits) == 1
    assert exits[0]["label"] == "Iron Gate"
    assert exits[0]["status"] == "locked"
    assert exits[0]["requires_item_slug"] == "iron-key"


def test_seeds_manifest_exits_without_dungeon(repo: MemoryRepository) -> None:
    seed = RoomExitSeed(
        from_room_id="room-x",
        to_room_id="room-y",
        label="Secret Tunnel",
        status="hidden",
    )
    seed_from_manifest(_manifest(room_exits=[seed]), repo, campaign_id=_CAMPAIGN_ID)

    exits = repo.get_exits_by_room(_CAMPAIGN_ID, "room-x")
    assert len(exits) == 1
    assert exits[0]["label"] == "Secret Tunnel"
    assert exits[0]["status"] == "hidden"


def test_seed_exits_skips_existing_without_force(repo: MemoryRepository) -> None:
    dungeon = _dungeon_with_connection()
    seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon)
    result2 = seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon)

    assert result2.created == 0
    # 2 bidirectional exits + 2 rooms (Slice B0 projects the dungeon's rooms too).
    assert result2.skipped == 4


def test_seed_exits_force_updates_existing(repo: MemoryRepository) -> None:
    dungeon = _dungeon_with_connection()
    seed_from_manifest(_manifest(), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon)

    override = RoomExitSeed(from_room_id="room-a", to_room_id="room-b", label="Forced Door", status="locked")
    result2 = seed_from_manifest(
        _manifest(room_exits=[override]), repo, campaign_id=_CAMPAIGN_ID, dungeon=dungeon, force=True
    )

    assert result2.updated >= 1
    exits = repo.get_exits_by_room(_CAMPAIGN_ID, "room-a")
    assert exits[0]["label"] == "Forced Door"
    assert exits[0]["status"] == "locked"

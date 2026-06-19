"""Tests for the pre-Phase-48 room_exits backfill tool."""
from __future__ import annotations

from pathlib import Path

from dungeon_daddy.data.models import Connection, Dungeon, DungeonMeta, Level, Room
from dungeon_daddy.memory.repository import MemoryRepository
from tools.backfill_room_exits import _backfill_one

_MIGRATIONS_DIR = Path("dungeon_daddy/data/migrations")


def _room(room_id: str, num: int) -> Room:
    return Room(id=room_id, num=num, name=room_id, x=0, y=0, w=1, h=1, type="room", note="")


def _dungeon() -> Dungeon:
    conn = Connection.model_validate({"from": "room-a", "to": "room-b", "type": "door"})
    level = Level(
        id=1, name="L1", summary="", ecology="", loop="",
        width=10, height=10, entries=[],
        rooms=[_room("room-a", 1), _room("room-b", 2)], connections=[conn],
    )
    meta = DungeonMeta(title="Test Dungeon", theme="d", setting="c", party="h", quest="e")
    return Dungeon(meta=meta, levels=[level])


def _make_campaign_dir(tmp_path: Path) -> Path:
    """A campaign dir as the app stores it: campaign.duckdb (seeded) + dungeon.json."""
    repo = MemoryRepository(tmp_path / "campaign.duckdb")
    repo.initialize_schema(_MIGRATIONS_DIR)
    repo.save_campaign("campaign:the-crucible", "the-crucible", "The Crucible")
    repo.close()
    (tmp_path / "dungeon.json").write_text(
        _dungeon().model_dump_json(), encoding="utf-8"
    )
    return tmp_path


def _exit_count(db_path: Path) -> int:
    repo = MemoryRepository(db_path)
    try:
        rows = repo.get_exits_by_room("campaign:the-crucible", "room-a")
        rows += repo.get_exits_by_room("campaign:the-crucible", "room-b")
        return len(rows)
    finally:
        repo.close()


def test_backfill_creates_exits_from_connections(tmp_path):
    campaign_dir = _make_campaign_dir(tmp_path)
    assert _exit_count(campaign_dir / "campaign.duckdb") == 0

    _backfill_one(campaign_dir, dry_run=False, force=False)

    assert _exit_count(campaign_dir / "campaign.duckdb") == 2  # bidirectional


def test_backfill_dry_run_writes_nothing(tmp_path):
    campaign_dir = _make_campaign_dir(tmp_path)

    _backfill_one(campaign_dir, dry_run=True, force=False)

    assert _exit_count(campaign_dir / "campaign.duckdb") == 0


def test_backfill_is_idempotent(tmp_path):
    campaign_dir = _make_campaign_dir(tmp_path)
    _backfill_one(campaign_dir, dry_run=False, force=False)
    _backfill_one(campaign_dir, dry_run=False, force=False)

    assert _exit_count(campaign_dir / "campaign.duckdb") == 2

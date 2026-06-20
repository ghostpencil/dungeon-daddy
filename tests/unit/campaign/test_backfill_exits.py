"""Tests for self-healing exit backfill on load (pre-Phase-48 campaigns)."""
import json
from pathlib import Path

import pytest

from dungeon_daddy.campaign.backfill import backfill_exits_if_empty, refresh_exit_labels
from dungeon_daddy.data.models import Connection, Dungeon, DungeonMeta, Level, Room
from dungeon_daddy.memory.repository import MemoryRepository

_MIGRATIONS_DIR = Path("dungeon_daddy/data/migrations")
_CAMPAIGN_ID = "campaign:the-crucible"
_SLUG = "the-crucible"


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "campaign.duckdb")
    r.initialize_schema(_MIGRATIONS_DIR)
    yield r
    r.close()


def _room(room_id: str, num: int) -> Room:
    return Room(id=room_id, num=num, name=room_id, x=0, y=0, w=1, h=1, type="room", note="")


def _dungeon() -> Dungeon:
    connection = Connection.model_validate({"from": "room-a", "to": "room-b", "type": "door"})
    level = Level(
        id=1, name="Level One", summary="", ecology="", loop="",
        width=10, height=10, entries=[],
        rooms=[_room("room-a", 1), _room("room-b", 2)],
        connections=[connection],
    )
    meta = DungeonMeta(title="Test", theme="dark", setting="cave", party="heroes", quest="escape")
    return Dungeon(meta=meta, levels=[level])


def _write_dungeon(path: Path) -> None:
    path.write_text(json.dumps(_dungeon().model_dump(mode="json")), encoding="utf-8")


def test_backfills_exits_for_empty_campaign(repo: MemoryRepository, tmp_path: Path) -> None:
    repo.save_campaign(campaign_id=_CAMPAIGN_ID, slug=_SLUG, title="The Crucible")
    dungeon_path = tmp_path / "dungeon.json"
    _write_dungeon(dungeon_path)

    created = backfill_exits_if_empty(repo, dungeon_path)

    assert created == 2  # one bidirectional connection -> two exits
    assert len(repo.get_exits_by_room(_CAMPAIGN_ID, "room-a")) == 1
    assert len(repo.get_exits_by_room(_CAMPAIGN_ID, "room-b")) == 1


def test_noop_when_exits_already_present(repo: MemoryRepository, tmp_path: Path) -> None:
    repo.save_campaign(campaign_id=_CAMPAIGN_ID, slug=_SLUG, title="The Crucible")
    dungeon_path = tmp_path / "dungeon.json"
    _write_dungeon(dungeon_path)
    backfill_exits_if_empty(repo, dungeon_path)  # first pass populates

    created = backfill_exits_if_empty(repo, dungeon_path)  # second pass

    assert created == 0
    assert len(repo.get_exits_by_room(_CAMPAIGN_ID, "room-a")) == 1  # no duplicates


def test_noop_when_dungeon_file_missing(repo: MemoryRepository, tmp_path: Path) -> None:
    repo.save_campaign(campaign_id=_CAMPAIGN_ID, slug=_SLUG, title="The Crucible")

    created = backfill_exits_if_empty(repo, tmp_path / "absent.json")

    assert created == 0


def test_noop_when_no_campaign_row(repo: MemoryRepository, tmp_path: Path) -> None:
    dungeon_path = tmp_path / "dungeon.json"
    _write_dungeon(dungeon_path)

    created = backfill_exits_if_empty(repo, dungeon_path)

    assert created == 0


# --- refresh_exit_labels (label/exit_type only; never touches status) --------


def _exit_id(from_room: str, to_room: str) -> str:
    return f"exit:{_SLUG}:{from_room}:{to_room}"


def test_refresh_corrects_stale_label(repo: MemoryRepository, tmp_path: Path) -> None:
    repo.save_campaign(campaign_id=_CAMPAIGN_ID, slug=_SLUG, title="The Crucible")
    dungeon_path = tmp_path / "dungeon.json"
    _write_dungeon(dungeon_path)
    backfill_exits_if_empty(repo, dungeon_path)  # populates with correct labels
    # Corrupt one exit's label to simulate a pre-fix stale save.
    repo._conn.execute(
        "UPDATE room_exits SET label = ? WHERE exit_id = ?",
        ["WRONG", _exit_id("room-a", "room-b")],
    )

    updated = refresh_exit_labels(repo, dungeon_path)

    assert updated == 1
    row = repo.get_exit_by_id(_exit_id("room-a", "room-b"))
    assert row["label"] == "Door"


def test_refresh_preserves_runtime_status(repo: MemoryRepository, tmp_path: Path) -> None:
    repo.save_campaign(campaign_id=_CAMPAIGN_ID, slug=_SLUG, title="The Crucible")
    dungeon_path = tmp_path / "dungeon.json"
    _write_dungeon(dungeon_path)
    backfill_exits_if_empty(repo, dungeon_path)
    exit_id = _exit_id("room-a", "room-b")
    # Simulate runtime state changes: a stale label AND a locked->unlocked status.
    repo._conn.execute(
        "UPDATE room_exits SET label = ?, status = ? WHERE exit_id = ?",
        ["WRONG", "sealed", exit_id],
    )

    refresh_exit_labels(repo, dungeon_path)

    row = repo.get_exit_by_id(exit_id)
    assert row["label"] == "Door"      # label corrected
    assert row["status"] == "sealed"   # runtime status untouched


def test_refresh_noop_when_labels_already_correct(repo: MemoryRepository, tmp_path: Path) -> None:
    repo.save_campaign(campaign_id=_CAMPAIGN_ID, slug=_SLUG, title="The Crucible")
    dungeon_path = tmp_path / "dungeon.json"
    _write_dungeon(dungeon_path)
    backfill_exits_if_empty(repo, dungeon_path)

    updated = refresh_exit_labels(repo, dungeon_path)

    assert updated == 0


def test_refresh_does_not_create_missing_exits(repo: MemoryRepository, tmp_path: Path) -> None:
    repo.save_campaign(campaign_id=_CAMPAIGN_ID, slug=_SLUG, title="The Crucible")
    dungeon_path = tmp_path / "dungeon.json"
    _write_dungeon(dungeon_path)
    # Table left empty — refresh only updates existing rows.

    updated = refresh_exit_labels(repo, dungeon_path)

    assert updated == 0
    assert repo.get_exits_by_room(_CAMPAIGN_ID, "room-a") == []

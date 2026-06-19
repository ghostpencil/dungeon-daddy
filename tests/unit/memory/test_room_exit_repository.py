from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import RoomExit

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "test.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()


def _exit(
    exit_id: str = "exit:test:room-a:room-b",
    campaign_id: str = "campaign:test",
    from_room_id: str = "room:test:a",
    to_room_id: str = "room:test:b",
    level_id: str = "level:test:1",
    label: str = "North Door",
    status: str = "open",
) -> RoomExit:
    return RoomExit(
        exit_id=exit_id,
        campaign_id=campaign_id,
        from_room_id=from_room_id,
        to_room_id=to_room_id,
        level_id=level_id,
        label=label,
        status=status,
    )


def test_save_and_get_exits_by_room(repo: MemoryRepository) -> None:
    e = _exit()
    repo.save_room_exit(e)

    results = repo.get_exits_by_room("campaign:test", "room:test:a")
    assert len(results) == 1
    assert results[0]["exit_id"] == "exit:test:room-a:room-b"
    assert results[0]["to_room_id"] == "room:test:b"
    assert results[0]["label"] == "North Door"
    assert results[0]["status"] == "open"


def test_update_exit_status(repo: MemoryRepository) -> None:
    repo.save_room_exit(_exit(status="open"))
    repo.update_exit_status("exit:test:room-a:room-b", "locked")

    results = repo.get_exits_by_room("campaign:test", "room:test:a")
    assert results[0]["status"] == "locked"
